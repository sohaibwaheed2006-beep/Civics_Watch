"""User administration endpoints.

Mounted at ``/users`` by :mod:`app.api.v1.router`, which is itself mounted
under ``settings.API_V1_PREFIX``. Paths here are declared relative so the
prefix is applied exactly once.

==========================================  ============  ===============
Route                                       Access        Success
==========================================  ============  ===============
``GET    /api/v1/users/``                   admin only    200
``GET    /api/v1/users/{user_id}``          admin only    200
``PATCH  /api/v1/users/{user_id}/role``     admin only    200
==========================================  ============  ===============

Authorisation is applied through ``AdminUser``, which resolves the bearer
token, re-reads the user from the database and then checks the stored role -
a role claim inside a token is never trusted on its own.

Responses use ``UserRead``, which declares no password field, so credential
material cannot leak through this module.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminUser, DbSession, PaginationDep
from app.core.enums import UserRole
from app.schemas.common import ErrorResponse, Page
from app.schemas.user import UserRead, UserRoleUpdate
from app.services import user_service

router = APIRouter()

#: Reused by the admin-only routes in this module.
_ADMIN_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Missing, malformed or expired token.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "Authenticated, but not an administrator.",
    },
}

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "No user with that ID.",
    }
}


@router.get(
    "/",
    response_model=Page[UserRead],
    status_code=status.HTTP_200_OK,
    summary="List users",
    responses=_ADMIN_ERRORS,
    description=(
        "Paginated list of all users. Administrators only.\n\n"
        "Filterable by `role`, `department_id` and `is_active`, and "
        "searchable by name or email. Results are ordered by the requested "
        "`sort_by` with `id` as a tie-breaker, so paging is stable.\n\n"
        "Passwords are never included."
    ),
)
def list_users(
    db: DbSession,
    admin: AdminUser,
    pagination: PaginationDep,
    role: Annotated[
        UserRole | None, Query(description="Only users with this role.")
    ] = None,
    department_id: Annotated[
        int | None, Query(ge=1, description="Only users in this department.")
    ] = None,
    is_active: Annotated[
        bool | None, Query(description="Filter by account status.")
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=255,
            description="Case-insensitive match on full name or email.",
        ),
    ] = None,
) -> Page[UserRead]:
    items, total = user_service.list_users(
        db,
        offset=pagination.offset,
        limit=pagination.limit,
        role=role,
        department_id=department_id,
        is_active=is_active,
        search=search,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
    )
    return Page[UserRead].create(
        items=[UserRead.model_validate(user) for user in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get a user",
    responses={**_ADMIN_ERRORS, **_NOT_FOUND},
    description=(
        "Returns one user by ID. Administrators only.\n\n"
        "A user can read their own profile through `GET /auth/me` without "
        "needing administrator access."
    ),
)
def get_user(
    db: DbSession,
    admin: AdminUser,
    user_id: Annotated[int, Path(ge=1, description="Target user ID.")],
) -> UserRead:
    user = user_service.get_user(db, user_id)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Change a user's role",
    responses={
        **_ADMIN_ERRORS,
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "No user, or no department, with that ID.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": (
                "The change would remove the last active administrator, or "
                "the target department is inactive."
            ),
        },
    },
    description=(
        "Sets a user's role to `citizen`, `admin` or `worker`. "
        "Administrators only.\n\n"
        "Pass `department_id` to assign a worker to a department at the same "
        "time; omit it to leave the current assignment alone. Promoting to "
        "`admin` or demoting to `citizen` clears the department, since only "
        "workers hold one.\n\n"
        "Two safeguards apply:\n\n"
        "- **You cannot change your own role** (403). Ask another "
        "administrator, so an accidental self-demotion cannot lock you out.\n"
        "- **The last active administrator cannot be demoted** (409), which "
        "would otherwise leave nobody able to manage the system."
    ),
)
def update_user_role(
    db: DbSession,
    admin: AdminUser,
    payload: UserRoleUpdate,
    user_id: Annotated[int, Path(ge=1, description="Target user ID.")],
) -> UserRead:
    user = user_service.update_user_role(
        db, actor=admin, user_id=user_id, payload=payload
    )
    return UserRead.model_validate(user)
