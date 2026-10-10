"""Report lifecycle (status transition) service.

The transition matrix is enforced in exactly one place: this module. Routes
never mutate ``report.status`` directly.

Matrix
------
    submitted      -> under_review, rejected
    under_review   -> assigned, rejected
    assigned       -> in_progress, under_review
    in_progress    -> resolved, assigned
    resolved       -> reopened
    rejected       -> under_review          (admin only)
    reopened       -> under_review, assigned, in_progress

Permissions
-----------
    citizen owner: resolved -> reopened (own report only)
    worker:        on their active assignment, within allowed transitions
    admin:         any transition in the matrix
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import NotificationType, ReportStatus, UserRole
from app.core.exceptions import ConflictError, PermissionDeniedError
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.report import Report
from app.models.status_history import StatusHistory
from app.models.user import User
from app.services import notification_service

logger = get_logger(__name__)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "transition",
    "record_initial_status",
]


#: The authoritative transition matrix. Keyed by current status.
ALLOWED_TRANSITIONS: dict[ReportStatus, frozenset[ReportStatus]] = {
    ReportStatus.SUBMITTED: frozenset(
        {ReportStatus.UNDER_REVIEW, ReportStatus.REJECTED}
    ),
    ReportStatus.UNDER_REVIEW: frozenset(
        {ReportStatus.ASSIGNED, ReportStatus.REJECTED, ReportStatus.IN_PROGRESS}
    ),
    ReportStatus.ASSIGNED: frozenset(
        {ReportStatus.IN_PROGRESS, ReportStatus.UNDER_REVIEW}
    ),
    ReportStatus.IN_PROGRESS: frozenset(
        {ReportStatus.RESOLVED, ReportStatus.ASSIGNED}
    ),
    ReportStatus.RESOLVED: frozenset({ReportStatus.REOPENED}),
    ReportStatus.REJECTED: frozenset({ReportStatus.UNDER_REVIEW}),
    ReportStatus.REOPENED: frozenset(
        {
            ReportStatus.UNDER_REVIEW,
            ReportStatus.ASSIGNED,
            ReportStatus.IN_PROGRESS,
        }
    ),
}


def _check_permission(
    *, actor: User, report: Report, new_status: ReportStatus
) -> None:
    role = UserRole(actor.role)
    if role == UserRole.ADMIN:
        return

    if role == UserRole.CITIZEN:
        # The only transition a citizen may request is reopening their own report.
        if (
            report.citizen_id == actor.id
            and report.status == ReportStatus.RESOLVED
            and new_status == ReportStatus.REOPENED
        ):
            return
        raise PermissionDeniedError(
            "Citizens may only reopen their own resolved reports."
        )

    if role == UserRole.WORKER:
        # Workers may act only on their current assignment and may not reject.
        if report.assigned_worker_id != actor.id:
            raise PermissionDeniedError(
                "You can only update reports assigned to you."
            )
        if new_status == ReportStatus.REJECTED:
            raise PermissionDeniedError(
                "Only administrators may reject reports."
            )
        return

    raise PermissionDeniedError("Not permitted to change report status.")


def record_initial_status(
    db: Session, *, report: Report, actor: User, note: str | None = None
) -> StatusHistory:
    """Add the opening history entry for a brand-new report."""
    event = StatusHistory(
        report_id=report.id,
        old_status=None,
        new_status=report.status,
        changed_by_id=actor.id,
        note=note,
    )
    db.add(event)
    db.flush()
    return event


def transition(
    db: Session,
    *,
    report: Report,
    actor: User,
    new_status: ReportStatus,
    note: str | None = None,
) -> Report:
    """Transition ``report`` to ``new_status`` atomically.

    Writes the history row and (when applicable) a notification in the same
    transaction. The caller must still commit; keeping the boundary at the
    service layer above makes larger composite operations possible.
    """
    if report.status == new_status:
        raise ConflictError(
            f"Report is already in status {new_status.value!r}."
        )

    allowed = ALLOWED_TRANSITIONS.get(report.status, frozenset())
    if new_status not in allowed:
        raise ConflictError(
            f"Cannot transition from {report.status.value!r} to "
            f"{new_status.value!r}."
        )

    _check_permission(actor=actor, report=report, new_status=new_status)

    old_status = report.status
    report.status = new_status

    if new_status == ReportStatus.RESOLVED:
        report.resolved_at = utcnow()
    elif new_status == ReportStatus.REOPENED:
        report.resolved_at = None

    db.add(
        StatusHistory(
            report_id=report.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=actor.id,
            note=note,
        )
    )

    # Fan out notifications to interested parties. These share the current
    # transaction - a committed status change is never silently un-notified.
    _notify_status_change(
        db,
        report=report,
        actor=actor,
        old_status=old_status,
        new_status=new_status,
    )

    db.flush()
    logger.info(
        "Report id=%s status %s -> %s by user=%s",
        report.id,
        old_status.value,
        new_status.value,
        actor.id,
    )
    return report


def _notify_status_change(
    db: Session,
    *,
    report: Report,
    actor: User,
    old_status: ReportStatus,
    new_status: ReportStatus,
) -> None:
    message = (
        f"Report #{report.id} ({report.title!r}) moved from "
        f"{old_status.value} to {new_status.value}."
    )

    if new_status == ReportStatus.RESOLVED:
        notification_service.create_notification(
            db,
            user_id=report.citizen_id,
            notification_type=NotificationType.RESOLVED,
            title="Your report has been resolved",
            message=message,
            report_id=report.id,
        )
    elif new_status == ReportStatus.REJECTED:
        notification_service.create_notification(
            db,
            user_id=report.citizen_id,
            notification_type=NotificationType.REJECTED,
            title="Your report has been rejected",
            message=message,
            report_id=report.id,
        )
    elif new_status == ReportStatus.REOPENED:
        if report.assigned_worker_id is not None:
            notification_service.create_notification(
                db,
                user_id=report.assigned_worker_id,
                notification_type=NotificationType.REOPENED,
                title="Report reopened",
                message=message,
                report_id=report.id,
            )
    else:
        notification_service.create_notification(
            db,
            user_id=report.citizen_id,
            notification_type=NotificationType.STATUS_CHANGED,
            title="Report status updated",
            message=message,
            report_id=report.id,
        )
