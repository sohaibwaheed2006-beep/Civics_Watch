"""Department management endpoints.

Mounted at ``/departments`` by :mod:`app.api.v1.router`. Paths are declared
relative so the ``/api/v1`` prefix is applied exactly once.

====================================================  ==================  =========
Route                                                 Access              Success
====================================================  ==================  =========
``GET    /api/v1/departments/``                       any authenticated   200
``POST   /api/v1/departments/``                       admin only          201
``PATCH  /api/v1/departments/{department_id}``        admin only          200
====================================================  ==================  =========

Reading is open to every authenticated user, because citizens need the
department list to understand where a report was routed. Creating and
updating are administrator-only.

Retiring a department is done with ``PATCH`` and ``is_active=false`` rather
than a delete, so workers and historical reports that reference it still
resolve.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, PaginationDep
from app.schemas.common import ErrorResponse, Page
from app.repositories import department_repository
from app.schemas.department import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
)
from app.services import department_service


def _with_worker_count(department: object, worker_count: int) -> DepartmentRead:
    """Serialise a department, attaching its live active-worker headcount."""
    return DepartmentRead.model_validate(department).model_copy(
        update={"worker_count": worker_count}
    )

router = APIRouter()

_AUTH_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Missing, malformed or expired token.",
    }
}

_ADMIN_ERRORS: dict[int | str, dict[str, object]] = {
    **_AUTH_ERRORS,
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "Authenticated, but not an administrator.",
    },
}


@router.get(
    "",
    response_model=Page[DepartmentRead],
    status_code=status.HTTP_200_OK,
    summary="List departments",
    responses=_AUTH_ERRORS,
    description=(
        "Paginated list of departments, available to any authenticated "
        "user.\n\n"
        "By default **only active departments** are returned, which is what a "
        "picker in the UI wants. Pass `is_active=false` for retired ones, or "
        "`include_inactive=true` to get both.\n\n"
        "Ordered by name, with `id` as a tie-breaker for stable paging."
    ),
)
def list_departments(
    db: DbSession,
    current_user: CurrentUser,
    pagination: PaginationDep,
    is_active: Annotated[
        bool | None,
        Query(
            description=(
                "Filter by status. Defaults to active only; ignored when "
                "include_inactive is true."
            )
        ),
    ] = None,
    include_inactive: Annotated[
        bool,
        Query(description="Return active and inactive departments together."),
    ] = False,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=150,
            description="Case-insensitive match on the department name.",
        ),
    ] = None,
) -> Page[DepartmentRead]:
    # Default to active-only, but let a caller opt into the full list.
    status_filter: bool | None
    if include_inactive:
        status_filter = None
    elif is_active is None:
        status_filter = True
    else:
        status_filter = is_active

    items, total = department_service.list_departments(
        db,
        offset=pagination.offset,
        limit=pagination.limit,
        is_active=status_filter,
        search=search,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
    )
    counts = department_repository.active_worker_counts(
        db, [item.id for item in items]
    )
    return Page[DepartmentRead].create(
        items=[
            _with_worker_count(item, counts.get(item.id, 0)) for item in items
        ],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


@router.post(
    "",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
    responses={
        **_ADMIN_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "A department with that name already exists.",
        },
    },
    description=(
        "Creates a department. Administrators only.\n\n"
        "`name` must be unique, compared case-insensitively, so 'Roads' and "
        "'roads' cannot both exist. A collision returns 409.\n\n"
        "`default_sla_hours` is the target resolution time for reports routed "
        "here; it must be positive and defaults to 72 (three days)."
    ),
)
def create_department(
    db: DbSession, admin: AdminUser, payload: DepartmentCreate
) -> DepartmentRead:
    department = department_service.create_department(
        db, actor=admin, payload=payload
    )
    # A brand-new department has no workers yet.
    return _with_worker_count(department, 0)


@router.patch(
    "/{department_id}",
    response_model=DepartmentRead,
    status_code=status.HTTP_200_OK,
    summary="Update a department",
    responses={
        **_ADMIN_ERRORS,
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "No department with that ID.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "That name is already used by another department.",
        },
    },
    description=(
        "Partially updates a department. Administrators only.\n\n"
        "Send only the fields you want to change; `description: null` clears "
        "the description. An empty body returns 422 rather than silently "
        "succeeding.\n\n"
        "Set `is_active=false` to retire a department. This is the supported "
        "alternative to deletion: the row is kept, so workers and historical "
        "reports pointing at it still resolve. Set it back to true to "
        "restore."
    ),
)
def update_department(
    db: DbSession,
    admin: AdminUser,
    payload: DepartmentUpdate,
    department_id: Annotated[
        int, Path(ge=1, description="Target department ID.")
    ],
) -> DepartmentRead:
    department = department_service.update_department(
        db, actor=admin, department_id=department_id, payload=payload
    )
    counts = department_repository.active_worker_counts(db, [department.id])
    return _with_worker_count(department, counts.get(department.id, 0))
