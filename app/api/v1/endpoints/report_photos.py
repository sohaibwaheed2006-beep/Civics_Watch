"""Report photo endpoints: upload, list, delete, and dev-serve.

Mounted under ``/reports``: paths are ``/reports/{id}/photos`` and
``/reports/{id}/photos/{photo_id}``.
"""

from __future__ import annotations

from pathlib import Path as FsPath
from typing import Annotated

from fastapi import APIRouter, File, Path, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, SettingsDep
from app.core.enums import UserRole
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.report import Report
from app.models.report_photo import ReportPhoto
from app.schemas.common import ErrorResponse, MessageResponse
from app.schemas.report_photo import ReportPhotoRead
from app.services.image_storage_service import (
    generate_storage_key,
    get_storage,
    validate_image,
)

router = APIRouter()

_AUTH_ERRORS: dict[int | str, dict[str, object]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
}


def _photo_url(request: Request, photo_id: int) -> str:
    """Build a URL to the dev photo-serving endpoint for this photo id.

    Internal storage keys never appear in responses.
    """
    return str(request.url_for("get_report_photo_bytes", photo_id=photo_id))


def _to_photo_read(photo: ReportPhoto, request: Request) -> ReportPhotoRead:
    return ReportPhotoRead(
        id=photo.id,
        report_id=photo.report_id,
        original_filename=photo.original_filename,
        content_type=photo.content_type,
        file_size=photo.file_size,
        created_at=photo.created_at,
        url=_photo_url(request, photo.id),
    )


@router.post(
    "/{report_id}/photos",
    response_model=ReportPhotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo for a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def upload_photo(
    db: DbSession,
    current_user: CurrentUser,
    settings: SettingsDep,
    request: Request,
    report_id: Annotated[int, Path(ge=1)],
    file: Annotated[UploadFile, File(description="Image to attach.")],
) -> ReportPhotoRead:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")

    role = UserRole(current_user.role)
    if role != UserRole.ADMIN:
        if role == UserRole.WORKER:
            if report.assigned_worker_id != current_user.id:
                raise PermissionDeniedError(
                    "Only the assigned worker may upload photos."
                )
        elif report.citizen_id != current_user.id:
            raise PermissionDeniedError(
                "Only the report owner may upload photos."
            )

    # Enforce the per-report cap.
    photo_count = int(
        db.execute(
            select(func.count())
            .select_from(ReportPhoto)
            .where(ReportPhoto.report_id == report.id)
        ).scalar_one()
    )
    if photo_count >= settings.MAX_PHOTOS_PER_REPORT:
        raise ConflictError(
            f"This report already has the maximum of "
            f"{settings.MAX_PHOTOS_PER_REPORT} photos."
        )

    data = await file.read()
    content_type = validate_image(
        data=data,
        declared_content_type=file.content_type or "",
        max_bytes=settings.max_upload_size_bytes,
    )
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[content_type]
    key = generate_storage_key(report_id=report.id, extension=extension)

    storage = get_storage(settings)
    storage.save(key, data)

    try:
        photo = ReportPhoto(
            report_id=report.id,
            storage_key=key,
            original_filename=(file.filename or "upload")[:255],
            content_type=content_type,
            file_size=len(data),
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
    except Exception:
        # Clean up the orphan file; the metadata row never made it in.
        try:
            storage.delete(key)
        except Exception:
            pass
        raise

    return _to_photo_read(photo, request)


@router.get(
    "/{report_id}/photos",
    response_model=list[ReportPhotoRead],
    status_code=status.HTTP_200_OK,
    summary="List photos for a report",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def list_photos(
    db: DbSession,
    current_user: CurrentUser,
    request: Request,
    report_id: Annotated[int, Path(ge=1)],
) -> list[ReportPhotoRead]:
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    stmt = (
        select(ReportPhoto)
        .where(ReportPhoto.report_id == report.id)
        .order_by(ReportPhoto.id.asc())
    )
    return [_to_photo_read(p, request) for p in db.execute(stmt).scalars().all()]


@router.delete(
    "/{report_id}/photos/{photo_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a report photo",
    responses={
        **_AUTH_ERRORS,
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def delete_photo(
    db: DbSession,
    current_user: CurrentUser,
    settings: SettingsDep,
    report_id: Annotated[int, Path(ge=1)],
    photo_id: Annotated[int, Path(ge=1)],
) -> MessageResponse:
    photo = db.get(ReportPhoto, photo_id)
    if photo is None or photo.report_id != report_id:
        raise NotFoundError("Photo not found.")
    report = db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")

    role = UserRole(current_user.role)
    if role != UserRole.ADMIN and report.citizen_id != current_user.id:
        raise PermissionDeniedError(
            "Only the report owner or an admin may delete photos."
        )

    storage = get_storage(settings)
    key = photo.storage_key
    db.delete(photo)
    db.commit()
    try:
        storage.delete(key)
    except Exception:
        # Metadata is already gone; a leftover file is a cleanup task, not an
        # API error. Keep the request successful.
        pass
    return MessageResponse(message="Photo deleted.")


# ---------------------------------------------------------------------------
# Dev-only byte serving.
#
# In production, replace with an S3 presigned URL or an nginx X-Accel route.
# Here it goes through the API so the storage abstraction stays authoritative.
# ---------------------------------------------------------------------------
@router.get(
    "/photos/{photo_id}/content",
    name="get_report_photo_bytes",
    summary="Serve the bytes of a photo (dev)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def get_photo_bytes(
    db: DbSession,
    current_user: CurrentUser,
    settings: SettingsDep,
    photo_id: Annotated[int, Path(ge=1)],
) -> FileResponse:
    photo = db.get(ReportPhoto, photo_id)
    if photo is None:
        raise NotFoundError("Photo not found.")
    storage = get_storage(settings)
    try:
        path: FsPath = storage.path(photo.storage_key)
    except BadRequestError:
        raise NotFoundError("Photo not found.")
    if not path.exists():
        raise NotFoundError("Photo not found.")
    return FileResponse(path, media_type=photo.content_type)
