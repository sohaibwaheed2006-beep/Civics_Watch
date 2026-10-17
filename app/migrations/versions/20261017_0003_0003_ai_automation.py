"""AI automation: vision autofill, clustering, resolution checks, spam filter,
reviews and the monthly worker bonus.

Revision ID: 0003_ai_automation
Revises: 0002_reports
Create Date: 2026-10-17

Adds the columns the AI pipeline writes to ``reports`` (vision suggestions,
incident-cluster id, resolution-photo verdict and the spam filter result) plus
the two new tables that back citizen reviews and the worker-of-the-month award.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_ai_automation"
down_revision: Union[str, None] = "0002_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- reports: AI vision + clustering + resolution check + spam ---------
    op.add_column(
        "reports",
        sa.Column("ai_title_suggested", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("ai_description_suggested", sa.Text(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("ai_priority_suggested", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("incident_cluster_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("resolution_photo_match_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column(
            "resolution_flagged_for_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "reports",
        sa.Column("resolution_review_reason", sa.String(length=400), nullable=True),
    )
    op.add_column("reports", sa.Column("spam_score", sa.Float(), nullable=True))
    op.add_column(
        "reports",
        sa.Column(
            "spam_flagged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "reports",
        sa.Column("spam_reason", sa.String(length=400), nullable=True),
    )
    op.create_index(
        "ix_reports_incident_cluster_id", "reports", ["incident_cluster_id"]
    )
    op.create_index("ix_reports_spam_flagged", "reports", ["spam_flagged"])

    # --- reviews ----------------------------------------------------------
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("citizen_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"], name="fk_reviews_report", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"], ["users.id"], name="fk_reviews_worker", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["citizen_id"], ["users.id"], name="fk_reviews_citizen", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.UniqueConstraint("report_id", "citizen_id", name="uq_reviews_report_citizen"),
    )
    op.create_index("ix_reviews_report_id", "reviews", ["report_id"])
    op.create_index("ix_reviews_worker_id", "reviews", ["worker_id"])
    op.create_index("ix_reviews_citizen_id", "reviews", ["citizen_id"])
    op.create_index("ix_reviews_worker_created", "reviews", ["worker_id", "created_at"])

    # --- worker_bonuses ---------------------------------------------------
    op.create_table(
        "worker_bonuses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Integer(), nullable=False),
        sa.Column("resolved_count", sa.Integer(), nullable=False),
        sa.Column("average_rating", sa.Float(), nullable=False),
        sa.Column("average_hours_to_resolve", sa.Float(), nullable=True),
        sa.Column("on_time_rate", sa.Float(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["users.id"],
            name="fk_worker_bonuses_worker",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_worker_bonuses"),
        sa.UniqueConstraint(
            "period_year", "period_month", name="uq_worker_bonuses_period"
        ),
    )
    op.create_index("ix_worker_bonuses_worker_id", "worker_bonuses", ["worker_id"])


def downgrade() -> None:
    op.drop_index("ix_worker_bonuses_worker_id", table_name="worker_bonuses")
    op.drop_table("worker_bonuses")

    op.drop_index("ix_reviews_worker_created", table_name="reviews")
    op.drop_index("ix_reviews_citizen_id", table_name="reviews")
    op.drop_index("ix_reviews_worker_id", table_name="reviews")
    op.drop_index("ix_reviews_report_id", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_reports_spam_flagged", table_name="reports")
    op.drop_index("ix_reports_incident_cluster_id", table_name="reports")
    op.drop_column("reports", "spam_reason")
    op.drop_column("reports", "spam_flagged")
    op.drop_column("reports", "spam_score")
    op.drop_column("reports", "resolution_review_reason")
    op.drop_column("reports", "resolution_flagged_for_review")
    op.drop_column("reports", "resolution_photo_match_score")
    op.drop_column("reports", "incident_cluster_id")
    op.drop_column("reports", "ai_priority_suggested")
    op.drop_column("reports", "ai_description_suggested")
    op.drop_column("reports", "ai_title_suggested")
