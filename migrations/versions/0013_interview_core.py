"""Add canonical Interview records pinned to exact Application revisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_interview_core"
down_revision: str | None = "0012_application_outcome"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "interview_identity",
    "interview_revision_record",
    "interview_evidence_ref",
)


def upgrade() -> None:
    op.create_table(
        "interview_identity",
        sa.Column("interview_id", sa.String(128), primary_key=True),
        sa.Column("application_id", sa.String(128), nullable=False),
        sa.Column("application_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application_identity.application_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "application_revision"],
            ["application_revision_record.application_id", "application_revision_record.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_interview_identity_application_id", "interview_identity", ["application_id"]
    )
    op.create_table(
        "interview_revision_record",
        sa.Column("interview_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("round", sa.String(32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_interview_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_interview_schema_version"),
        sa.CheckConstraint(
            "round IN ('screen', 'technical', 'loop', 'offer_talk')", name="ck_interview_round"
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled')", name="ck_interview_status"
        ),
        sa.CheckConstraint("evidence_count >= 0", name="ck_interview_evidence_count"),
        sa.CheckConstraint(
            "revision > 1 OR status = 'scheduled'", name="ck_interview_first_revision_scheduled"
        ),
        sa.ForeignKeyConstraint(
            ["interview_id"], ["interview_identity.interview_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "interview_evidence_ref",
        sa.Column("interview_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref_id", sa.String(128), nullable=False),
        sa.UniqueConstraint(
            "interview_id", "revision", "evidence_ref_id", name="uq_interview_evidence_ref"
        ),
        sa.CheckConstraint("revision >= 1", name="ck_interview_evidence_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_interview_evidence_ordinal"),
        sa.ForeignKeyConstraint(
            ["interview_id", "revision"],
            ["interview_revision_record.interview_id", "interview_revision_record.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
    )
    op.execute(
        "CREATE TRIGGER trg_interview_revision_seal BEFORE INSERT "
        "ON interview_revision_record WHEN "
        "(SELECT count(*) FROM interview_evidence_ref WHERE interview_id = NEW.interview_id "
        "AND revision = NEW.revision) != NEW.evidence_count OR (NEW.evidence_count > 0 AND ("
        "COALESCE((SELECT min(ordinal) FROM interview_evidence_ref WHERE "
        "interview_id = NEW.interview_id AND revision = NEW.revision), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM interview_evidence_ref WHERE "
        "interview_id = NEW.interview_id AND revision = NEW.revision), -1) "
        "!= NEW.evidence_count - 1)) BEGIN "
        "SELECT RAISE(ABORT, 'interview evidence aggregate is incomplete'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_interview_evidence_ref_sealed BEFORE INSERT ON "
        "interview_evidence_ref WHEN EXISTS (SELECT 1 FROM interview_revision_record WHERE "
        "interview_id = NEW.interview_id AND revision = NEW.revision) BEGIN "
        "SELECT RAISE(ABORT, 'interview evidence aggregate is sealed'); END"
    )
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
    op.execute("DROP TRIGGER trg_interview_evidence_ref_sealed")
    op.execute("DROP TRIGGER trg_interview_revision_seal")
    op.drop_table("interview_evidence_ref")
    op.drop_table("interview_revision_record")
    op.drop_index("ix_interview_identity_application_id", table_name="interview_identity")
    op.drop_table("interview_identity")
