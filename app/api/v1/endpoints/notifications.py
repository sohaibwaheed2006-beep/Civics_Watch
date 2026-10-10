"""Notification endpoints. Mounted under ``/notifications``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, DbSession, PaginationDep
from app.schemas.common import ErrorResponse, MessageResponse, Page
from app.schemas.notification import NotificationRead, UnreadCountRead
from app.services import notification_service

router = APIRouter()

_AUTH_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
}


@router.get(
    "",
    response_model=Page[NotificationRead],
    status_code=status.HTTP_200_OK,
    summary="List my notifications",
    responses=_AUTH_ERRORS,
)
def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    pagination: PaginationDep,
    unread_only: Annotated[bool, Query()] = False,
) -> Page[NotificationRead]:
    items, total = notification_service.list_for_user(
        db,
        user=current_user,
        offset=pagination.offset,
        limit=pagination.limit,
        unread_only=unread_only,
    )
    return Page[NotificationRead].create(
        items=[NotificationRead.model_validate(n) for n in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountRead,
    status_code=status.HTTP_200_OK,
    summary="How many unread notifications I have",
    responses=_AUTH_ERRORS,
)
def unread_count(
    db: DbSession, current_user: CurrentUser
) -> UnreadCountRead:
    return UnreadCountRead(
        unread=notification_service.count_unread(db, user=current_user)
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Mark a notification as read",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def mark_read(
    db: DbSession,
    current_user: CurrentUser,
    notification_id: Annotated[int, Path(ge=1)],
) -> NotificationRead:
    n = notification_service.mark_read(
        db, user=current_user, notification_id=notification_id
    )
    return NotificationRead.model_validate(n)


@router.post(
    "/mark-all-read",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all my notifications as read",
    responses=_AUTH_ERRORS,
)
def mark_all_read(
    db: DbSession, current_user: CurrentUser
) -> MessageResponse:
    count = notification_service.mark_all_read(db, user=current_user)
    return MessageResponse(message=f"Marked {count} notification(s) as read.")
