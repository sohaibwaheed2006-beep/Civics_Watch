"""Department request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.schemas.common import APIModel

__all__ = [
    "DepartmentCreate",
    "DepartmentUpdate",
    "DepartmentRead",
    "DEFAULT_SLA_HOURS",
    "MAX_SLA_HOURS",
]

#: Three working days.
DEFAULT_SLA_HOURS = 72

#: One year. An upper bound keeps an obvious typo (e.g. 72000) out of the data.
MAX_SLA_HOURS = 8760

DepartmentName = Annotated[
    str,
    Field(
        min_length=2,
        max_length=150,
        description="Display name. Must be unique.",
        examples=["Roads & Pavements"],
    ),
]

SlaHours = Annotated[
    int,
    Field(
        gt=0,
        le=MAX_SLA_HOURS,
        description=(
            "Target resolution time in hours for reports routed to this "
            f"department. Must be positive and at most {MAX_SLA_HOURS}."
        ),
        examples=[72],
    ),
]

Description = Annotated[
    str,
    Field(max_length=2000, description="Optional longer description."),
]


class DepartmentCreate(APIModel):
    """Body for creating a department. Admin only."""

    name: DepartmentName
    description: Description | None = Field(default=None)
    default_sla_hours: SlaHours = Field(default=DEFAULT_SLA_HOURS)
    is_active: bool = Field(
        default=True, description="Create the department already active."
    )


class DepartmentUpdate(APIModel):
    """Body for updating a department. Admin only.

    Every field is optional; send only what should change. An empty body is
    rejected rather than treated as a successful no-op.
    """

    name: DepartmentName | None = Field(default=None)
    description: Description | None = Field(
        default=None, description="Send null to clear the description."
    )
    default_sla_hours: SlaHours | None = Field(default=None)
    is_active: bool | None = Field(
        default=None,
        description="Set false to retire the department, true to restore it.",
    )

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        return self


class DepartmentRead(APIModel):
    """Public representation of a department."""

    id: int = Field(description="Unique department identifier.")
    name: str = Field(description="Display name.")
    description: str | None = Field(default=None, description="Longer description.")
    is_active: bool = Field(description="False once the department is retired.")
    default_sla_hours: int = Field(description="Target resolution time in hours.")
    created_at: datetime = Field(description="Creation timestamp (UTC).")
    updated_at: datetime = Field(description="Last modification timestamp (UTC).")
