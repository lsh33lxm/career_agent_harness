"""Add canonical Resume Base, Patch and Revision records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_resume_core"
down_revision: str | None = "0010_fact_promotion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "resume_identity",
    "resume_base_revision",
    "resume_patch_identity",
    "resume_patch_revision",
    "resume_revision_record",
    "resume_revision_patch_ref",
)


def upgrade() -> None:
    op.create_table(
        "resume_identity",
        sa.Column("resume_id", sa.String(128), primary_key=True),
        sa.Column("candidate_id", sa.String(128), nullable=False),
    )
    op.create_index("ix_resume_identity_candidate_id", "resume_identity", ["candidate_id"])
    op.create_table(
        "resume_base_revision",
        sa.Column("resume_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_resume_base_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_resume_base_schema_version"),
        sa.CheckConstraint(
            "json_type(sections) = 'object' AND length(sections) <= 65536",
            name="ck_resume_base_sections",
        ),
        sa.ForeignKeyConstraint(["resume_id"], ["resume_identity.resume_id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "resume_patch_identity",
        sa.Column("patch_id", sa.String(128), primary_key=True),
        sa.Column("resume_id", sa.String(128), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resume_identity.resume_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["resume_id", "base_revision"],
            ["resume_base_revision.resume_id", "resume_base_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_resume_patch_identity_resume_id", "resume_patch_identity", ["resume_id"])
    op.create_table(
        "resume_patch_revision",
        sa.Column("patch_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("operations", sa.JSON(), nullable=False),
        sa.Column("generator_run_id", sa.String(128)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("proposed_by", sa.String(255), nullable=False),
        sa.Column("proposed_by_kind", sa.String(32), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("reviewed_by_kind", sa.String(32)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("revision >= 1", name="ck_resume_patch_revision"),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected')", name="ck_resume_patch_status"
        ),
        sa.CheckConstraint(
            "json_type(operations) = 'array' AND json_array_length(operations) BETWEEN 1 AND 128 "
            "AND length(operations) <= 65536",
            name="ck_resume_patch_operations",
        ),
        sa.CheckConstraint(
            "(status = 'proposed' AND reviewed_by IS NULL AND reviewed_by_kind IS NULL "
            "AND review_reason IS NULL AND reviewed_at IS NULL) OR "
            "(status != 'proposed' AND length(trim(reviewed_by)) > 0 "
            "AND reviewed_by_kind = 'user' AND length(trim(review_reason)) > 0 "
            "AND reviewed_at IS NOT NULL)",
            name="ck_resume_patch_review",
        ),
        sa.ForeignKeyConstraint(
            ["patch_id"], ["resume_patch_identity.patch_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "resume_revision_record",
        sa.Column("revision_id", sa.String(128), primary_key=True),
        sa.Column("resume_id", sa.String(128), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("patch_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.CheckConstraint("base_revision >= 1", name="ck_resume_revision_base"),
        sa.CheckConstraint("patch_count >= 0", name="ck_resume_revision_patch_count"),
        sa.CheckConstraint(
            "json_type(content) = 'object' AND length(content) <= 65536",
            name="ck_resume_revision_content",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_resume_revision_hash",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id", "base_revision"],
            ["resume_base_revision.resume_id", "resume_base_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_resume_revision_record_resume_id", "resume_revision_record", ["resume_id"])
    op.create_table(
        "resume_revision_patch_ref",
        sa.Column("revision_id", sa.String(128), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("patch_id", sa.String(128), nullable=False),
        sa.Column("patch_revision", sa.Integer(), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_resume_revision_patch_ordinal"),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["resume_revision_record.revision_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["patch_id", "patch_revision"],
            ["resume_patch_revision.patch_id", "resume_patch_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.execute(
        "CREATE TRIGGER trg_resume_revision_record_seal BEFORE INSERT "
        "ON resume_revision_record WHEN "
        "(SELECT count(*) FROM resume_revision_patch_ref WHERE revision_id = NEW.revision_id) "
        "!= NEW.patch_count OR (NEW.patch_count > 0 AND ("
        "COALESCE((SELECT min(ordinal) FROM resume_revision_patch_ref WHERE "
        "revision_id = NEW.revision_id), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM resume_revision_patch_ref WHERE "
        "revision_id = NEW.revision_id), -1) != NEW.patch_count - 1)) BEGIN "
        "SELECT RAISE(ABORT, 'resume revision patch aggregate is incomplete'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_resume_revision_patch_ref_sealed BEFORE INSERT "
        "ON resume_revision_patch_ref WHEN EXISTS (SELECT 1 FROM resume_revision_record "
        "WHERE revision_id = NEW.revision_id) BEGIN "
        "SELECT RAISE(ABORT, 'resume revision patch aggregate is sealed'); END"
    )
    _immutable_triggers()


def _immutable_triggers() -> None:
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_update BEFORE UPDATE ON {table} BEGIN "
            f"SELECT RAISE(ABORT, '{table} is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} BEGIN "
            f"SELECT RAISE(ABORT, '{table} is immutable'); END"
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP TRIGGER trg_{table}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table}_no_update")
    op.execute("DROP TRIGGER trg_resume_revision_patch_ref_sealed")
    op.execute("DROP TRIGGER trg_resume_revision_record_seal")
    op.drop_table("resume_revision_patch_ref")
    op.drop_index("ix_resume_revision_record_resume_id", table_name="resume_revision_record")
    op.drop_table("resume_revision_record")
    op.drop_table("resume_patch_revision")
    op.drop_index("ix_resume_patch_identity_resume_id", table_name="resume_patch_identity")
    op.drop_table("resume_patch_identity")
    op.drop_table("resume_base_revision")
    op.drop_index("ix_resume_identity_candidate_id", table_name="resume_identity")
    op.drop_table("resume_identity")
