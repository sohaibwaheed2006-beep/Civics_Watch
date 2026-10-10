"""Department model.

A municipal department that work is routed to, e.g. "Roads & Pavements".
Workers belong to a department; reports are assigned to one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # avoids a circular import at runtime
    from app.models.user import User

__all__ = ["Department", "DEFAULT_SLA_HOURS"]

#: Default resolution target for a new department: three working days.
DEFAULT_SLA_HOURS = 72


class Department(TimestampMixin, Base):
    """A municipal department."""

    __tablename__ = "departments"
    __table_args__ = (
        CheckConstraint(
            "default_sla_hours > 0", name="default_sla_hours_positive"
        ),
        {"comment": "Municipal departments that issue reports are routed to."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
        doc="Display name. Unique; a collision is reported as a 409.",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Optional longer description."
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc=(
            "False once the department is retired. Deactivation is preferred "
            "over deletion so historical reports keep a resolvable reference."
        ),
    )
    default_sla_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_SLA_HOURS,
        doc="Target resolution time, in hours, for reports routed here.",
    )

    #: Workers assigned to this department.
    #:
    #: ``passive_deletes`` lets the database apply the ``ON DELETE SET NULL``
    #: defined on ``users.department_id`` instead of SQLAlchemy loading every
    #: child row to null it out one by one.
    workers: Mapped[list["User"]] = relationship(
        "User",
        back_populates="department",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Department(id={self.id!r}, name={self.name!r}, "
            f"is_active={self.is_active!r})"
        )
