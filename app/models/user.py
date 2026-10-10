"""User model.

Covers all three roles. ``password_hash`` is the only credential stored, and
it is never exposed through a response schema.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # avoids a circular import at runtime
    from app.models.department import Department

__all__ = ["User"]


class User(TimestampMixin, Base):
    """An account: citizen, worker or administrator."""

    __tablename__ = "users"
    __table_args__ = (
        # Supports the admin user list filtered by role and status.
        Index("ix_users_role_is_active", "role", "is_active"),
        {"comment": "Application accounts for citizens, workers and admins."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="The user's display name."
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc=(
            "Login identifier, stored lower-cased and trimmed so that "
            "'Ada@Example.com' and 'ada@example.com' are one account. "
            "255 chars keeps the unique index within MySQL's key length limit."
        ),
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc=(
            "Argon2 hash. Never returned by the API - no response schema "
            "declares this field."
        ),
    )
    role: Mapped[UserRole] = mapped_column(
        # native_enum=False stores a VARCHAR with a CHECK constraint instead of
        # a MySQL ENUM. Adding a role later is then a CHECK change rather than
        # an ALTER TABLE that rewrites the column, and SQLite behaves the same
        # way in tests.
        Enum(
            UserRole,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
            validate_strings=True,
        ),
        nullable=False,
        default=UserRole.CITIZEN,
        server_default=UserRole.CITIZEN.value,
        index=True,
        doc="Authorisation role: citizen, admin or worker.",
    )
    phone: Mapped[str | None] = mapped_column(
        String(32), nullable=True, doc="Optional contact number."
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc="False once deactivated; such a user cannot authenticate.",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether the account has completed verification.",
    )
    department_id: Mapped[int | None] = mapped_column(
        # SET NULL rather than CASCADE: removing a department must never
        # delete the people who worked in it.
        ForeignKey("departments.id", ondelete="SET NULL", name="fk_users_department"),
        nullable=True,
        index=True,
        doc="Department a worker belongs to. Null for citizens and admins.",
    )

    department: Mapped["Department | None"] = relationship(
        "Department", back_populates="workers", lazy="joined"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        # Deliberately excludes email and password_hash so an accidental
        # repr() in a log leaks nothing.
        return (
            f"User(id={self.id!r}, role={self.role!r}, "
            f"is_active={self.is_active!r})"
        )
