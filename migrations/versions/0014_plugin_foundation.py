"""Add the reversible v2.0 plugin foundation tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_plugin_foundation"
down_revision: str | None = "0013_interview_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "plugin_packages",
    "plugin_releases",
    "plugin_installations",
    "plugin_permissions",
    "plugin_runs",
    "plugin_update_plans",
    "plugin_audit_events",
)


def _immutable_triggers(table: str) -> None:
    op.execute(
        f"CREATE TRIGGER trg_{table}_no_update BEFORE UPDATE ON {table} BEGIN "
        f"SELECT RAISE(ABORT, '{table} is immutable'); END"
    )
    op.execute(
        f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} BEGIN "
        f"SELECT RAISE(ABORT, '{table} is immutable'); END"
    )


def _drop_immutable_triggers(table: str) -> None:
    op.execute(f"DROP TRIGGER trg_{table}_no_delete")
    op.execute(f"DROP TRIGGER trg_{table}_no_update")


def upgrade() -> None:
    op.create_table(
        "plugin_packages",
        sa.Column("plugin_id", sa.String(64), primary_key=True),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("source_repo", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(256), nullable=False),
        sa.Column("source_commit", sa.String(128), nullable=False),
        sa.Column("license", sa.String(128), nullable=False),
        sa.Column("trust", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "trust IN ('trusted', 'quarantined', 'unverified')",
            name="ck_plugin_package_trust",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64 AND content_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_plugin_package_content_hash",
        ),
    )
    op.create_table(
        "plugin_releases",
        sa.Column("plugin_id", sa.String(64), nullable=False),
        sa.Column("version", sa.String(128), nullable=False),
        sa.Column("release_commit", sa.String(128), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("compatibility", sa.JSON(), nullable=False),
        sa.Column("scan_report", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id", "version"),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin_packages.plugin_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64 AND content_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_plugin_release_content_hash",
        ),
    )
    op.create_index("ix_plugin_releases_plugin_id", "plugin_releases", ["plugin_id"])
    op.create_table(
        "plugin_installations",
        sa.Column("plugin_id", sa.String(64), primary_key=True),
        sa.Column("current_version", sa.String(128), nullable=False),
        sa.Column("previous_version", sa.String(128)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("pinned_release", sa.String(128), nullable=False),
        sa.Column("last_health_at", sa.DateTime(timezone=True)),
        sa.Column("last_health_status", sa.String(32)),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plugin_id", "current_version"],
            ["plugin_releases.plugin_id", "plugin_releases.version"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('discovered', 'installed', 'enabled', 'disabled', "
            "'quarantined', 'failed', 'rolled_back')",
            name="ck_plugin_installation_status",
        ),
        sa.CheckConstraint(
            "last_health_status IS NULL OR last_health_status IN ('ok', 'error', 'timeout')",
            name="ck_plugin_health_status",
        ),
    )
    op.create_table(
        "plugin_permissions",
        sa.Column("plugin_id", sa.String(64), nullable=False),
        sa.Column("permission_kind", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(512), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id", "permission_kind", "scope"),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin_packages.plugin_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "permission_kind IN ('network', 'filesystem', 'secret', 'external_write', 'scope')",
            name="ck_plugin_permission_kind",
        ),
    )
    op.create_table(
        "plugin_runs",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column("request_id", sa.String(128), nullable=False, unique=True),
        sa.Column("plugin_id", sa.String(64), nullable=False),
        sa.Column("plugin_version", sa.String(128), nullable=False),
        sa.Column("capability", sa.String(128), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("cost", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin_packages.plugin_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('ok', 'proposal', 'blocked', 'error')", name="ck_plugin_run_status"
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_plugin_run_input_hash",
        ),
        sa.CheckConstraint(
            "output_hash IS NULL OR (length(output_hash) = 64 AND "
            "output_hash NOT GLOB '*[^0-9a-f]*')",
            name="ck_plugin_run_output_hash",
        ),
    )
    op.create_index("ix_plugin_runs_plugin_id", "plugin_runs", ["plugin_id"])
    op.create_index("ix_plugin_runs_started_at", "plugin_runs", ["started_at"])
    op.create_table(
        "plugin_update_plans",
        sa.Column("plan_id", sa.String(128), primary_key=True),
        sa.Column("plugin_id", sa.String(64), nullable=False),
        sa.Column("current_version", sa.String(128), nullable=False),
        sa.Column("candidate_version", sa.String(128), nullable=False),
        sa.Column("tests", sa.JSON(), nullable=False),
        sa.Column("migration", sa.JSON(), nullable=False),
        sa.Column("approval", sa.String(32), nullable=False),
        sa.Column("rollback_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin_packages.plugin_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "approval IN ('pending', 'approved', 'rejected', 'applied')",
            name="ck_plugin_update_approval",
        ),
    )
    op.create_index("ix_plugin_update_plans_plugin_id", "plugin_update_plans", ["plugin_id"])
    op.create_table(
        "plugin_audit_events",
        sa.Column("audit_id", sa.String(128), primary_key=True),
        sa.Column("plugin_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plugin_id"], ["plugin_packages.plugin_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "plugin_id", "action", "idempotency_key", name="uq_plugin_audit_idempotency"
        ),
    )
    op.create_index(
        "ix_plugin_audit_events_plugin_id", "plugin_audit_events", ["plugin_id", "occurred_at"]
    )
    for table in (
        "plugin_packages",
        "plugin_releases",
        "plugin_permissions",
        "plugin_runs",
        "plugin_audit_events",
    ):
        _immutable_triggers(table)


def downgrade() -> None:
    for table in (
        "plugin_packages",
        "plugin_releases",
        "plugin_permissions",
        "plugin_runs",
        "plugin_audit_events",
    ):
        _drop_immutable_triggers(table)
    op.drop_index("ix_plugin_audit_events_plugin_id", table_name="plugin_audit_events")
    op.drop_table("plugin_audit_events")
    op.drop_index("ix_plugin_update_plans_plugin_id", table_name="plugin_update_plans")
    op.drop_table("plugin_update_plans")
    op.drop_index("ix_plugin_runs_started_at", table_name="plugin_runs")
    op.drop_index("ix_plugin_runs_plugin_id", table_name="plugin_runs")
    op.drop_table("plugin_runs")
    op.drop_table("plugin_permissions")
    op.drop_table("plugin_installations")
    op.drop_index("ix_plugin_releases_plugin_id", table_name="plugin_releases")
    op.drop_table("plugin_releases")
    op.drop_table("plugin_packages")
