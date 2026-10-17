"""Monthly worker-of-the-month award record.

One row per month, naming the winning worker and the component scores that
produced the win. The service that creates these rows is idempotent on
``period_year`` + ``period_month``, so re-running the monthly task over an
already-closed month is safe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

__all__ = ["WorkerBonus"]


class WorkerBonus(TimestampMixin, Base):
    """One monthly bonus award."""

    __tablename__ = "worker_bonuses"
    __table_args__ = (
        UniqueConstraint(
            "period_year", "period_month", name="uq_worker_bonuses_period"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)

    worker_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_worker_bonuses_worker"
        ),
        nullable=False,
        index=True,
    )

    resolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_hours_to_resolve: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    on_time_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    worker: Mapped["User"] = relationship(
        "User", foreign_keys=[worker_id], lazy="joined"
    )
