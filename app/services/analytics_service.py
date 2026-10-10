"""Admin analytics queries.

Aggregations are expressed in SQL so the DB does the summing, not Python.
Date boundaries are UTC; the metric definitions are documented in the schema
file.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy import Date, Select, cast, func, select
from sqlalchemy.orm import Session

from app.core.enums import ReportStatus
from app.db.base import utcnow
from app.models.department import Department
from app.models.report import Report

__all__ = [
    "overview",
    "reports_by_status",
    "reports_by_category",
    "reports_over_time",
    "department_performance",
    "overdue_reports",
]


_OPEN = (
    ReportStatus.SUBMITTED,
    ReportStatus.UNDER_REVIEW,
    ReportStatus.ASSIGNED,
    ReportStatus.IN_PROGRESS,
    ReportStatus.REOPENED,
)


def _apply_date_window(
    stmt: Select, *, date_from: datetime | None, date_to: datetime | None
) -> Select:
    if date_from is not None:
        stmt = stmt.where(Report.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Report.created_at <= date_to)
    return stmt


def _average_resolution_hours(
    db: Session, *, date_from: datetime | None, date_to: datetime | None
) -> float | None:
    stmt = select(Report.created_at, Report.resolved_at).where(
        Report.status == ReportStatus.RESOLVED,
        Report.resolved_at.is_not(None),
    )
    stmt = _apply_date_window(
        stmt, date_from=date_from, date_to=date_to
    )
    rows = db.execute(stmt).all()
    if not rows:
        return None
    totals = [
        (resolved - created).total_seconds() / 3600.0
        for created, resolved in rows
        if resolved is not None and created is not None
    ]
    if not totals:
        return None
    return round(sum(totals) / len(totals), 2)


def overview(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, int | float | None]:
    total_stmt = _apply_date_window(
        select(func.count()).select_from(Report),
        date_from=date_from,
        date_to=date_to,
    )
    open_stmt = _apply_date_window(
        select(func.count())
        .select_from(Report)
        .where(Report.status.in_(_OPEN)),
        date_from=date_from,
        date_to=date_to,
    )
    resolved_stmt = _apply_date_window(
        select(func.count())
        .select_from(Report)
        .where(Report.status == ReportStatus.RESOLVED),
        date_from=date_from,
        date_to=date_to,
    )
    rejected_stmt = _apply_date_window(
        select(func.count())
        .select_from(Report)
        .where(Report.status == ReportStatus.REJECTED),
        date_from=date_from,
        date_to=date_to,
    )
    now = utcnow()
    overdue_stmt = _apply_date_window(
        select(func.count())
        .select_from(Report)
        .where(
            Report.deadline_at.is_not(None),
            Report.deadline_at < now,
            Report.status.in_(_OPEN),
        ),
        date_from=date_from,
        date_to=date_to,
    )
    week_ago = now - timedelta(days=7)
    last_week_stmt = select(func.count()).select_from(Report).where(
        Report.created_at >= week_ago
    )

    return {
        "total_reports": int(db.execute(total_stmt).scalar_one()),
        "open_reports": int(db.execute(open_stmt).scalar_one()),
        "resolved_reports": int(db.execute(resolved_stmt).scalar_one()),
        "rejected_reports": int(db.execute(rejected_stmt).scalar_one()),
        "overdue_reports": int(db.execute(overdue_stmt).scalar_one()),
        "reports_last_7_days": int(db.execute(last_week_stmt).scalar_one()),
        "average_resolution_hours": _average_resolution_hours(
            db, date_from=date_from, date_to=date_to
        ),
    }


def reports_by_status(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, int | str]]:
    stmt = _apply_date_window(
        select(Report.status, func.count(Report.id)).group_by(Report.status),
        date_from=date_from,
        date_to=date_to,
    )
    rows = db.execute(stmt).all()
    return [
        {"status": status.value if hasattr(status, "value") else str(status),
         "count": int(count)}
        for status, count in rows
    ]


def reports_by_category(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, int | str]]:
    stmt = _apply_date_window(
        select(Report.category, func.count(Report.id)).group_by(
            Report.category
        ),
        date_from=date_from,
        date_to=date_to,
    )
    rows = db.execute(stmt).all()
    return [
        {"category": cat.value if hasattr(cat, "value") else str(cat),
         "count": int(count)}
        for cat, count in rows
    ]


def reports_over_time(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, date | int]]:
    day = cast(Report.created_at, Date).label("day")
    stmt = (
        _apply_date_window(
            select(day, func.count(Report.id)).group_by(day),
            date_from=date_from,
            date_to=date_to,
        )
        .order_by(day)
    )
    rows = db.execute(stmt).all()
    out: list[dict[str, date | int]] = []
    for d, count in rows:
        if isinstance(d, str):
            d = date.fromisoformat(d)
        out.append({"day": d, "count": int(count)})
    return out


def department_performance(db: Session) -> list[dict[str, object]]:
    totals_stmt = (
        select(
            Department.id.label("dep_id"),
            Department.name.label("dep_name"),
            func.count(Report.id).label("total"),
        )
        .select_from(Department)
        .join(Report, Report.department_id == Department.id, isouter=True)
        .group_by(Department.id, Department.name)
    )
    rows = db.execute(totals_stmt).all()

    now = utcnow()
    resolved_counts: dict[int, int] = {}
    overdue_counts: dict[int, int] = {}

    resolved_stmt = (
        select(Report.department_id, func.count(Report.id))
        .where(
            Report.department_id.is_not(None),
            Report.status == ReportStatus.RESOLVED,
        )
        .group_by(Report.department_id)
    )
    for dep_id, c in db.execute(resolved_stmt).all():
        resolved_counts[int(dep_id)] = int(c)

    overdue_stmt = (
        select(Report.department_id, func.count(Report.id))
        .where(
            Report.department_id.is_not(None),
            Report.deadline_at.is_not(None),
            Report.deadline_at < now,
            Report.status.in_(_OPEN),
        )
        .group_by(Report.department_id)
    )
    for dep_id, c in db.execute(overdue_stmt).all():
        overdue_counts[int(dep_id)] = int(c)

    out: list[dict[str, object]] = []
    for dep_id, dep_name, total in rows:
        dep_id_int = int(dep_id)
        resolved_rows = db.execute(
            select(Report.created_at, Report.resolved_at)
            .where(
                Report.department_id == dep_id_int,
                Report.status == ReportStatus.RESOLVED,
                Report.resolved_at.is_not(None),
            )
        ).all()
        avg_hours: float | None = None
        if resolved_rows:
            totals = [
                (r - c).total_seconds() / 3600.0
                for c, r in resolved_rows
                if r is not None and c is not None
            ]
            if totals:
                avg_hours = round(sum(totals) / len(totals), 2)
        out.append(
            {
                "department_id": dep_id_int,
                "department_name": str(dep_name),
                "total_reports": int(total),
                "resolved_reports": resolved_counts.get(dep_id_int, 0),
                "overdue_reports": overdue_counts.get(dep_id_int, 0),
                "average_resolution_hours": avg_hours,
            }
        )
    return out


def overdue_reports(db: Session, *, limit: int = 50) -> Sequence[Report]:
    now = utcnow()
    stmt = (
        select(Report)
        .where(
            Report.deadline_at.is_not(None),
            Report.deadline_at < now,
            Report.status.in_(_OPEN),
        )
        .order_by(Report.deadline_at.asc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
