"""Preserve radar constraints and persist ranking provenance for replay."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_opportunity_radar_hardening"
down_revision: str | None = "0019_opportunity_radar_ranking_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _source_run_constraints() -> tuple[sa.CheckConstraint, ...]:
    return (
        sa.CheckConstraint(
            "terms_status IN ('verified', 'unknown', 'blocked')",
            name="ck_job_source_run_terms_status",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'blocked', 'failed')",
            name="ck_job_source_run_status",
        ),
        sa.CheckConstraint("record_count >= 0", name="ck_job_source_run_record_count"),
    )


def _staging_constraints(*, include_ranking: bool = True) -> tuple[sa.CheckConstraint, ...]:
    constraints = [
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
            "json_type(score_breakdown) = 'object'",
            name="ck_job_staging_score_breakdown",
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
    ]
    if include_ranking:
        constraints.append(
            sa.CheckConstraint(
                "json_type(ranking_inputs) = 'object'",
                name="ck_job_staging_ranking_inputs",
            )
        )
    return tuple(constraints)


def _restore_source_run_triggers() -> None:
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_job_source_run_no_update "
        "BEFORE UPDATE ON job_source_run BEGIN "
        "SELECT RAISE(ABORT, 'job_source_run is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_job_source_run_no_delete "
        "BEFORE DELETE ON job_source_run BEGIN "
        "SELECT RAISE(ABORT, 'job_source_run is immutable'); END"
    )


def upgrade() -> None:
    with op.batch_alter_table(
        "job_source_run", recreate="always", table_args=_source_run_constraints()
    ) as batch:
        batch.add_column(
            sa.Column("ranking_inputs", sa.JSON(), nullable=False, server_default="{}")
        )
        batch.add_column(
            sa.Column(
                "ranking_policy_version",
                sa.String(32),
                nullable=False,
                server_default="v1",
            )
        )
    with op.batch_alter_table(
        "job_staging_record",
        recreate="always",
        table_args=_staging_constraints(),
    ) as batch:
        batch.add_column(
            sa.Column("ranking_inputs", sa.JSON(), nullable=False, server_default="{}")
        )
        batch.add_column(
            sa.Column(
                "ranking_policy_version",
                sa.String(32),
                nullable=False,
                server_default="v1",
            )
        )
        batch.add_column(
            sa.Column(
                "evaluated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
    _restore_source_run_triggers()


def downgrade() -> None:
    with op.batch_alter_table(
        "job_staging_record",
        recreate="always",
        table_args=_staging_constraints(include_ranking=False),
    ) as batch:
        batch.drop_constraint("ck_job_staging_ranking_inputs", type_="check")
        batch.drop_column("evaluated_at")
        batch.drop_column("ranking_policy_version")
        batch.drop_column("ranking_inputs")
    with op.batch_alter_table(
        "job_source_run", recreate="always", table_args=_source_run_constraints()
    ) as batch:
        batch.drop_column("ranking_policy_version")
        batch.drop_column("ranking_inputs")
    _restore_source_run_triggers()
