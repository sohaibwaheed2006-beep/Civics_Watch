"""Citizen rating of the work a worker did on a report.

Written once per (report, citizen) after the report moves to ``resolved``.
Feeds the monthly bonus calculation and the worker's visible performance
score. One review per citizen per report (unique constraint).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.user import User

__all__ = ["Review"]


class Review(TimestampMixin, Base):
    """Citizen's 1-5 star rating of a resolved report."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
        UniqueConstraint(
            "report_id", "citizen_id", name="uq_reviews_report_citizen"
        ),
        Index("ix_reviews_worker_created", "worker_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reports.id", ondelete="CASCADE", name="fk_reviews_report"
        ),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_reviews_worker"
        ),
        nullable=False,
        index=True,
        doc="Worker whose closure is being rated.",
    )
    citizen_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_reviews_citizen"
        ),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Integer 1..5."
    )
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    report: Mapped["Report"] = relationship(
        "Report", foreign_keys=[report_id], lazy="joined"
    )
    worker: Mapped["User"] = relationship(
        "User", foreign_keys=[worker_id], lazy="joined"
    )
    citizen: Mapped["User"] = relationship(
        "User", foreign_keys=[citizen_id], lazy="joined"
    )
