"""Report assignment workflow.

Reassignment closes the previous assignment row rather than overwriting it, so
the audit history is complete. Status is advanced from ``submitted``/
``under_review`` to ``assigned`` as part of the same transaction.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.core.enums import (
    NotificationType,
    ReportStatus,
    UserRole,
)
from app.core.exceptions import (
    ConflictError,
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
) -> Assignment:
    """Create a new active assignment and advance the report's state.

    Raises
    ------
    NotFoundError
        Worker does not exist.
    UnprocessableEntityError
        Target account is not an active worker, or the department mismatches
        and the actor is not an admin.
    ConflictError
        Report is already assigned to this worker.
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

    if (
        report.assigned_worker_id == worker.id
        and report.status == ReportStatus.ASSIGNED
    ):
        raise ConflictError("Report is already assigned to this worker.")

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
