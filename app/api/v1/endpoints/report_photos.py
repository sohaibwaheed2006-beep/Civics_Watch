"""Report photo endpoints: upload, list, delete, and dev-serve.

Mounted under ``/reports``: paths are ``/reports/{id}/photos`` and
``/reports/{id}/photos/{photo_id}``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Path, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, SettingsDep
from app.core.config import Settings
from app.core.enums import UserRole
from app.core.exceptions import (
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


def _photo_url(settings: Settings, photo_id: int) -> str:
    """Build a *same-origin, relative* URL to the photo-serving endpoint.

    A relative path (``/api/v1/reports/photos/{id}/content``) loads from
    whatever origin served the app — the Vite dev origin, a public tunnel, or
    another device on the LAN — and is forwarded to the backend by the dev
    proxy. An absolute URL baked from the request host (``127.0.0.1:8000``)
    only worked for a browser on this exact machine and showed a broken image
    everywhere else. Internal storage keys never appear in responses.
    """
    return f"{settings.API_V1_PREFIX}/reports/photos/{photo_id}/content"


def _to_photo_read(photo: ReportPhoto, settings: Settings) -> ReportPhotoRead:
    # With object storage (Supabase) the public CDN URL is absolute and
    # origin-independent, so the <img> loads no matter where the frontend and
    # API are hosted (e.g. a Vercel SPA calling a Render API). The local-disk
    # backend has no public URL, so fall back to the same-origin content route.
    url: str | None = None
    if settings.photo_storage_is_supabase:
        try:
            url = get_storage(settings).url(photo.storage_key)
        except Exception:
            url = None
    if not url:
        url = _photo_url(settings, photo.id)
    return ReportPhotoRead(
        id=photo.id,
        report_id=photo.report_id,
        original_filename=photo.original_filename,
        content_type=photo.content_type,
        file_size=photo.file_size,
        created_at=photo.created_at,
        url=url,
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

    return _to_photo_read(photo, settings)


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
    settings: SettingsDep,
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
    return [_to_photo_read(p, settings) for p in db.execute(stmt).scalars().all()]


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
#
# This route is intentionally UNAUTHENTICATED: browsers load it through an
# ``<img src>`` tag, which cannot attach the bearer token, so requiring auth
# here makes every photo 404/401 in the UI. Reports (and their photos) are
# already public on the issue map, so serving the bytes by opaque photo id is
# acceptable for this dev path. A production CDN/presigned-URL layer replaces
# it entirely.
# ---------------------------------------------------------------------------
@router.get(
    "/photos/{photo_id}/content",
    name="get_report_photo_bytes",
    summary="Serve a photo (public): redirect to object storage, or stream bytes",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def get_photo_bytes(
    db: DbSession,
    settings: SettingsDep,
    photo_id: Annotated[int, Path(ge=1)],
) -> Response:
    photo = db.get(ReportPhoto, photo_id)
    if photo is None:
        raise NotFoundError("Photo not found.")
    storage = get_storage(settings)

    # Object-storage backends (Supabase) expose a CDN URL: redirect the browser
    # there so the bytes never round-trip through the API. The local-disk
    # backend returns None and we stream the bytes instead.
    public_url = storage.url(photo.storage_key)
    if public_url:
        return RedirectResponse(public_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    try:
        data = storage.read(photo.storage_key)
    except Exception:
        raise NotFoundError("Photo not found.")
    return Response(content=data, media_type=photo.content_type)
