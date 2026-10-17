"""Schemas for AI assist endpoints (vision auto-fill, routing suggestions)."""

from __future__ import annotations

from app.core.enums import ReportCategory, ReportPriority
from app.schemas.common import APIModel

__all__ = [
    "VisionAnalyzeResponse",
    "ResolutionCheckResponse",
    "WorkerSuggestionResponse",
    "AutoRouteResponse",
]


class VisionAnalyzeResponse(APIModel):
    category: ReportCategory
    priority: ReportPriority
    title: str
    description: str
    location_hint: str | None = None
    confidence: float
    source: str
    spam_score: float = 0.0
    is_spam: bool = False
    spam_reason: str | None = None


class ResolutionCheckResponse(APIModel):
    match_score: float
    looks_fixed: bool
    reason: str
    flagged_for_review: bool


class WorkerSuggestionResponse(APIModel):
    worker_id: int
    worker_name: str
    department_id: int | None
    open_assignments: int
    recent_on_time_rate: float
    score: float


class AutoRouteResponse(APIModel):
    department_id: int | None
    department_name: str | None
    suggested_worker: WorkerSuggestionResponse | None
