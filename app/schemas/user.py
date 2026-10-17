"""User schemas.

``UserRead`` is the only user representation returned by the API, and it has
no password field at all - so a password cannot leak through a response even
if a record carries one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.enums import UserRole
from app.schemas.common import APIModel

__all__ = [
    "UserRole",
    "UserRead",
    "UserProfileUpdate",
    "UserRoleUpdate",
    "WorkerCreate",
    "AdminUserUpdate",
    "FullName",
    "Phone",
    "Password",
]

#: Minimum accepted password length, kept in step with the auth schemas.
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


# --- Reusable constrained field types --------------------------------------
FullName = Annotated[
    str,
    Field(
        min_length=2,
        max_length=255,
        description="The user's display name.",
        examples=["Ada Lovelace"],
    ),
]

Phone = Annotated[
    str,
    Field(
        min_length=5,
        max_length=32,
        pattern=r"^\+?[0-9\s\-()]+$",
        description="Optional contact number. Digits, spaces, +, - and () only.",
        examples=["+1 555 0142"],
    ),
]


class UserRead(APIModel):
    """Public representation of a user. Never includes password material."""

    id: int = Field(description="Unique user identifier.")
    full_name: str = Field(description="The user's display name.")
    email: str = Field(description="Normalized (lower-cased) email address.")
    role: UserRole = Field(description="Authorisation role.")
    phone: str | None = Field(default=None, description="Optional contact number.")
    is_active: bool = Field(description="False once the account is deactivated.")
    is_verified: bool = Field(description="Whether the account has been verified.")
    department_id: int | None = Field(
        default=None, description="Department a worker belongs to, if any."
    )
    created_at: datetime = Field(description="Creation timestamp (UTC).")
    updated_at: datetime = Field(description="Last modification timestamp (UTC).")


class UserProfileUpdate(APIModel):
    """Fields a user may change on their own profile.

    Only ``full_name`` and ``phone`` are present. Because ``APIModel`` sets
    ``extra="forbid"``, a request that tries to include ``role``,
    ``is_active``, ``is_verified``, ``department_id`` or ``email`` is rejected
    with a 422 - privilege escalation is blocked by the schema itself, before
    any handler code runs.
    """

    full_name: FullName | None = Field(
        default=None, description="New display name. Omit to leave unchanged."
    )
    phone: Phone | None = Field(
        default=None,
        description="New contact number. Send null to clear it, omit to leave unchanged.",
    )

    @field_validator("full_name")
    @classmethod
    def _reject_blank_name(cls, value: str | None) -> str | None:
        # str_strip_whitespace has already trimmed; catch an all-whitespace name.
        if value is not None and not value.strip():
            raise ValueError("full_name must not be blank")
        return value

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> Self:
        """An empty PATCH body is a client mistake, not a no-op success."""
        if not self.model_fields_set:
            raise ValueError(
                "provide at least one field to update (full_name or phone)"
            )
        return self


class UserRoleUpdate(APIModel):
    """Body for ``PATCH /users/{user_id}/role``. Admin only.

    ``department_id`` is accepted alongside the role because the two belong
    together: promoting someone to ``worker`` is normally the moment they are
    attached to a department, and demoting them should detach them. Omit it to
    leave the current assignment untouched.
    """

    role: UserRole = Field(
        description="New role: citizen, admin or worker.",
        examples=["worker"],
    )
    department_id: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Department to assign. Only meaningful for the worker role; send "
            "null to clear the assignment. Omit to leave it unchanged."
        ),
    )


class WorkerCreate(APIModel):
    """Body for ``POST /users/workers``. Admin only.

    Creates a field-worker account directly, with a department attached.
    Unlike public registration, the role is fixed to ``worker`` and the
    account is created already verified so the person can sign in immediately.
    """

    full_name: FullName
    email: EmailStr = Field(
        description="Email address. Normalized to lower case before storage.",
        examples=["worker@example.com"],
    )
    password: Password
    phone: Phone | None = Field(default=None, description="Optional contact number.")
    department_id: int = Field(
        ge=1, description="Department the worker belongs to. Must exist and be active."
    )


class AdminUserUpdate(APIModel):
    """Body for ``PATCH /users/{user_id}``. Admin only.

    Lets an administrator edit a user's profile and status in one call. Every
    field is optional; an empty body is rejected. ``role``/``department_id``
    go through the same safeguards as ``PATCH /users/{id}/role``.
    """

    full_name: FullName | None = Field(
        default=None, description="New display name. Omit to leave unchanged."
    )
    phone: Phone | None = Field(
        default=None,
        description="New contact number. Send null to clear it, omit to leave unchanged.",
    )
    is_active: bool | None = Field(
        default=None, description="Activate or deactivate the account."
    )
    role: UserRole | None = Field(
        default=None, description="New role: citizen, admin or worker."
    )
    department_id: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Department to assign. Only meaningful for workers; send null to "
            "clear it, omit to leave unchanged."
        ),
    )

    @field_validator("full_name")
    @classmethod
    def _reject_blank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("full_name must not be blank")
        return value

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        return self
