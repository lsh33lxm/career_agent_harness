"""Add auditable job source runs and pre-admission staging records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_opportunity_radar"
down_revision: str | None = "0016_resume_studio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_source_run",
        sa.Column("source_run_id", sa.String(128), primary_key=True),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("query", sa.String(2048), nullable=False),
        sa.Column("terms_status", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("terms_status IN ('verified', 'unknown', 'blocked')"),
        sa.CheckConstraint("status IN ('completed', 'blocked', 'failed')"),
        sa.CheckConstraint("record_count >= 0"),
    )
    op.create_table(
        "job_staging_record",
        sa.Column("staging_id", sa.String(128), primary_key=True),
        sa.Column("source_run_id", sa.String(128), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("raw_artifact_id", sa.String(128), nullable=False),
        sa.Column("raw_sha256", sa.String(64), nullable=False),
        sa.Column("url_fingerprint", sa.String(64), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("normalized", sa.JSON(), nullable=False),
        sa.Column("terms_status", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("duplicate_of", sa.String(128)),
        sa.Column("suggested_score", sa.Float(), nullable=False),
        sa.Column("suggested_reasons", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("admitted_job_id", sa.String(128)),
        sa.Column("admitted_opportunity_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_run_id"], ["job_source_run.source_run_id"]),
        sa.ForeignKeyConstraint(["raw_artifact_id"], ["evidence_artifact.artifact_id"]),
        sa.ForeignKeyConstraint(["duplicate_of"], ["job_staging_record.staging_id"]),
        sa.CheckConstraint("terms_status IN ('verified', 'unknown', 'blocked')"),
        sa.CheckConstraint("status IN ('staged', 'duplicate', 'admitted', 'rejected')"),
        sa.CheckConstraint("suggested_score >= 0 AND suggested_score <= 1"),
        sa.CheckConstraint("json_type(normalized) = 'object'"),
        sa.CheckConstraint("json_type(suggested_reasons) = 'array'"),
        sa.CheckConstraint("json_type(gaps) = 'array'"),
        sa.CheckConstraint(
            "(status = 'duplicate' AND duplicate_of IS NOT NULL) OR "
            "(status != 'duplicate' AND duplicate_of IS NULL)"
        ),
        sa.CheckConstraint(
            "(status = 'admitted' AND admitted_job_id IS NOT NULL "
            "AND admitted_opportunity_id IS NOT NULL) OR "
            "(status != 'admitted' AND admitted_job_id IS NULL "
            "AND admitted_opportunity_id IS NULL)"
        ),
    )
    op.create_index(
        "ix_job_staging_fingerprints",
        "job_staging_record",
        ["url_fingerprint", "content_fingerprint"],
    )
    op.create_index(
        "ix_job_staging_status_score",
        "job_staging_record",
        ["status", "suggested_score"],
    )
    op.execute(
        "CREATE TRIGGER trg_job_source_run_no_update BEFORE UPDATE ON job_source_run BEGIN "
        "SELECT RAISE(ABORT, 'job_source_run is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_job_source_run_no_delete BEFORE DELETE ON job_source_run BEGIN "
        "SELECT RAISE(ABORT, 'job_source_run is immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_job_source_run_no_delete")
    op.execute("DROP TRIGGER trg_job_source_run_no_update")
    op.drop_index("ix_job_staging_status_score", table_name="job_staging_record")
    op.drop_index("ix_job_staging_fingerprints", table_name="job_staging_record")
    op.drop_table("job_staging_record")
    op.drop_table("job_source_run")
