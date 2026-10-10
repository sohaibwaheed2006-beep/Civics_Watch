"""Report photo metadata.

File bytes live in the configured storage backend (local filesystem in
development); this row holds the metadata that lets the API serve them safely
without exposing filesystem paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.report import Report

__all__ = ["ReportPhoto"]


class ReportPhoto(TimestampMixin, Base):
    """Metadata describing one uploaded photo attached to a report."""

    __tablename__ = "report_photos"
    __table_args__ = ({"comment": "Metadata for photos attached to reports."},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reports.id", ondelete="CASCADE", name="fk_report_photos_report"
        ),
        nullable=False,
        index=True,
    )

    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc=(
            "Relative key into the storage backend. Server-generated; never a "
            "user-supplied path."
        ),
    )
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Client-supplied name, kept for display."
    )
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped["Report"] = relationship("Report", back_populates="photos")

    def __repr__(self) -> str:  # pragma: no cover
        return f"ReportPhoto(id={self.id!r}, report_id={self.report_id!r})"
