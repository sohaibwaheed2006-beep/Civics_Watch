"""Schemas for the worker-of-the-month bonus."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import APIModel

__all__ = ["WorkerBonusRead", "WorkerScoreRead"]


class WorkerBonusRead(APIModel):
    id: int
    period_year: int
    period_month: int
    worker_id: int
    worker_name: str | None = None
    resolved_count: int
    average_rating: float
    average_hours_to_resolve: float | None = None
    on_time_rate: float
    total_score: float
    created_at: datetime
    updated_at: datetime


class WorkerScoreRead(APIModel):
    worker_id: int
    worker_name: str
    resolved_count: int
    average_rating: float
    average_hours_to_resolve: float | None = None
    on_time_rate: float
    total_score: float
