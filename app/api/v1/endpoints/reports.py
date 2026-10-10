"""Report endpoints.

Mounted under ``/reports``. Status transitions and assignments live in their
own routers that are mounted alongside this one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import (
    AdminUser,
    CurrentUser,
    DbSession,
    PaginationDep,
    require_roles,
)
from app.core.enums import (
    ReportCategory,
    ReportPriority,
    ReportStatus,
    UserRole,
)
from app.core.exceptions import PermissionDeniedError
from app.schemas.common import ErrorResponse, MessageResponse, Page
from app.schemas.report import (
    DuplicateCandidate,
    ReportCreate,
    ReportMapMarker,
    ReportModerate,
    ReportRead,
    ReportStatusUpdate,
    ReportSummary,
    ReportUpdate,
)
from app.schemas.status_history import StatusHistoryRead
from app.services import report_service, report_workflow_service

router = APIRouter()

_AUTH_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Missing, malformed or expired token.",
    }
}

Bbox = Annotated[
    str | None,
    Query(
        description=(
            "Bounding box filter 'min_lat,min_lon,max_lat,max_lon' in decimal "
            "degrees."
        )
    ),
]


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if bbox is None:
        return None
    try:
        parts = [float(p.strip()) for p in bbox.split(",")]
    except ValueError:
        return None
    if len(parts) != 4:
        return None
    return (parts[0], parts[1], parts[2], parts[3])


def _to_summary(report, vote_count: int) -> ReportSummary:
    return ReportSummary(
        id=report.id,
        title=report.title,
        category=report.category,
        priority=report.priority,
        status=report.status,
        latitude=report.latitude,
        longitude=report.longitude,
        citizen_id=report.citizen_id,
        department_id=report.department_id,
        assigned_worker_id=report.assigned_worker_id,
        created_at=report.created_at,
        updated_at=report.updated_at,
        deadline_at=report.deadline_at,
        resolved_at=report.resolved_at,
        vote_count=vote_count,
    )


def _to_read(report, vote_count: int) -> ReportRead:
    return ReportRead(
        id=report.id,
        title=report.title,
        description=report.description,
        category=report.category,
        priority=report.priority,
        status=report.status,
        latitude=report.latitude,
        longitude=report.longitude,
        location_text=report.location_text,
        citizen_id=report.citizen_id,
        department_id=report.department_id,
        assigned_worker_id=report.assigned_worker_id,
        created_at=report.created_at,
        updated_at=report.updated_at,
        deadline_at=report.deadline_at,
        resolved_at=report.resolved_at,
        ai_category=report.ai_category,
        ai_confidence=report.ai_confidence,
        duplicate_score=report.duplicate_score,
        duplicate_of_report_id=report.duplicate_of_report_id,
        vote_count=vote_count,
    )


# ---------------------------------------------------------------------------
# Create / list / get
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a report",
    responses=_AUTH_ERRORS,
)
def create_report(
    db: DbSession, current_user: CurrentUser, payload: ReportCreate
) -> ReportRead:
    report = report_service.create_report(db, actor=current_user, payload=payload)
    return _to_read(report, vote_count=0)


@router.get(
    "",
    response_model=Page[ReportSummary],
    status_code=status.HTTP_200_OK,
    summary="List reports",
    responses=_AUTH_ERRORS,
)
def list_reports(
    db: DbSession,
    current_user: CurrentUser,
    pagination: PaginationDep,
    status_filter: Annotated[ReportStatus | None, Query(alias="status")] = None,
    category: Annotated[ReportCategory | None, Query()] = None,
    priority: Annotated[ReportPriority | None, Query()] = None,
    department_id: Annotated[int | None, Query(ge=1)] = None,
    assigned_worker_id: Annotated[int | None, Query(ge=1)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    bbox: Bbox = None,
) -> Page[ReportSummary]:
    role = UserRole(current_user.role)
    # Workers see their own queue by default; admins see everything.
    citizen_scope: int | None = None
    if role == UserRole.CITIZEN:
        citizen_scope = current_user.id
    elif role == UserRole.WORKER and assigned_worker_id is None:
        assigned_worker_id = current_user.id

    items, total, votes = report_service.list_reports(
        db,
        offset=pagination.offset,
        limit=pagination.limit,
        status=status_filter,
        category=category,
        priority=priority,
        department_id=department_id,
        assigned_worker_id=assigned_worker_id,
        citizen_id=citizen_scope,
        date_from=date_from,
        date_to=date_to,
        bbox=_parse_bbox(bbox),
        sort_by=pagination.sort_by,
        descending=pagination.descending,
    )
    return Page[ReportSummary].create(
        items=[_to_summary(r, votes.get(r.id, 0)) for r in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


@router.get(
    "/my",
    response_model=Page[ReportSummary],
    status_code=status.HTTP_200_OK,
    summary="List my reports",
    responses=_AUTH_ERRORS,
)
def list_my_reports(
    db: DbSession,
    current_user: CurrentUser,
    pagination: PaginationDep,
) -> Page[ReportSummary]:
    items, total, votes = report_service.list_reports(
        db,
        offset=pagination.offset,
        limit=pagination.limit,
        citizen_id=current_user.id,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
    )
    return Page[ReportSummary].create(
        items=[_to_summary(r, votes.get(r.id, 0)) for r in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


@router.get(
    "/map",
    response_model=list[ReportMapMarker],
    status_code=status.HTTP_200_OK,
    summary="Map markers",
    responses=_AUTH_ERRORS,
)
def list_map(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: Annotated[ReportStatus | None, Query(alias="status")] = None,
    category: Annotated[ReportCategory | None, Query()] = None,
    bbox: Bbox = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> list[ReportMapMarker]:
    items = report_service.list_map(
        db,
        bbox=_parse_bbox(bbox),
        status=status_filter,
        category=category,
        limit=limit,
    )
    return [
        ReportMapMarker(
            id=r.id,
            category=r.category,
            status=r.status,
            priority=r.priority,
            latitude=r.latitude,
            longitude=r.longitude,
        )
        for r in items
    ]


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    status_code=status.HTTP_200_OK,
    summary="Get a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def get_report(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> ReportRead:
    report = report_service.get_report(db, report_id)
    role = UserRole(current_user.role)
    # Citizens can see any report but only their own private detail.
    # (Here, public and owner views carry the same payload shape; location text
    # and AI metadata are not PII and are safe.)
    if role == UserRole.WORKER:
        if (
            report.assigned_worker_id != current_user.id
            and report.department_id != current_user.department_id
        ):
            raise PermissionDeniedError(
                "You cannot view reports outside your assignments or department."
            )
    return _to_read(report, vote_count=report_service.vote_count(db, report_id=report.id))


@router.get(
    "/{report_id}/history",
    response_model=list[StatusHistoryRead],
    status_code=status.HTTP_200_OK,
    summary="Status history for a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def list_history(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> list[StatusHistoryRead]:
    report_service.get_report(db, report_id)
    events = report_service.list_history(db, report_id=report_id)
    return [StatusHistoryRead.model_validate(e) for e in events]


@router.get(
    "/{report_id}/duplicates",
    response_model=list[DuplicateCandidate],
    status_code=status.HTTP_200_OK,
    summary="Likely duplicates of a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def list_duplicates(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[DuplicateCandidate]:
    matches = report_service.find_duplicate_candidates(
        db, report_id=report_id, limit=limit
    )
    return [
        DuplicateCandidate(
            report_id=m.report.id,
            score=round(m.score, 4),
            distance_meters=round(m.distance_meters, 2),
            created_at=m.report.created_at,
            status=m.report.status,
        )
        for m in matches
    ]


# ---------------------------------------------------------------------------
# Update / delete
# ---------------------------------------------------------------------------
@router.patch(
    "/{report_id}",
    response_model=ReportRead,
    status_code=status.HTTP_200_OK,
    summary="Update a report (owner, while still submitted)",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def update_report(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
    payload: ReportUpdate,
) -> ReportRead:
    report = report_service.update_report(
        db, actor=current_user, report_id=report_id, payload=payload
    )
    return _to_read(report, vote_count=report_service.vote_count(db, report_id=report.id))


@router.post(
    "/{report_id}/moderate",
    response_model=ReportRead,
    status_code=status.HTTP_200_OK,
    summary="Admin moderation (priority, department, note)",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def moderate_report(
    db: DbSession,
    admin: AdminUser,
    report_id: Annotated[int, Path(ge=1)],
    payload: ReportModerate,
) -> ReportRead:
    report = report_service.moderate_report(
        db, admin=admin, report_id=report_id, payload=payload
    )
    return _to_read(report, vote_count=report_service.vote_count(db, report_id=report.id))


@router.delete(
    "/{report_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a report (owner while submitted, or admin)",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def delete_report(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> MessageResponse:
    report_service.delete_report(db, actor=current_user, report_id=report_id)
    return MessageResponse(message="Report deleted.")


# ---------------------------------------------------------------------------
# Status transition (staff/admin)
# ---------------------------------------------------------------------------
@router.post(
    "/{report_id}/status",
    response_model=ReportRead,
    status_code=status.HTTP_200_OK,
    summary="Transition report status (staff/admin, or citizen reopen)",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def change_status(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
    payload: ReportStatusUpdate,
) -> ReportRead:
    report = report_service.get_report(db, report_id)
    report_workflow_service.transition(
        db,
        report=report,
        actor=current_user,
        new_status=payload.status,
        note=payload.note,
    )
    db.commit()
    db.refresh(report)
    return _to_read(report, vote_count=report_service.vote_count(db, report_id=report.id))
