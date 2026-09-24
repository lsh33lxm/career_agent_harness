"""Persist evidence-backed Job revisions and reviewed JobRequirements."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_job_requirement_persistence"
down_revision: str | None = "0007_evidence_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LEGACY_JOB_REF_TABLES = (
    "watchlist_item",
    "opportunity_admission_proposal",
    "opportunity_record",
    "opportunity_admission_decision",
)


def upgrade() -> None:
    op.create_table(
        "job_identity",
        sa.Column("job_id", sa.String(length=128), primary_key=True),
    )
    op.create_table(
        "job_revision",
        sa.Column("job_id", sa.String(length=128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_evidence_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_job_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_job_schema_version"),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_job_content_sha256",
        ),
        sa.CheckConstraint("source_evidence_count >= 1", name="ck_job_evidence_count"),
        sa.ForeignKeyConstraint(["job_id"], ["job_identity.job_id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "job_revision_evidence_ref",
        sa.Column("job_id", sa.String(length=128), primary_key=True),
        sa.Column("job_revision", sa.Integer(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("job_id", "job_revision", "evidence_ref_id"),
        sa.CheckConstraint("job_revision >= 1", name="ck_job_evidence_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_job_evidence_ordinal"),
        sa.ForeignKeyConstraint(
            ["job_id", "job_revision"],
            ["job_revision.job_id", "job_revision.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_job_revision_evidence_ref_evidence_ref_id",
        "job_revision_evidence_ref",
        ["evidence_ref_id"],
    )

    op.create_table(
        "job_requirement_identity",
        sa.Column("requirement_id", sa.String(length=128), primary_key=True),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("requirement_id", "job_id"),
        sa.ForeignKeyConstraint(["job_id"], ["job_identity.job_id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_job_requirement_identity_job_id", "job_requirement_identity", ["job_id"])
    op.create_table(
        "job_requirement_revision",
        sa.Column("requirement_id", sa.String(length=128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=32), nullable=False),
        sa.Column("capability_id", sa.String(length=128)),
        sa.Column("graph_version_id", sa.String(length=128)),
        sa.Column("required_scope_count", sa.Integer(), nullable=False),
        sa.Column("source_evidence_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("proposed_by", sa.String(length=255), nullable=False),
        sa.Column("proposed_by_kind", sa.String(length=32), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255)),
        sa.Column("reviewed_by_kind", sa.String(length=32)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("revision >= 1", name="ck_job_requirement_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_job_requirement_schema_version"),
        sa.CheckConstraint("job_revision >= 1", name="ck_job_requirement_job_revision"),
        sa.CheckConstraint(
            "length(trim(requirement_text)) > 0 AND length(requirement_text) <= 4096",
            name="ck_job_requirement_text",
        ),
        sa.CheckConstraint(
            "importance IN ('required', 'preferred')", name="ck_job_requirement_importance"
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'superseded')",
            name="ck_job_requirement_status",
        ),
        sa.CheckConstraint(
            "(capability_id IS NULL AND graph_version_id IS NULL) OR "
            "(capability_id IS NOT NULL AND graph_version_id IS NOT NULL)",
            name="ck_job_requirement_mapping_pair",
        ),
        sa.CheckConstraint(
            "required_scope_count >= 1 AND source_evidence_count >= 1",
            name="ck_job_requirement_counts",
        ),
        sa.CheckConstraint(
            "length(trim(proposed_by)) > 0 AND proposed_by_kind IN ('user', 'agent', 'rule')",
            name="ck_job_requirement_proposer",
        ),
        sa.CheckConstraint(
            "(status = 'proposed' AND reviewed_by IS NULL AND reviewed_by_kind IS NULL "
            "AND review_reason IS NULL AND reviewed_at IS NULL) OR "
            "(status != 'proposed' AND length(trim(reviewed_by)) > 0 "
            "AND reviewed_by_kind IN ('user', 'rule') "
            "AND length(trim(review_reason)) > 0 AND reviewed_at IS NOT NULL)",
            name="ck_job_requirement_review",
        ),
        sa.CheckConstraint(
            "status != 'accepted' OR capability_id IS NOT NULL",
            name="ck_job_requirement_accepted_mapping",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id", "job_id"],
            ["job_requirement_identity.requirement_id", "job_requirement_identity.job_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_id", "job_revision"],
            ["job_revision.job_id", "job_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id", "graph_version_id"],
            ["capability_node.capability_id", "capability_node.graph_version_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_job_requirement_revision_job_id", "job_requirement_revision", ["job_id"])
    op.create_index(
        "ix_job_requirement_job_status",
        "job_requirement_revision",
        ["job_id", "job_revision", "status", "requirement_id", "revision"],
    )
    op.create_index(
        "ix_job_requirement_capability_status",
        "job_requirement_revision",
        ["capability_id", "graph_version_id", "status"],
    )

    op.create_table(
        "job_requirement_scope",
        sa.Column("requirement_id", sa.String(length=128), primary_key=True),
        sa.Column("requirement_revision", sa.Integer(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("requirement_id", "requirement_revision", "scope"),
        sa.CheckConstraint("requirement_revision >= 1", name="ck_job_requirement_scope_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_job_requirement_scope_ordinal"),
        sa.CheckConstraint(
            "scope IN ('understand', 'explain', 'apply', 'evidence', 'interview_ready')",
            name="ck_job_requirement_scope_value",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id", "requirement_revision"],
            ["job_requirement_revision.requirement_id", "job_requirement_revision.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_table(
        "job_requirement_evidence_ref",
        sa.Column("requirement_id", sa.String(length=128), primary_key=True),
        sa.Column("requirement_revision", sa.Integer(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("requirement_id", "requirement_revision", "evidence_ref_id"),
        sa.CheckConstraint(
            "requirement_revision >= 1", name="ck_job_requirement_evidence_revision"
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_job_requirement_evidence_ordinal"),
        sa.ForeignKeyConstraint(
            ["requirement_id", "requirement_revision"],
            ["job_requirement_revision.requirement_id", "job_requirement_revision.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_job_requirement_evidence_ref_evidence_ref_id",
        "job_requirement_evidence_ref",
        ["evidence_ref_id"],
    )

    _create_sealing_triggers()
    _create_immutable_triggers()
    _create_legacy_job_ref_guards()


def _create_sealing_triggers() -> None:
    op.execute(
        "CREATE TRIGGER trg_job_revision_seal BEFORE INSERT ON job_revision WHEN "
        "(SELECT count(*) FROM job_revision_evidence_ref WHERE job_id = NEW.job_id "
        "AND job_revision = NEW.revision) != NEW.source_evidence_count OR "
        "COALESCE((SELECT min(ordinal) FROM job_revision_evidence_ref WHERE "
        "job_id = NEW.job_id AND job_revision = NEW.revision), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM job_revision_evidence_ref WHERE "
        "job_id = NEW.job_id AND job_revision = NEW.revision), -1) "
        "!= NEW.source_evidence_count - 1 BEGIN "
        "SELECT RAISE(ABORT, 'job revision evidence aggregate is incomplete'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_job_revision_evidence_sealed BEFORE INSERT "
        "ON job_revision_evidence_ref WHEN EXISTS (SELECT 1 FROM job_revision "
        "WHERE job_id = NEW.job_id AND revision = NEW.job_revision) BEGIN "
        "SELECT RAISE(ABORT, 'job revision evidence aggregate is sealed'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_job_requirement_seal BEFORE INSERT ON job_requirement_revision WHEN "
        "(SELECT count(*) FROM job_requirement_scope WHERE requirement_id = NEW.requirement_id "
        "AND requirement_revision = NEW.revision) != NEW.required_scope_count OR "
        "COALESCE((SELECT min(ordinal) FROM job_requirement_scope WHERE "
        "requirement_id = NEW.requirement_id AND requirement_revision = NEW.revision), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM job_requirement_scope WHERE "
        "requirement_id = NEW.requirement_id AND requirement_revision = NEW.revision), -1) "
        "!= NEW.required_scope_count - 1 OR "
        "(SELECT count(*) FROM job_requirement_evidence_ref WHERE "
        "requirement_id = NEW.requirement_id AND requirement_revision = NEW.revision) "
        "!= NEW.source_evidence_count OR "
        "COALESCE((SELECT min(ordinal) FROM job_requirement_evidence_ref WHERE "
        "requirement_id = NEW.requirement_id AND requirement_revision = NEW.revision), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM job_requirement_evidence_ref WHERE "
        "requirement_id = NEW.requirement_id AND requirement_revision = NEW.revision), -1) "
        "!= NEW.source_evidence_count - 1 BEGIN "
        "SELECT RAISE(ABORT, 'job requirement aggregate is incomplete'); END"
    )
    for child_table in ("job_requirement_scope", "job_requirement_evidence_ref"):
        op.execute(
            f"CREATE TRIGGER trg_{child_table}_sealed BEFORE INSERT ON {child_table} "
            "WHEN EXISTS (SELECT 1 FROM job_requirement_revision WHERE "
            "requirement_id = NEW.requirement_id AND revision = NEW.requirement_revision) BEGIN "
            "SELECT RAISE(ABORT, 'job requirement aggregate is sealed'); END"
        )


def _create_immutable_triggers() -> None:
    for table_name in (
        "job_identity",
        "job_revision",
        "job_revision_evidence_ref",
        "job_requirement_identity",
        "job_requirement_revision",
        "job_requirement_scope",
        "job_requirement_evidence_ref",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update BEFORE UPDATE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete BEFORE DELETE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )


def _create_legacy_job_ref_guards() -> None:
    for table_name in LEGACY_JOB_REF_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_job_ref_insert BEFORE INSERT ON {table_name} "
            "WHEN NOT EXISTS (SELECT 1 FROM job_revision WHERE job_id = NEW.job_id "
            "AND revision = NEW.job_revision) BEGIN "
            "SELECT RAISE(ABORT, 'legacy record requires an exact canonical job revision'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_job_ref_update "
            f"BEFORE UPDATE OF job_id, job_revision ON {table_name} "
            "WHEN NOT EXISTS (SELECT 1 FROM job_revision WHERE job_id = NEW.job_id "
            "AND revision = NEW.job_revision) BEGIN "
            "SELECT RAISE(ABORT, 'legacy record requires an exact canonical job revision'); END"
        )


def downgrade() -> None:
    for table_name in reversed(LEGACY_JOB_REF_TABLES):
        op.execute(f"DROP TRIGGER trg_{table_name}_job_ref_update")
        op.execute(f"DROP TRIGGER trg_{table_name}_job_ref_insert")

    for table_name in reversed(
        (
            "job_identity",
            "job_revision",
            "job_revision_evidence_ref",
            "job_requirement_identity",
            "job_requirement_revision",
            "job_requirement_scope",
            "job_requirement_evidence_ref",
        )
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")

    op.execute("DROP TRIGGER trg_job_requirement_evidence_ref_sealed")
    op.execute("DROP TRIGGER trg_job_requirement_scope_sealed")
    op.execute("DROP TRIGGER trg_job_requirement_seal")
    op.execute("DROP TRIGGER trg_job_revision_evidence_sealed")
    op.execute("DROP TRIGGER trg_job_revision_seal")

    op.drop_index(
        "ix_job_requirement_evidence_ref_evidence_ref_id",
        table_name="job_requirement_evidence_ref",
    )
    op.drop_table("job_requirement_evidence_ref")
    op.drop_table("job_requirement_scope")
    op.drop_index("ix_job_requirement_capability_status", table_name="job_requirement_revision")
    op.drop_index("ix_job_requirement_job_status", table_name="job_requirement_revision")
    op.drop_index("ix_job_requirement_revision_job_id", table_name="job_requirement_revision")
    op.drop_table("job_requirement_revision")
    op.drop_index("ix_job_requirement_identity_job_id", table_name="job_requirement_identity")
    op.drop_table("job_requirement_identity")
    op.drop_index(
        "ix_job_revision_evidence_ref_evidence_ref_id",
        table_name="job_revision_evidence_ref",
    )
    op.drop_table("job_revision_evidence_ref")
    op.drop_table("job_revision")
    op.drop_table("job_identity")
