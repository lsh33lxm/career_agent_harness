"""Add scoped project evidence, capability state, and L1 enhancement records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_project_evidence"
down_revision: str | None = "0003_capability_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _revision_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "project_identity",
        sa.Column("project_id", sa.String(length=128), primary_key=True),
    )
    op.create_table(
        "project_record",
        sa.Column("project_id", sa.String(length=128), primary_key=True),
        *_revision_columns(),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("root_locator", sa.Text(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_project_record_revision"),
        sa.CheckConstraint(
            "schema_version >= 1", name="ck_project_record_schema_version"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project_identity.project_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "project_scan_scope",
        sa.Column("scope_id", sa.String(length=128), primary_key=True),
        *_revision_columns(),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("allowed_paths", sa.JSON(), nullable=False),
        sa.Column("denied_paths", sa.JSON(), nullable=False),
        sa.Column("follow_symlinks", sa.Boolean(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_project_scope_revision"),
        sa.CheckConstraint(
            "schema_version >= 1", name="ck_project_scope_schema_version"
        ),
        sa.CheckConstraint(
            "json_type(allowed_paths) = 'array' "
            "AND json_array_length(allowed_paths) > 0",
            name="ck_project_scope_allowed_paths",
        ),
        sa.CheckConstraint(
            "json_type(denied_paths) = 'array'",
            name="ck_project_scope_denied_paths",
        ),
        sa.CheckConstraint(
            "follow_symlinks = 0", name="ck_project_scope_no_symlinks"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project_identity.project_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("scope_id", "revision", "project_id"),
    )
    op.create_index(
        "ix_project_scan_scope_project_id", "project_scan_scope", ["project_id"]
    )
    op.create_table(
        "project_source_manifest",
        sa.Column("manifest_id", sa.String(length=128), primary_key=True),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("scan_scope_id", sa.String(length=128), nullable=False),
        sa.Column("scan_scope_revision", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scan_scope_revision >= 1", name="ck_project_manifest_scope_revision"
        ),
        sa.ForeignKeyConstraint(
            ["scan_scope_id", "scan_scope_revision", "project_id"],
            [
                "project_scan_scope.scope_id",
                "project_scan_scope.revision",
                "project_scan_scope.project_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("manifest_id", "project_id"),
    )
    op.create_index(
        "ix_project_source_manifest_project_id",
        "project_source_manifest",
        ["project_id"],
    )
    op.create_table(
        "project_source_entry",
        sa.Column("manifest_id", sa.String(length=128), primary_key=True),
        sa.Column("relative_path", sa.Text(), primary_key=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(relative_path) > 0", name="ck_project_source_relative_path"
        ),
        sa.CheckConstraint(
            "length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_project_source_sha256",
        ),
        sa.CheckConstraint(
            "byte_length >= 0", name="ck_project_source_byte_length"
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["project_source_manifest.manifest_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "project_evidence",
        sa.Column("evidence_id", sa.String(length=128), primary_key=True),
        *_revision_columns(),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("claim_kind", sa.String(length=32), nullable=False),
        sa.Column("manifest_id", sa.String(length=128), nullable=False),
        sa.Column("scanner", sa.String(length=255), nullable=False),
        sa.Column("scanner_version", sa.String(length=128), nullable=False),
        sa.Column("authority", sa.String(length=32), nullable=False),
        sa.Column("freshness", sa.String(length=32), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255)),
        sa.Column("reviewed_by_kind", sa.String(length=32)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_project_evidence_revision"),
        sa.CheckConstraint(
            "schema_version >= 1", name="ck_project_evidence_schema_version"
        ),
        sa.CheckConstraint(
            "claim_kind IN ('technical_observation', 'change', 'validation', 'performance', "
            "'business_outcome', 'personal_contribution', 'ownership', 'usage')",
            name="ck_project_evidence_claim_kind",
        ),
        sa.CheckConstraint(
            "authority IN ('code_verified', 'document_supported', 'user_confirmed', "
            "'ai_inferred')",
            name="ck_project_evidence_authority",
        ),
        sa.CheckConstraint(
            "freshness IN ('current', 'stale', 'unknown')",
            name="ck_project_evidence_freshness",
        ),
        sa.CheckConstraint(
            "review_status IN ('proposed', 'accepted', 'rejected', 'superseded')",
            name="ck_project_evidence_review_status",
        ),
        sa.CheckConstraint(
            "(review_status = 'proposed' AND reviewed_by IS NULL "
            "AND reviewed_by_kind IS NULL AND review_reason IS NULL) OR "
            "(review_status != 'proposed' AND reviewed_by IS NOT NULL "
            "AND trim(reviewed_by) != '' AND reviewed_by_kind IN ('user', 'rule') "
            "AND review_reason IS NOT NULL AND trim(review_reason) != '')",
            name="ck_project_evidence_review_authority",
        ),
        sa.CheckConstraint(
            "NOT (authority = 'ai_inferred' AND review_status = 'accepted')",
            name="ck_project_evidence_ai_requires_promotion",
        ),
        sa.CheckConstraint(
            "NOT (authority = 'code_verified' AND claim_kind IN "
            "('performance', 'business_outcome', 'personal_contribution', "
            "'ownership', 'usage'))",
            name="ck_project_evidence_code_authority_limit",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id", "project_id"],
            ["project_source_manifest.manifest_id", "project_source_manifest.project_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_project_evidence_project_id", "project_evidence", ["project_id"]
    )
    op.add_column(
        "capability_evidence_binding",
        sa.Column("project_evidence_revision", sa.Integer()),
    )
    op.create_table(
        "project_capability_state",
        sa.Column("capability_state_id", sa.String(length=128), primary_key=True),
        *_revision_columns(),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "revision >= 1", name="ck_project_capability_revision"
        ),
        sa.CheckConstraint(
            "schema_version >= 1", name="ck_project_capability_schema_version"
        ),
        sa.CheckConstraint(
            "state IN ('existing', 'understood', 'modified', 'extended', "
            "'validated', 'resume_ready')",
            name="ck_project_capability_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project_identity.project_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"],
            ["capability_identity.capability_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_project_capability_state_project_id",
        "project_capability_state",
        ["project_id"],
    )
    op.create_table(
        "project_capability_basis",
        sa.Column("basis_id", sa.String(length=128), primary_key=True),
        sa.Column("capability_state_id", sa.String(length=128), nullable=False),
        sa.Column("state_revision", sa.Integer(), nullable=False),
        sa.Column("basis_kind", sa.String(length=32), nullable=False),
        sa.Column("project_evidence_id", sa.String(length=128)),
        sa.Column("project_evidence_revision", sa.Integer()),
        sa.Column("approval_id", sa.String(length=128)),
        sa.Column("approval_revision", sa.Integer()),
        sa.CheckConstraint(
            "state_revision >= 1", name="ck_project_basis_state_revision"
        ),
        sa.CheckConstraint(
            "basis_kind IN ('code_evidence', 'document_evidence', 'user_confirmation', "
            "'change_evidence', 'validation_evidence', 'resume_approval')",
            name="ck_project_basis_kind",
        ),
        sa.CheckConstraint(
            "(basis_kind = 'resume_approval' AND project_evidence_id IS NULL "
            "AND project_evidence_revision IS NULL AND approval_id IS NOT NULL "
            "AND approval_revision >= 1) OR (basis_kind != 'resume_approval' "
            "AND project_evidence_id IS NOT NULL AND project_evidence_revision >= 1 "
            "AND approval_id IS NULL AND approval_revision IS NULL)",
            name="ck_project_basis_typed_reference",
        ),
        sa.ForeignKeyConstraint(
            ["capability_state_id", "state_revision"],
            [
                "project_capability_state.capability_state_id",
                "project_capability_state.revision",
            ],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["project_evidence_id", "project_evidence_revision"],
            ["project_evidence.evidence_id", "project_evidence.revision"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_id", "approval_revision"],
            ["entity_revision.entity_id", "entity_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_project_capability_basis_capability_state_id",
        "project_capability_basis",
        ["capability_state_id"],
    )
    op.create_index(
        "ix_project_capability_basis_project_evidence_id",
        "project_capability_basis",
        ["project_evidence_id"],
    )
    op.create_index(
        "ix_project_capability_basis_approval_id",
        "project_capability_basis",
        ["approval_id"],
    )
    op.create_table(
        "project_enhancement_task",
        sa.Column("task_id", sa.String(length=128), primary_key=True),
        *_revision_columns(),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("target_gap_id", sa.String(length=128), nullable=False),
        sa.Column("target_capability_id", sa.String(length=128), nullable=False),
        sa.Column("learning_plan", sa.JSON(), nullable=False),
        sa.Column("files_to_review", sa.JSON(), nullable=False),
        sa.Column("change_plan", sa.JSON(), nullable=False),
        sa.Column("experiment_plan", sa.JSON(), nullable=False),
        sa.Column("validation_plan", sa.JSON(), nullable=False),
        sa.Column("expected_evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "revision >= 1", name="ck_project_enhancement_revision"
        ),
        sa.CheckConstraint(
            "schema_version >= 1", name="ck_project_enhancement_schema_version"
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'ready', 'in_progress', 'awaiting_validation', "
            "'completed', 'cancelled')",
            name="ck_project_enhancement_status",
        ),
        sa.CheckConstraint(
            "json_type(learning_plan) = 'array' "
            "AND json_array_length(learning_plan) > 0 "
            "AND json_type(files_to_review) = 'array' "
            "AND json_array_length(files_to_review) > 0 "
            "AND json_type(change_plan) = 'array' "
            "AND json_array_length(change_plan) > 0 "
            "AND json_type(experiment_plan) = 'array' "
            "AND json_array_length(experiment_plan) > 0 "
            "AND json_type(validation_plan) = 'array' "
            "AND json_array_length(validation_plan) > 0 "
            "AND json_type(expected_evidence) = 'array' "
            "AND json_array_length(expected_evidence) > 0",
            name="ck_project_enhancement_plans",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project_identity.project_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_capability_id"],
            ["capability_identity.capability_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_project_enhancement_task_project_id",
        "project_enhancement_task",
        ["project_id"],
    )
    op.create_index(
        "ix_project_enhancement_task_target_gap_id",
        "project_enhancement_task",
        ["target_gap_id"],
    )

    _create_scope_path_triggers()
    _create_evidence_and_basis_triggers()
    _create_revision_identity_triggers()
    _create_immutable_history_triggers()


def _create_scope_path_triggers() -> None:
    op.execute(
        "CREATE TRIGGER trg_project_scope_paths_valid "
        "BEFORE INSERT ON project_scan_scope WHEN EXISTS ("
        "SELECT 1 FROM (SELECT value, type FROM json_each(NEW.allowed_paths) "
        "UNION ALL SELECT value, type FROM json_each(NEW.denied_paths)) AS path "
        "WHERE path.type != 'text' OR trim(path.value) = '' "
        "OR path.value LIKE '/%' OR path.value GLOB '[A-Za-z]:*' "
        "OR instr(path.value, char(92)) > 0 OR instr(path.value, '//') > 0 "
        "OR (path.value != '.' AND (path.value LIKE './%' "
        "OR instr(path.value, '/./') > 0 OR path.value LIKE '%/.')) "
        "OR path.value = '..' OR path.value LIKE '../%' "
        "OR path.value LIKE '%/../%' OR path.value LIKE '%/..') BEGIN "
        "SELECT RAISE(ABORT, 'project scope paths must be normalized relative paths'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_source_path_valid "
        "BEFORE INSERT ON project_source_entry WHEN "
        "NEW.relative_path LIKE '/%' OR NEW.relative_path GLOB '[A-Za-z]:*' "
        "OR instr(NEW.relative_path, char(92)) > 0 "
        "OR instr(NEW.relative_path, '//') > 0 "
        "OR (NEW.relative_path != '.' AND (NEW.relative_path LIKE './%' "
        "OR instr(NEW.relative_path, '/./') > 0 "
        "OR NEW.relative_path LIKE '%/.')) OR NEW.relative_path = '..' "
        "OR NEW.relative_path LIKE '../%' OR NEW.relative_path LIKE '%/../%' "
        "OR NEW.relative_path LIKE '%/..' BEGIN "
        "SELECT RAISE(ABORT, 'source entry path must be normalized and relative'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_source_path_in_scope "
        "BEFORE INSERT ON project_source_entry WHEN "
        "NOT EXISTS (SELECT 1 FROM project_source_manifest AS manifest "
        "JOIN project_scan_scope AS scope ON scope.scope_id = manifest.scan_scope_id "
        "AND scope.revision = manifest.scan_scope_revision "
        "AND scope.project_id = manifest.project_id "
        "JOIN json_each(scope.allowed_paths) AS allowed "
        "WHERE manifest.manifest_id = NEW.manifest_id AND (allowed.value = '.' "
        "OR lower(NEW.relative_path) = lower(allowed.value) "
        "OR substr(lower(NEW.relative_path), 1, length(allowed.value) + 1) "
        "= lower(allowed.value) || '/')) "
        "OR EXISTS (SELECT 1 FROM project_source_manifest AS manifest "
        "JOIN project_scan_scope AS scope ON scope.scope_id = manifest.scan_scope_id "
        "AND scope.revision = manifest.scan_scope_revision "
        "AND scope.project_id = manifest.project_id "
        "JOIN json_each(scope.denied_paths) AS denied "
        "WHERE manifest.manifest_id = NEW.manifest_id AND (denied.value = '.' "
        "OR lower(NEW.relative_path) = lower(denied.value) "
        "OR substr(lower(NEW.relative_path), 1, length(denied.value) + 1) "
        "= lower(denied.value) || '/')) BEGIN "
        "SELECT RAISE(ABORT, 'source entry is outside the explicit project scope'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_source_manifest_frozen "
        "BEFORE INSERT ON project_source_entry WHEN EXISTS ("
        "SELECT 1 FROM project_evidence WHERE manifest_id = NEW.manifest_id) BEGIN "
        "SELECT RAISE(ABORT, 'cannot append to an evidence source manifest'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_task_files_valid "
        "BEFORE INSERT ON project_enhancement_task WHEN EXISTS ("
        "SELECT 1 FROM json_each(NEW.files_to_review) AS path "
        "WHERE path.type != 'text' OR trim(path.value) = '' "
        "OR path.value LIKE '/%' OR path.value GLOB '[A-Za-z]:*' "
        "OR instr(path.value, char(92)) > 0 OR instr(path.value, '//') > 0 "
        "OR (path.value != '.' AND (path.value LIKE './%' "
        "OR instr(path.value, '/./') > 0 OR path.value LIKE '%/.')) "
        "OR path.value = '..' OR path.value LIKE '../%' "
        "OR path.value LIKE '%/../%' OR path.value LIKE '%/..') BEGIN "
        "SELECT RAISE(ABORT, 'task files must be normalized relative paths'); END"
    )


def _create_evidence_and_basis_triggers() -> None:
    op.execute(
        "CREATE TRIGGER trg_project_evidence_manifest_has_entries "
        "BEFORE INSERT ON project_evidence WHEN NOT EXISTS ("
        "SELECT 1 FROM project_source_entry WHERE manifest_id = NEW.manifest_id) BEGIN "
        "SELECT RAISE(ABORT, 'project evidence requires a non-empty source manifest'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_capability_project_evidence_exact_revision "
        "BEFORE INSERT ON capability_evidence_binding WHEN "
        "(NEW.project_evidence_id IS NULL AND NEW.project_evidence_revision IS NOT NULL) "
        "OR (NEW.project_evidence_id IS NOT NULL AND ("
        "NEW.project_evidence_revision IS NULL OR NOT EXISTS ("
        "SELECT 1 FROM project_evidence WHERE evidence_id = NEW.project_evidence_id "
        "AND revision = NEW.project_evidence_revision))) BEGIN "
        "SELECT RAISE(ABORT, 'capability binding requires an exact project evidence revision'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_capability_project_evidence_exact_revision_update "
        "BEFORE UPDATE ON capability_evidence_binding WHEN "
        "(NEW.project_evidence_id IS NULL AND NEW.project_evidence_revision IS NOT NULL) "
        "OR (NEW.project_evidence_id IS NOT NULL AND ("
        "NEW.project_evidence_revision IS NULL OR NOT EXISTS ("
        "SELECT 1 FROM project_evidence WHERE evidence_id = NEW.project_evidence_id "
        "AND revision = NEW.project_evidence_revision))) BEGIN "
        "SELECT RAISE(ABORT, 'capability binding requires an exact project evidence revision'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_capability_basis_append_only "
        "BEFORE INSERT ON project_capability_basis WHEN EXISTS ("
        "SELECT 1 FROM project_capability_state WHERE "
        "capability_state_id = NEW.capability_state_id "
        "AND revision = NEW.state_revision) BEGIN "
        "SELECT RAISE(ABORT, 'cannot append basis to finalized capability state'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_capability_basis_evidence_authority "
        "BEFORE INSERT ON project_capability_basis WHEN "
        "NEW.basis_kind != 'resume_approval' AND NOT EXISTS ("
        "SELECT 1 FROM project_evidence AS evidence "
        "WHERE evidence.evidence_id = NEW.project_evidence_id "
        "AND evidence.revision = NEW.project_evidence_revision "
        "AND evidence.review_status = 'accepted' "
        "AND evidence.authority != 'ai_inferred' AND ("
        "(NEW.basis_kind = 'code_evidence' AND evidence.authority = 'code_verified') "
        "OR (NEW.basis_kind = 'document_evidence' "
        "AND evidence.authority = 'document_supported') "
        "OR (NEW.basis_kind = 'user_confirmation' "
        "AND evidence.authority = 'user_confirmed') "
        "OR (NEW.basis_kind = 'change_evidence' "
        "AND evidence.claim_kind = 'change') "
        "OR (NEW.basis_kind = 'validation_evidence' "
        "AND evidence.claim_kind = 'validation'))) BEGIN "
        "SELECT RAISE(ABORT, 'project capability evidence basis is not authoritative'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_capability_basis_approval_authority "
        "BEFORE INSERT ON project_capability_basis WHEN "
        "NEW.basis_kind = 'resume_approval' AND NOT EXISTS ("
        "SELECT 1 FROM entity_revision AS approval_revision "
        "JOIN entity_state AS approval ON approval.entity_id = approval_revision.entity_id "
        "WHERE approval_revision.entity_id = NEW.approval_id "
        "AND approval_revision.revision = NEW.approval_revision "
        "AND approval.entity_kind = 'approval' "
        "AND json_extract(approval_revision.state, '$.status') = 'approved' "
        "AND json_extract(approval_revision.state, '$.approver_kind') = 'user' "
        "AND json_extract(approval_revision.state, '$.subject_id') "
        "= NEW.capability_state_id "
        "AND json_extract(approval_revision.state, '$.subject_revision') "
        "= NEW.state_revision "
        "AND json_extract(approval_revision.state, '$.purpose') "
        "= 'project_capability_resume_ready') BEGIN "
        "SELECT RAISE(ABORT, 'project capability approval basis is not authoritative'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_capability_state_basis_scope "
        "BEFORE INSERT ON project_capability_state WHEN EXISTS ("
        "SELECT 1 FROM project_capability_basis AS basis "
        "JOIN project_evidence AS evidence "
        "ON evidence.evidence_id = basis.project_evidence_id "
        "AND evidence.revision = basis.project_evidence_revision "
        "WHERE basis.capability_state_id = NEW.capability_state_id "
        "AND basis.state_revision = NEW.revision "
        "AND evidence.project_id != NEW.project_id) BEGIN "
        "SELECT RAISE(ABORT, 'project capability evidence belongs to another project'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_capability_insert_basis "
        "BEFORE INSERT ON project_capability_state WHEN "
        "(NEW.state = 'existing' AND NOT EXISTS (SELECT 1 FROM project_capability_basis "
        "WHERE capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind IN ('code_evidence', 'document_evidence', 'user_confirmation'))) "
        "OR (NEW.state = 'understood' AND NOT EXISTS (SELECT 1 FROM project_capability_basis "
        "WHERE capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind = 'user_confirmation')) "
        "OR (NEW.state IN ('modified', 'extended') AND ("
        "NOT EXISTS (SELECT 1 FROM project_capability_basis WHERE "
        "capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind = 'change_evidence') OR NOT EXISTS ("
        "SELECT 1 FROM project_capability_basis WHERE "
        "capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind = 'user_confirmation'))) "
        "OR (NEW.state = 'validated' AND NOT EXISTS ("
        "SELECT 1 FROM project_capability_basis WHERE "
        "capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind = 'validation_evidence')) "
        "OR (NEW.state = 'resume_ready' AND (NOT EXISTS ("
        "SELECT 1 FROM project_capability_basis WHERE "
        "capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind = 'validation_evidence') OR NOT EXISTS ("
        "SELECT 1 FROM project_capability_basis WHERE "
        "capability_state_id = NEW.capability_state_id AND state_revision = NEW.revision "
        "AND basis_kind = 'resume_approval'))) BEGIN "
        "SELECT RAISE(ABORT, 'project capability state lacks required basis'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_enhancement_plan_items "
        "BEFORE INSERT ON project_enhancement_task WHEN EXISTS ("
        "SELECT 1 FROM (SELECT value, type FROM json_each(NEW.learning_plan) "
        "UNION ALL SELECT value, type FROM json_each(NEW.change_plan) "
        "UNION ALL SELECT value, type FROM json_each(NEW.experiment_plan) "
        "UNION ALL SELECT value, type FROM json_each(NEW.validation_plan) "
        "UNION ALL SELECT value, type FROM json_each(NEW.expected_evidence)) AS item "
        "WHERE item.type != 'text' OR trim(item.value) = '') BEGIN "
        "SELECT RAISE(ABORT, 'enhancement plan items must be non-empty text'); END"
    )


def _create_immutable_history_triggers() -> None:
    for table_name in (
        "project_record",
        "project_scan_scope",
        "project_source_manifest",
        "project_source_entry",
        "project_evidence",
        "project_capability_state",
        "project_capability_basis",
        "project_enhancement_task",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update BEFORE UPDATE ON {table_name} BEGIN "
            "SELECT RAISE(ABORT, 'project history is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete BEFORE DELETE ON {table_name} BEGIN "
            "SELECT RAISE(ABORT, 'project history is immutable'); END"
        )
    op.execute(
        "CREATE TRIGGER trg_entity_revision_no_update BEFORE UPDATE ON entity_revision BEGIN "
        "SELECT RAISE(ABORT, 'entity revisions are immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_entity_revision_no_delete BEFORE DELETE ON entity_revision BEGIN "
        "SELECT RAISE(ABORT, 'entity revisions are immutable'); END"
    )


def _create_revision_identity_triggers() -> None:
    op.execute(
        "CREATE TRIGGER trg_project_scope_stable_identity "
        "BEFORE INSERT ON project_scan_scope WHEN EXISTS ("
        "SELECT 1 FROM project_scan_scope WHERE scope_id = NEW.scope_id "
        "AND project_id != NEW.project_id) BEGIN "
        "SELECT RAISE(ABORT, 'project scope revisions cannot change project'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_evidence_stable_identity "
        "BEFORE INSERT ON project_evidence WHEN EXISTS ("
        "SELECT 1 FROM project_evidence WHERE evidence_id = NEW.evidence_id "
        "AND project_id != NEW.project_id) BEGIN "
        "SELECT RAISE(ABORT, 'project evidence revisions cannot change project'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_capability_stable_identity "
        "BEFORE INSERT ON project_capability_state WHEN EXISTS ("
        "SELECT 1 FROM project_capability_state "
        "WHERE capability_state_id = NEW.capability_state_id AND ("
        "project_id != NEW.project_id OR capability_id != NEW.capability_id)) BEGIN "
        "SELECT RAISE(ABORT, 'project capability revisions cannot change identity'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_project_task_stable_identity "
        "BEFORE INSERT ON project_enhancement_task WHEN EXISTS ("
        "SELECT 1 FROM project_enhancement_task WHERE task_id = NEW.task_id AND ("
        "project_id != NEW.project_id OR target_gap_id != NEW.target_gap_id "
        "OR target_capability_id != NEW.target_capability_id)) BEGIN "
        "SELECT RAISE(ABORT, 'project task revisions cannot change identity'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_project_task_stable_identity")
    op.execute("DROP TRIGGER trg_project_capability_stable_identity")
    op.execute("DROP TRIGGER trg_project_evidence_stable_identity")
    op.execute("DROP TRIGGER trg_project_scope_stable_identity")
    op.execute("DROP TRIGGER trg_entity_revision_no_delete")
    op.execute("DROP TRIGGER trg_entity_revision_no_update")
    for table_name in (
        "project_enhancement_task",
        "project_capability_basis",
        "project_capability_state",
        "project_evidence",
        "project_source_entry",
        "project_source_manifest",
        "project_scan_scope",
        "project_record",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")
    op.execute("DROP TRIGGER trg_project_capability_insert_basis")
    op.execute("DROP TRIGGER trg_project_capability_state_basis_scope")
    op.execute("DROP TRIGGER trg_project_capability_basis_approval_authority")
    op.execute("DROP TRIGGER trg_project_capability_basis_evidence_authority")
    op.execute("DROP TRIGGER trg_project_capability_basis_append_only")
    op.execute("DROP TRIGGER trg_project_enhancement_plan_items")
    op.execute("DROP TRIGGER trg_capability_project_evidence_exact_revision_update")
    op.execute("DROP TRIGGER trg_capability_project_evidence_exact_revision")
    op.execute("DROP TRIGGER trg_project_evidence_manifest_has_entries")
    op.execute("DROP TRIGGER trg_project_task_files_valid")
    op.execute("DROP TRIGGER trg_project_source_manifest_frozen")
    op.execute("DROP TRIGGER trg_project_source_path_in_scope")
    op.execute("DROP TRIGGER trg_project_source_path_valid")
    op.execute("DROP TRIGGER trg_project_scope_paths_valid")

    op.drop_index(
        "ix_project_enhancement_task_target_gap_id",
        table_name="project_enhancement_task",
    )
    op.drop_index(
        "ix_project_enhancement_task_project_id",
        table_name="project_enhancement_task",
    )
    op.drop_table("project_enhancement_task")
    op.drop_index(
        "ix_project_capability_state_project_id",
        table_name="project_capability_state",
    )
    op.drop_index(
        "ix_project_capability_basis_approval_id",
        table_name="project_capability_basis",
    )
    op.drop_index(
        "ix_project_capability_basis_project_evidence_id",
        table_name="project_capability_basis",
    )
    op.drop_index(
        "ix_project_capability_basis_capability_state_id",
        table_name="project_capability_basis",
    )
    op.drop_table("project_capability_basis")
    op.drop_table("project_capability_state")
    op.drop_index("ix_project_evidence_project_id", table_name="project_evidence")
    op.drop_table("project_evidence")
    op.drop_column("capability_evidence_binding", "project_evidence_revision")
    op.drop_table("project_source_entry")
    op.drop_index(
        "ix_project_source_manifest_project_id",
        table_name="project_source_manifest",
    )
    op.drop_table("project_source_manifest")
    op.drop_index(
        "ix_project_scan_scope_project_id", table_name="project_scan_scope"
    )
    op.drop_table("project_scan_scope")
    op.drop_table("project_record")
    op.drop_table("project_identity")
