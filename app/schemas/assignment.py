"""Assignment schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.core.enums import ReportPriority
from app.schemas.common import APIModel

__all__ = ["AssignmentCreate", "AssignmentRead"]


class AssignmentCreate(APIModel):
    """Body for ``POST /reports/{id}/assign``.

    The admin dispatch modal also lets the operator set the report's priority
    and a target deadline at assignment time, so those optional fields are
    accepted here and applied to the report. ``department_id`` is accepted for
    backwards compatibility with the client payload but ignored: the effective
    department is always derived from the worker being assigned.
    """

    worker_id: int = Field(ge=1, description="ID of the worker to assign.")
    notes: str | None = Field(default=None, max_length=1000)
    department_id: int | None = Field(
        default=None,
        ge=1,
        description="Accepted for compatibility; the department is taken from the worker.",
    )
    priority: ReportPriority | None = Field(
        default=None, description="Optional new priority for the report."
    )
    deadline: datetime | None = Field(
        default=None,
        description="Optional target deadline; stored as the report's deadline_at.",
    )


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
