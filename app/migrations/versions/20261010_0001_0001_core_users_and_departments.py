"""core schema: departments and users

Revision ID: 0001_core
Revises: None
Create Date: 2026-10-10

The first migration in the chain. The report-domain migration must declare
``down_revision = "0001_core"`` so both developers' schemas apply in a
defined order.

``departments`` is created first because ``users.department_id`` references
it.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_core"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: Allowed values for users.role. Stored as VARCHAR + CHECK rather than a
#: native MySQL ENUM, so adding a role later is a constraint change instead of
#: a column rewrite.
USER_ROLES = ("citizen", "admin", "worker")


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "default_sla_hours",
            sa.Integer(),
            nullable=False,
            server_default="72",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        # Bare name: the metadata naming convention
        # ("ck_%(table_name)s_%(constraint_name)s") expands it to
        # ck_departments_default_sla_hours_positive, matching the model.
        sa.CheckConstraint(
            "default_sla_hours > 0", name="default_sla_hours_positive"
        ),
        comment="Municipal departments that issue reports are routed to.",
    )
    op.create_index(
        "ix_departments_name", "departments", ["name"], unique=True
    )
    op.create_index(
        "ix_departments_is_active", "departments", ["is_active"], unique=False
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        # 255 keeps the unique index inside MySQL's utf8mb4 key-length limit.
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                *USER_ROLES,
                name="user_role",
                native_enum=False,
                length=20,
            ),
            nullable=False,
            server_default="citizen",
        ),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        # SET NULL, not CASCADE: removing a department must never delete the
        # people who worked in it.
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_users_department",
            ondelete="SET NULL",
        ),
        comment="Application accounts for citizens, workers and admins.",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index(
        "ix_users_is_active", "users", ["is_active"], unique=False
    )
    op.create_index(
        "ix_users_department_id", "users", ["department_id"], unique=False
    )
    # Composite index backing the admin user list filtered by role + status.
    op.create_index(
        "ix_users_role_is_active", "users", ["role", "is_active"], unique=False
    )


def downgrade() -> None:
    # Reverse order: users holds the foreign key into departments.
    op.drop_index("ix_users_role_is_active", table_name="users")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_departments_is_active", table_name="departments")
    op.drop_index("ix_departments_name", table_name="departments")
    op.drop_table("departments")
