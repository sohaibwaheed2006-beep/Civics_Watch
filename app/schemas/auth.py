"""Authentication request and response schemas.

Every request model inherits ``APIModel``, which sets ``extra="forbid"``. That
single setting is what stops a registration or profile request from carrying
``role``, ``is_active`` or ``department_id``: an unknown field is a 422 rather
than being silently dropped.
"""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import EmailStr, Field, model_validator

from app.schemas.common import APIModel
from app.schemas.user import FullName, Phone, UserRead

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "AuthResponse",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "MIN_PASSWORD_LENGTH",
]

#: Minimum accepted password length. Modest, and enforced in one place.
MIN_PASSWORD_LENGTH = 8

Password = Annotated[
    str,
    Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        description=f"At least {MIN_PASSWORD_LENGTH} characters.",
        examples=["correct-horse-battery"],
    ),
]


class RegisterRequest(APIModel):
    """Self-service citizen registration.

    The role is **not** accepted from the client. Every account created here is
    a ``citizen``; admin and worker accounts are created by an administrator.
    """

    full_name: FullName
    email: EmailStr = Field(
        description="Email address. Normalized to lower case before storage.",
        examples=["ada@example.com"],
    )
    password: Password
    phone: Phone | None = Field(default=None, description="Optional contact number.")


class LoginRequest(APIModel):
    """Email and password credentials."""

    email: EmailStr = Field(description="Registered email address.")
    password: str = Field(
        min_length=1,
        max_length=128,
        description="Account password.",
    )


class TokenResponse(APIModel):
    """A freshly issued access token."""

    access_token: str = Field(description="Signed JWT access token.")
    token_type: str = Field(
        default="bearer",
        description="Scheme for the Authorization header: 'Bearer <token>'.",
    )
    expires_in: int = Field(
        description="Token lifetime in seconds from issue time.",
        examples=[3600],
    )


class AuthResponse(APIModel):
    """Access token plus the authenticated user profile.

    Login and register return this envelope so the client has both the bearer
    token and the user record in a single round-trip.
    """

    access_token: str = Field(description="Signed JWT access token.")
    token_type: str = Field(
        default="bearer",
        description="Scheme for the Authorization header: 'Bearer <token>'.",
    )
    expires_in: int = Field(description="Token lifetime in seconds.")
    user: UserRead = Field(description="The authenticated user's profile.")


class ChangePasswordRequest(APIModel):
    """Change the authenticated user's password.

    The current password is required, so a stolen token alone cannot be used
    to lock the real owner out of their account.
    """

    current_password: str = Field(
        min_length=1,
        max_length=128,
        description="The password currently in use.",
    )
    new_password: Password = Field(description="The replacement password.")

    @model_validator(mode="after")
    def _reject_unchanged_password(self) -> Self:
        if self.current_password == self.new_password:
            raise ValueError("new_password must differ from current_password")
        return self


class ForgotPasswordRequest(APIModel):
    """Request a password-reset link by email.

    The endpoint deliberately returns the same acknowledgement whether or not
    the address is registered, so this request cannot be used to discover which
    emails have accounts.
    """

    email: EmailStr = Field(
        description="The email address to send a reset link to.",
        examples=["ada@example.com"],
    )


class ResetPasswordRequest(APIModel):
    """Set a new password using a token from a reset link."""

    token: str = Field(
        min_length=1,
        max_length=2048,
        description="The opaque token from the emailed reset link.",
    )
    new_password: Password = Field(description="The replacement password.")
