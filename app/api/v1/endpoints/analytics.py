"""Admin analytics endpoints. Mounted under ``/analytics``."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, DbSession
from app.schemas.analytics import (
    CategoryBucket,
    DepartmentPerformanceRead,
    OverviewRead,
    StatusBucket,
    TimeBucket,
)
from app.schemas.common import ErrorResponse
from app.schemas.report import ReportSummary
from app.services import analytics_service

router = APIRouter()

_ADMIN_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}


@router.get(
    "/overview",
    response_model=OverviewRead,
    status_code=status.HTTP_200_OK,
    summary="High-level counters",
    responses=_ADMIN_ERRORS,
)
def overview(
    db: DbSession,
    admin: AdminUser,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> OverviewRead:
    data = analytics_service.overview(db, date_from=date_from, date_to=date_to)
    return OverviewRead.model_validate(data)


@router.get(
    "/reports-by-status",
    response_model=list[StatusBucket],
    status_code=status.HTTP_200_OK,
    summary="Report counts by status",
    responses=_ADMIN_ERRORS,
)
def reports_by_status(
    db: DbSession,
    admin: AdminUser,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[StatusBucket]:
    rows = analytics_service.reports_by_status(
        db, date_from=date_from, date_to=date_to
    )
    return [StatusBucket.model_validate(r) for r in rows]


@router.get(
    "/reports-by-category",
    response_model=list[CategoryBucket],
    status_code=status.HTTP_200_OK,
    summary="Report counts by category",
    responses=_ADMIN_ERRORS,
)
def reports_by_category(
    db: DbSession,
    admin: AdminUser,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[CategoryBucket]:
    rows = analytics_service.reports_by_category(
        db, date_from=date_from, date_to=date_to
    )
    return [CategoryBucket.model_validate(r) for r in rows]


@router.get(
    "/reports-over-time",
    response_model=list[TimeBucket],
    status_code=status.HTTP_200_OK,
    summary="Daily report creation counts",
    responses=_ADMIN_ERRORS,
)
def reports_over_time(
    db: DbSession,
    admin: AdminUser,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[TimeBucket]:
    rows = analytics_service.reports_over_time(
        db, date_from=date_from, date_to=date_to
    )
    return [TimeBucket.model_validate(r) for r in rows]


@router.get(
    "/department-performance",
    response_model=list[DepartmentPerformanceRead],
    status_code=status.HTTP_200_OK,
    summary="Per-department throughput",
    responses=_ADMIN_ERRORS,
)
def department_performance(
    db: DbSession, admin: AdminUser
) -> list[DepartmentPerformanceRead]:
    rows = analytics_service.department_performance(db)
    return [DepartmentPerformanceRead.model_validate(r) for r in rows]


@router.get(
    "/overdue-reports",
    response_model=list[ReportSummary],
    status_code=status.HTTP_200_OK,
    summary="Open reports past their deadline",
    responses=_ADMIN_ERRORS,
)
def overdue_reports(
    db: DbSession,
    admin: AdminUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ReportSummary]:
    items = analytics_service.overdue_reports(db, limit=limit)
    return [
        ReportSummary(
            id=r.id,
            title=r.title,
            category=r.category,
            priority=r.priority,
            status=r.status,
            latitude=r.latitude,
            longitude=r.longitude,
            citizen_id=r.citizen_id,
            department_id=r.department_id,
            assigned_worker_id=r.assigned_worker_id,
            created_at=r.created_at,
            updated_at=r.updated_at,
            deadline_at=r.deadline_at,
            resolved_at=r.resolved_at,
            vote_count=0,
        )
        for r in items
    ]
