"""The shared SQLAlchemy declarative base.

**Every** model in the project inherits this one class. A second ``Base``
would produce a second ``MetaData``, and Alembic would then only see half the
schema - so the report-domain models must import this exact object:

    from app.db.base import Base

Importing ``app.db.base`` deliberately does **not** import the models. Use
:mod:`app.db.registry` when you need the full metadata (Alembic does).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["Base", "TimestampMixin", "utcnow"]


def utcnow() -> datetime:
    """Current time as an aware UTC datetime.

    Used for every timestamp so stored values are unambiguous. Note that
    MySQL's ``DATETIME`` has no timezone storage: values go in as UTC and come
    back naive, which is why nothing in the application should compare a
    database timestamp against a local-time value.
    """
    return datetime.now(timezone.utc)


#: Explicit, deterministic constraint names. Without this, MySQL and SQLite
#: invent different names and an Alembic downgrade cannot reliably drop a
#: constraint it did not name itself.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every model in the application."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """``created_at`` / ``updated_at`` columns with UTC defaults.

    Defaults are applied in Python rather than by the database so the two
    backends (MySQL in production, SQLite in tests) behave identically.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        doc="Row creation time (UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        doc="Last modification time (UTC).",
    )
