"""SQLAlchemy models.

All models inherit the shared :class:`app.db.base.Base`. Importing this package
registers them on ``Base.metadata``.

Developer 2: add the report-domain models here and in
:mod:`app.db.registry`. Do not redefine ``User`` or ``Department``, and do not
create placeholder tables for them - import these.
"""

from app.core.enums import (
    NotificationType,
    ReportCategory,
    ReportPriority,
    ReportStatus,
    UserRole,
)
from app.models.assignment import Assignment
from app.models.department import DEFAULT_SLA_HOURS, Department
from app.models.notification import Notification
from app.models.report import Report
from app.models.report_photo import ReportPhoto
from app.models.status_history import StatusHistory
from app.models.user import User
from app.models.vote import Vote

__all__ = [
    "Assignment",
    "DEFAULT_SLA_HOURS",
    "Department",
    "Notification",
    "NotificationType",
    "Report",
    "ReportCategory",
    "ReportPhoto",
    "ReportPriority",
    "ReportStatus",
    "StatusHistory",
    "User",
    "UserRole",
    "Vote",
]
