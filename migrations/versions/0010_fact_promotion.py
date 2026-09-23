"""Persist reviewed ExtractedClaims and revisioned promoted Facts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_fact_promotion"
down_revision: str | None = "0009_match_gap_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FACT_TABLES = (
    "extracted_claim_identity",
    "extracted_claim_revision",
    "extracted_claim_evidence_ref",
    "fact_identity",
    "fact_revision",
    "fact_evidence_ref",
)


def upgrade() -> None:
    op.create_table(
        "extracted_claim_identity",
        sa.Column("claim_id", sa.String(length=128), primary_key=True),
    )
    op.create_table(
        "extracted_claim_revision",
        sa.Column("claim_id", sa.String(length=128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("claim_type", sa.String(length=128), nullable=False),
        sa.Column("subject_entity_id", sa.String(length=128), nullable=False),
        sa.Column("subject_entity_kind", sa.String(length=64), nullable=False),
        sa.Column("proposed_value", sa.JSON(), nullable=False),
        sa.Column("extractor", sa.String(length=255), nullable=False),
        sa.Column("extractor_version", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("proposed_by", sa.String(length=255), nullable=False),
        sa.Column("proposed_by_kind", sa.String(length=32), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255)),
        sa.Column("reviewed_by_kind", sa.String(length=32)),
        sa.Column("review_reason", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("revision >= 1", name="ck_extracted_claim_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_extracted_claim_schema_version"),
        sa.CheckConstraint("length(trim(claim_type)) > 0", name="ck_extracted_claim_claim_type"),
        sa.CheckConstraint(
            "json_type(proposed_value) IS NOT NULL AND length(proposed_value) <= 65536",
            name="ck_extracted_claim_proposed_value",
        ),
        sa.CheckConstraint(
            "length(trim(extractor)) > 0 AND length(trim(extractor_version)) > 0",
            name="ck_extracted_claim_extractor",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_extracted_claim_confidence"
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'superseded')",
            name="ck_extracted_claim_status",
        ),
        sa.CheckConstraint("evidence_count >= 1", name="ck_extracted_claim_evidence_count"),
        sa.CheckConstraint(
            "length(trim(proposed_by)) > 0 AND proposed_by_kind IN ('user', 'agent', 'rule')",
            name="ck_extracted_claim_proposer",
        ),
        sa.CheckConstraint(
            "(status = 'proposed' AND reviewed_by IS NULL AND reviewed_by_kind IS NULL "
            "AND review_reason IS NULL AND reviewed_at IS NULL) OR "
            "(status != 'proposed' AND length(trim(reviewed_by)) > 0 "
            "AND reviewed_by_kind IN ('user', 'rule') "
            "AND length(trim(review_reason)) > 0 AND reviewed_at IS NOT NULL)",
            name="ck_extracted_claim_review",
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["extracted_claim_identity.claim_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_extracted_claim_revision_subject",
        "extracted_claim_revision",
        ["subject_entity_id", "subject_entity_kind"],
    )
    op.create_table(
        "extracted_claim_evidence_ref",
        sa.Column("claim_id", sa.String(length=128), primary_key=True),
        sa.Column("claim_revision", sa.Integer(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("claim_id", "claim_revision", "evidence_ref_id"),
        sa.CheckConstraint("claim_revision >= 1", name="ck_extracted_claim_evidence_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_extracted_claim_evidence_ordinal"),
        sa.ForeignKeyConstraint(
            ["claim_id", "claim_revision"],
            ["extracted_claim_revision.claim_id", "extracted_claim_revision.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_extracted_claim_evidence_ref_evidence_ref_id",
        "extracted_claim_evidence_ref",
        ["evidence_ref_id"],
    )

    op.create_table(
        "fact_identity",
        sa.Column("fact_id", sa.String(length=128), primary_key=True),
        sa.Column("candidate_id", sa.String(length=128)),
    )
    op.create_table(
        "fact_revision",
        sa.Column("fact_id", sa.String(length=128), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("subject_entity_id", sa.String(length=128), nullable=False),
        sa.Column("subject_entity_kind", sa.String(length=64), nullable=False),
        sa.Column("fact_type", sa.String(length=128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("authority", sa.String(length=32), nullable=False),
        sa.Column("source_claim_id", sa.String(length=128), nullable=False),
        sa.Column("source_claim_revision", sa.Integer(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_by", sa.String(length=255), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_fact_revision"),
        sa.CheckConstraint("schema_version >= 1", name="ck_fact_schema_version"),
        sa.CheckConstraint("length(trim(fact_type)) > 0", name="ck_fact_fact_type"),
        sa.CheckConstraint(
            "json_type(value) IS NOT NULL AND length(value) <= 65536",
            name="ck_fact_value",
        ),
        sa.CheckConstraint(
            "authority IN ('user_asserted', 'document_supported', 'rule_verified')",
            name="ck_fact_authority",
        ),
        sa.CheckConstraint("source_claim_revision >= 1", name="ck_fact_source_claim_revision"),
        sa.CheckConstraint("evidence_count >= 0", name="ck_fact_evidence_count"),
        sa.CheckConstraint("length(trim(verified_by)) > 0", name="ck_fact_verified_by"),
        sa.ForeignKeyConstraint(["fact_id"], ["fact_identity.fact_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_claim_id", "source_claim_revision"],
            ["extracted_claim_revision.claim_id", "extracted_claim_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_fact_revision_subject",
        "fact_revision",
        ["subject_entity_id", "subject_entity_kind"],
    )
    op.create_index(
        "ix_fact_revision_source_claim",
        "fact_revision",
        ["source_claim_id", "source_claim_revision"],
    )
    op.create_table(
        "fact_evidence_ref",
        sa.Column("fact_id", sa.String(length=128), primary_key=True),
        sa.Column("fact_revision", sa.Integer(), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("evidence_ref_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint("fact_id", "fact_revision", "evidence_ref_id"),
        sa.CheckConstraint("fact_revision >= 1", name="ck_fact_evidence_revision"),
        sa.CheckConstraint("ordinal >= 0", name="ck_fact_evidence_ordinal"),
        sa.ForeignKeyConstraint(
            ["fact_id", "fact_revision"],
            ["fact_revision.fact_id", "fact_revision.revision"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_ref_id"], ["evidence_ref.evidence_ref_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_fact_evidence_ref_evidence_ref_id",
        "fact_evidence_ref",
        ["evidence_ref_id"],
    )

    _create_sealing_triggers()
    _create_immutable_triggers()


def _create_sealing_triggers() -> None:
    op.execute(
        "CREATE TRIGGER trg_extracted_claim_revision_seal BEFORE INSERT "
        "ON extracted_claim_revision WHEN "
        "(SELECT count(*) FROM extracted_claim_evidence_ref WHERE claim_id = NEW.claim_id "
        "AND claim_revision = NEW.revision) != NEW.evidence_count OR "
        "COALESCE((SELECT min(ordinal) FROM extracted_claim_evidence_ref WHERE "
        "claim_id = NEW.claim_id AND claim_revision = NEW.revision), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM extracted_claim_evidence_ref WHERE "
        "claim_id = NEW.claim_id AND claim_revision = NEW.revision), -1) "
        "!= NEW.evidence_count - 1 BEGIN "
        "SELECT RAISE(ABORT, 'extracted claim evidence aggregate is incomplete'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_extracted_claim_evidence_ref_sealed BEFORE INSERT "
        "ON extracted_claim_evidence_ref WHEN EXISTS (SELECT 1 FROM extracted_claim_revision "
        "WHERE claim_id = NEW.claim_id AND revision = NEW.claim_revision) BEGIN "
        "SELECT RAISE(ABORT, 'extracted claim evidence aggregate is sealed'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_fact_revision_seal BEFORE INSERT ON fact_revision WHEN "
        "(SELECT count(*) FROM fact_evidence_ref WHERE fact_id = NEW.fact_id "
        "AND fact_revision = NEW.revision) != NEW.evidence_count OR "
        "(NEW.evidence_count > 0 AND ("
        "COALESCE((SELECT min(ordinal) FROM fact_evidence_ref WHERE "
        "fact_id = NEW.fact_id AND fact_revision = NEW.revision), -1) != 0 OR "
        "COALESCE((SELECT max(ordinal) FROM fact_evidence_ref WHERE "
        "fact_id = NEW.fact_id AND fact_revision = NEW.revision), -1) "
        "!= NEW.evidence_count - 1)) BEGIN "
        "SELECT RAISE(ABORT, 'fact evidence aggregate is incomplete'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_fact_evidence_ref_sealed BEFORE INSERT "
        "ON fact_evidence_ref WHEN EXISTS (SELECT 1 FROM fact_revision "
        "WHERE fact_id = NEW.fact_id AND revision = NEW.fact_revision) BEGIN "
        "SELECT RAISE(ABORT, 'fact evidence aggregate is sealed'); END"
    )


def _create_immutable_triggers() -> None:
    for table_name in FACT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update BEFORE UPDATE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete BEFORE DELETE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )


def downgrade() -> None:
    for table_name in reversed(FACT_TABLES):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")

    op.execute("DROP TRIGGER trg_fact_evidence_ref_sealed")
    op.execute("DROP TRIGGER trg_fact_revision_seal")
    op.execute("DROP TRIGGER trg_extracted_claim_evidence_ref_sealed")
    op.execute("DROP TRIGGER trg_extracted_claim_revision_seal")

    op.drop_index("ix_fact_evidence_ref_evidence_ref_id", table_name="fact_evidence_ref")
    op.drop_table("fact_evidence_ref")
    op.drop_index("ix_fact_revision_source_claim", table_name="fact_revision")
    op.drop_index("ix_fact_revision_subject", table_name="fact_revision")
    op.drop_table("fact_revision")
    op.drop_table("fact_identity")
    op.drop_index(
        "ix_extracted_claim_evidence_ref_evidence_ref_id",
        table_name="extracted_claim_evidence_ref",
    )
    op.drop_table("extracted_claim_evidence_ref")
    op.drop_index("ix_extracted_claim_revision_subject", table_name="extracted_claim_revision")
    op.drop_table("extracted_claim_revision")
    op.drop_table("extracted_claim_identity")
