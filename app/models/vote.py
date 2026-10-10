"""Upvotes on reports.

One row per (report, user). The unique constraint is the real guarantee - a
duplicate submission produces an IntegrityError the service handles idempotently.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.user import User

__all__ = ["Vote"]


class Vote(Base):
    """A single upvote on a report by a user."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("report_id", "user_id", name="uq_votes_report_user"),
        {"comment": "One upvote per user per report."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE", name="fk_votes_report"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_votes_user"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    report: Mapped["Report"] = relationship("Report", back_populates="votes")
    user: Mapped["User"] = relationship("User")
