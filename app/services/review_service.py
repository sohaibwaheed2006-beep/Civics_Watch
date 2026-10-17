"""Citizen reviews on resolved reports.

A citizen rates the worker who closed their report. The rating goes directly
into the worker's rolling performance score and the monthly bonus pick. One
review per citizen per report; a repeat PATCH updates the existing row rather
than creating a new one.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ReportStatus, UserRole
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.logging import get_logger
from app.models.report import Report
from app.models.review import Review
from app.models.user import User

logger = get_logger(__name__)

__all__ = ["upsert_review", "list_reviews_for_worker", "get_review_for_report"]


def upsert_review(
    db: Session,
    *,
    actor: User,
    report: Report,
    rating: int,
    comment: str | None = None,
) -> Review:
    """Create or update a citizen's review of the resolved report."""
    if report.citizen_id != actor.id:
        raise PermissionDeniedError(
            "Only the report owner may review the resolution."
        )
    if report.status != ReportStatus.RESOLVED:
        raise ConflictError(
            "You can only review a report after it has been resolved."
        )
    if report.assigned_worker_id is None:
        raise ConflictError(
            "This report has no assigned worker to review."
        )
    if not 1 <= rating <= 5:
        raise ConflictError("Rating must be between 1 and 5.")

    existing = db.execute(
        select(Review).where(
            Review.report_id == report.id, Review.citizen_id == actor.id
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.rating = rating
        existing.comment = comment
        db.commit()
        db.refresh(existing)
        return existing

    review = Review(
        report_id=report.id,
        worker_id=report.assigned_worker_id,
        citizen_id=actor.id,
        rating=rating,
        comment=comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    logger.info(
        "Review stored report=%s worker=%s rating=%s",
        report.id,
        report.assigned_worker_id,
        rating,
    )
    return review


def get_review_for_report(
    db: Session, *, report_id: int, citizen_id: int
) -> Review | None:
    return db.execute(
        select(Review).where(
            Review.report_id == report_id, Review.citizen_id == citizen_id
        )
    ).scalar_one_or_none()


def list_reviews_for_worker(
    db: Session, *, worker_id: int, limit: int = 50
) -> Sequence[Review]:
    stmt = (
        select(Review)
        .where(Review.worker_id == worker_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
