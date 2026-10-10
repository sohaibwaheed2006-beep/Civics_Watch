"""Database layer: declarative base, engine, session factory.

Public surface, stable for every domain module:

- :data:`app.db.base.Base` - the one declarative base
- :func:`app.db.session.get_db` - the one request-scoped session dependency

Do not create a second engine, ``Base`` or ``sessionmaker`` anywhere else.
"""

from app.db.base import Base, TimestampMixin, utcnow
from app.db.session import get_db

__all__ = ["Base", "TimestampMixin", "utcnow", "get_db"]
