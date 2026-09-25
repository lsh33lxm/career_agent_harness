"""Persist immutable Match assessments, requirement results and canonical Gaps."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_match_gap_persistence"
down_revision: str | None = "0008_job_requirement_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MATCH_TABLES = (
    "match_assessment",
    "match_requirement_result",
    "match_gap",
)


def upgrade() -> None:
    op.create_table(
        "match_assessment",
        sa.Column("assessment_id", sa.String(length=128), primary_key=True),
        sa.Column("opportunity_id", sa.String(length=128), nullable=False),
        sa.Column("opportunity_revision", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("manifest", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            "opportunity_revision >= 1", name="ck_match_assessment_opportunity_revision"
        ),
        sa.CheckConstraint("job_revision >= 1", name="ck_match_assessment_job_revision"),
        sa.CheckConstraint(
            "policy_version = 'match-policy-v1'", name="ck_match_assessment_policy_version"
        ),
        sa.CheckConstraint(
            "json_type(manifest) = 'object' AND length(manifest) <= 65536 AND "
            "json_array_length(manifest, '$.requirements') BETWEEN 1 AND 256",
            name="ck_match_assessment_manifest",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunity_record.opportunity_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id", "opportunity_revision"],
            ["entity_revision.entity_id", "entity_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_id", "job_revision"],
            ["job_revision.job_id", "job_revision.revision"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_match_assessment_opportunity",
        "match_assessment",
        ["opportunity_id", "created_at", "assessment_id"],
    )

    op.create_table(
        "match_requirement_result",
        sa.Column("assessment_id", sa.String(length=128), primary_key=True),
        sa.Column("requirement_id", sa.String(length=128), primary_key=True),
        sa.Column("requirement_revision", sa.Integer(), primary_key=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("covered_scopes", sa.JSON(), nullable=False),
        sa.Column("missing_scopes", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "requirement_revision >= 1", name="ck_match_requirement_result_revision"
        ),
        sa.CheckConstraint(
            "classification IN ('covered', 'quick_to_strengthen', 'clear_gap')",
            name="ck_match_requirement_result_classification",
        ),
        sa.CheckConstraint(
            "json_type(covered_scopes) = 'array' AND json_array_length(covered_scopes) <= 5 AND "
            "json_type(missing_scopes) = 'array' AND json_array_length(missing_scopes) <= 5",
            name="ck_match_requirement_result_scopes",
        ),
        sa.CheckConstraint(
            "json_type(reasons) = 'array' AND json_array_length(reasons) BETWEEN 1 AND 64 AND "
            "length(reasons) <= 16384",
            name="ck_match_requirement_result_reasons",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["match_assessment.assessment_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id", "requirement_revision"],
            ["job_requirement_revision.requirement_id", "job_requirement_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_match_requirement_result_requirement",
        "match_requirement_result",
        ["requirement_id", "requirement_revision"],
    )

    op.create_table(
        "match_gap",
        sa.Column("gap_id", sa.String(length=128), primary_key=True),
        sa.Column("assessment_id", sa.String(length=128), nullable=False),
        sa.Column("requirement_id", sa.String(length=128), nullable=False),
        sa.Column("requirement_revision", sa.Integer(), nullable=False),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("assessment_id", "requirement_id", "requirement_revision"),
        sa.CheckConstraint("requirement_revision >= 1", name="ck_match_gap_revision"),
        sa.CheckConstraint(
            "classification IN ('quick_to_strengthen', 'clear_gap')",
            name="ck_match_gap_classification",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id", "requirement_id", "requirement_revision"],
            [
                "match_requirement_result.assessment_id",
                "match_requirement_result.requirement_id",
                "match_requirement_result.requirement_revision",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["capability_id"], ["capability_identity.capability_id"], ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_match_gap_assessment", "match_gap", ["assessment_id"])

    for table_name in MATCH_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update BEFORE UPDATE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete BEFORE DELETE ON {table_name} BEGIN "
            f"SELECT RAISE(ABORT, '{table_name} is immutable'); END"
        )


def downgrade() -> None:
    for table_name in reversed(MATCH_TABLES):
        op.execute(f"DROP TRIGGER trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table_name}_no_update")

    op.drop_index("ix_match_gap_assessment", table_name="match_gap")
    op.drop_table("match_gap")
    op.drop_index("ix_match_requirement_result_requirement", table_name="match_requirement_result")
    op.drop_table("match_requirement_result")
    op.drop_index("ix_match_assessment_opportunity", table_name="match_assessment")
    op.drop_table("match_assessment")
