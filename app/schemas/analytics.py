"""Analytics response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from app.schemas.common import APIModel

__all__ = [
    "OverviewRead",
    "StatusBucket",
    "CategoryBucket",
    "TimeBucket",
    "DepartmentPerformanceRead",
]


class OverviewRead(APIModel):
    total_reports: int = Field(ge=0)
    open_reports: int = Field(ge=0)
    resolved_reports: int = Field(ge=0)
    rejected_reports: int = Field(ge=0)
    overdue_reports: int = Field(ge=0)
    reports_last_7_days: int = Field(ge=0)
    average_resolution_hours: float | None = None


class StatusBucket(APIModel):
    status: str
    count: int


class CategoryBucket(APIModel):
    category: str
    count: int


class TimeBucket(APIModel):
    day: date
    count: int


class DepartmentPerformanceRead(APIModel):
    department_id: int
    department_name: str
    total_reports: int
    resolved_reports: int
    overdue_reports: int
    average_resolution_hours: float | None = None
