"""Add immutable read-only GitHub project analysis profiles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_github_project_analysis"
down_revision: str | None = "0024_model_provider_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "github_project_analysis",
        sa.Column("analysis_id", sa.String(128), primary_key=True),
        sa.Column("project_id", sa.String(128), nullable=False),
        sa.Column("repository_url", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("repository", sa.String(128), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=False),
        sa.Column("cache_key", sa.String(64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("readme_sha256", sa.String(64)),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project_identity.project_id"]),
        sa.UniqueConstraint("repository_url", "commit_sha", name="uq_github_analysis_commit"),
        sa.CheckConstraint("length(commit_sha) = 40", name="ck_github_analysis_commit"),
        sa.CheckConstraint("length(cache_key) = 64", name="ck_github_analysis_cache_key"),
        sa.CheckConstraint("file_count >= 0", name="ck_github_analysis_file_count"),
        sa.CheckConstraint("byte_count >= 0", name="ck_github_analysis_byte_count"),
        sa.CheckConstraint("json_type(profile) = 'object'", name="ck_github_analysis_profile"),
        sa.CheckConstraint(
            "json_type(provenance) = 'object'", name="ck_github_analysis_provenance"
        ),
    )
    op.create_index("ix_github_analysis_project", "github_project_analysis", ["project_id"])
    op.execute(
        "CREATE TRIGGER trg_github_project_analysis_no_update "
        "BEFORE UPDATE ON github_project_analysis BEGIN "
        "SELECT RAISE(ABORT, 'github_project_analysis is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_github_project_analysis_no_delete "
        "BEFORE DELETE ON github_project_analysis BEGIN "
        "SELECT RAISE(ABORT, 'github_project_analysis is immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_github_project_analysis_no_delete")
    op.execute("DROP TRIGGER trg_github_project_analysis_no_update")
    op.drop_index("ix_github_analysis_project", table_name="github_project_analysis")
    op.drop_table("github_project_analysis")
