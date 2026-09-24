"""Add canonical Application revisions and Outcome records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_application_outcome"
down_revision: str | None = "0011_resume_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "application_identity",
    "application_revision_record",
    "outcome_record",
    "outcome_evidence_ref",
)


def upgrade() -> None:
    op.create_table(
        "application_identity",
        sa.Column("application_id", sa.String(128), primary_key=True),
        sa.Column("opportunity_id", sa.String(128), nullable=False),
        sa.Column("opportunity_revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity_record.opportunity_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id", "opportunity_revision"],
            ["entity_revision.entity_id", "entity_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "application_revision_record",
        sa.Column("application_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("resume_revision_id", sa.String(128)),
        sa.Column("submission_authority", sa.String(32)),
        sa.Column("submission_evidence_ref_id", sa.String(128)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_application_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_application_schema_version"),
        sa.CheckConstraint(
            "state IN ('preparing', 'ready_for_review', 'submitted_by_user', 'screen', 'oa', "
            "'interview', 'offer', 'rejected', 'withdrawn', 'closed')",
            name="ck_application_state",
        ),
        sa.CheckConstraint(
            "(state IN ('preparing', 'ready_for_review') AND resume_revision_id IS NULL "
            "AND submission_authority IS NULL AND submission_evidence_ref_id IS NULL "
            "AND submitted_at IS NULL) OR (state NOT IN ('preparing', 'ready_for_review') "
            "AND resume_revision_id IS NOT NULL "
            "AND submission_authority IN ('user_confirmed', 'portal_receipt') "
            "AND submitted_at IS NOT NULL)",
            name="ck_application_submission",
        ),
        sa.CheckConstraint(
            "submission_authority != 'portal_receipt' OR submission_evidence_ref_id IS NOT NULL",
            name="ck_application_portal_receipt",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["application_identity.application_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resume_revision_id"],
            ["resume_revision_record.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_evidence_ref_id"],
            ["evidence_ref.evidence_ref_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "outcome_record",
        sa.Column("outcome_id", sa.String(128), primary_key=True),
        sa.Column("application_id", sa.String(128), nullable=False),
        sa.Column("application_revision", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("recorded_by", sa.String(255), nullable=False),
        sa.CheckConstraint("application_revision >= 1", name="ck_outcome_application_revision"),
        sa.CheckConstraint(
            "result IN ('offer', 'rejection', 'withdrawal', 'closed')", name="ck_outcome_result"
        ),
        sa.CheckConstraint(
            "authority IN ('user_confirmed', 'portal_receipt')", name="ck_outcome_authority"
        ),
        sa.CheckConstraint("evidence_count >= 0", name="ck_outcome_evidence_count"),
        sa.CheckConstraint(
            "authority != 'portal_receipt' OR evidence_count > 0",
            name="ck_outcome_portal_receipt",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "application_revision"],
            ["application_revision_record.application_id", "application_revision_record.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_outcome_record_application_id", "outcome_record", ["application_id"])
    op.create_table(
        "outcome_evidence_ref",
        sa.Column("outcome_id", sa.String(128), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref_id", sa.String(128), nullable=False),
        sa.UniqueConstraint("outcome_id", "evidence_ref_id", name="uq_outcome_evidence_ref"),
        sa.CheckConstraint("ordinal >= 0", name="ck_outcome_evidence_ordinal"),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["outcome_record.outcome_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
    )
    op.execute(
        "CREATE TRIGGER trg_application_submission_stable BEFORE INSERT "
        "ON application_revision_record WHEN EXISTS (SELECT 1 FROM application_revision_record "
        "AS prior WHERE prior.application_id = NEW.application_id "
        "AND prior.submission_authority IS NOT NULL AND ("
        "prior.resume_revision_id IS NOT NEW.resume_revision_id OR "
        "prior.submission_authority IS NOT NEW.submission_authority OR "
        "prior.submission_evidence_ref_id IS NOT NEW.submission_evidence_ref_id OR "
        "prior.submitted_at IS NOT NEW.submitted_at)) BEGIN "
        "SELECT RAISE(ABORT, 'Application submission identity cannot change'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_outcome_record_seal BEFORE INSERT ON outcome_record WHEN "
        "(SELECT count(*) FROM outcome_evidence_ref WHERE outcome_id = NEW.outcome_id) "
        "!= NEW.evidence_count OR (NEW.evidence_count > 0 AND ("
        "COALESCE((SELECT min(ordinal) FROM outcome_evidence_ref WHERE "
        "outcome_id = NEW.outcome_id), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM outcome_evidence_ref WHERE "
        "outcome_id = NEW.outcome_id), -1) "
        "!= NEW.evidence_count - 1)) BEGIN "
        "SELECT RAISE(ABORT, 'outcome evidence aggregate is incomplete'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_outcome_evidence_ref_sealed BEFORE INSERT ON outcome_evidence_ref "
        "WHEN EXISTS (SELECT 1 FROM outcome_record WHERE outcome_id = NEW.outcome_id) BEGIN "
        "SELECT RAISE(ABORT, 'outcome evidence aggregate is sealed'); END"
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
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_no_delete")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_no_update")
    op.execute("DROP TRIGGER trg_outcome_evidence_ref_sealed")
    op.execute("DROP TRIGGER trg_outcome_record_seal")
    op.execute("DROP TRIGGER IF EXISTS trg_application_submission_stable")
    op.drop_table("outcome_evidence_ref")
    op.drop_index("ix_outcome_record_application_id", table_name="outcome_record")
    op.drop_table("outcome_record")
    op.drop_table("application_revision_record")
    op.drop_table("application_identity")
