"""Report status transition history.

One row per state change. Written inside the same transaction as the status
update by the workflow service, so the audit trail cannot drift from the
report.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ReportStatus
from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.user import User

__all__ = ["StatusHistory"]


def _status_enum() -> Enum:
    return Enum(
        ReportStatus,
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class StatusHistory(Base):
    """One entry in the audit log for a report's lifecycle."""

    __tablename__ = "status_history"
    __table_args__ = (
        Index("ix_status_history_report_created", "report_id", "created_at"),
        {"comment": "Immutable log of report status transitions."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reports.id", ondelete="CASCADE", name="fk_status_history_report"
        ),
        nullable=False,
    )
    old_status: Mapped[ReportStatus | None] = mapped_column(
        _status_enum(),
        nullable=True,
        doc="Previous status; null on the submission event.",
    )
    new_status: Mapped[ReportStatus] = mapped_column(
        _status_enum(), nullable=False
    )
    changed_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_status_history_changed_by"
        ),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    report: Mapped["Report"] = relationship(
        "Report", back_populates="status_history"
    )
    changed_by: Mapped["User"] = relationship("User", lazy="joined")
