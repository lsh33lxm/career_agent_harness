"""Add immutable Context Manifest audit records without compiled prompt content."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_context_manifest"
down_revision: str | None = "0004_project_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "context_manifest",
        sa.Column("manifest_id", sa.String(length=128), primary_key=True),
        sa.Column("contract_version", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=128), nullable=False),
        sa.Column("selection_policy_version", sa.String(length=64), nullable=False),
        sa.Column("compression_policy_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("included_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("knowledge_ref_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "selection_policy_version = 'context-relevance-v1'",
            name="ck_context_manifest_selection_policy",
        ),
        sa.CheckConstraint(
            "compression_policy_version = 'context-no-compression-v1'",
            name="ck_context_manifest_compression_policy",
        ),
        sa.CheckConstraint(
            "length(trim(contract_version)) > 0 AND length(trim(task_type)) > 0 "
            "AND length(trim(provider)) > 0 AND length(trim(model_id)) > 0 "
            "AND length(trim(actor)) > 0",
            name="ck_context_manifest_required_text",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_context_manifest_input_hash",
        ),
        sa.CheckConstraint(
            "json_type(capabilities) = 'array' AND json_array_length(capabilities) <= 64",
            name="ck_context_capabilities",
        ),
        sa.CheckConstraint(
            "json_type(skills) = 'array' AND json_array_length(skills) <= 64",
            name="ck_context_skills",
        ),
        sa.CheckConstraint(
            "included_count >= 0 AND excluded_count >= 0 AND knowledge_ref_count >= 0",
            name="ck_context_manifest_counts",
        ),
    )
    op.create_index("ix_context_manifest_run_id", "context_manifest", ["run_id"])
    op.create_table(
        "context_manifest_asset_ref",
        sa.Column("manifest_id", sa.String(length=128), primary_key=True),
        sa.Column("asset_id", sa.String(length=128), primary_key=True),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("asset_class", sa.String(length=32), nullable=False),
        sa.Column("asset_revision", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("matched_terms", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "asset_class IN ('personal_context', 'career_state', 'project_evidence', "
            "'market_evidence', 'career_history_outcome')",
            name="ck_context_asset_class",
        ),
        sa.CheckConstraint("asset_revision >= 1", name="ck_context_asset_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_context_asset_ordinal"),
        sa.CheckConstraint(
            "disposition IN ('included', 'excluded')",
            name="ck_context_asset_disposition",
        ),
        sa.CheckConstraint(
            "(disposition = 'included' AND reason IN "
            "('explicit_reference', 'relevance_term_match')) OR "
            "(disposition = 'excluded' AND reason IN "
            "('asset_class_not_allowed', 'no_relevance_match', 'selection_limit'))",
            name="ck_context_asset_reason",
        ),
        sa.CheckConstraint(
            "json_type(matched_terms) = 'array' "
            "AND json_array_length(matched_terms) <= 64 AND "
            "((reason = 'relevance_term_match' AND json_array_length(matched_terms) > 0) "
            "OR (reason != 'relevance_term_match' AND json_array_length(matched_terms) = 0))",
            name="ck_context_asset_matched_terms",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["context_manifest.manifest_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint("manifest_id", "disposition", "ordinal"),
    )
    op.create_index(
        "ix_context_manifest_asset_ref_asset_id",
        "context_manifest_asset_ref",
        ["asset_id"],
    )
    op.create_table(
        "context_manifest_knowledge_ref",
        sa.Column("manifest_id", sa.String(length=128), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("knowledge_id", sa.String(length=128), nullable=False),
        sa.Column("knowledge_revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("knowledge_revision >= 1", name="ck_context_knowledge_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_context_knowledge_ordinal"),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["context_manifest.manifest_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint("manifest_id", "knowledge_id", "knowledge_revision"),
    )
    op.create_index(
        "ix_context_manifest_knowledge_ref_knowledge_id",
        "context_manifest_knowledge_ref",
        ["knowledge_id"],
    )
    _create_context_triggers()


def _create_context_triggers() -> None:
    op.execute(
        "CREATE TRIGGER trg_context_manifest_names_valid "
        "BEFORE INSERT ON context_manifest WHEN EXISTS ("
        "SELECT 1 FROM (SELECT 'capability' AS kind, value, type "
        "FROM json_each(NEW.capabilities) UNION ALL "
        "SELECT 'skill' AS kind, value, type FROM json_each(NEW.skills)) AS item "
        "WHERE item.type != 'text' OR trim(item.value) = '' "
        "OR item.value != trim(item.value) OR length(item.value) > 128) OR EXISTS ("
        "SELECT 1 FROM (SELECT 'capability' AS kind, value FROM json_each(NEW.capabilities) "
        "UNION ALL SELECT 'skill' AS kind, value FROM json_each(NEW.skills)) AS item "
        "GROUP BY item.kind, item.value HAVING count(*) > 1) BEGIN "
        "SELECT RAISE(ABORT, 'context capability and skill names must be unique text'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_context_asset_terms_valid "
        "BEFORE INSERT ON context_manifest_asset_ref WHEN EXISTS ("
        "SELECT 1 FROM json_each(NEW.matched_terms) AS term "
        "WHERE term.type != 'text' OR trim(term.value) = '' "
        "OR term.value != lower(trim(term.value)) OR length(term.value) > 128) OR EXISTS ("
        "SELECT 1 FROM json_each(NEW.matched_terms) GROUP BY value HAVING count(*) > 1) BEGIN "
        "SELECT RAISE(ABORT, 'context matched terms must be unique normalized text'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_context_asset_project_evidence_exact_revision "
        "BEFORE INSERT ON context_manifest_asset_ref WHEN "
        "NEW.asset_class = 'project_evidence' AND NOT EXISTS ("
        "SELECT 1 FROM project_evidence WHERE evidence_id = NEW.asset_id "
        "AND revision = NEW.asset_revision) BEGIN "
        "SELECT RAISE(ABORT, 'context project evidence reference must use an exact revision'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_context_manifest_child_counts "
        "BEFORE INSERT ON context_manifest WHEN "
        "NEW.included_count != (SELECT count(*) FROM context_manifest_asset_ref "
        "WHERE manifest_id = NEW.manifest_id AND disposition = 'included') "
        "OR NEW.excluded_count != (SELECT count(*) FROM context_manifest_asset_ref "
        "WHERE manifest_id = NEW.manifest_id AND disposition = 'excluded') "
        "OR NEW.knowledge_ref_count != (SELECT count(*) FROM context_manifest_knowledge_ref "
        "WHERE manifest_id = NEW.manifest_id) BEGIN "
        "SELECT RAISE(ABORT, 'context manifest child counts do not match'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_context_manifest_asset_ordinals "
        "BEFORE INSERT ON context_manifest WHEN "
        "(NEW.included_count > 0 AND (SELECT max(ordinal) "
        "FROM context_manifest_asset_ref WHERE manifest_id = NEW.manifest_id "
        "AND disposition = 'included') != NEW.included_count - 1) "
        "OR (NEW.excluded_count > 0 AND (SELECT max(ordinal) "
        "FROM context_manifest_asset_ref WHERE manifest_id = NEW.manifest_id "
        "AND disposition = 'excluded') != NEW.excluded_count - 1) "
        "OR (NEW.knowledge_ref_count > 0 AND (SELECT max(ordinal) "
        "FROM context_manifest_knowledge_ref WHERE manifest_id = NEW.manifest_id) "
        "!= NEW.knowledge_ref_count - 1) BEGIN "
        "SELECT RAISE(ABORT, 'context manifest ordinals must be contiguous from zero'); END"
    )
    for table_name in (
        "context_manifest_asset_ref",
        "context_manifest_knowledge_ref",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_append_sealed BEFORE INSERT ON {table_name} "
            "WHEN EXISTS (SELECT 1 FROM context_manifest "
            "WHERE manifest_id = NEW.manifest_id) BEGIN "
            "SELECT RAISE(ABORT, 'cannot append to a sealed context manifest'); END"
        )
    for table_name in (
        "context_manifest",
        "context_manifest_asset_ref",
        "context_manifest_knowledge_ref",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update BEFORE UPDATE ON {table_name} BEGIN "
            "SELECT RAISE(ABORT, 'context manifest history is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete BEFORE DELETE ON {table_name} BEGIN "
            "SELECT RAISE(ABORT, 'context manifest history is immutable'); END"
        )


def downgrade() -> None:
    for table_name in (
        "context_manifest_knowledge_ref",
        "context_manifest_asset_ref",
        "context_manifest",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")
    for table_name in (
        "context_manifest_knowledge_ref",
        "context_manifest_asset_ref",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_append_sealed")
    op.execute("DROP TRIGGER trg_context_manifest_asset_ordinals")
    op.execute("DROP TRIGGER trg_context_manifest_child_counts")
    op.execute("DROP TRIGGER trg_context_asset_project_evidence_exact_revision")
    op.execute("DROP TRIGGER trg_context_asset_terms_valid")
    op.execute("DROP TRIGGER trg_context_manifest_names_valid")

    op.drop_index(
        "ix_context_manifest_knowledge_ref_knowledge_id",
        table_name="context_manifest_knowledge_ref",
    )
    op.drop_table("context_manifest_knowledge_ref")
    op.drop_index(
        "ix_context_manifest_asset_ref_asset_id",
        table_name="context_manifest_asset_ref",
    )
    op.drop_table("context_manifest_asset_ref")
    op.drop_index("ix_context_manifest_run_id", table_name="context_manifest")
    op.drop_table("context_manifest")
