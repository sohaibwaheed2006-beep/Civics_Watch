"""report domain: reports, photos, assignments, status history, votes, notifications

Revision ID: 0002_reports
Revises: 0001_core
Create Date: 2026-10-10

Second migration in the chain. Depends on ``0001_core`` which provides the
``users`` and ``departments`` tables that this migration's foreign keys target.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_reports"
down_revision: Union[str, None] = "0001_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REPORT_CATEGORIES = (
    "road_damage",
    "streetlight",
    "garbage",
    "water_leak",
    "drainage",
    "public_property",
    "other",
)
REPORT_PRIORITIES = ("low", "medium", "high", "urgent")
REPORT_STATUSES = (
    "submitted",
    "under_review",
    "assigned",
    "in_progress",
    "resolved",
    "rejected",
    "reopened",
)
NOTIFICATION_TYPES = (
    "report_submitted",
    "status_changed",
    "assignment",
    "reassignment",
    "resolved",
    "rejected",
    "reopened",
    "deadline_warning",
    "overdue",
)


def upgrade() -> None:
    # ---- reports ---------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                *REPORT_CATEGORIES,
                name="report_category",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                *REPORT_PRIORITIES,
                name="report_priority",
                native_enum=False,
                length=32,
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            sa.Enum(
                *REPORT_STATUSES,
                name="report_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
            server_default="submitted",
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_text", sa.String(length=500), nullable=True),
        sa.Column("citizen_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("assigned_worker_id", sa.Integer(), nullable=True),
        sa.Column("duplicate_of_report_id", sa.Integer(), nullable=True),
        sa.Column("ai_category", sa.String(length=32), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("duplicate_score", sa.Float(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
        sa.ForeignKeyConstraint(
            ["citizen_id"],
            ["users.id"],
            name="fk_reports_citizen_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_reports_department_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_worker_id"],
            ["users.id"],
            name="fk_reports_assigned_worker_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_report_id"],
            ["reports.id"],
            name="fk_reports_duplicate_of_report_id_reports",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_reports_latitude_range"
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_reports_longitude_range",
        ),
        comment="Citizen-submitted issue reports.",
    )
    op.create_index("ix_reports_category", "reports", ["category"])
    op.create_index("ix_reports_priority", "reports", ["priority"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_citizen_id", "reports", ["citizen_id"])
    op.create_index("ix_reports_department_id", "reports", ["department_id"])
    op.create_index("ix_reports_assigned_worker_id", "reports", ["assigned_worker_id"])
    op.create_index(
        "ix_reports_duplicate_of_report_id", "reports", ["duplicate_of_report_id"]
    )
    op.create_index("ix_reports_deadline_at", "reports", ["deadline_at"])
    op.create_index(
        "ix_reports_status_created_at", "reports", ["status", "created_at"]
    )
    op.create_index(
        "ix_reports_category_status", "reports", ["category", "status"]
    )
    op.create_index(
        "ix_reports_department_status", "reports", ["department_id", "status"]
    )

    # ---- report_photos ---------------------------------------------------
    op.create_table(
        "report_photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_report_photos"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_report_photos_report_reports",
            ondelete="CASCADE",
        ),
        comment="Metadata for photos attached to reports.",
    )
    op.create_index(
        "ix_report_photos_report_id", "report_photos", ["report_id"]
    )

    # ---- status_history --------------------------------------------------
    op.create_table(
        "status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column(
            "old_status",
            sa.Enum(
                *REPORT_STATUSES,
                name="report_status",
                native_enum=False,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            sa.Enum(
                *REPORT_STATUSES,
                name="report_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("changed_by_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_status_history"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_status_history_report_reports",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_id"],
            ["users.id"],
            name="fk_status_history_changed_by_users",
            ondelete="CASCADE",
        ),
        comment="Immutable log of report status transitions.",
    )
    op.create_index(
        "ix_status_history_report_created",
        "status_history",
        ["report_id", "created_at"],
    )

    # ---- assignments -----------------------------------------------------
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id", name="pk_assignments"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_assignments_report_reports",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["users.id"],
            name="fk_assignments_worker_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_id"],
            ["users.id"],
            name="fk_assignments_assigned_by_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_assignments_department_departments",
            ondelete="SET NULL",
        ),
        comment="Audit trail of report assignments.",
    )
    op.create_index("ix_assignments_worker_active", "assignments", ["worker_id", "active"])
    op.create_index("ix_assignments_report_active", "assignments", ["report_id", "active"])

    # ---- votes -----------------------------------------------------------
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_votes"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_votes_report_reports",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_votes_user_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("report_id", "user_id", name="uq_votes_report_user"),
        comment="One upvote per user per report.",
    )

    # ---- notifications ---------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column(
            "notification_type",
            sa.Enum(
                *NOTIFICATION_TYPES,
                name="notification_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_notifications_report_reports",
            ondelete="SET NULL",
        ),
        comment="In-app notifications per user.",
    )
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read"],
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_table("notifications")

    op.drop_table("votes")

    op.drop_index("ix_assignments_report_active", table_name="assignments")
    op.drop_index("ix_assignments_worker_active", table_name="assignments")
    op.drop_table("assignments")

    op.drop_index("ix_status_history_report_created", table_name="status_history")
    op.drop_table("status_history")

    op.drop_index("ix_report_photos_report_id", table_name="report_photos")
    op.drop_table("report_photos")

    op.drop_index("ix_reports_department_status", table_name="reports")
    op.drop_index("ix_reports_category_status", table_name="reports")
    op.drop_index("ix_reports_status_created_at", table_name="reports")
    op.drop_index("ix_reports_deadline_at", table_name="reports")
    op.drop_index("ix_reports_duplicate_of_report_id", table_name="reports")
    op.drop_index("ix_reports_assigned_worker_id", table_name="reports")
    op.drop_index("ix_reports_department_id", table_name="reports")
    op.drop_index("ix_reports_citizen_id", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_priority", table_name="reports")
    op.drop_index("ix_reports_category", table_name="reports")
    op.drop_table("reports")
