"""Worker performance scoring + monthly "worker of the month" bonus.

Every month the admin triggers (or a scheduled task triggers) ``award_month``.
The service aggregates, per worker, every report they resolved in the window
and combines three signals:

* **Average citizen rating** (1..5, scaled to 0..1).
* **Speed**: average resolve time versus deadline. On-time + under-SLA scores
  higher; blown deadlines pull it down.
* **Volume**: number of resolved reports, scaled against the top worker's
  count that month, so a quiet month does not reward zero work.

Weights live in settings and must sum to 1. The winner is persisted as a
``WorkerBonus`` row (idempotent on year+month) and a notification is sent to
the winning worker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import NotificationType, ReportStatus, UserRole
from app.core.exceptions import ConflictError
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.report import Report
from app.models.review import Review
from app.models.user import User
from app.models.worker_bonus import WorkerBonus
from app.services import notification_service

logger = get_logger(__name__)

__all__ = [
    "WorkerScore",
    "month_bounds",
    "compute_worker_scores",
    "award_month",
    "get_bonus_for_month",
    "list_recent_bonuses",
]


@dataclass(frozen=True, slots=True)
class WorkerScore:
    worker_id: int
    worker_name: str
    resolved_count: int
    average_rating: float  # 0..5 (0 when no ratings)
    average_hours_to_resolve: float | None
    on_time_rate: float  # 0..1
    total_score: float  # 0..1


def month_bounds(*, year: int, month: int) -> tuple[datetime, datetime]:
    """Inclusive-start, exclusive-end UTC bounds for the given calendar month."""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _speed_score(hours: float | None, on_time: bool) -> float:
    """Normalize resolve speed into a 0..1 score.

    A sub-24h fix earns 1.0, a one-week fix ~0.0; missing the deadline halves
    whatever that curve returned.
    """
    if hours is None:
        return 0.0
    hours = max(0.0, hours)
    # Linear-ish decay: 0h -> 1.0, 168h (one week) -> 0.0, floor at 0.
    curve = max(0.0, 1.0 - (hours / 168.0))
    return curve if on_time else curve * 0.5


def compute_worker_scores(
    db: Session, *, period_start: datetime, period_end: datetime
) -> list[WorkerScore]:
    """Aggregate resolved-in-period reports per worker and score them."""
    settings = get_settings()

    stmt = (
        select(Report)
        .where(
            Report.status == ReportStatus.RESOLVED,
            Report.resolved_at.is_not(None),
            Report.resolved_at >= period_start,
            Report.resolved_at < period_end,
            Report.assigned_worker_id.is_not(None),
        )
    )
    resolved: Sequence[Report] = db.execute(stmt).scalars().all()
    if not resolved:
        return []

    # Group by worker.
    by_worker: dict[int, list[Report]] = {}
    for report in resolved:
        wid = report.assigned_worker_id
        if wid is None:
            continue
        by_worker.setdefault(wid, []).append(report)

    # Fetch reviews for the period's reports in one shot.
    report_ids = [r.id for r in resolved]
    rating_rows = db.execute(
        select(Review.worker_id, func.avg(Review.rating))
        .where(Review.report_id.in_(report_ids))
        .group_by(Review.worker_id)
    ).all()
    avg_rating_by_worker: dict[int, float] = {
        int(row[0]): float(row[1] or 0.0) for row in rating_rows
    }

    # Fetch display names for the surviving workers.
    worker_rows = db.execute(
        select(User.id, User.full_name).where(User.id.in_(list(by_worker.keys())))
    ).all()
    names: dict[int, str] = {int(r[0]): str(r[1]) for r in worker_rows}

    scores: list[WorkerScore] = []
    max_volume = max(len(reports) for reports in by_worker.values()) or 1

    for worker_id, reports in by_worker.items():
        # Average resolution time (hours) + on-time rate.
        durations: list[float] = []
        on_time_hits = 0
        on_time_total = 0
        for report in reports:
            if report.resolved_at is None:
                continue
            created = report.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            resolved_at = report.resolved_at
            if resolved_at.tzinfo is None:
                resolved_at = resolved_at.replace(tzinfo=timezone.utc)
            durations.append((resolved_at - created).total_seconds() / 3600.0)
            if report.deadline_at is not None:
                deadline = report.deadline_at
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                on_time_total += 1
                if resolved_at <= deadline:
                    on_time_hits += 1

        avg_hours = sum(durations) / len(durations) if durations else None
        on_time_rate = (on_time_hits / on_time_total) if on_time_total else 1.0
        avg_rating = avg_rating_by_worker.get(worker_id, 0.0)

        # Combine. Each sub-score lives in 0..1; weights sum to 1 (validated).
        rating_component = (avg_rating / 5.0) if avg_rating > 0 else 0.0
        speed_component = _speed_score(avg_hours, on_time_rate >= 0.5)
        volume_component = len(reports) / max_volume

        total = (
            settings.BONUS_WEIGHT_RATING * rating_component
            + settings.BONUS_WEIGHT_SPEED * speed_component
            + settings.BONUS_WEIGHT_VOLUME * volume_component
        )

        scores.append(
            WorkerScore(
                worker_id=worker_id,
                worker_name=names.get(worker_id, f"Worker #{worker_id}"),
                resolved_count=len(reports),
                average_rating=avg_rating,
                average_hours_to_resolve=avg_hours,
                on_time_rate=on_time_rate,
                total_score=total,
            )
        )

    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores


def get_bonus_for_month(
    db: Session, *, year: int, month: int
) -> WorkerBonus | None:
    stmt = select(WorkerBonus).where(
        WorkerBonus.period_year == year,
        WorkerBonus.period_month == month,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_recent_bonuses(
    db: Session, *, limit: int = 12
) -> Sequence[WorkerBonus]:
    stmt = (
        select(WorkerBonus)
        .order_by(
            WorkerBonus.period_year.desc(),
            WorkerBonus.period_month.desc(),
        )
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def award_month(
    db: Session, *, year: int, month: int, overwrite: bool = False
) -> WorkerBonus | None:
    """Score the given month and persist the winning worker.

    Returns the persisted ``WorkerBonus`` row, or ``None`` if there was no
    resolved work in the window. Raises :class:`ConflictError` when an award
    already exists and ``overwrite`` is False.
    """
    existing = get_bonus_for_month(db, year=year, month=month)
    if existing is not None and not overwrite:
        raise ConflictError(
            f"A bonus for {year}-{month:02d} is already recorded."
        )

    start, end = month_bounds(year=year, month=month)
    scores = compute_worker_scores(db, period_start=start, period_end=end)
    if not scores:
        logger.info("No resolved work in %s-%02d; no bonus awarded.", year, month)
        return None

    top = scores[0]
    if existing is not None:
        existing.worker_id = top.worker_id
        existing.resolved_count = top.resolved_count
        existing.average_rating = top.average_rating
        existing.average_hours_to_resolve = top.average_hours_to_resolve
        existing.on_time_rate = top.on_time_rate
        existing.total_score = top.total_score
        bonus = existing
    else:
        bonus = WorkerBonus(
            period_year=year,
            period_month=month,
            worker_id=top.worker_id,
            resolved_count=top.resolved_count,
            average_rating=top.average_rating,
            average_hours_to_resolve=top.average_hours_to_resolve,
            on_time_rate=top.on_time_rate,
            total_score=top.total_score,
        )
        db.add(bonus)

    notification_service.create_notification(
        db,
        user_id=top.worker_id,
        notification_type=NotificationType.STATUS_CHANGED,
        title=f"Worker of the month: {year}-{month:02d}",
        message=(
            f"Congratulations - you were selected as worker of the month "
            f"for {year}-{month:02d} with a performance score of "
            f"{top.total_score:.2f}."
        ),
        report_id=None,
    )
    db.commit()
    db.refresh(bonus)
    logger.info(
        "Awarded bonus for %s-%02d to worker %s (score=%.3f)",
        year,
        month,
        top.worker_id,
        top.total_score,
    )
    return bonus


def previous_month(now: datetime | None = None) -> tuple[int, int]:
    """Return the (year, month) of the month before ``now`` (UTC)."""
    reference = now or utcnow()
    first_of_this = reference.replace(day=1)
    last_of_prev = first_of_this - timedelta(days=1)
    return last_of_prev.year, last_of_prev.month
