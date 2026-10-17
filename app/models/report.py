"""Report model.

The citizen-submitted record describing a local issue. All lifecycle, workflow
and ownership details live in surrounding models (StatusHistory, Assignment,
Vote, Notification, ReportPhoto); this row holds the identity, routing and
current status.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ReportCategory, ReportPriority, ReportStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # avoid circular imports at runtime
    from app.models.assignment import Assignment
    from app.models.department import Department
    from app.models.report_photo import ReportPhoto
    from app.models.status_history import StatusHistory
    from app.models.user import User
    from app.models.vote import Vote

__all__ = ["Report"]


def _enum(enum_cls: type) -> Enum:
    """Produce a VARCHAR + CHECK enum matching the project's convention."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Report(TimestampMixin, Base):
    """A single citizen-submitted issue."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="latitude_range"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="longitude_range"
        ),
        Index("ix_reports_status_created_at", "status", "created_at"),
        Index("ix_reports_category_status", "category", "status"),
        Index("ix_reports_department_status", "department_id", "status"),
        {"comment": "Citizen-submitted issue reports."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(
        String(200), nullable=False, doc="Short descriptive title."
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, doc="Full description of the issue."
    )

    category: Mapped[ReportCategory] = mapped_column(
        _enum(ReportCategory),
        nullable=False,
        index=True,
        doc="Issue classification; drives routing and SLA.",
    )
    priority: Mapped[ReportPriority] = mapped_column(
        _enum(ReportPriority),
        nullable=False,
        default=ReportPriority.MEDIUM,
        server_default=ReportPriority.MEDIUM.value,
        index=True,
        doc="Current priority. May be refined after triage.",
    )
    status: Mapped[ReportStatus] = mapped_column(
        _enum(ReportStatus),
        nullable=False,
        default=ReportStatus.SUBMITTED,
        server_default=ReportStatus.SUBMITTED.value,
        index=True,
        doc="Lifecycle state; only mutated by the workflow service.",
    )

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location_text: Mapped[str | None] = mapped_column(
        String(500), nullable=True, doc="Human-readable address, optional."
    )

    citizen_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_reports_citizen"),
        nullable=False,
        index=True,
        doc="The citizen who filed the report.",
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id", ondelete="SET NULL", name="fk_reports_department"
        ),
        nullable=True,
        index=True,
        doc="Routing department, nullable before triage.",
    )
    assigned_worker_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id", ondelete="SET NULL", name="fk_reports_worker"
        ),
        nullable=True,
        index=True,
        doc="Current assignee (also kept in Assignment history).",
    )
    duplicate_of_report_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "reports.id", ondelete="SET NULL", name="fk_reports_duplicate_of"
        ),
        nullable=True,
        index=True,
        doc="Points to the canonical report, if this one is flagged as a duplicate.",
    )

    ai_category: Mapped[str | None] = mapped_column(
        String(32), nullable=True, doc="AI-suggested category, if any."
    )
    ai_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="AI confidence score (0..1)."
    )
    ai_title_suggested: Mapped[str | None] = mapped_column(
        String(200), nullable=True, doc="Vision-generated title suggestion."
    )
    ai_description_suggested: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Vision-generated description suggestion."
    )
    ai_priority_suggested: Mapped[str | None] = mapped_column(
        String(16), nullable=True, doc="Vision-generated priority suggestion."
    )
    duplicate_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Best duplicate similarity found at submission."
    )
    incident_cluster_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc=(
            "Shared cluster id for reports that likely describe the same "
            "real-world incident. The canonical report in a cluster is the "
            "oldest one; all duplicate_of_report_id members share its value."
        ),
    )

    resolution_photo_match_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc=(
            "Gemini Vision score (0..1) comparing the worker's evidence "
            "photo to the original complaint. Null if the check never ran."
        ),
    )
    resolution_flagged_for_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc=(
            "True when the resolution-note quality check scored below the "
            "configured threshold and the closure should be audited."
        ),
    )
    resolution_review_reason: Mapped[str | None] = mapped_column(
        String(400),
        nullable=True,
        doc="Short reason from the vision model, if the closure was flagged.",
    )

    spam_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Spam/junk likelihood (0..1) assessed at submission.",
    )
    spam_flagged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
        doc=(
            "True when the report scored in the borderline spam band and "
            "needs a human to confirm or dismiss it."
        ),
    )
    spam_reason: Mapped[str | None] = mapped_column(
        String(400),
        nullable=True,
        doc="Short reason from the spam filter, if scored above zero.",
    )

    deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    citizen: Mapped["User"] = relationship(
        "User",
        foreign_keys=[citizen_id],
        lazy="joined",
    )
    department: Mapped["Department | None"] = relationship(
        "Department",
        foreign_keys=[department_id],
        lazy="joined",
    )
    assigned_worker: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_worker_id],
        lazy="joined",
    )
    duplicate_of: Mapped["Report | None"] = relationship(
        "Report",
        foreign_keys=[duplicate_of_report_id],
        remote_side="Report.id",
    )

    photos: Mapped[list["ReportPhoto"]] = relationship(
        "ReportPhoto",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    status_history: Mapped[list["StatusHistory"]] = relationship(
        "StatusHistory",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StatusHistory.created_at",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    votes: Mapped[list["Vote"]] = relationship(
        "Vote",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return (
            f"Report(id={self.id!r}, status={self.status!r}, "
            f"category={self.category!r}, citizen_id={self.citizen_id!r})"
        )
