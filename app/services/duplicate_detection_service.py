"""Duplicate-report detection.

Deterministic by design: fast enough to run on every submission, explainable,
and completely offline. External AI (if ever added) can supplement but never
override - a duplicate score is a flag for review, never grounds for silent
merge or deletion.

Signals combined:
  - geographic distance (haversine)
  - title/description text similarity (SequenceMatcher)
  - category compatibility (same category or OTHER)
  - time proximity
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from difflib import SequenceMatcher
from math import asin, cos, radians, sin, sqrt
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import ReportCategory, ReportStatus
from app.db.base import utcnow
from app.models.report import Report

__all__ = [
    "DuplicateMatch",
    "haversine_meters",
    "similarity_score",
    "find_duplicates",
]

EARTH_RADIUS_METERS = 6_371_000


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    report: Report
    score: float
    distance_meters: float


def haversine_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance between two WGS-84 points in metres."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(a))


def similarity_score(a: str, b: str) -> float:
    """Normalised 0..1 ratio using Python's SequenceMatcher.

    No external library and no vocabulary. Fast enough for the volumes a
    neighbourhood tool needs to handle.
    """
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _category_compatible(a: ReportCategory, b: ReportCategory) -> bool:
    """Two reports are category-compatible if they share one or either is OTHER."""
    if a == b:
        return True
    return ReportCategory.OTHER in (a, b)


def _combined_score(
    *, distance_m: float, radius_m: float, text_sim: float
) -> float:
    """Weight distance and text similarity into a single 0..1 score."""
    if radius_m <= 0:
        proximity = 0.0
    else:
        proximity = max(0.0, 1.0 - min(distance_m / radius_m, 1.0))
    # Weight: location is the stronger signal in a geo-tagged system.
    return 0.6 * proximity + 0.4 * text_sim


def find_duplicates(
    db: Session,
    *,
    latitude: float,
    longitude: float,
    title: str,
    description: str,
    category: ReportCategory,
    exclude_report_id: int | None = None,
    limit: int = 5,
) -> list[DuplicateMatch]:
    """Return up to ``limit`` likely duplicates, sorted by score descending."""
    settings = get_settings()
    radius = settings.DUPLICATE_RADIUS_METERS
    min_score = settings.DUPLICATE_MIN_SCORE
    cutoff = utcnow() - timedelta(hours=settings.DUPLICATE_TIME_WINDOW_HOURS)

    # Shortlist candidates in the time window and still open; we filter
    # finely in Python because the lat/lon maths is not SQL-portable here.
    stmt = select(Report).where(
        and_(
            Report.created_at >= cutoff,
            Report.status.notin_(
                [ReportStatus.RESOLVED, ReportStatus.REJECTED]
            ),
        )
    )
    if exclude_report_id is not None:
        stmt = stmt.where(Report.id != exclude_report_id)
    candidates: Sequence[Report] = db.execute(stmt).scalars().all()

    out: list[DuplicateMatch] = []
    for candidate in candidates:
        if not _category_compatible(candidate.category, category):
            continue
        distance = haversine_meters(
            latitude, longitude, candidate.latitude, candidate.longitude
        )
        if distance > radius * 2:  # hard cutoff; score would already be ~0
            continue
        text_sim = max(
            similarity_score(title, candidate.title),
            similarity_score(description, candidate.description),
        )
        score = _combined_score(
            distance_m=distance, radius_m=radius, text_sim=text_sim
        )
        if score >= min_score:
            out.append(
                DuplicateMatch(
                    report=candidate, score=score, distance_meters=distance
                )
            )

    out.sort(key=lambda m: m.score, reverse=True)
    return out[:limit]
