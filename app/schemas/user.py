"""User schemas.

``UserRead`` is the only user representation returned by the API, and it has
no password field at all - so a password cannot leak through a response even
if a record carries one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from app.core.enums import UserRole
from app.schemas.common import APIModel

__all__ = [
    "UserRole",
    "UserRead",
    "UserProfileUpdate",
    "UserRoleUpdate",
    "FullName",
    "Phone",
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
