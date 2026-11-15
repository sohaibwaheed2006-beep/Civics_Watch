"""enable row level security on every public table

Revision ID: 0006_enable_rls
Revises: 0005_seed_workers
Create Date: 2026-11-15

Supabase exposes the ``public`` schema through its auto-generated REST API,
and the ``anon`` role (whose key is designed to be public) holds full grants
on these tables. With RLS off, anyone who knows the project URL and the
publishable key can read and write every row, including ``users``.

This app never uses that REST API for data: the browser talks only to the
FastAPI backend, which connects as the table owner (``postgres``) and so
bypasses RLS. Enabling RLS with no policies therefore closes the public API
completely while leaving the backend unaffected.

Any table added by a later migration must enable RLS as well.

No-op on non-PostgreSQL databases (SQLite has no RLS).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_enable_rls"
down_revision: Union[str, None] = "0005_seed_workers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_rls(action: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        f"""
        DO $$
        DECLARE t record;
        BEGIN
            FOR t IN
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
            LOOP
                EXECUTE format(
                    'ALTER TABLE public.%I {action} ROW LEVEL SECURITY', t.relname
                );
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    _set_rls("ENABLE")


def downgrade() -> None:
    _set_rls("DISABLE")
