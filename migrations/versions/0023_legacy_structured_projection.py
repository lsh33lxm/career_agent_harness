"""Add auditable read-only Legacy structured import projections."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_legacy_structured_projection"
down_revision: str | None = "0022_job_source_terms_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _immutable(table: str) -> None:
    op.execute(
        f"CREATE TRIGGER trg_{table}_no_update BEFORE UPDATE ON {table} BEGIN "
        f"SELECT RAISE(ABORT, '{table} is immutable'); END"
    )
    op.execute(
        f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} BEGIN "
        f"SELECT RAISE(ABORT, '{table} is immutable'); END"
    )


def upgrade() -> None:
    op.create_table(
        "legacy_import_batch",
        sa.Column("batch_id", sa.String(128), primary_key=True),
        sa.Column("source_root", sa.Text(), nullable=False),
        sa.Column("source_signature_before", sa.String(64), nullable=False),
        sa.Column("source_signature_after", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("report", sa.JSON(), nullable=False, server_default="{}"),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_legacy_import_batch_status",
        ),
        sa.CheckConstraint(
            "length(source_signature_before) = 64",
            name="ck_legacy_import_batch_before_hash",
        ),
        sa.CheckConstraint(
            "source_signature_after IS NULL OR length(source_signature_after) = 64",
            name="ck_legacy_import_batch_after_hash",
        ),
        sa.CheckConstraint("json_type(report) = 'object'", name="ck_legacy_import_report"),
    )
    op.create_table(
        "legacy_source_file_version",
        sa.Column("file_version_id", sa.String(128), primary_key=True),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_class", sa.String(64), nullable=False),
        sa.Column("artifact_class", sa.String(32), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("relative_path", "sha256", name="uq_legacy_source_path_hash"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_legacy_source_sha"),
        sa.CheckConstraint("length(artifact_sha256) = 64", name="ck_legacy_source_artifact_sha"),
        sa.CheckConstraint("byte_length >= 0", name="ck_legacy_source_size"),
        sa.CheckConstraint(
            "artifact_class IN ('public_source', 'personal', 'sensitive')",
            name="ck_legacy_source_artifact_class",
        ),
    )
    op.create_table(
        "legacy_import_batch_file",
        sa.Column("batch_id", sa.String(128), primary_key=True),
        sa.Column("file_version_id", sa.String(128), primary_key=True),
        sa.Column("read_count", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("sample_validation", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["legacy_import_batch.batch_id"]),
        sa.ForeignKeyConstraint(
            ["file_version_id"], ["legacy_source_file_version.file_version_id"]
        ),
        sa.CheckConstraint(
            "read_count >= 0 AND new_count >= 0 AND updated_count >= 0 "
            "AND unchanged_count >= 0 "
            "AND duplicate_count >= 0 AND failed_count >= 0",
            name="ck_legacy_batch_file_counts",
        ),
        sa.CheckConstraint("json_type(failures) = 'array'", name="ck_legacy_file_failures"),
        sa.CheckConstraint(
            "json_type(sample_validation) = 'object'",
            name="ck_legacy_file_sample",
        ),
    )
    op.create_table(
        "job_staging_provenance",
        sa.Column("staging_id", sa.String(128), primary_key=True),
        sa.Column("file_version_id", sa.String(128), nullable=False),
        sa.Column("batch_id", sa.String(128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("record_key", sa.String(512), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("transform", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["staging_id"], ["job_staging_record.staging_id"]),
        sa.ForeignKeyConstraint(
            ["file_version_id"], ["legacy_source_file_version.file_version_id"]
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["legacy_import_batch.batch_id"]),
        sa.CheckConstraint("row_number >= 1", name="ck_job_staging_provenance_row"),
        sa.CheckConstraint(
            "review_status IN ('historical_unconfirmed', 'needs_review', 'duplicate')",
            name="ck_job_staging_provenance_review",
        ),
        sa.CheckConstraint("json_type(transform) = 'object'", name="ck_job_staging_transform"),
    )
    op.create_index(
        "ix_job_staging_provenance_file_row",
        "job_staging_provenance",
        ["file_version_id", "row_number"],
    )
    op.create_table(
        "legacy_projection_record",
        sa.Column("record_id", sa.String(128), primary_key=True),
        sa.Column("record_kind", sa.String(32), nullable=False),
        sa.Column("business_key", sa.String(512), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("file_version_id", sa.String(128), nullable=False),
        sa.Column("batch_id", sa.String(128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("duplicate_of", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["file_version_id"], ["legacy_source_file_version.file_version_id"]
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["legacy_import_batch.batch_id"]),
        sa.ForeignKeyConstraint(["duplicate_of"], ["legacy_projection_record.record_id"]),
        sa.CheckConstraint(
            "record_kind IN ('interview', 'question', 'coding', 'source')",
            name="ck_legacy_projection_kind",
        ),
        sa.CheckConstraint(
            "review_status IN ('historical_unconfirmed', 'needs_review', 'duplicate')",
            name="ck_legacy_projection_review",
        ),
        sa.CheckConstraint("json_type(content) = 'object'", name="ck_legacy_projection_content"),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_legacy_projection_content_sha"),
        sa.CheckConstraint("row_number >= 1", name="ck_legacy_projection_row"),
    )
    op.create_index(
        "ix_legacy_projection_kind_business",
        "legacy_projection_record",
        ["record_kind", "business_key"],
    )
    op.create_index(
        "ix_legacy_projection_kind_content",
        "legacy_projection_record",
        ["record_kind", "content_sha256"],
    )
    for table in (
        "legacy_source_file_version",
        "legacy_import_batch_file",
        "job_staging_provenance",
        "legacy_projection_record",
    ):
        _immutable(table)


def downgrade() -> None:
    for table in (
        "legacy_projection_record",
        "job_staging_provenance",
        "legacy_import_batch_file",
        "legacy_source_file_version",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table}_no_update")
    op.drop_index("ix_legacy_projection_kind_content", table_name="legacy_projection_record")
    op.drop_index("ix_legacy_projection_kind_business", table_name="legacy_projection_record")
    op.drop_table("legacy_projection_record")
    op.drop_index("ix_job_staging_provenance_file_row", table_name="job_staging_provenance")
    op.drop_table("job_staging_provenance")
    op.drop_table("legacy_import_batch_file")
    op.drop_table("legacy_source_file_version")
    op.drop_table("legacy_import_batch")
