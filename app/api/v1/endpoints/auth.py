"""Authentication endpoints.

Mounted at ``/auth`` by :mod:`app.api.v1.router`, which in turn is mounted
under ``settings.API_V1_PREFIX`` by ``app.main``. Paths here are therefore
declared *relative* (``"/login"``, not ``"/auth/login"``) so the prefix is
applied exactly once.

Routes
------
======================================  ================  =================
Route                                   Auth              Success status
======================================  ================  =================
``POST   /api/v1/auth/register``        public            201
``POST   /api/v1/auth/login``           public            200
``GET    /api/v1/auth/me``              bearer token      200
``PATCH  /api/v1/auth/me``              bearer token      200
``POST   /api/v1/auth/change-password`` bearer token      200
``POST   /api/v1/auth/logout``          bearer token      200
======================================  ================  =================

Handlers stay thin: validate via schema, delegate to
:mod:`app.services.auth_service`, serialise with ``UserRead``. The rules live
in the service.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.user import UserProfileUpdate, UserRead
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a citizen account",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "That email address is already registered.",
        }
    },
    description=(
        "Creates a new account with the `citizen` role.\n\n"
        "The role cannot be chosen by the caller: this endpoint always creates "
        "a citizen. Admin and worker accounts are created by an administrator. "
        "Sending `role`, `is_active`, `is_verified` or `department_id` in the "
        "body is rejected with a 422.\n\n"
        "The password is never returned."
    ),
)
def register(
    payload: RegisterRequest, db: DbSession
) -> UserRead:
    user = auth_service.register_citizen(db, payload)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange credentials for an access token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Incorrect email or password, or the account is inactive.",
        }
    },
    description=(
        "Returns a JWT access token on success.\n\n"
        "Send it on subsequent requests as `Authorization: Bearer <access_token>`.\n\n"
        "An unknown email, a wrong password and a deactivated account all "
        "produce the same 401 message, so this endpoint cannot be used to "
        "discover which addresses are registered."
    ),
)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = auth_service.authenticate(db, payload.email, payload.password)
    return auth_service.issue_access_token(user)


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get the current user's profile",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, malformed, expired or revoked token.",
        }
    },
    description=(
        "Returns the profile of the authenticated user, without password "
        "material.\n\n"
        "The user record is re-read from storage on every call, so a "
        "deactivated account is refused immediately even if its token has not "
        "yet expired."
    ),
)
def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update the current user's profile",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, malformed or expired token.",
        },
        # Literal 422: Starlette renamed its constant for this status.
        422: {
            "model": ErrorResponse,
            "description": (
                "Validation failed, the body was empty, or it contained a "
                "field that is not self-editable."
            ),
        },
    },
    description=(
        "Updates `full_name` and/or `phone`. Send only the fields you want to "
        "change; `phone: null` clears the stored number.\n\n"
        "`role`, `is_active`, `is_verified`, `department_id` and `email` are "
        "**not** editable here - including any of them returns a 422. Role and "
        "status changes are administrator operations."
    ),
)
def update_current_user(
    payload: UserProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserRead:
    user = auth_service.update_own_profile(db, current_user.id, payload)
    return UserRead.model_validate(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change the current user's password",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "The supplied current password is incorrect.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, malformed or expired token.",
        },
    },
    description=(
        "Replaces the password after confirming the current one, so a stolen "
        "token alone cannot lock the owner out.\n\n"
        "A wrong current password returns 400, not 401: the request itself was "
        "properly authenticated, and a 401 would make most clients discard a "
        "valid session.\n\n"
        "Previously issued tokens remain valid until they expire - see the "
        "logout note."
    ),
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    auth_service.change_password(db, current_user.id, payload)
    return MessageResponse(message="Password changed successfully.")


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, malformed or expired token.",
        }
    },
    description=(
        "Acknowledges the logout. **The client must discard its token.**\n\n"
        "JWTs are stateless and self-contained: this endpoint cannot revoke "
        "one, so a token stays valid until its `exp` passes. Delete it from "
        "storage on the client. Server-side revocation needs a token "
        "denylist or short-lived access tokens paired with refresh tokens, "
        "neither of which is in scope for this phase."
    ),
)
def logout(current_user: CurrentUser) -> MessageResponse:
    # Requires a valid token so the call is attributable in the audit log,
    # even though there is no server-side state to clear.
    return MessageResponse(
        message="Logged out. Discard the access token on the client."
    )
