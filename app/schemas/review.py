"""Schemas for citizen reviews on resolved reports."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.schemas.common import APIModel

__all__ = ["ReviewCreate", "ReviewRead"]


class ReviewCreate(APIModel):
    rating: Annotated[int, Field(ge=1, le=5)]
    comment: str | None = Field(default=None, max_length=1000)


class ReviewRead(APIModel):
    id: int
    report_id: int
    worker_id: int
    citizen_id: int
    rating: int
    comment: str | None = None
    created_at: datetime
    updated_at: datetime
