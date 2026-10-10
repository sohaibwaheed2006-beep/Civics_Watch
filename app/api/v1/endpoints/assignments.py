"""Assignment endpoints.

Mounted under ``/reports`` for the create/change routes and ``/assignments``
for the per-worker queue. The department queue sits under ``/departments``
and is handled here as a thin convenience path.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.enums import UserRole
from app.core.exceptions import PermissionDeniedError
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.common import ErrorResponse
from app.schemas.report import ReportSummary
from app.services import assignment_service, report_service

router = APIRouter()

_AUTH_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}


@router.post(
    "/reports/{report_id}/assign",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a worker to a report (admin)",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
    },
    tags=["Assignments"],
)
def assign_worker(
    db: DbSession,
    admin: AdminUser,
    report_id: Annotated[int, Path(ge=1)],
    payload: AssignmentCreate,
) -> AssignmentRead:
    report = report_service.get_report(db, report_id)
    assignment = assignment_service.assign_worker(
        db,
        report=report,
        actor=admin,
        worker_id=payload.worker_id,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(assignment)
    return AssignmentRead.model_validate(assignment)


@router.get(
    "/assignments/my",
    response_model=list[AssignmentRead],
    status_code=status.HTTP_200_OK,
    summary="My active assignments (workers)",
    responses=_AUTH_ERRORS,
    tags=["Assignments"],
)
def list_my_assignments(
    db: DbSession,
    current_user: CurrentUser,
    active_only: Annotated[bool, Query()] = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AssignmentRead]:
    if UserRole(current_user.role) not in (UserRole.WORKER, UserRole.ADMIN):
        raise PermissionDeniedError("Only workers have assignments.")
    items = assignment_service.list_my_assignments(
        db,
        worker=current_user,
        active_only=active_only,
        offset=offset,
        limit=limit,
    )
    return [AssignmentRead.model_validate(a) for a in items]


@router.get(
    "/departments/{department_id}/queue",
    response_model=list[ReportSummary],
    status_code=status.HTTP_200_OK,
    summary="Open-work queue for a department (staff/admin)",
    responses={
        **_AUTH_ERRORS,
    },
    tags=["Assignments"],
)
def department_queue(
    db: DbSession,
    current_user: CurrentUser,
    department_id: Annotated[int, Path(ge=1)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReportSummary]:
    role = UserRole(current_user.role)
    if role == UserRole.CITIZEN:
        raise PermissionDeniedError(
            "Citizens cannot access department queues."
        )
    if role == UserRole.WORKER and current_user.department_id != department_id:
        raise PermissionDeniedError(
            "Workers may only view their own department's queue."
        )

    items = assignment_service.list_department_queue(
        db, department_id=department_id, offset=offset, limit=limit
    )
    # Vote counts omitted here; the queue is a work list, not a feed.
    return [
        ReportSummary(
            id=r.id,
            title=r.title,
            category=r.category,
            priority=r.priority,
            status=r.status,
            latitude=r.latitude,
            longitude=r.longitude,
            citizen_id=r.citizen_id,
            department_id=r.department_id,
            assigned_worker_id=r.assigned_worker_id,
            created_at=r.created_at,
            updated_at=r.updated_at,
            deadline_at=r.deadline_at,
            resolved_at=r.resolved_at,
            vote_count=0,
        )
        for r in items
    ]
