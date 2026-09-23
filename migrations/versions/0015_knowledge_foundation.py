"""Add proposal-first Career Knowledge / Wiki foundation tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_knowledge_foundation"
down_revision: str | None = "0014_plugin_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "knowledge_entry",
        sa.Column("knowledge_id", sa.String(128), primary_key=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(32), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('personal_fact', 'project_evidence', 'skill', 'star_story', "
            "'interview_story', 'preference', 'target_role', 'company', 'market_signal', "
            "'template', 'application_history')",
            name="ck_knowledge_entry_category",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'archived')",
            name="ck_knowledge_entry_status",
        ),
        sa.CheckConstraint(
            "authority IN ('user_confirmed', 'document_supported', 'external_source', "
            "'ai_inferred', 'rule_verified')",
            name="ck_knowledge_entry_authority",
        ),
        sa.CheckConstraint(
            "created_by IN ('USER', 'LLM', 'PLUGIN', 'IMPORTER', 'RULE')",
            name="ck_knowledge_entry_created_by",
        ),
        sa.CheckConstraint("current_revision >= 1", name="ck_knowledge_entry_revision"),
    )
    op.create_index(
        "ix_knowledge_entry_category_status",
        "knowledge_entry",
        ["category", "status"],
    )
    op.create_table(
        "knowledge_revision",
        sa.Column("knowledge_id", sa.String(128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(128), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.String(128)),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_by", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("prompt_injection_flag", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("knowledge_id", "revision"),
        sa.ForeignKeyConstraint(
            ["knowledge_id"], ["knowledge_entry.knowledge_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"], ["evidence_artifact.artifact_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_knowledge_revision_hash",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_knowledge_revision_confidence",
        ),
        sa.CheckConstraint(
            "authority IN ('user_confirmed', 'document_supported', 'external_source', "
            "'ai_inferred', 'rule_verified')",
            name="ck_knowledge_revision_authority",
        ),
        sa.CheckConstraint(
            "created_by IN ('USER', 'LLM', 'PLUGIN', 'IMPORTER', 'RULE')",
            name="ck_knowledge_revision_created_by",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'archived')",
            name="ck_knowledge_revision_status",
        ),
    )
    op.create_index(
        "ix_knowledge_revision_source",
        "knowledge_revision",
        ["source_type", "source_locator"],
    )
    op.create_table(
        "knowledge_revision_evidence_ref",
        sa.Column("knowledge_id", sa.String(128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("evidence_ref_id", sa.String(128), nullable=False),
        sa.PrimaryKeyConstraint("knowledge_id", "revision", "ordinal"),
        sa.UniqueConstraint(
            "knowledge_id",
            "revision",
            "evidence_ref_id",
            name="uq_knowledge_revision_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_id", "revision"],
            ["knowledge_revision.knowledge_id", "knowledge_revision.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_knowledge_evidence_ordinal"),
    )
    op.create_table(
        "knowledge_link",
        sa.Column("link_id", sa.String(128), primary_key=True),
        sa.Column("source_knowledge_id", sa.String(128), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("target_knowledge_id", sa.String(128), nullable=False),
        sa.Column("target_revision", sa.Integer(), nullable=False),
        sa.Column("relation", sa.String(64), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_knowledge_id",
            "source_revision",
            "target_knowledge_id",
            "target_revision",
            "relation",
            name="uq_knowledge_link_identity",
        ),
        sa.ForeignKeyConstraint(
            ["source_knowledge_id", "source_revision"],
            ["knowledge_revision.knowledge_id", "knowledge_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_knowledge_id", "target_revision"],
            ["knowledge_revision.knowledge_id", "knowledge_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "created_by IN ('USER', 'LLM', 'PLUGIN', 'IMPORTER', 'RULE')",
            name="ck_knowledge_link_created_by",
        ),
    )
    op.create_table(
        "knowledge_proposal",
        sa.Column("proposal_id", sa.String(128), primary_key=True),
        sa.Column("target_knowledge_id", sa.String(128)),
        sa.Column("base_revision", sa.Integer()),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["target_knowledge_id"], ["knowledge_entry.knowledge_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'withdrawn')",
            name="ck_knowledge_proposal_status",
        ),
        sa.CheckConstraint(
            "category IN ('personal_fact', 'project_evidence', 'skill', 'star_story', "
            "'interview_story', 'preference', 'target_role', 'company', 'market_signal', "
            "'template', 'application_history')",
            name="ck_knowledge_proposal_category",
        ),
        sa.CheckConstraint(
            "authority IN ('user_confirmed', 'document_supported', 'external_source', "
            "'ai_inferred', 'rule_verified')",
            name="ck_knowledge_proposal_authority",
        ),
        sa.CheckConstraint(
            "created_by IN ('USER', 'LLM', 'PLUGIN', 'IMPORTER', 'RULE')",
            name="ck_knowledge_proposal_created_by",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_knowledge_proposal_hash",
        ),
    )
    op.create_index(
        "ix_knowledge_proposal_status",
        "knowledge_proposal",
        ["status", "created_at"],
    )
    op.create_table(
        "knowledge_chunk",
        sa.Column("chunk_id", sa.String(128), primary_key=True),
        sa.Column("knowledge_id", sa.String(128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["knowledge_id", "revision"],
            ["knowledge_revision.knowledge_id", "knowledge_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "knowledge_id",
            "revision",
            "ordinal",
            name="uq_knowledge_chunk_position",
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_knowledge_chunk_ordinal"),
        sa.CheckConstraint("token_count >= 0", name="ck_knowledge_chunk_tokens"),
        sa.CheckConstraint(
            "length(text_sha256) = 64 AND text_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_knowledge_chunk_hash",
        ),
    )
    op.create_index(
        "ix_knowledge_chunk_revision",
        "knowledge_chunk",
        ["knowledge_id", "revision"],
    )
    for table in (
        "knowledge_revision",
        "knowledge_revision_evidence_ref",
        "knowledge_link",
    ):
        _immutable_triggers(table)


def downgrade() -> None:
    for table in (
        "knowledge_revision",
        "knowledge_revision_evidence_ref",
        "knowledge_link",
    ):
        _drop_immutable_triggers(table)
    op.drop_index("ix_knowledge_chunk_revision", table_name="knowledge_chunk")
    op.drop_table("knowledge_chunk")
    op.drop_index("ix_knowledge_proposal_status", table_name="knowledge_proposal")
    op.drop_table("knowledge_proposal")
    op.drop_table("knowledge_link")
    op.drop_table("knowledge_revision_evidence_ref")
    op.drop_index("ix_knowledge_revision_source", table_name="knowledge_revision")
    op.drop_table("knowledge_revision")
    op.drop_index("ix_knowledge_entry_category_status", table_name="knowledge_entry")
    op.drop_table("knowledge_entry")
