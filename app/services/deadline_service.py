"""Deadline / SLA computation.

Deadline comes from the department's ``default_sla_hours`` scaled by priority:

    urgent  -> 0.25x (very fast)
    high    -> 0.5x
    medium  -> 1.0x  (baseline)
    low     -> 2.0x

All times UTC. Pure functions - no DB access - so this is trivial to test.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.enums import ReportPriority, ReportStatus
from app.db.base import utcnow
from app.models.department import DEFAULT_SLA_HOURS, Department
from app.models.report import Report

__all__ = [
    "PRIORITY_SLA_MULTIPLIER",
    "compute_deadline",
    "is_overdue",
    "list_overdue_reports",
]


#: Multiplicative adjustment applied to the department SLA. Kept here so a
#: policy tweak is a one-line change, auditable in git.
PRIORITY_SLA_MULTIPLIER: dict[ReportPriority, float] = {
    ReportPriority.URGENT: 0.25,
    ReportPriority.HIGH: 0.5,
    ReportPriority.MEDIUM: 1.0,
    ReportPriority.LOW: 2.0,
}


#: Statuses that still count as "open" when identifying overdue reports.
_OPEN_STATUSES: tuple[ReportStatus, ...] = (
    ReportStatus.SUBMITTED,
    ReportStatus.UNDER_REVIEW,
    ReportStatus.ASSIGNED,
    ReportStatus.IN_PROGRESS,
    ReportStatus.REOPENED,
)


def compute_deadline(
    *,
    priority: ReportPriority,
    department: Department | None,
    reference_time: datetime | None = None,
) -> datetime:
    """Deadline for a report with the given priority and routed department."""
    base_hours = (
        department.default_sla_hours if department is not None else DEFAULT_SLA_HOURS
    )
    multiplier = PRIORITY_SLA_MULTIPLIER.get(priority, 1.0)
    hours = max(1, int(round(base_hours * multiplier)))
    reference = reference_time or utcnow()
    return reference + timedelta(hours=hours)


def is_overdue(report: Report, *, now: datetime | None = None) -> bool:
    if report.deadline_at is None:
        return False
    if report.status in {
        ReportStatus.RESOLVED,
        ReportStatus.REJECTED,
    }:
        return False
    return (now or utcnow()) > report.deadline_at


def list_overdue_reports(
    db: Session, *, limit: int = 100
) -> Sequence[Report]:
    """Open reports whose ``deadline_at`` is in the past."""
    now = utcnow()
    stmt = (
        select(Report)
        .where(
            and_(
                Report.deadline_at.is_not(None),
                Report.deadline_at < now,
                Report.status.in_(_OPEN_STATUSES),
            )
        )
        .order_by(Report.deadline_at.asc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
