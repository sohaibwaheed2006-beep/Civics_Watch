"""In-app notification record."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import NotificationType
from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.user import User

__all__ = ["Notification"]


class Notification(Base):
    """A single notification delivered to one user."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_user_unread",
            "user_id",
            "is_read",
        ),
        Index(
            "ix_notifications_user_created",
            "user_id",
            "created_at",
        ),
        {"comment": "In-app notifications per user."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_notifications_user"
        ),
        nullable=False,
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "reports.id", ondelete="SET NULL", name="fk_notifications_report"
        ),
        nullable=True,
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            native_enum=False,
            length=32,
            values_callable=lambda e: [m.value for m in e],
            validate_strings=True,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User")
    report: Mapped["Report | None"] = relationship("Report")
