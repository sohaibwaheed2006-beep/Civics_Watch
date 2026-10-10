"""Notification schemas."""

from __future__ import annotations

from datetime import datetime

from app.core.enums import NotificationType
from app.schemas.common import APIModel

__all__ = ["NotificationRead", "UnreadCountRead"]


class NotificationRead(APIModel):
    id: int
    user_id: int
    report_id: int | None = None
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None


class UnreadCountRead(APIModel):
    unread: int
