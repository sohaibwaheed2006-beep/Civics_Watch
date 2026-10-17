"""seed the three standard departments

Revision ID: 0004_seed_departments
Revises: 0003_ai_automation
Create Date: 2026-10-17

The service routes every report to one of three departments:

    * Electrical    - street lamps, generators, wiring, lighting/power issues
    * Plumbing      - leaks, burst mains, leakage, drainage/water issues
    * General Works - everything else (roads, garbage, public property, other)

This data migration inserts those three rows so a fresh deployment can route
and assign work immediately. It is idempotent: a department whose name already
exists (case-insensitive) is left untouched, so it is safe to re-run and it
will not clash with departments an administrator created by hand.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_seed_departments"
down_revision: Union[str, None] = "0003_ai_automation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: (name, description, default SLA in hours) for each seeded department.
_DEPARTMENTS: tuple[tuple[str, str, int], ...] = (
    (
        "Electrical",
        "Street lamps, generators, public wiring, traffic signals and any "
        "lighting or power issue.",
        24,
    ),
    (
        "Plumbing",
        "Water leaks, burst mains, leakage, water bursts, blocked drains and "
        "any water or drainage issue.",
        18,
    ),
    (
        "General Works",
        "All remaining neighborhood issues: road damage, garbage and waste, "
        "public property and anything uncategorised.",
        72,
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    departments = sa.table(
        "departments",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
        sa.column("default_sla_hours", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    for name, description, sla_hours in _DEPARTMENTS:
        already_there = bind.execute(
            sa.text(
                "SELECT 1 FROM departments "
                "WHERE LOWER(name) = LOWER(:name) LIMIT 1"
            ),
            {"name": name},
        ).first()
        if already_there:
            continue
        bind.execute(
            departments.insert().values(
                name=name,
                description=description,
                is_active=True,
                default_sla_hours=sla_hours,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM departments "
            "WHERE name IN ('Electrical', 'Plumbing', 'General Works')"
        )
    )
