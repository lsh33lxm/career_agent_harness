"""Add governed source connectors and sync ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_source_connectors"
down_revision: str | None = "0027_task_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_connector",
        sa.Column("connector_id", sa.String(128), primary_key=True),
        sa.Column("connector_type", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("auth_schema", sa.JSON(), nullable=False),
        sa.Column("sync_cursor", sa.JSON()),
        sa.Column("conflict_policy", sa.String(32), nullable=False),
        sa.Column("delete_policy", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("connector_type IN ('local_folder')", name="ck_source_connector_type"),
        sa.CheckConstraint("status IN ('active','paused')", name="ck_source_connector_status"),
        sa.CheckConstraint(
            "conflict_policy IN ('source_wins','local_wins','defer')",
            name="ck_source_connector_conflict",
        ),
        sa.CheckConstraint(
            "delete_policy IN ('keep','mark_deleted')", name="ck_source_connector_delete"
        ),
        sa.CheckConstraint("json_type(config) = 'object'", name="ck_source_connector_config"),
        sa.CheckConstraint(
            "json_type(auth_schema) = 'object'", name="ck_source_connector_auth_schema"
        ),
    )
    op.create_table(
        "source_resource",
        sa.Column("connector_id", sa.String(128), nullable=False),
        sa.Column("resource_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.Column("source_modified_ns", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connector_id"], ["source_connector.connector_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("connector_id", "resource_key"),
        sa.CheckConstraint(
            "status IN ('active','source_deleted')", name="ck_source_resource_status"
        ),
        sa.CheckConstraint("length(fingerprint) = 64", name="ck_source_resource_fingerprint"),
        sa.CheckConstraint(
            "length(artifact_sha256) = 64", name="ck_source_resource_artifact_hash"
        ),
        sa.CheckConstraint("byte_length >= 0", name="ck_source_resource_length"),
    )
    op.create_table(
        "source_sync_run",
        sa.Column("sync_run_id", sa.String(128), primary_key=True),
        sa.Column("connector_id", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("cursor_before", sa.JSON()),
        sa.Column("cursor_after", sa.JSON()),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("deleted_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["connector_id"], ["source_connector.connector_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("mode IN ('full','incremental')", name="ck_source_sync_mode"),
        sa.CheckConstraint(
            "status IN ('processing','completed','failed')", name="ck_source_sync_status"
        ),
        sa.CheckConstraint(
            "created_count >= 0 AND updated_count >= 0 AND skipped_count >= 0 "
            "AND deleted_count >= 0 AND failed_count >= 0",
            name="ck_source_sync_counts",
        ),
    )
    op.create_index(
        "ix_source_sync_connector", "source_sync_run", ["connector_id", "started_at"]
    )
    op.execute(
        "CREATE TRIGGER trg_source_sync_completed_no_update "
        "BEFORE UPDATE ON source_sync_run WHEN OLD.status != 'processing' BEGIN "
        "SELECT RAISE(ABORT, 'completed sync runs are immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_source_sync_completed_no_update")
    op.drop_index("ix_source_sync_connector", table_name="source_sync_run")
    op.drop_table("source_sync_run")
    op.drop_table("source_resource")
    op.drop_table("source_connector")
