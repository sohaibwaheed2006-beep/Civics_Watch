"""Report creation, retrieval, update and vote tallies.

Owns:
  - creation (with AI/duplicate/deadline hooks)
  - listing with filters
  - citizen-side editing and deletion
  - vote add/remove and tally

Status transitions live in :mod:`app.services.report_workflow_service` and are
NEVER triggered through a direct citizen patch.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import Select, and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import (
    NotificationType,
    ReportCategory,
    ReportPriority,
    ReportStatus,
    UserRole,
)
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.department import Department
from app.models.report import Report
from app.models.status_history import StatusHistory
from app.models.user import User
from app.models.vote import Vote
from app.schemas.report import ReportCreate, ReportModerate, ReportUpdate
from app.services import (
    ai_service,
    deadline_service,
    duplicate_detection_service,
    notification_service,
)

logger = get_logger(__name__)

__all__ = [
    "SORTABLE_FIELDS",
    "create_report",
    "get_report",
    "list_reports",
    "list_map",
    "list_history",
    "update_report",
    "moderate_report",
    "delete_report",
    "add_vote",
    "remove_vote",
    "vote_count",
    "has_voted",
    "find_duplicate_candidates",
]


SORTABLE_FIELDS: dict[str, object] = {
    "id": Report.id,
    "created_at": Report.created_at,
    "updated_at": Report.updated_at,
    "priority": Report.priority,
    "status": Report.status,
    "deadline_at": Report.deadline_at,
}
DEFAULT_SORT_FIELD = "created_at"


#: Default category->department name mapping. The service tolerates a missing
#: department: a report submitted before any routing is configured keeps a
#: null ``department_id`` and the admin triage queue picks it up.
_CATEGORY_DEPARTMENT_HINTS: dict[ReportCategory, tuple[str, ...]] = {
    ReportCategory.ROAD_DAMAGE: ("Roads & Pavements", "Roads"),
    ReportCategory.STREETLIGHT: ("Lighting", "Public Works"),
    ReportCategory.GARBAGE: ("Sanitation", "Waste Management"),
    ReportCategory.WATER_LEAK: ("Water", "Water & Sewer"),
    ReportCategory.DRAINAGE: ("Drainage", "Water & Sewer"),
    ReportCategory.PUBLIC_PROPERTY: ("Parks", "Public Property"),
}


def _route_department(
    db: Session, *, category: ReportCategory
) -> Department | None:
    hints = _CATEGORY_DEPARTMENT_HINTS.get(category)
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


def create_report(
    db: Session, *, actor: User, payload: ReportCreate
) -> Report:
    """Create a report, triggering AI/duplicate/deadline enrichment safely."""
    priority = ai_service.suggest_priority(
        category=payload.category,
        title=payload.title,
        description=payload.description,
    )
    department = _route_department(db, category=payload.category)
    deadline = deadline_service.compute_deadline(
        priority=priority, department=department
    )

    report = Report(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=priority,
        status=ReportStatus.SUBMITTED,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_text=payload.location_text,
        citizen_id=actor.id,
        department_id=department.id if department else None,
        deadline_at=deadline,
    )
    db.add(report)
    db.flush()  # we need report.id for the history and photo keys

    # Optional AI: must not fail the submission.
    try:
        suggestion = ai_service.suggest_category(
            payload.title, payload.description
        )
        if suggestion is not None:
            report.ai_category = suggestion.category.value
            report.ai_confidence = suggestion.confidence
    except Exception as exc:  # noqa: BLE001 - sanitised log, no re-raise
        logger.warning(
            "AI category step skipped: %s", type(exc).__name__
        )

    # Duplicate detection is also non-fatal.
    try:
        matches = duplicate_detection_service.find_duplicates(
            db,
            latitude=payload.latitude,
            longitude=payload.longitude,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            exclude_report_id=report.id,
            limit=1,
        )
        if matches:
            top = matches[0]
            report.duplicate_score = top.score
            report.duplicate_of_report_id = top.report.id
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Duplicate scan skipped: %s", type(exc).__name__
        )

    # Audit entry for the opening event.
    db.add(
        StatusHistory(
            report_id=report.id,
            old_status=None,
            new_status=ReportStatus.SUBMITTED,
            changed_by_id=actor.id,
            note="Report submitted.",
        )
    )

    notification_service.create_notification(
        db,
        user_id=actor.id,
        notification_type=NotificationType.REPORT_SUBMITTED,
        title="Report submitted",
        message=f"Your report #{report.id} has been received.",
        report_id=report.id,
    )

    db.commit()
    db.refresh(report)
    logger.info(
        "Report created id=%s citizen=%s category=%s priority=%s",
        report.id,
        actor.id,
        report.category.value,
        report.priority.value,
    )
    return report


def get_report(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report


def _vote_count_map(
    db: Session, report_ids: Sequence[int]
) -> dict[int, int]:
    if not report_ids:
        return {}
    stmt = (
        select(Vote.report_id, func.count(Vote.id))
        .where(Vote.report_id.in_(report_ids))
        .group_by(Vote.report_id)
    )
    return {row[0]: int(row[1]) for row in db.execute(stmt).all()}


def _apply_filters(
    stmt: Select,
    *,
    status: ReportStatus | None,
    category: ReportCategory | None,
    priority: ReportPriority | None,
    department_id: int | None,
    assigned_worker_id: int | None,
    citizen_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    bbox: tuple[float, float, float, float] | None,
) -> Select:
    if status is not None:
        stmt = stmt.where(Report.status == status)
    if category is not None:
        stmt = stmt.where(Report.category == category)
    if priority is not None:
        stmt = stmt.where(Report.priority == priority)
    if department_id is not None:
        stmt = stmt.where(Report.department_id == department_id)
    if assigned_worker_id is not None:
        stmt = stmt.where(Report.assigned_worker_id == assigned_worker_id)
    if citizen_id is not None:
        stmt = stmt.where(Report.citizen_id == citizen_id)
    if date_from is not None:
        stmt = stmt.where(Report.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Report.created_at <= date_to)
    if bbox is not None:
        min_lat, min_lon, max_lat, max_lon = bbox
        stmt = stmt.where(
            and_(
                Report.latitude >= min_lat,
                Report.latitude <= max_lat,
                Report.longitude >= min_lon,
                Report.longitude <= max_lon,
            )
        )
    return stmt


def list_reports(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 20,
    status: ReportStatus | None = None,
    category: ReportCategory | None = None,
    priority: ReportPriority | None = None,
    department_id: int | None = None,
    assigned_worker_id: int | None = None,
    citizen_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    sort_by: str | None = None,
    descending: bool = True,
) -> tuple[Sequence[Report], int, dict[int, int]]:
    """Paginated list + total count + vote counts for the current page."""
    base = _apply_filters(
        select(Report),
        status=status,
        category=category,
        priority=priority,
        department_id=department_id,
        assigned_worker_id=assigned_worker_id,
        citizen_id=citizen_id,
        date_from=date_from,
        date_to=date_to,
        bbox=bbox,
    )
    count_stmt = _apply_filters(
        select(func.count()).select_from(Report),
        status=status,
        category=category,
        priority=priority,
        department_id=department_id,
        assigned_worker_id=assigned_worker_id,
        citizen_id=citizen_id,
        date_from=date_from,
        date_to=date_to,
        bbox=bbox,
    )

    column = SORTABLE_FIELDS.get(sort_by or DEFAULT_SORT_FIELD)
    if column is None:
        column = SORTABLE_FIELDS[DEFAULT_SORT_FIELD]
    order = column.desc() if descending else column.asc()  # type: ignore[union-attr]

    items = (
        db.execute(
            base.order_by(order, Report.id.desc()).offset(offset).limit(limit)
        )
        .scalars()
        .all()
    )
    total = int(db.execute(count_stmt).scalar_one())
    votes = _vote_count_map(db, [r.id for r in items])
    return items, total, votes


def list_map(
    db: Session,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    status: ReportStatus | None = None,
    category: ReportCategory | None = None,
    limit: int = 500,
) -> Sequence[Report]:
    stmt = _apply_filters(
        select(Report),
        status=status,
        category=category,
        priority=None,
        department_id=None,
        assigned_worker_id=None,
        citizen_id=None,
        date_from=None,
        date_to=None,
        bbox=bbox,
    )
    stmt = stmt.order_by(Report.id.desc()).limit(limit)
    return db.execute(stmt).scalars().all()


def list_history(db: Session, *, report_id: int) -> Sequence[StatusHistory]:
    stmt = (
        select(StatusHistory)
        .where(StatusHistory.report_id == report_id)
        .order_by(StatusHistory.created_at.asc(), StatusHistory.id.asc())
    )
    return db.execute(stmt).scalars().all()


def _citizen_can_edit(report: Report) -> bool:
    """A citizen can only amend their report while it is still ``submitted``."""
    return report.status == ReportStatus.SUBMITTED


def update_report(
    db: Session, *, actor: User, report_id: int, payload: ReportUpdate
) -> Report:
    """Owner-side edit. Only during the ``submitted`` window."""
    report = get_report(db, report_id)
    if report.citizen_id != actor.id and UserRole(actor.role) != UserRole.ADMIN:
        raise PermissionDeniedError(
            "You can only edit your own reports."
        )
    if UserRole(actor.role) != UserRole.ADMIN and not _citizen_can_edit(report):
        raise ConflictError(
            "Reports can only be edited while they are still 'submitted'."
        )

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(report, field, value)
    db.commit()
    db.refresh(report)
    return report


def moderate_report(
    db: Session, *, admin: User, report_id: int, payload: ReportModerate
) -> Report:
    """Admin-only priority/department/note override.

    Does NOT change status (that path lives in the workflow service), so no
    citizen patch can indirectly flip the state.
    """
    if UserRole(admin.role) != UserRole.ADMIN:
        raise PermissionDeniedError("Only admins may moderate reports.")
    report = get_report(db, report_id)
    changes = payload.model_dump(exclude_unset=True)
    note = changes.pop("note", None)

    if "department_id" in changes:
        dep_id = changes["department_id"]
        if dep_id is not None:
            department = db.get(Department, dep_id)
            if department is None or not department.is_active:
                raise NotFoundError("Department not found.")
        report.department_id = dep_id
        # Reroute deadline if priority also changed, otherwise keep it.

    if "priority" in changes:
        report.priority = changes["priority"]
        new_deadline = deadline_service.compute_deadline(
            priority=report.priority, department=report.department
        )
        report.deadline_at = new_deadline

    if note:
        db.add(
            StatusHistory(
                report_id=report.id,
                old_status=report.status,
                new_status=report.status,
                changed_by_id=admin.id,
                note=note,
            )
        )

    db.commit()
    db.refresh(report)
    return report


def delete_report(db: Session, *, actor: User, report_id: int) -> None:
    """Delete a report.

    Admins may always delete; citizens may delete their own report only while
    it is still ``submitted``.
    """
    report = get_report(db, report_id)
    role = UserRole(actor.role)
    if role != UserRole.ADMIN:
        if report.citizen_id != actor.id:
            raise PermissionDeniedError(
                "You can only delete your own reports."
            )
        if not _citizen_can_edit(report):
            raise ConflictError(
                "Reports can only be deleted while they are still 'submitted'."
            )
    db.delete(report)
    db.commit()


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------
def vote_count(db: Session, *, report_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Vote)
        .where(Vote.report_id == report_id)
    )
    return int(db.execute(stmt).scalar_one())


def has_voted(db: Session, *, report_id: int, user_id: int) -> bool:
    stmt = (
        select(func.count())
        .select_from(Vote)
        .where(Vote.report_id == report_id, Vote.user_id == user_id)
    )
    return bool(db.execute(stmt).scalar_one())


def add_vote(db: Session, *, report_id: int, user: User) -> int:
    """Idempotent upvote. Returns the current vote count."""
    report = get_report(db, report_id)
    if report.citizen_id == user.id:
        raise PermissionDeniedError("You cannot vote on your own report.")

    try:
        db.add(Vote(report_id=report.id, user_id=user.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        # Already voted - treat as success.
    return vote_count(db, report_id=report.id)


def remove_vote(db: Session, *, report_id: int, user: User) -> int:
    """Idempotent down-vote (vote removal). Returns the current vote count."""
    get_report(db, report_id)  # 404 if the report is gone
    stmt = select(Vote).where(
        Vote.report_id == report_id, Vote.user_id == user.id
    )
    vote = db.execute(stmt).scalar_one_or_none()
    if vote is not None:
        db.delete(vote)
        db.commit()
    return vote_count(db, report_id=report_id)


def find_duplicate_candidates(
    db: Session, *, report_id: int, limit: int = 5
) -> list[duplicate_detection_service.DuplicateMatch]:
    report = get_report(db, report_id)
    return duplicate_detection_service.find_duplicates(
        db,
        latitude=report.latitude,
        longitude=report.longitude,
        title=report.title,
        description=report.description,
        category=report.category,
        exclude_report_id=report.id,
        limit=limit,
    )
