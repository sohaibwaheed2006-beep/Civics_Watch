"""Status history schemas."""

from __future__ import annotations

from datetime import datetime

from app.core.enums import ReportStatus
from app.schemas.common import APIModel

__all__ = ["StatusHistoryRead"]


class StatusHistoryRead(APIModel):
    id: int
    report_id: int
    old_status: ReportStatus | None = None
    new_status: ReportStatus
    changed_by_id: int
    note: str | None = None
    created_at: datetime
