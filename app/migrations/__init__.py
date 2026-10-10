"""Alembic migration environment.

Alembic is the only supported way to change the schema.
``Base.metadata.create_all()`` is never used in production - it cannot alter
an existing table and leaves no revision history. The test suite does use it
against a throwaway SQLite database, which is a different concern.
"""
