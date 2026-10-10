"""Report photo schemas."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import APIModel

__all__ = ["ReportPhotoRead"]


class ReportPhotoRead(APIModel):
    id: int
    report_id: int
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime
    url: str
