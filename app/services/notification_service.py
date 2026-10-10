"""Notification creation and retrieval.

Notifications ride in the same transaction as the triggering state change,
so a committed status update always has its audit log and its notification.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import NotificationType
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.notification import Notification
from app.models.user import User

logger = get_logger(__name__)

__all__ = [
    "create_notification",
    "list_for_user",
    "count_unread",
    "mark_read",
    "mark_all_read",
]


def create_notification(
    db: Session,
    *,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    report_id: int | None = None,
    flush: bool = True,
) -> Notification:
    """Insert a notification. Caller owns the commit."""
    notification = Notification(
        user_id=user_id,
        report_id=report_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )
    db.add(notification)
    if flush:
        db.flush()
    return notification


def list_for_user(
    db: Session,
    *,
    user: User,
    offset: int = 0,
    limit: int = 20,
    unread_only: bool = False,
) -> tuple[Sequence[Notification], int]:
    """Page of a user's notifications and the matching total count."""
    base = select(Notification).where(Notification.user_id == user.id)
    count_stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id)
    )
    if unread_only:
        base = base.where(Notification.is_read.is_(False))
        count_stmt = count_stmt.where(Notification.is_read.is_(False))

    total = int(db.execute(count_stmt).scalar_one())
    items = (
        db.execute(
            base.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return items, total


def count_unread(db: Session, *, user: User) -> int:
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return int(db.execute(stmt).scalar_one())


def mark_read(
    db: Session, *, user: User, notification_id: int
) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    if notification.user_id != user.id:
        raise PermissionDeniedError(
            "You cannot modify another user's notifications."
        )
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utcnow()
        db.commit()
    return notification


def mark_all_read(db: Session, *, user: User) -> int:
    """Return the number of notifications marked read."""
    stmt = (
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=utcnow())
    )
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)
