"""Worker-of-the-month bonus endpoints.

Reading is open to any authenticated user (workers want to see the current
leaderboard); writing is admin-only.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, require_admin
from app.core.exceptions import NotFoundError
from app.db.base import utcnow
from app.schemas.bonus import WorkerBonusRead, WorkerScoreRead
from app.schemas.common import ErrorResponse
from app.services import worker_performance_service

router = APIRouter()

_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
}


def _to_bonus_read(bonus) -> WorkerBonusRead:
    return WorkerBonusRead(
        id=bonus.id,
        period_year=bonus.period_year,
        period_month=bonus.period_month,
        worker_id=bonus.worker_id,
        worker_name=bonus.worker.full_name if bonus.worker else None,
        resolved_count=bonus.resolved_count,
        average_rating=bonus.average_rating,
        average_hours_to_resolve=bonus.average_hours_to_resolve,
        on_time_rate=bonus.on_time_rate,
        total_score=bonus.total_score,
        created_at=bonus.created_at,
        updated_at=bonus.updated_at,
    )


@router.get(
    "",
    response_model=list[WorkerBonusRead],
    status_code=status.HTTP_200_OK,
    summary="List recent worker-of-the-month awards",
    responses=_ERRORS,
)
def list_bonuses(
    db: DbSession,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=36)] = 12,
) -> list[WorkerBonusRead]:
    rows = worker_performance_service.list_recent_bonuses(db, limit=limit)
    return [_to_bonus_read(b) for b in rows]


@router.get(
    "/current-leaderboard",
    response_model=list[WorkerScoreRead],
    status_code=status.HTTP_200_OK,
    summary="Live leaderboard for the ongoing month",
    responses=_ERRORS,
)
def current_leaderboard(
    db: DbSession,
    current_user: CurrentUser,
) -> list[WorkerScoreRead]:
    now = utcnow()
    start, end = worker_performance_service.month_bounds(
        year=now.year, month=now.month
    )
    scores = worker_performance_service.compute_worker_scores(
        db, period_start=start, period_end=end
    )
    return [
        WorkerScoreRead(
            worker_id=s.worker_id,
            worker_name=s.worker_name,
            resolved_count=s.resolved_count,
            average_rating=s.average_rating,
            average_hours_to_resolve=s.average_hours_to_resolve,
            on_time_rate=s.on_time_rate,
            total_score=s.total_score,
        )
        for s in scores
    ]


@router.post(
    "/award/{year}/{month}",
    response_model=WorkerBonusRead | None,
    status_code=status.HTTP_200_OK,
    summary="Award (or re-award) the bonus for a given month (admin)",
    dependencies=[Depends(require_admin)],
    responses=_ERRORS,
)
def award_month(
    db: DbSession,
    year: int,
    month: int,
    overwrite: Annotated[bool, Query()] = False,
) -> WorkerBonusRead | None:
    if not 1 <= month <= 12:
        raise NotFoundError("Month must be between 1 and 12.")
    bonus = worker_performance_service.award_month(
        db, year=year, month=month, overwrite=overwrite
    )
    if bonus is None:
        return None
    return _to_bonus_read(bonus)


@router.post(
    "/award/previous-month",
    response_model=WorkerBonusRead | None,
    status_code=status.HTTP_200_OK,
    summary="Convenience: award the previous calendar month",
    dependencies=[Depends(require_admin)],
    responses=_ERRORS,
)
def award_previous_month(
    db: DbSession,
    overwrite: Annotated[bool, Query()] = False,
) -> WorkerBonusRead | None:
    year, month = worker_performance_service.previous_month()
    bonus = worker_performance_service.award_month(
        db, year=year, month=month, overwrite=overwrite
    )
    if bonus is None:
        return None
    return _to_bonus_read(bonus)
