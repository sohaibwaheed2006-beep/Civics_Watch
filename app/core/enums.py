"""Shared enumerations.

Lives in ``core`` so that both ``app.models`` and ``app.schemas`` can import it
without either depending on the other.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["UserRole"]


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
