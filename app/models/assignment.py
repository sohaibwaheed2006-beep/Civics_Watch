"""Report assignment history.

A new row is inserted every time work is assigned or reassigned, so the audit
trail is intact. The ``active`` flag identifies the current assignment; prior
rows carry an ``unassigned_at`` timestamp.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.report import Report
    from app.models.user import User

__all__ = ["Assignment"]


class Assignment(Base):
    """One historical assignment of a report to a worker."""

    __tablename__ = "assignments"
    __table_args__ = (
        Index("ix_assignments_worker_active", "worker_id", "active"),
        Index("ix_assignments_report_active", "report_id", "active"),
        {"comment": "Audit trail of report assignments."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reports.id", ondelete="CASCADE", name="fk_assignments_report"
        ),
        nullable=False,
    )
    worker_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_assignments_worker"
        ),
        nullable=False,
    )
    assigned_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_assignments_assigned_by"
        ),
        nullable=False,
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="SET NULL",
            name="fk_assignments_department",
        ),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc=(
            "True on the current active assignment for a report. A report may "
            "have at most one active=True row at a time."
        ),
    )

    report: Mapped["Report"] = relationship("Report", back_populates="assignments")
    worker: Mapped["User"] = relationship(
        "User", foreign_keys=[worker_id], lazy="joined"
    )
    assigned_by: Mapped["User"] = relationship(
        "User", foreign_keys=[assigned_by_id]
    )
    department: Mapped["Department | None"] = relationship(
        "Department", foreign_keys=[department_id]
    )
