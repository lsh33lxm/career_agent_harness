"""Create foundation command, revision, event, outbox, and migration tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entity_state",
        sa.Column("entity_id", sa.String(length=128), primary_key=True),
        sa.Column("entity_kind", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "entity_revision",
        sa.Column("revision_id", sa.String(length=128), primary_key=True),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entity_state.entity_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("entity_id", "revision"),
    )
    op.create_table(
        "domain_event",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("entity_revision", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_domain_event_entity_id", "domain_event", ["entity_id"])
    op.create_index("ix_domain_event_command_id", "domain_event", ["command_id"])
    op.create_table(
        "idempotency_record",
        sa.Column("idempotency_key", sa.String(length=255), primary_key=True),
        sa.Column("command_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "outbox_message",
        sa.Column("message_id", sa.String(length=128), primary_key=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("destination", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["domain_event.event_id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "migration_mismatch",
        sa.Column("mismatch_id", sa.String(length=128), primary_key=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("legacy_key", sa.String(length=512)),
        sa.Column("candidate_core_identity", sa.String(length=128)),
        sa.Column("mismatch", sa.Text(), nullable=False),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("migration_mismatch")
    op.drop_table("outbox_message")
    op.drop_table("idempotency_record")
    op.drop_index("ix_domain_event_command_id", table_name="domain_event")
    op.drop_index("ix_domain_event_entity_id", table_name="domain_event")
    op.drop_table("domain_event")
    op.drop_table("entity_revision")
    op.drop_table("entity_state")

