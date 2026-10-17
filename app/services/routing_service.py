"""Auto-routing: pick a department and suggest the best worker.

Admin still confirms the assignment, but the triage work drops to one click.
The suggestion blends two signals:

* **Current workload**: a worker already carrying ten open assignments
  shouldn't be handed the eleventh.
* **Historical performance**: on-time rate from the resolved tail of their
  recent work.

A worker with no history yet starts at a neutral baseline, so new hires are
not permanently excluded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.enums import ReportCategory, ReportStatus, UserRole
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.department import Department
from app.models.report import Report
from app.models.user import User

logger = get_logger(__name__)

__all__ = ["WorkerSuggestion", "suggest_department", "suggest_worker"]


#: Default category -> department-name hints. Kept here so both services and
#: the frontend can import a canonical mapping.
#:
#: The service runs on three departments:
#:   * **Electrical** - street lamps, generators, wiring and any lighting/power
#:     issue.
#:   * **Plumbing**   - leaks, burst mains, leakage and drainage/water issues.
#:   * **General Works** - everything else: road damage, garbage, public
#:     property and anything uncategorised ("other").
#:
#: Each tuple lists the canonical name first, then older/synonym names so a
#: database that still carries the legacy departments keeps routing correctly.
CATEGORY_DEPARTMENT_HINTS: dict[ReportCategory, tuple[str, ...]] = {
    # Electrical
    ReportCategory.STREETLIGHT: (
        "Electrical", "Electrical & Lighting", "Lighting",
    ),
    # Plumbing (water + drainage)
    ReportCategory.WATER_LEAK: (
        "Plumbing", "Water & Sewerage Authority", "Water", "Water & Sewer",
    ),
    ReportCategory.DRAINAGE: (
        "Plumbing", "Water & Sewerage Authority", "Drainage", "Water & Sewer",
    ),
    # General Works (everything else)
    ReportCategory.ROAD_DAMAGE: (
        "General Works", "Roads & Infrastructure", "Roads & Pavements",
        "Roads", "Public Works",
    ),
    ReportCategory.GARBAGE: (
        "General Works", "Sanitation & Solid Waste", "Sanitation",
        "Waste Management",
    ),
    ReportCategory.PUBLIC_PROPERTY: (
        "General Works", "Parks & Public Property", "Parks",
        "Public Property",
    ),
    ReportCategory.OTHER: ("General Works",),
}


@dataclass(frozen=True, slots=True)
class WorkerSuggestion:
    worker_id: int
    worker_name: str
    department_id: int | None
    open_assignments: int
    recent_on_time_rate: float  # 0..1
    score: float  # 0..1 - higher is better


_OPEN_STATUSES = (
    ReportStatus.ASSIGNED,
    ReportStatus.IN_PROGRESS,
    ReportStatus.UNDER_REVIEW,
    ReportStatus.REOPENED,
)


def suggest_department(
    db: Session, *, category: ReportCategory
) -> Department | None:
    """Return the active department that best fits ``category``."""
    hints = CATEGORY_DEPARTMENT_HINTS.get(category)
    if not hints:
        return None
    stmt = (
        select(Department)
        .where(
            Department.is_active.is_(True),
            Department.name.in_(hints),
        )
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _open_counts(db: Session, worker_ids: Sequence[int]) -> dict[int, int]:
    if not worker_ids:
        return {}
    rows = db.execute(
        select(Report.assigned_worker_id, func.count(Report.id))
        .where(
            Report.assigned_worker_id.in_(worker_ids),
            Report.status.in_(_OPEN_STATUSES),
        )
        .group_by(Report.assigned_worker_id)
    ).all()
    return {int(r[0]): int(r[1]) for r in rows if r[0] is not None}


def _recent_on_time_rates(
    db: Session, worker_ids: Sequence[int], *, days: int = 60
) -> dict[int, float]:
    """On-time resolution rate in the last ``days``."""
    if not worker_ids:
        return {}
    cutoff = utcnow() - timedelta(days=days)
    stmt = select(
        Report.assigned_worker_id,
        Report.resolved_at,
        Report.deadline_at,
    ).where(
        and_(
            Report.assigned_worker_id.in_(worker_ids),
            Report.status == ReportStatus.RESOLVED,
            Report.resolved_at.is_not(None),
            Report.resolved_at >= cutoff,
        )
    )
    totals: dict[int, int] = {}
    on_time: dict[int, int] = {}
    for worker_id, resolved_at, deadline_at in db.execute(stmt).all():
        if worker_id is None or resolved_at is None:
            continue
        wid = int(worker_id)
        totals[wid] = totals.get(wid, 0) + 1
        # Treat "no deadline recorded" as on-time: can't penalise what wasn't
        # a commitment.
        if deadline_at is None or resolved_at <= deadline_at:
            on_time[wid] = on_time.get(wid, 0) + 1
    return {
        wid: (on_time.get(wid, 0) / count) if count else 1.0
        for wid, count in totals.items()
    }


def suggest_worker(
    db: Session,
    *,
    department: Department | None,
    exclude_worker_ids: Sequence[int] = (),
) -> WorkerSuggestion | None:
    """Pick the best worker for a report routed to ``department``.

    When ``department`` is ``None`` the pool is every active worker; this is
    the fallback admins use when triaging an "other" category manually.
    """
    stmt = select(User).where(
        User.role == UserRole.WORKER,
        User.is_active.is_(True),
    )
    if department is not None:
        stmt = stmt.where(User.department_id == department.id)
    if exclude_worker_ids:
        stmt = stmt.where(User.id.notin_(list(exclude_worker_ids)))

    workers: Sequence[User] = db.execute(stmt).scalars().all()
    if not workers:
        return None

    worker_ids = [w.id for w in workers]
    open_counts = _open_counts(db, worker_ids)
    on_time_rates = _recent_on_time_rates(db, worker_ids)
    max_open = max((open_counts.get(wid, 0) for wid in worker_ids), default=0)

    best: WorkerSuggestion | None = None
    for worker in workers:
        wid = worker.id
        open_count = open_counts.get(wid, 0)
        # Workload: fewer open assignments is better. 0 -> 1.0; max -> 0.0.
        workload_score = (
            1.0 - (open_count / max_open) if max_open > 0 else 1.0
        )
        on_time = on_time_rates.get(wid, 0.75)  # neutral baseline for new hires
        # Blend: workload is the stronger signal (prevent pile-ups), then
        # historical on-time reliability.
        score = 0.6 * workload_score + 0.4 * on_time

        candidate = WorkerSuggestion(
            worker_id=wid,
            worker_name=worker.full_name,
            department_id=worker.department_id,
            open_assignments=open_count,
            recent_on_time_rate=on_time,
            score=score,
        )
        if best is None or candidate.score > best.score:
            best = candidate

    return best
