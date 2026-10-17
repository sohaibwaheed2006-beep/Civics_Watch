"""Local filesystem image storage with a thin abstraction.

File bytes land under ``settings.upload_path``; the DB holds only metadata.
Every method is defensive: filenames are server-generated, user paths are
rejected, orphaned files are cleaned up when metadata persistence fails.

The ``Storage`` interface is intentionally small so an S3-backed implementation
can replace it without touching callers.
"""

from __future__ import annotations

import os
import secrets
import uuid
from pathlib import Path
from typing import Final, Protocol

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "IMAGE_SIGNATURES",
    "Storage",
    "LocalFilesystemStorage",
    "SupabaseImageStorage",
    "get_storage",
    "validate_image",
    "generate_storage_key",
    "ensure_safe_relative_path",
]

#: Extension -> MIME type, so a stored object is served with the right content
#: type (a public URL with the wrong type makes the browser download, not show).
_EXTENSION_CONTENT_TYPE: Final[dict[str, str]] = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

#: MIME types the API will accept for a photo upload.
ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

#: Magic-byte signatures used to verify the actual bytes are an image.
IMAGE_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # RIFF container; verify "WEBP" later
)


def _sniff_content_type(data: bytes) -> str | None:
    for sig, ctype in IMAGE_SIGNATURES:
        if data.startswith(sig):
            if ctype == "image/webp" and len(data) >= 12 and data[8:12] == b"WEBP":
                return ctype
            if ctype != "image/webp":
                return ctype
    return None


def validate_image(
    *, data: bytes, declared_content_type: str, max_bytes: int
) -> str:
    """Validate size and content; return the sniffed MIME type.

    Trusting the client-supplied content type would let an attacker upload a
    disguised script and have it served back as an image. We check the file
    bytes directly instead.
    """
    if len(data) == 0:
        raise BadRequestError("Uploaded file is empty.")
    if len(data) > max_bytes:
        raise BadRequestError(
            f"Uploaded file exceeds the {max_bytes // 1024 // 1024} MB limit."
        )
    sniffed = _sniff_content_type(data)
    if sniffed is None:
        raise BadRequestError(
            "Uploaded file is not a supported image (JPEG, PNG or WebP)."
        )
    if declared_content_type and declared_content_type not in ALLOWED_CONTENT_TYPES:
        raise BadRequestError(
            f"Unsupported content type: {declared_content_type!r}."
        )
    return sniffed


def generate_storage_key(*, report_id: int, extension: str) -> str:
    """Produce a server-generated relative key: ``reports/{id}/{uuid}.ext``.

    Only trusted extensions (``.jpg``, ``.png``, ``.webp``) are allowed.
    """
    ext = extension.lower().lstrip(".")
    if ext == "jpeg":
        ext = "jpg"
    if ext not in {"jpg", "png", "webp"}:
        raise BadRequestError(f"Unsupported file extension: {extension!r}.")
    rand = secrets.token_hex(8)
    uid = uuid.uuid4().hex
    return f"reports/{int(report_id)}/{rand}-{uid}.{ext}"


def ensure_safe_relative_path(root: Path, key: str) -> Path:
    """Resolve a storage key under ``root`` and refuse to escape it."""
    if not key or "\x00" in key or ".." in key.replace("\\", "/").split("/"):
        raise BadRequestError("Invalid storage key.")
    resolved = (root / key).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise BadRequestError("Storage key escapes the upload root.") from exc
    return resolved


class Storage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def read(self, key: str) -> bytes: ...
    def url(self, key: str) -> str | None: ...
    def path(self, key: str) -> Path: ...


class LocalFilesystemStorage:
    """Minimal local-fs implementation of :class:`Storage`."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _resolve(self, key: str) -> Path:
        return ensure_safe_relative_path(self._root, key)

    def save(self, key: str, data: bytes) -> None:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        try:
            with open(tmp, "wb") as handle:
                handle.write(data)
            os.replace(tmp, target)
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            raise

    def delete(self, key: str) -> None:
        target = self._resolve(key)
        try:
            target.unlink()
        except FileNotFoundError:
            # Nothing to do; the metadata row is already being deleted.
            return

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).exists()
        except Exception:
            return False

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def url(self, key: str) -> str | None:
        # Local files have no external URL; callers serve the bytes themselves.
        return None

    def path(self, key: str) -> Path:
        return self._resolve(key)


class SupabaseImageStorage:
    """Supabase Storage implementation of :class:`Storage`.

    Bytes live in a Supabase Storage bucket; the database still holds only
    metadata. Unlike :class:`LocalFilesystemStorage` this survives host restarts
    and works on ephemeral/serverless filesystems, so it is the backend to use
    in production (Render, Vercel, ...).

    The admin (service-role) client is used so uploads and deletes are never
    blocked by Row Level Security. Reads are served to browsers via the bucket's
    public URL (make the bucket public in the Supabase dashboard).
    """

    def __init__(self, bucket: str) -> None:
        self._bucket = bucket

    def _api(self):  # noqa: ANN202 - supabase SDK type is version-dependent
        # Imported lazily so local/dev and tests never need the supabase SDK or
        # credentials unless this backend is actually selected.
        from app.core.supabase import get_supabase_admin_client

        return get_supabase_admin_client().storage.from_(self._bucket)

    @staticmethod
    def _content_type_for(key: str) -> str:
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        return _EXTENSION_CONTENT_TYPE.get(ext, "application/octet-stream")

    def save(self, key: str, data: bytes) -> None:
        self._api().upload(
            path=key,
            file=data,
            file_options={
                "content-type": self._content_type_for(key),
                "cache-control": "3600",
                "upsert": "true",
            },
        )

    def delete(self, key: str) -> None:
        # A missing object is not an error for our callers; the metadata row is
        # already being removed. Swallow failures so delete stays idempotent.
        try:
            self._api().remove([key])
        except Exception:
            return

    def exists(self, key: str) -> bool:
        try:
            self._api().download(key)
            return True
        except Exception:
            return False

    def read(self, key: str) -> bytes:
        return self._api().download(key)

    def url(self, key: str) -> str | None:
        result = self._api().get_public_url(key)
        # supabase-py returns a plain string; stay defensive across versions.
        if isinstance(result, str):
            return result or None
        if isinstance(result, dict):  # pragma: no cover - older SDKs
            candidate = result.get("publicUrl") or result.get("public_url")
            return str(candidate) if candidate else None
        return None

    def path(self, key: str) -> Path:
        raise BadRequestError("Supabase storage has no local filesystem path.")


def get_storage(settings: Settings | None = None) -> Storage:
    settings = settings or get_settings()
    if settings.photo_storage_is_supabase:
        return SupabaseImageStorage(settings.SUPABASE_STORAGE_BUCKET)
    return LocalFilesystemStorage(settings.upload_path)
