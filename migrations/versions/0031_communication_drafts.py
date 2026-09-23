"""Add review-gated communication drafts for opportunity follow-up."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_communication_drafts"
down_revision: str | None = "0030_github_source_connector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "communication_draft",
        sa.Column("draft_id", sa.String(128), primary_key=True),
        sa.Column("opportunity_id", sa.String(128), nullable=False),
        sa.Column("source_staging_id", sa.String(128), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("recipient", sa.String(512), nullable=True),
        sa.Column("body", sa.String(10000), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("review_reason", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "channel IN ('email','platform_message','follow_up_note')",
            name="ck_communication_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending_review','approved','rejected','sent',"
            "'replied','follow_up','closed','blocked')",
            name="ck_communication_status",
        ),
        sa.CheckConstraint("json_type(provenance) = 'object'", name="ck_communication_provenance"),
        sa.Index("ix_communication_opportunity", "opportunity_id", "status"),
    )


def downgrade() -> None:
    op.drop_table("communication_draft")
