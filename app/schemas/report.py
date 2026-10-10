"""Report request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.core.enums import ReportCategory, ReportPriority, ReportStatus
from app.schemas.common import APIModel

__all__ = [
    "ReportCategory",
    "ReportPriority",
    "ReportStatus",
    "ReportCreate",
    "ReportUpdate",
    "ReportStatusUpdate",
    "ReportModerate",
    "ReportRead",
    "ReportSummary",
    "ReportMapMarker",
    "DuplicateCandidate",
]

Latitude = Annotated[
    float,
    Field(ge=-90, le=90, description="Latitude in decimal degrees."),
]
Longitude = Annotated[
    float,
    Field(ge=-180, le=180, description="Longitude in decimal degrees."),
]
Title = Annotated[str, Field(min_length=3, max_length=200)]
Description = Annotated[str, Field(min_length=5, max_length=5000)]
LocationText = Annotated[str, Field(max_length=500)]


class ReportCreate(APIModel):
    """Body for ``POST /reports``. Submitted by citizens."""

    title: Title
    description: Description
    category: ReportCategory
    latitude: Latitude
    longitude: Longitude
    location_text: LocationText | None = None


class ReportUpdate(APIModel):
    """Body for ``PATCH /reports/{id}`` from the citizen owner.

    Citizens cannot change ``status``, ``priority``, ``department_id``,
    ``assigned_worker_id`` or audit fields - ``extra="forbid"`` on ``APIModel``
    rejects any attempt to include those keys.
    """

    title: Title | None = None
    description: Description | None = None
    category: ReportCategory | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    location_text: LocationText | None = None

    @model_validator(mode="after")
    def _require_at_least_one(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        return self


class ReportStatusUpdate(APIModel):
    """Body for ``POST /reports/{id}/status`` (staff/admin)."""

    status: ReportStatus
    note: str | None = Field(default=None, max_length=1000)


class ReportModerate(APIModel):
    """Admin-only moderation body."""

    priority: ReportPriority | None = None
    department_id: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _require_at_least_one(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        return self


class ReportSummary(APIModel):
    """Compact view used in list responses."""

    id: int
    title: str
    category: ReportCategory
    priority: ReportPriority
    status: ReportStatus
    latitude: float
    longitude: float
    citizen_id: int
    department_id: int | None = None
    assigned_worker_id: int | None = None
    created_at: datetime
    updated_at: datetime
    deadline_at: datetime | None = None
    resolved_at: datetime | None = None
    vote_count: int = 0


class ReportRead(ReportSummary):
    """Full report view, used on detail endpoints."""

    description: str
    location_text: str | None = None
    ai_category: str | None = None
    ai_confidence: float | None = None
    duplicate_score: float | None = None
    duplicate_of_report_id: int | None = None


class ReportMapMarker(APIModel):
    """Lean payload for map tiles. No PII."""

    id: int
    category: ReportCategory
    status: ReportStatus
    priority: ReportPriority
    latitude: float
    longitude: float


class DuplicateCandidate(APIModel):
    """A possibly-duplicate report."""

    report_id: int
    score: float = Field(ge=0.0, le=1.0)
    distance_meters: float
    created_at: datetime
    status: ReportStatus
