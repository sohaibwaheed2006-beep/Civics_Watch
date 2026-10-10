"""Assignment schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel

__all__ = ["AssignmentCreate", "AssignmentRead"]


class AssignmentCreate(APIModel):
    """Body for ``POST /reports/{id}/assign``."""

    worker_id: int = Field(ge=1, description="ID of the worker to assign.")
    notes: str | None = Field(default=None, max_length=1000)


class AssignmentRead(APIModel):
    id: int
    report_id: int
    worker_id: int
    assigned_by_id: int
    department_id: int | None = None
    notes: str | None = None
    assigned_at: datetime
    unassigned_at: datetime | None = None
    active: bool
