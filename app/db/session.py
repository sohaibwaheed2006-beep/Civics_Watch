"""Engine, session factory and the ``get_db`` request dependency.

There is exactly **one** engine and **one** session factory in the project.
Every module - including the report domain - obtains its session through
:func:`get_db`:

    from app.db.session import get_db

Both are built lazily and cached. ``create_engine`` opens no connection, so
importing this module is safe even when ``DATABASE_URL`` is still a
placeholder: a misconfiguration surfaces on the first request that needs data,
not at startup, which keeps ``/health`` answering.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "get_engine",
    "get_session_factory",
    "get_db",
    "session_scope",
    "check_database_connection",
    "dispose_engine",
    "reset_engine",
]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Build (once) and return the application engine.

    ``pool_pre_ping`` issues a cheap liveness check before a pooled connection
    is handed out, which prevents a stale connection to Supabase's pooler from
    being handed out after an idle period.

    Takes no arguments on purpose. An ``lru_cache`` keyed on a settings
    argument would build a *separate* engine for ``get_engine()`` and
    ``get_engine(settings)`` - which, with an in-memory SQLite database, means
    two different databases. Configuration comes from the already-cached
    :func:`~app.core.config.get_settings`, so there is exactly one engine per
    process. Call ``get_engine.cache_clear()`` after changing settings.
    """
    settings = get_settings()

    if settings.is_sqlite:
        # FastAPI runs sync endpoints in a threadpool, so connections must be
        # usable across threads.
        url = make_url(settings.DATABASE_URL)
        in_memory = url.database in (None, "", ":memory:")
        if in_memory:
            # An in-memory database lives only as long as its one connection,
            # so that single connection has to be shared by the whole pool.
            return create_engine(
                settings.DATABASE_URL,
                echo=settings.DB_ECHO,
                future=True,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        # A file database must NOT share one connection: a page load fires
        # several requests at once, and two threads using the same sqlite3
        # connection fail with "bad parameter or other API misuse" (seen as
        # random 500s / 401s). Give each checkout its own connection, and
        # wait for a writer lock instead of failing immediately.
        return create_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 15},
        )

    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        future=True,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    )
    logger.debug("Database engine created for %s", settings.database_url_safe)
    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Build (once) and return the session factory.

    ``expire_on_commit=False`` keeps attributes readable after a commit, so an
    endpoint can serialise the object it just saved without triggering a
    second SELECT.
    """
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def reset_engine() -> None:
    """Drop the cached engine and session factory.

    For tests and for a configuration reload. Disposes the existing pool first
    so connections are not leaked.
    """
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    Transaction policy: services commit explicitly, so the boundary is visible
    at the call site. This wrapper guarantees the two things that are easy to
    forget - an uncommitted or failed transaction is rolled back, and the
    connection is always returned to the pool.
    """
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def session_scope() -> Iterator[Session]:
    """Context-manager form of :func:`get_db`, for scripts and CLI tasks.

    Usage::

        with contextlib.closing(next(session_scope())) as db: ...

    Prefer :func:`get_db` inside request handlers.
    """
    return get_db()


def check_database_connection() -> bool:
    """Attempt a trivial round-trip. Returns ``False`` instead of raising.

    Used by the startup probe so a missing database produces a clear warning
    rather than an unhandled exception during boot.
    """
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - deliberately broad
        # Log the exception type and message only. The URL (and therefore the
        # password) is never included.
        logger.warning(
            "Database connectivity check failed: %s: %s",
            type(exc).__name__,
            str(exc).splitlines()[0] if str(exc) else "no detail",
        )
        return False


def dispose_engine() -> None:
    """Close every pooled connection. Called on application shutdown."""
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        logger.debug("Database engine disposed")
