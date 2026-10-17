"""Report assignment workflow.

Reassignment closes the previous assignment row rather than overwriting it, so
the audit history is complete. Status is advanced from ``submitted``/
``under_review`` to ``assigned`` as part of the same transaction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.core.enums import (
    NotificationType,
    ReportPriority,
    ReportStatus,
    UserRole,
)
from app.core.exceptions import (
    NotFoundError,
    UnprocessableEntityError,
)
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.assignment import Assignment
from app.models.report import Report
from app.models.status_history import StatusHistory
from app.models.user import User
from app.services import notification_service

logger = get_logger(__name__)

__all__ = ["assign_worker", "list_my_assignments", "list_department_queue"]


def _close_active_assignments(db: Session, report_id: int) -> None:
    stmt = (
        update(Assignment)
        .where(
            and_(
                Assignment.report_id == report_id,
                Assignment.active.is_(True),
            )
        )
        .values(active=False, unassigned_at=utcnow())
    )
    db.execute(stmt)


def assign_worker(
    db: Session,
    *,
    report: Report,
    actor: User,
    worker_id: int,
    notes: str | None = None,
    priority: ReportPriority | None = None,
    deadline_at: datetime | None = None,
) -> Assignment:
    """Create a new active assignment and advance the report's state.

    ``priority`` and ``deadline_at`` are optional overrides set by the admin in
    the dispatch modal; when provided they are written onto the report as part
    of the same transaction.

    Raises
    ------
    NotFoundError
        Worker does not exist.
    UnprocessableEntityError
        Target account is not an active worker, or the department mismatches
        and the actor is not an admin.

    Re-dispatching a report to the worker it is already assigned to is allowed
    and treated idempotently: the active assignment is refreshed (the old row
    is closed and a new one opened for the audit trail) and any priority or
    deadline override is re-applied, so the "Re-dispatch" action always works.
    """
    worker: User | None = db.get(User, worker_id)
    if worker is None or not worker.is_active:
        raise NotFoundError("Worker not found.")
    if UserRole(worker.role) != UserRole.WORKER:
        raise UnprocessableEntityError(
            "Only accounts with the 'worker' role can be assigned reports."
        )

    actor_is_admin = UserRole(actor.role) == UserRole.ADMIN
    if report.department_id is not None and worker.department_id is not None:
        if worker.department_id != report.department_id and not actor_is_admin:
            raise UnprocessableEntityError(
                "Worker's department does not match the report's department."
            )

    # Re-dispatching to the same worker is intentionally NOT an error: the
    # admin may be refreshing the deadline/priority or re-sending the dispatch
    # notification. The active assignment is simply refreshed below.
    _close_active_assignments(db, report.id)

    assignment = Assignment(
        report_id=report.id,
        worker_id=worker.id,
        assigned_by_id=actor.id,
        department_id=worker.department_id or report.department_id,
        notes=notes,
        active=True,
    )
    db.add(assignment)

    previous_status = report.status
    report.assigned_worker_id = worker.id
    if worker.department_id is not None:
        report.department_id = worker.department_id

    # Optional dispatch-time overrides from the admin modal.
    if priority is not None:
        report.priority = priority
    if deadline_at is not None:
        # The datetime-local picker sends a timezone-less value; treat it as
        # UTC so the stored deadline is always tz-aware and never trips the
        # naive/aware comparison in the overdue checks.
        if deadline_at.tzinfo is None:
            deadline_at = deadline_at.replace(tzinfo=timezone.utc)
        report.deadline_at = deadline_at

    if report.status != ReportStatus.ASSIGNED:
        report.status = ReportStatus.ASSIGNED
        db.add(
            StatusHistory(
                report_id=report.id,
                old_status=previous_status,
                new_status=ReportStatus.ASSIGNED,
                changed_by_id=actor.id,
                note=f"Assigned to worker id={worker.id}",
            )
        )

    notification_service.create_notification(
        db,
        user_id=worker.id,
        notification_type=NotificationType.ASSIGNMENT,
        title="New report assignment",
        message=f"You have been assigned report #{report.id}: {report.title!r}.",
        report_id=report.id,
    )
    notification_service.create_notification(
        db,
        user_id=report.citizen_id,
        notification_type=NotificationType.ASSIGNMENT,
        title="Your report has been assigned",
        message=f"A worker has been assigned to your report #{report.id}.",
        report_id=report.id,
    )

    db.flush()
    logger.info(
        "Assignment created: report=%s worker=%s by=%s",
        report.id,
        worker.id,
        actor.id,
    )
    return assignment


def list_my_assignments(
    db: Session,
    *,
    worker: User,
    active_only: bool = True,
    offset: int = 0,
    limit: int = 20,
) -> Sequence[Assignment]:
    stmt = select(Assignment).where(Assignment.worker_id == worker.id)
    if active_only:
        stmt = stmt.where(Assignment.active.is_(True))
    stmt = (
        stmt.order_by(Assignment.assigned_at.desc(), Assignment.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


def list_department_queue(
    db: Session,
    *,
    department_id: int,
    offset: int = 0,
    limit: int = 20,
) -> Sequence[Report]:
    """Open reports routed to a given department, oldest-first."""
    open_statuses = (
        ReportStatus.SUBMITTED,
        ReportStatus.UNDER_REVIEW,
        ReportStatus.ASSIGNED,
        ReportStatus.IN_PROGRESS,
        ReportStatus.REOPENED,
    )
    stmt = (
        select(Report)
        .where(
            Report.department_id == department_id,
            Report.status.in_(open_statuses),
        )
        .order_by(Report.created_at.asc(), Report.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
