"""seed three field workers per department

Revision ID: 0005_seed_workers
Revises: 0004_seed_departments
Create Date: 2026-10-17

Gives a fresh deployment enough field staff to dispatch work immediately:
three active workers in each of the three seeded departments (Electrical,
Plumbing, General Works), nine in total. The accounts mirror the frontend
mock data so the two layers line up.

Every seeded worker shares the same temporary password:

    Password123!

so an administrator can sign in and hand the accounts over (or reset them)
after the first deploy. Change these in any real environment.

The migration is idempotent: a user whose email already exists is left
untouched, and a worker is only inserted if its target department is present.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.security import hash_password

# revision identifiers, used by Alembic.
revision: str = "0005_seed_workers"
down_revision: Union[str, None] = "0004_seed_departments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Shared temporary password for every seeded worker (see module docstring).
_DEFAULT_PASSWORD = "Password123!"

#: (full_name, email, phone, department_name) for each seeded worker.
_WORKERS: tuple[tuple[str, str, str, str], ...] = (
    # Electrical
    ("Elena Rostova", "elena.worker@example.com", "+1 (555) 456-7890", "Electrical"),
    ("Liam O'Connor", "liam.worker@example.com", "+1 (555) 789-0123", "Electrical"),
    ("Priya Nair", "priya.worker@example.com", "+1 (555) 890-1234", "Electrical"),
    # Plumbing
    ("Amara Okafor", "amara.worker@example.com", "+1 (555) 678-9012", "Plumbing"),
    ("Tomas Varga", "tomas.worker@example.com", "+1 (555) 901-2345", "Plumbing"),
    ("Fatima Zahra", "fatima.worker@example.com", "+1 (555) 012-3456", "Plumbing"),
    # General Works
    ("Dave Miller", "worker@example.com", "+1 (555) 345-6789", "General Works"),
    ("Carlos Mendes", "carlos.worker@example.com", "+1 (555) 567-8901", "General Works"),
    ("Grace Kim", "grace.worker@example.com", "+1 (555) 123-4567", "General Works"),
)

#: Emails of the workers this migration owns, used by downgrade.
_WORKER_EMAILS = tuple(email for _, email, _, _ in _WORKERS)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    users = sa.table(
        "users",
        sa.column("full_name", sa.String),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("role", sa.String),
        sa.column("phone", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_verified", sa.Boolean),
        sa.column("department_id", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    # One hash for the shared temporary password; reused for every row.
    password_hash = hash_password(_DEFAULT_PASSWORD)

    for full_name, email, phone, department_name in _WORKERS:
        already_there = bind.execute(
            sa.text(
                "SELECT 1 FROM users WHERE LOWER(email) = LOWER(:email) LIMIT 1"
            ),
            {"email": email},
        ).first()
        if already_there:
            continue

        department_id = bind.execute(
            sa.text(
                "SELECT id FROM departments "
                "WHERE LOWER(name) = LOWER(:name) LIMIT 1"
            ),
            {"name": department_name},
        ).scalar_one_or_none()
        if department_id is None:
            # The department was renamed or removed; skip rather than orphan.
            continue

        bind.execute(
            users.insert().values(
                full_name=full_name,
                email=email,
                password_hash=password_hash,
                role="worker",
                phone=phone,
                is_active=True,
                is_verified=True,
                department_id=department_id,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM users WHERE email IN :emails").bindparams(
            sa.bindparam("emails", expanding=True)
        ),
        {"emails": list(_WORKER_EMAILS)},
    )
