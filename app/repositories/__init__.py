"""Persistence access layer.

Query construction lives here so services stay readable and queries are
reusable. Repository functions take the request's ``Session`` and **never
commit** - the calling service owns the transaction boundary.

- ``user_repository``       - user lookups, filtered listing, inserts
- ``department_repository`` - department lookups, filtered listing, inserts
"""

from app.repositories import department_repository, user_repository

__all__ = ["user_repository", "department_repository"]
