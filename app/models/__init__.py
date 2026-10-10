"""SQLAlchemy models.

All models inherit the shared :class:`app.db.base.Base`. Importing this package
registers them on ``Base.metadata``.

Developer 2: add the report-domain models here and in
:mod:`app.db.registry`. Do not redefine ``User`` or ``Department``, and do not
create placeholder tables for them - import these.
"""

from app.core.enums import UserRole
from app.models.department import DEFAULT_SLA_HOURS, Department
from app.models.user import User

__all__ = ["Department", "User", "UserRole", "DEFAULT_SLA_HOURS"]
