"""Vote endpoints, mounted under ``/reports``."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import ErrorResponse
from app.schemas.vote import VoteCountRead
from app.services import report_service

router = APIRouter()

_AUTH_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
}


@router.post(
    "/{report_id}/vote",
    response_model=VoteCountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Vote for a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def add_vote(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> VoteCountRead:
    count = report_service.add_vote(db, report_id=report_id, user=current_user)
    return VoteCountRead(report_id=report_id, count=count, voted=True)


@router.delete(
    "/{report_id}/vote",
    response_model=VoteCountRead,
    status_code=status.HTTP_200_OK,
    summary="Remove your vote",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def remove_vote(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> VoteCountRead:
    count = report_service.remove_vote(
        db, report_id=report_id, user=current_user
    )
    return VoteCountRead(report_id=report_id, count=count, voted=False)


@router.get(
    "/{report_id}/votes",
    response_model=VoteCountRead,
    status_code=status.HTTP_200_OK,
    summary="Vote count for a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def get_votes(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> VoteCountRead:
    report_service.get_report(db, report_id)
    count = report_service.vote_count(db, report_id=report_id)
    voted = report_service.has_voted(
        db, report_id=report_id, user_id=current_user.id
    )
    return VoteCountRead(report_id=report_id, count=count, voted=voted)
