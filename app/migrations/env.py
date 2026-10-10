"""Alembic environment.

Two things matter here:

1. The database URL comes from the application settings, not ``alembic.ini``,
   so ``.env`` is the single source of truth and no credential is committed.
2. ``app.db.registry`` is imported before ``target_metadata`` is read. That
   import is what registers every model on ``Base.metadata``. Skip it and
   ``--autogenerate`` would see an empty schema and cheerfully emit a
   migration that drops all the tables.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings

# Importing the registry populates Base.metadata with every model.
from app.db.registry import target_metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

# Escape any '%' in the URL: ConfigParser would otherwise treat it as
# interpolation syntax and fail on a password containing one.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (``alembic upgrade head --sql``)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        # Needed for SQLite, harmless on MySQL: rebuilds a table when an
        # ALTER cannot be expressed directly.
        render_as_batch=settings.is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect and apply migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=settings.is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
