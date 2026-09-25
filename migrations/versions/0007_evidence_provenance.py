"""Persist immutable Evidence provenance metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_evidence_provenance"
down_revision: str | None = "0006_capability_personal_state_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_artifact",
        sa.Column("artifact_id", sa.String(length=128), primary_key=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("artifact_class", sa.String(length=32), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_evidence_artifact_sha256",
        ),
        sa.CheckConstraint(
            "length(trim(media_type)) > 0",
            name="ck_evidence_artifact_media_type",
        ),
        sa.CheckConstraint(
            "artifact_class IN ('public_source', 'personal', 'sensitive')",
            name="ck_evidence_artifact_class",
        ),
        sa.CheckConstraint("byte_length >= 0", name="ck_evidence_artifact_byte_length"),
    )
    op.create_index("ix_evidence_artifact_sha256", "evidence_artifact", ["sha256"])

    op.create_table(
        "evidence_source",
        sa.Column("source_id", sa.String(length=128), primary_key=True),
        sa.Column("source_type", sa.String(length=128), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "length(trim(source_type)) > 0 AND length(source_type) <= 128",
            name="ck_evidence_source_type",
        ),
        sa.CheckConstraint(
            "length(trim(locator)) > 0 AND length(locator) <= 2048",
            name="ck_evidence_source_locator",
        ),
    )

    op.create_table(
        "source_snapshot",
        sa.Column("snapshot_id", sa.String(length=128), primary_key=True),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("artifact_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("snapshot_id", "artifact_id"),
        sa.ForeignKeyConstraint(["source_id"], ["evidence_source.source_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["evidence_artifact.artifact_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_source_snapshot_source_id", "source_snapshot", ["source_id"])
    op.create_index("ix_source_snapshot_artifact_id", "source_snapshot", ["artifact_id"])

    op.create_table(
        "evidence_ref",
        sa.Column("evidence_ref_id", sa.String(length=128), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("artifact_id", sa.String(length=128), nullable=False),
        sa.Column("selector", sa.Text()),
        sa.CheckConstraint(
            "selector IS NULL OR length(selector) <= 2048",
            name="ck_evidence_ref_selector",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "artifact_id"],
            ["source_snapshot.snapshot_id", "source_snapshot.artifact_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_evidence_ref_snapshot_id", "evidence_ref", ["snapshot_id"])
    op.create_index("ix_evidence_ref_artifact_id", "evidence_ref", ["artifact_id"])

    for table_name in (
        "evidence_artifact",
        "evidence_source",
        "source_snapshot",
        "evidence_ref",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update BEFORE UPDATE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete BEFORE DELETE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )


def downgrade() -> None:
    for table_name in reversed(
        (
            "evidence_artifact",
            "evidence_source",
            "source_snapshot",
            "evidence_ref",
        )
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")

    op.drop_index("ix_evidence_ref_artifact_id", table_name="evidence_ref")
    op.drop_index("ix_evidence_ref_snapshot_id", table_name="evidence_ref")
    op.drop_table("evidence_ref")
    op.drop_index("ix_source_snapshot_artifact_id", table_name="source_snapshot")
    op.drop_index("ix_source_snapshot_source_id", table_name="source_snapshot")
    op.drop_table("source_snapshot")
    op.drop_table("evidence_source")
    op.drop_index("ix_evidence_artifact_sha256", table_name="evidence_artifact")
    op.drop_table("evidence_artifact")
