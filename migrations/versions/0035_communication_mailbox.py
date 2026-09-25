"""Add review-gated mailbox account metadata and manually imported messages."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_communication_mailbox"
down_revision: str | None = "0034_prepared_application_resume"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "communication_mailbox_account",
        sa.Column("account_id", sa.String(128), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("username", sa.String(512), nullable=False),
        sa.Column("imap_host", sa.String(512), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("security", sa.String(32), nullable=False, server_default="ssl"),
        sa.Column("credential_ref", sa.String(512), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(32), nullable=True),
        sa.Column("last_error_code", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("security IN ('ssl','starttls')", name="ck_mailbox_security"),
    )
    op.create_table(
        "communication_mail_message",
        sa.Column("message_id", sa.String(512), primary_key=True),
        sa.Column("account_id", sa.String(128), nullable=False),
        sa.Column("folder", sa.String(255), nullable=False),
        sa.Column("sender", sa.String(512), nullable=True),
        sa.Column("subject", sa.String(1000), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preview", sa.String(4000), nullable=False),
        sa.Column("opportunity_id", sa.String(128), nullable=True),
        sa.Column("application_id", sa.String(128), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["communication_mailbox_account.account_id"]),
        sa.Index("ix_mail_message_account_received", "account_id", "received_at"),
    )


def downgrade() -> None:
    op.drop_table("communication_mail_message")
    op.drop_table("communication_mailbox_account")
