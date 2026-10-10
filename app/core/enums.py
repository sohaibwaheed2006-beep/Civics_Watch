"""Shared enumerations.

Lives in ``core`` so that both ``app.models`` and ``app.schemas`` can import it
without either depending on the other.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "UserRole",
    "ReportCategory",
    "ReportPriority",
    "ReportStatus",
    "NotificationType",
]


class UserRole(StrEnum):
    """The three roles the application recognises.

    A fixed set, shared with the report domain. Public registration always
    assigns :attr:`CITIZEN`; the other two are granted by an administrator.

    Stored as the string value (``"citizen"``), so the database column and the
    JSON representation are identical.
    """

    CITIZEN = "citizen"
    ADMIN = "admin"
    WORKER = "worker"


class ReportCategory(StrEnum):
    """Supported report categories.

    Keep the list closed on the API edge so the client picker is deterministic.
    New categories require a code change + migration-safe constraint update.
    """

    ROAD_DAMAGE = "road_damage"
    STREETLIGHT = "streetlight"
    GARBAGE = "garbage"
    WATER_LEAK = "water_leak"
    DRAINAGE = "drainage"
    PUBLIC_PROPERTY = "public_property"
    OTHER = "other"


class ReportPriority(StrEnum):
    """Report priority levels, ordered from low to urgent."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ReportStatus(StrEnum):
    """Report lifecycle states."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    REOPENED = "reopened"


class NotificationType(StrEnum):
    """In-app notification kinds."""

    REPORT_SUBMITTED = "report_submitted"
    STATUS_CHANGED = "status_changed"
    ASSIGNMENT = "assignment"
    REASSIGNMENT = "reassignment"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    REOPENED = "reopened"
    DEADLINE_WARNING = "deadline_warning"
    OVERDUE = "overdue"
