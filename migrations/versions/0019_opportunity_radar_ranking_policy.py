"""Persist explainable staging score components and per-source policy state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_opportunity_radar_ranking_policy"
down_revision: str | None = "0018_resume_studio_completion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    preserved_constraints = (
        sa.CheckConstraint(
            "terms_status IN ('verified', 'unknown', 'blocked')",
            name="ck_job_staging_terms_status",
        ),
        sa.CheckConstraint(
            "status IN ('staged', 'duplicate', 'admitted', 'rejected')",
            name="ck_job_staging_status",
        ),
        sa.CheckConstraint(
            "suggested_score >= 0 AND suggested_score <= 1",
            name="ck_job_staging_score",
        ),
        sa.CheckConstraint(
            "json_type(normalized) = 'object'", name="ck_job_staging_normalized"
        ),
        sa.CheckConstraint(
            "json_type(suggested_reasons) = 'array'",
            name="ck_job_staging_suggested_reasons",
        ),
        sa.CheckConstraint(
            "json_type(gaps) = 'array'", name="ck_job_staging_gaps"
        ),
        sa.CheckConstraint(
            "(status = 'duplicate' AND duplicate_of IS NOT NULL) OR "
            "(status != 'duplicate' AND duplicate_of IS NULL)",
            name="ck_job_staging_duplicate_ref",
        ),
        sa.CheckConstraint(
            "(status = 'admitted' AND admitted_job_id IS NOT NULL "
            "AND admitted_opportunity_id IS NOT NULL) OR "
            "(status != 'admitted' AND admitted_job_id IS NULL "
            "AND admitted_opportunity_id IS NULL)",
            name="ck_job_staging_admission_refs",
        ),
    )
    with op.batch_alter_table(
        "job_staging_record", recreate="always", table_args=preserved_constraints
    ) as batch:
        batch.add_column(
            sa.Column("score_breakdown", sa.JSON(), nullable=False, server_default="{}")
        )
        batch.create_check_constraint(
            "ck_job_staging_score_breakdown", "json_type(score_breakdown) = 'object'"
        )
    op.create_table(
        "job_source_policy",
        sa.Column("source_id", sa.String(128), primary_key=True),
        sa.Column("rate_limit_ms", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("failure_threshold", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("last_error", sa.String(2048)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rate_limit_ms >= 0", name="ck_job_source_policy_rate_limit"),
        sa.CheckConstraint("max_retries BETWEEN 0 AND 5", name="ck_job_source_policy_retries"),
        sa.CheckConstraint(
            "failure_threshold BETWEEN 1 AND 20",
            name="ck_job_source_policy_threshold",
        ),
        sa.CheckConstraint("failure_count >= 0", name="ck_job_source_policy_failures"),
    )


def downgrade() -> None:
    op.drop_table("job_source_policy")
    preserved_constraints = (
        sa.CheckConstraint(
            "terms_status IN ('verified', 'unknown', 'blocked')",
            name="ck_job_staging_terms_status",
        ),
        sa.CheckConstraint(
            "status IN ('staged', 'duplicate', 'admitted', 'rejected')",
            name="ck_job_staging_status",
        ),
        sa.CheckConstraint(
            "suggested_score >= 0 AND suggested_score <= 1",
            name="ck_job_staging_score",
        ),
        sa.CheckConstraint(
            "json_type(normalized) = 'object'", name="ck_job_staging_normalized"
        ),
        sa.CheckConstraint(
            "json_type(suggested_reasons) = 'array'",
            name="ck_job_staging_suggested_reasons",
        ),
        sa.CheckConstraint(
            "json_type(gaps) = 'array'", name="ck_job_staging_gaps"
        ),
        sa.CheckConstraint(
            "(status = 'duplicate' AND duplicate_of IS NOT NULL) OR "
            "(status != 'duplicate' AND duplicate_of IS NULL)",
            name="ck_job_staging_duplicate_ref",
        ),
        sa.CheckConstraint(
            "(status = 'admitted' AND admitted_job_id IS NOT NULL "
            "AND admitted_opportunity_id IS NOT NULL) OR "
            "(status != 'admitted' AND admitted_job_id IS NULL "
            "AND admitted_opportunity_id IS NULL)",
            name="ck_job_staging_admission_refs",
        ),
    )
    with op.batch_alter_table(
        "job_staging_record", recreate="always", table_args=preserved_constraints
    ) as batch:
        batch.drop_constraint("ck_job_staging_score_breakdown", type_="check")
        batch.drop_column("score_breakdown")
