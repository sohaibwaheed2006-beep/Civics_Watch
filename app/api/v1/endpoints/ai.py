"""AI-assist endpoints: vision auto-fill, resolution check, auto-routing.

These sit alongside the existing report endpoints rather than inside them so
the vision upload path doesn't have to double as the primary submission one;
a citizen can analyze a photo without committing to creating a report.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, UploadFile, status
from sqlalchemy import select

from app.api.deps import (
    CurrentUser,
    DbSession,
    SettingsDep,
    require_admin,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.report import Report
from app.schemas.ai import (
    AutoRouteResponse,
    ResolutionCheckResponse,
    VisionAnalyzeResponse,
    WorkerSuggestionResponse,
)
from app.schemas.common import ErrorResponse
from app.services import (
    image_storage_service,
    routing_service,
    vision_service,
)

router = APIRouter()


@router.post(
    "/vision/analyze",
    response_model=VisionAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a photo and prefill the citizen report form",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def vision_analyze(
    current_user: CurrentUser,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="Citizen's issue photo.")],
) -> VisionAnalyzeResponse:
    data = await file.read()
    if not data:
        raise ConflictError("Uploaded file was empty.")
    image_storage_service.validate_image(
        data=data,
        declared_content_type=file.content_type or "",
        max_bytes=settings.max_upload_size_bytes,
    )
    result = vision_service.analyze_report_photo(data)
    if result is None:
        raise NotFoundError(
            "Vision analysis is unavailable. Please fill the form manually."
        )
    return VisionAnalyzeResponse(
        category=result.category,
        priority=result.priority,
        title=result.title,
        description=result.description,
        location_hint=result.location_hint,
        confidence=result.confidence,
        source=result.source,
        spam_score=result.spam_score,
        is_spam=result.is_spam,
        spam_reason=result.spam_reason,
    )


@router.post(
    "/vision/verify-resolution/{report_id}",
    response_model=ResolutionCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check a resolution photo against the complaint",
    dependencies=[Depends(require_admin)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def vision_verify_resolution(
    db: DbSession,
    settings: SettingsDep,
    report_id: Annotated[int, Path(ge=1)],
    file: Annotated[UploadFile, File(description="Worker's fix photo.")],
) -> ResolutionCheckResponse:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    data = await file.read()
    if not data:
        raise ConflictError("Uploaded file was empty.")
    image_storage_service.validate_image(
        data=data,
        declared_content_type=file.content_type or "",
        max_bytes=settings.max_upload_size_bytes,
    )
    verdict = vision_service.verify_resolution_photo(
        image_bytes=data,
        category=report.category,
        title=report.title,
        description=report.description,
    )
    if verdict is None:
        raise NotFoundError("Vision verification is unavailable.")
    flagged = (
        verdict.match_score < settings.RESOLUTION_MATCH_MIN_SCORE
        or not verdict.looks_fixed
    )
    report.resolution_photo_match_score = verdict.match_score
    report.resolution_review_reason = verdict.reason
    report.resolution_flagged_for_review = flagged
    db.commit()
    return ResolutionCheckResponse(
        match_score=verdict.match_score,
        looks_fixed=verdict.looks_fixed,
        reason=verdict.reason,
        flagged_for_review=flagged,
    )


@router.get(
    "/reports/{report_id}/auto-route",
    response_model=AutoRouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Suggest department + worker for a report (admin triage)",
    dependencies=[Depends(require_admin)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def auto_route(
    db: DbSession,
    report_id: Annotated[int, Path(ge=1)],
) -> AutoRouteResponse:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")

    # Prefer the department the report is already attached to; otherwise
    # fall back to the category-based hint.
    department = report.department
    if department is None:
        department = routing_service.suggest_department(
            db, category=report.category
        )

    suggestion = routing_service.suggest_worker(db, department=department)
    return AutoRouteResponse(
        department_id=department.id if department else None,
        department_name=department.name if department else None,
        suggested_worker=(
            WorkerSuggestionResponse(
                worker_id=suggestion.worker_id,
                worker_name=suggestion.worker_name,
                department_id=suggestion.department_id,
                open_assignments=suggestion.open_assignments,
                recent_on_time_rate=suggestion.recent_on_time_rate,
                score=suggestion.score,
            )
            if suggestion is not None
            else None
        ),
    )


@router.get(
    "/reports/{report_id}/cluster",
    status_code=status.HTTP_200_OK,
    summary="List the other reports in this report's incident cluster",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def cluster_members(
    db: DbSession,
    current_user: CurrentUser,
    report_id: Annotated[int, Path(ge=1)],
) -> dict[str, object]:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    if report.incident_cluster_id is None:
        return {
            "cluster_id": None,
            "canonical_report_id": report.id,
            "members": [],
        }
    members = db.execute(
        select(Report)
        .where(Report.incident_cluster_id == report.incident_cluster_id)
        .order_by(Report.created_at.asc(), Report.id.asc())
    ).scalars().all()
    canonical = members[0] if members else report
    return {
        "cluster_id": report.incident_cluster_id,
        "canonical_report_id": canonical.id,
        "members": [
            {
                "id": m.id,
                "title": m.title,
                "status": m.status.value,
                "created_at": m.created_at,
                "citizen_id": m.citizen_id,
            }
            for m in members
        ],
    }
