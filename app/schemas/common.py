"""Shared schema building blocks used across every domain module.

Defines the response conventions that the auth, user, department and (later)
report modules all follow: the error envelope, the pagination envelope, and
the base model configuration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Annotated, Generic, Literal, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

__all__ = [
    "APIModel",
    "ErrorDetail",
    "ErrorBody",
    "ErrorResponse",
    "HealthResponse",
    "MessageResponse",
    "PaginationMeta",
    "Page",
    "SortOrder",
]

T = TypeVar("T")


class APIModel(BaseModel):
    """Base model for request and response schemas.

    - ``from_attributes`` lets response models be built straight from ORM
      objects once SQLAlchemy lands in Phase 2.
    - ``str_strip_whitespace`` normalises padded input.
    - ``extra="forbid"`` makes unknown request fields a 422 instead of being
      silently dropped, which is what stops a client from attempting to set a
      protected field such as ``role``.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
        populate_by_name=True,
    )


# ---------------------------------------------------------------------------
# Errors - mirrors app.core.exceptions.build_error_payload
# ---------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    """A single field-level problem."""

    field: str = Field(
        description="Dotted path to the offending field, e.g. 'body.email'.",
        examples=["body.email"],
    )
    message: str = Field(
        description="Human-readable description of the problem.",
        examples=["value is not a valid email address"],
    )
    type: str = Field(
        description="Machine-readable validation error type.",
        examples=["value_error"],
    )


class ErrorBody(BaseModel):
    code: str = Field(
        description="Stable, machine-readable error code.",
        examples=["not_found"],
    )
    message: str = Field(
        description="Human-readable summary, safe to display to a user.",
        examples=["Resource not found."],
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Field-level breakdown; empty for non-validation errors.",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation ID of the request, for support and log lookup.",
    )


class ErrorResponse(BaseModel):
    """The canonical error payload for every non-2xx response."""

    error: ErrorBody

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "not_found",
                    "message": "Resource not found.",
                    "details": [],
                    "request_id": "9f1c2b7a4e6d4f0b8c3a1d2e5f6a7b8c",
                }
            }
        }
    )


# ---------------------------------------------------------------------------
# Simple responses
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """Liveness payload. Deliberately free of configuration detail."""

    status: Literal["ok"] = Field(
        default="ok", description="'ok' when the API process is serving requests."
    )
    app_name: str = Field(description="Configured application name.")
    environment: str = Field(description="Active APP_ENV value.")
    version: str = Field(description="API version identifier.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Server time in UTC when the check ran.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "app_name": "Neighborhood Issue Reporter API",
                "environment": "local",
                "version": "1.0.0",
                "timestamp": "2026-10-10T12:00:00Z",
            }
        }
    )


class MessageResponse(BaseModel):
    """Generic acknowledgement for actions with no resource to return."""

    message: str = Field(description="Human-readable result of the action.")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
SortOrder = Literal["asc", "desc"]

#: Query-parameter aliases shared by every paginated list endpoint.
PageNumber = Annotated[int, Field(ge=1, description="1-based page number.")]
PageSize = Annotated[
    int, Field(ge=1, le=100, description="Items per page (max 100).")
]


class PaginationMeta(BaseModel):
    """Counts describing the current slice of a collection."""

    page: int = Field(ge=1, description="1-based page number of this slice.")
    page_size: int = Field(ge=1, description="Requested items per page.")
    total_items: int = Field(ge=0, description="Total matching items.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return ceil(self.total_items / self.page_size)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_previous(self) -> bool:
        return self.page > 1


class Page(BaseModel, Generic[T]):
    """Envelope for every paginated list response.

    Example
    -------
    ``Page[UserRead]`` serialises as::

        {"items": [...], "meta": {"page": 1, "page_size": 20, ...}}
    """

    items: list[T] = Field(default_factory=list, description="Items on this page.")
    meta: PaginationMeta = Field(description="Pagination counters.")

    @classmethod
    def create(
        cls,
        *,
        items: Sequence[T],
        page: int,
        page_size: int,
        total_items: int,
    ) -> "Page[T]":
        """Build a page from a materialised slice and its total count."""
        return cls(
            items=list(items),
            meta=PaginationMeta(
                page=page, page_size=page_size, total_items=total_items
            ),
        )
