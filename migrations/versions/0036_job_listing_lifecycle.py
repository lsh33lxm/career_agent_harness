"""Track successful listing observations without guessing disappearance."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_job_listing_lifecycle"
down_revision: str | None = "0035_communication_mailbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_listing_observation",
        sa.Column("observation_id", sa.String(128), primary_key=True),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("query", sa.String(2048), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("url_fingerprint", sa.String(64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consecutive_missing", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("last_success_run_id", sa.String(128), nullable=False),
        sa.UniqueConstraint(
            "source_id", "query", "url_fingerprint", name="uq_job_listing_observation_key"
        ),
        sa.CheckConstraint(
            "consecutive_missing >= 0", name="ck_job_listing_missing_nonnegative"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'pending_verification', 'inactive')",
            name="ck_job_listing_status",
        ),
    )
    op.create_index(
        "ix_job_listing_observation_status",
        "job_listing_observation",
        ["source_id", "status", "last_checked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_listing_observation_status", table_name="job_listing_observation")
    op.drop_table("job_listing_observation")
