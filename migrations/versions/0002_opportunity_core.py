"""Add typed v1.4 opportunity, watchlist, and priority records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_opportunity_core"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist_item",
        sa.Column("watchlist_item_id", sa.String(length=128), primary_key=True),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("added_by", sa.String(length=32), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "job_revision"),
    )
    op.create_index("ix_watchlist_item_job_id", "watchlist_item", ["job_id"])

    op.create_table(
        "opportunity_admission_proposal",
        sa.Column("proposal_id", sa.String(length=128), primary_key=True),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("proposed_by", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_opportunity_admission_proposal_job_id",
        "opportunity_admission_proposal",
        ["job_id"],
    )

    op.create_table(
        "opportunity_record",
        sa.Column("opportunity_id", sa.String(length=128), primary_key=True),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admitted_by", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("job_id", "job_revision"),
    )
    op.create_index("ix_opportunity_record_job_id", "opportunity_record", ["job_id"])

    op.create_table(
        "opportunity_admission_decision",
        sa.Column("decision_id", sa.String(length=128), primary_key=True),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("path", sa.String(length=32), nullable=False),
        sa.Column("decided_by", sa.String(length=32), nullable=False),
        sa.Column("proposal_id", sa.String(length=128)),
        sa.Column("opportunity_id", sa.String(length=128)),
        sa.Column("reason", sa.Text()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decided_by = 'user'", name="ck_opportunity_decision_user"),
        sa.CheckConstraint(
            "(path = 'proposal' AND proposal_id IS NOT NULL) "
            "OR (path = 'manual' AND proposal_id IS NULL)",
            name="ck_opportunity_decision_path",
        ),
        sa.CheckConstraint(
            "(decision = 'admitted' AND opportunity_id IS NOT NULL) "
            "OR (decision = 'rejected' AND opportunity_id IS NULL)",
            name="ck_opportunity_decision_result",
        ),
        sa.CheckConstraint(
            "path != 'manual' OR decision = 'admitted'",
            name="ck_opportunity_manual_admission",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["opportunity_admission_proposal.proposal_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity_record.opportunity_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_opportunity_admission_decision_job_id",
        "opportunity_admission_decision",
        ["job_id"],
    )

    op.create_table(
        "suggested_priority",
        sa.Column("opportunity_id", sa.String(length=128), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("rank", sa.Integer()),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("input_revisions", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "level IN ('low', 'medium', 'high', 'urgent')",
            name="ck_suggested_priority_level",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="ck_priority_score",
        ),
        sa.CheckConstraint("rank IS NULL OR rank >= 1", name="ck_priority_rank"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity_record.opportunity_id"], ondelete="RESTRICT"
        ),
    )

    op.create_table(
        "user_priority",
        sa.Column("opportunity_id", sa.String(length=128), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.CheckConstraint(
            "level IN ('low', 'medium', 'high', 'urgent')",
            name="ck_user_priority_level",
        ),
        sa.CheckConstraint("actor = 'user'", name="ck_user_priority_actor"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity_record.opportunity_id"], ondelete="RESTRICT"
        ),
    )


def downgrade() -> None:
    op.drop_table("user_priority")
    op.drop_table("suggested_priority")
    op.drop_index(
        "ix_opportunity_admission_decision_job_id",
        table_name="opportunity_admission_decision",
    )
    op.drop_table("opportunity_admission_decision")
    op.drop_index("ix_opportunity_record_job_id", table_name="opportunity_record")
    op.drop_table("opportunity_record")
    op.drop_index(
        "ix_opportunity_admission_proposal_job_id",
        table_name="opportunity_admission_proposal",
    )
    op.drop_table("opportunity_admission_proposal")
    op.drop_index("ix_watchlist_item_job_id", table_name="watchlist_item")
    op.drop_table("watchlist_item")
