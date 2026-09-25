"""Add non-secret model provider configuration and connection audit."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_model_provider_configs"
down_revision: str | None = "0023_legacy_structured_projection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_provider_config",
        sa.Column("provider_id", sa.String(64), primary_key=True),
        sa.Column("provider_kind", sa.String(32), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("default_model", sa.String(128), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("has_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "connection_status", sa.String(32), nullable=False, server_default="unconfigured"
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "provider_kind IN ('openai', 'anthropic', 'deepseek', 'openai_compatible')",
            name="ck_model_provider_kind",
        ),
        sa.CheckConstraint(
            "connection_status IN ('unconfigured', 'not_tested', 'connected', 'failed')",
            name="ck_model_provider_connection_status",
        ),
        sa.CheckConstraint("timeout_seconds BETWEEN 1 AND 120", name="ck_model_provider_timeout"),
        sa.CheckConstraint("revision >= 1", name="ck_model_provider_revision"),
    )
    op.create_table(
        "model_provider_connection_audit",
        sa.Column("audit_id", sa.String(128), primary_key=True),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["model_provider_config.provider_id"]),
        sa.CheckConstraint("latency_ms >= 0", name="ck_model_provider_audit_latency"),
    )


def downgrade() -> None:
    op.drop_table("model_provider_connection_audit")
    op.drop_table("model_provider_config")
