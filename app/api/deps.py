"""Reusable FastAPI dependencies.

This module is the stable import surface for cross-cutting request concerns.
Both developers import from here rather than redefining dependencies locally,
so authorisation behaviour stays uniform across domain modules.

Stable names
------------
``get_current_user``
    Resolve the bearer token to the live, active user record.
``require_roles(*roles)``
    Factory producing a dependency that enforces role membership.
``get_user_repository``
    The active user store.

Phase 3 adds ``get_db`` (re-exported from ``app.db.session``) and swaps the
repository for a SQLAlchemy-backed one. The names above do not change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.enums import UserRole
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.logging import get_logger, get_request_id
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services import auth_service

logger = get_logger(__name__)

__all__ = [
    "PaginationParams",
    "SettingsDep",
    "PaginationDep",
    "DbSession",
    "CurrentUser",
    "AdminUser",
    "get_db",
    "get_pagination_params",
    "get_request_id_dep",
    "get_current_user",
    "require_roles",
    "require_admin",
    "require_staff",
]


# ---------------------------------------------------------------------------
# Settings and database
# ---------------------------------------------------------------------------
SettingsDep = Annotated[Settings, Depends(get_settings)]

#: Request-scoped SQLAlchemy session. ``get_db`` is re-exported from this
#: module so endpoints have one obvious place to import dependencies from.
DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
#: ``auto_error=False`` so a missing or malformed Authorization header reaches
#: our own handler and is rendered in the shared error envelope, instead of
#: Starlette emitting its own differently-shaped 403 body.
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Paste the `access_token` returned by `POST /api/v1/auth/login`.",
)


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    """Resolve the bearer token to the live user row.

    Two-step on purpose: the token is validated cryptographically, then the
    user is re-read from the database. Authorisation therefore follows current
    state - a deactivated user is refused immediately, even while holding a
    token that has not yet expired. Claims in the token are never treated as
    authoritative for permissions.

    Raises
    ------
    AuthenticationError
        No credentials, an invalid or expired token, or a user who no longer
        exists or is inactive (401).
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Not authenticated.")

    user_id = decode_access_token(credentials.credentials)
    return auth_service.load_active_user(db, user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str | UserRole) -> Callable[[User], User]:
    """Build a dependency that admits only the given roles.

    Usage::

        @router.get("/users", dependencies=[Depends(require_roles(UserRole.ADMIN))])

        # or, to also receive the record:
        def endpoint(admin: Annotated[UserRecord, Depends(require_admin)]): ...

    The check runs against the role stored for the user, not a token claim.
    Returns 403 (authenticated but not permitted), never 401.
    """
    allowed = frozenset(str(role) for role in roles)

    def dependency(current_user: CurrentUser) -> User:
        if str(current_user.role) not in allowed:
            logger.info(
                "Denied user id=%s role=%s; requires one of %s",
                current_user.id,
                current_user.role,
                sorted(allowed),
            )
            raise PermissionDeniedError(
                "You do not have permission to perform this action."
            )
        return current_user

    # Helps FastAPI produce readable dependency names in debug output.
    dependency.__name__ = f"require_roles_{'_'.join(sorted(allowed))}"
    return dependency


#: Admin-only access.
require_admin = require_roles(UserRole.ADMIN)

#: Municipal staff: admins and workers, but not citizens.
require_staff = require_roles(UserRole.ADMIN, UserRole.WORKER)

#: Annotated form of :data:`require_admin`, for endpoints that need the record.
AdminUser = Annotated[User, Depends(require_admin)]


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
#: Upper bound on ``page_size``, so a client cannot ask for an unbounded scan.
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


@dataclass(frozen=True, slots=True)
class PaginationParams:
    """Validated pagination and sorting input for list endpoints.

    ``offset``/``limit`` are what the query layer consumes; ``page`` and
    ``page_size`` are what the client sends and what is echoed back in the
    response envelope.
    """

    page: int
    page_size: int
    sort_by: str | None = None
    sort_order: str = "asc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def descending(self) -> bool:
        return self.sort_order == "desc"


def get_pagination_params(
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"Items per page (1-{MAX_PAGE_SIZE}).",
        ),
    ] = DEFAULT_PAGE_SIZE,
    sort_by: Annotated[
        str | None,
        Query(
            max_length=64,
            description=(
                "Field to sort by. Endpoints validate this against their own "
                "allow-list and fall back to a stable default."
            ),
        ),
    ] = None,
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort direction.")
    ] = "asc",
) -> PaginationParams:
    """Parse and validate the shared pagination query parameters.

    Note on stable ordering: a paginated result must always carry a
    tie-breaker (normally the primary key) so that two requests for the same
    page return the same rows. Endpoints are responsible for appending that
    tie-break column to whatever ``sort_by`` resolves to.
    """
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by.strip() if sort_by else None,
        sort_order=sort_order,
    )


PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]


# ---------------------------------------------------------------------------
# Request context
# ---------------------------------------------------------------------------
def get_request_id_dep(request: Request) -> str | None:
    """Expose the current correlation ID to endpoints that want to echo it."""
    return getattr(request.state, "request_id", None) or get_request_id()
