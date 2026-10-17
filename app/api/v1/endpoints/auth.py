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

from fastapi import APIRouter, BackgroundTasks, status

from app.api.deps import CurrentUser, DbSession, SettingsDep
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.user import UserProfileUpdate, UserRead
from app.services import auth_service, email_service

router = APIRouter()


def _link(base_url: str, path: str, token: str) -> str:
    """Build a frontend link of the form ``{base_url}{path}?token=...``.

    JWTs use only URL-safe characters, so the token needs no percent-encoding.
    """
    return f"{base_url}{path}?token={token}"


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
        "No email confirmation is required: the account can sign in immediately "
        "with the chosen credentials. The password is never returned."
    ),
)
def register(payload: RegisterRequest, db: DbSession) -> UserRead:
    user = auth_service.register_citizen(db, payload)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange credentials for an access token and user profile",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Incorrect email or password, or the account is inactive.",
        },
    },
    description=(
        "Returns a JWT access token *and* the authenticated user's profile.\n\n"
        "Send the token on subsequent requests as "
        "`Authorization: Bearer <access_token>`.\n\n"
        "An unknown email, a wrong password and a deactivated account all "
        "produce the same 401 message, so this endpoint cannot be used to "
        "discover which addresses are registered."
    ),
)
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    user = auth_service.authenticate(db, payload.email, payload.password)
    token = auth_service.issue_access_token(user)
    return AuthResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=UserRead.model_validate(user),
    )


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
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password-reset link by email",
    description=(
        "Sends a password-reset link to the address if - and only if - it "
        "belongs to an active account. The response is the **same** whether or "
        "not the email is registered, so this endpoint cannot be used to "
        "discover which addresses have accounts.\n\n"
        "The email is dispatched in the background. If SMTP is not configured "
        "the endpoint still returns 200; it simply sends nothing."
    ),
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: DbSession,
    background: BackgroundTasks,
    settings: SettingsDep,
) -> MessageResponse:
    result = auth_service.request_password_reset(db, payload.email)
    if result is not None:
        user, token = result
        background.add_task(
            email_service.send_password_reset_email,
            to_email=user.email,
            full_name=user.full_name,
            reset_url=_link(settings.FRONTEND_BASE_URL, "/reset-password", token),
        )
    return MessageResponse(
        message=(
            "If an account exists for that email, a password-reset link has "
            "been sent."
        )
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Set a new password from a reset link",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "The reset link is invalid, expired or already used.",
        }
    },
    description=(
        "Completes a password reset using the token from the emailed link.\n\n"
        "A link is single-use: it is tied to the password it was issued "
        "against, so once the password changes the link stops working. Expired "
        "or tampered links return 400."
    ),
)
def reset_password(
    payload: ResetPasswordRequest, db: DbSession
) -> MessageResponse:
    auth_service.reset_password(db, payload.token, payload.new_password)
    return MessageResponse(
        message="Your password has been reset. You can now sign in."
    )


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
