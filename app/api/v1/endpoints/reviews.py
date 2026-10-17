"""Citizen review endpoints: rate the worker who closed your report."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.models.report import Report
from app.schemas.common import ErrorResponse
from app.schemas.review import ReviewCreate, ReviewRead
from app.services import review_service

router = APIRouter()

_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
}


@router.post(
    "/{report_id}/review",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Rate the worker who resolved this report",
    responses=_ERRORS,
)
def submit_review(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
    payload: ReviewCreate,
) -> ReviewRead:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    review = review_service.upsert_review(
        db,
        actor=current_user,
        report=report,
        rating=payload.rating,
        comment=payload.comment,
    )
    return ReviewRead.model_validate(review)


@router.get(
    "/{report_id}/review",
    response_model=ReviewRead | None,
    status_code=status.HTTP_200_OK,
    summary="Fetch my review for this report, if any",
    responses=_ERRORS,
)
def get_my_review(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> ReviewRead | None:
    review = review_service.get_review_for_report(
        db, report_id=report_id, citizen_id=current_user.id
    )
    if review is None:
        return None
    return ReviewRead.model_validate(review)
