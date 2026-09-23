"""Add scoped, review-gated memory governance."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_memory_governance"
down_revision: str | None = "0025_github_project_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    memory_types = "'profile','preference','fact','task','interest'"
    scope_types = "'user','workspace','session'"
    creators = "'USER','LLM','PLUGIN','IMPORTER','RULE'"
    op.create_table(
        "memory_item",
        sa.Column("memory_id", sa.String(128), primary_key=True),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("scope_kind", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"memory_type IN ({memory_types})", name="ck_memory_item_type"),
        sa.CheckConstraint(f"scope_kind IN ({scope_types})", name="ck_memory_item_scope"),
        sa.CheckConstraint("status IN ('confirmed','tombstoned')", name="ck_memory_item_status"),
        sa.CheckConstraint("current_revision >= 1", name="ck_memory_item_revision"),
    )
    op.create_index("ix_memory_item_scope", "memory_item", ["scope_kind", "scope_id", "status"])
    op.create_table(
        "memory_revision",
        sa.Column("memory_id", sa.String(128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_by", sa.String(16), nullable=False),
        sa.Column("confirmed_by", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memory_item.memory_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("memory_id", "revision"),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_memory_revision_hash"),
        sa.CheckConstraint("json_type(source_refs) = 'array'", name="ck_memory_revision_refs"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_memory_revision_confidence"
        ),
        sa.CheckConstraint(f"created_by IN ({creators})", name="ck_memory_revision_creator"),
    )
    op.create_table(
        "memory_proposal",
        sa.Column("proposal_id", sa.String(128), primary_key=True),
        sa.Column("target_memory_id", sa.String(128)),
        sa.Column("base_revision", sa.Integer()),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("scope_kind", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.String(128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_by", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reviewed_by", sa.String(64)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("approved_content", sa.Text()),
        sa.Column("approved_content_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["target_memory_id"], ["memory_item.memory_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(f"memory_type IN ({memory_types})", name="ck_memory_proposal_type"),
        sa.CheckConstraint(f"scope_kind IN ({scope_types})", name="ck_memory_proposal_scope"),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_memory_proposal_hash"),
        sa.CheckConstraint("json_type(source_refs) = 'array'", name="ck_memory_proposal_refs"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_memory_proposal_confidence"
        ),
        sa.CheckConstraint(f"created_by IN ({creators})", name="ck_memory_proposal_creator"),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected')", name="ck_memory_proposal_status"
        ),
        sa.CheckConstraint(
            "base_revision IS NULL OR base_revision >= 1", name="ck_memory_proposal_base"
        ),
        sa.CheckConstraint(
            "approved_content_sha256 IS NULL OR length(approved_content_sha256) = 64",
            name="ck_memory_proposal_approved_hash",
        ),
    )
    op.create_index(
        "ix_memory_proposal_scope", "memory_proposal", ["scope_kind", "scope_id", "status"]
    )
    op.execute(
        "CREATE TRIGGER trg_memory_revision_no_update "
        "BEFORE UPDATE ON memory_revision BEGIN "
        "SELECT RAISE(ABORT, 'memory revisions are immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_memory_revision_no_delete "
        "BEFORE DELETE ON memory_revision BEGIN "
        "SELECT RAISE(ABORT, 'memory revisions are immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_memory_revision_no_delete")
    op.execute("DROP TRIGGER trg_memory_revision_no_update")
    op.drop_index("ix_memory_proposal_scope", table_name="memory_proposal")
    op.drop_table("memory_proposal")
    op.drop_table("memory_revision")
    op.drop_index("ix_memory_item_scope", table_name="memory_item")
    op.drop_table("memory_item")
