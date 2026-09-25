"""Add proposal-safe Resume Studio target, template and render records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_resume_studio"
down_revision: str | None = "0015_knowledge_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "resume_target_profile",
    "resume_target_patch_ref",
    "resume_template_registration",
    "resume_render_run",
    "resume_ats_report",
)


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


def _drop_immutable_triggers() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP TRIGGER trg_{table}_no_delete")
        op.execute(f"DROP TRIGGER trg_{table}_no_update")


def upgrade() -> None:
    op.create_table(
        "resume_target_profile",
        sa.Column("target_profile_id", sa.String(128), primary_key=True),
        sa.Column("resume_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255)),
        sa.Column("opportunity_id", sa.String(128)),
        sa.Column("opportunity_revision", sa.Integer()),
        sa.Column("requirement_refs", sa.JSON(), nullable=False),
        sa.Column("keyword_gaps", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["resume_id"], ["resume_identity.resume_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('approved', 'archived')", name="ck_resume_target_profile_status"
        ),
        sa.CheckConstraint(
            "json_type(requirement_refs) = 'array'",
            name="ck_resume_target_profile_requirements",
        ),
        sa.CheckConstraint(
            "json_type(keyword_gaps) = 'array'", name="ck_resume_target_profile_gaps"
        ),
        sa.CheckConstraint(
            "(opportunity_id IS NULL AND opportunity_revision IS NULL) OR "
            "(opportunity_id IS NOT NULL AND opportunity_revision >= 1)",
            name="ck_resume_target_profile_opportunity",
        ),
    )
    op.create_index(
        "ix_resume_target_profile_resume_id",
        "resume_target_profile",
        ["resume_id", "created_at"],
    )
    op.create_table(
        "resume_target_patch_ref",
        sa.Column("target_profile_id", sa.String(128), nullable=False),
        sa.Column("patch_id", sa.String(128), nullable=False),
        sa.Column("patch_revision", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("target_profile_id", "patch_id", "patch_revision"),
        sa.ForeignKeyConstraint(
            ["target_profile_id"],
            ["resume_target_profile.target_profile_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["patch_id", "patch_revision"],
            ["resume_patch_revision.patch_id", "resume_patch_revision.revision"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("patch_revision >= 1", name="ck_resume_target_patch_revision"),
    )
    op.create_table(
        "resume_template_registration",
        sa.Column("template_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("renderer", sa.String(32), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("description", sa.String(2048), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "renderer IN ('html_css')", name="ck_resume_template_renderer"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')", name="ck_resume_template_status"
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_resume_template_hash",
        ),
    )
    op.create_table(
        "resume_render_run",
        sa.Column("render_run_id", sa.String(128), primary_key=True),
        sa.Column("resume_revision_id", sa.String(128), nullable=False),
        sa.Column("target_profile_id", sa.String(128)),
        sa.Column("template_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("output_artifact_id", sa.String(128), nullable=False),
        sa.Column("output_sha256", sa.String(64), nullable=False),
        sa.Column("output_media_type", sa.String(255), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("preview_html", sa.Text(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["resume_revision_id"],
            ["resume_revision_record.revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_profile_id"],
            ["resume_target_profile.target_profile_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["resume_template_registration.template_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["output_artifact_id"],
            ["evidence_artifact.artifact_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed', 'blocked')", name="ck_resume_render_status"
        ),
        sa.CheckConstraint("page_count >= 1", name="ck_resume_render_page_count"),
        sa.CheckConstraint(
            "length(output_sha256) = 64 AND output_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_resume_render_hash",
        ),
        sa.CheckConstraint(
            "json_type(checks) = 'object'", name="ck_resume_render_checks"
        ),
    )
    op.create_index(
        "ix_resume_render_run_revision",
        "resume_render_run",
        ["resume_revision_id", "created_at"],
    )
    op.create_table(
        "resume_ats_report",
        sa.Column("render_run_id", sa.String(128), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("keyword_gaps", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["render_run_id"], ["resume_render_run.render_run_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'warnings', 'failed')", name="ck_resume_ats_status"
        ),
        sa.CheckConstraint("page_count >= 1", name="ck_resume_ats_page_count"),
        sa.CheckConstraint("json_type(checks) = 'object'", name="ck_resume_ats_checks"),
        sa.CheckConstraint(
            "json_type(keyword_gaps) = 'array'", name="ck_resume_ats_keyword_gaps"
        ),
    )
    _immutable_triggers()


def downgrade() -> None:
    _drop_immutable_triggers()
    op.drop_table("resume_ats_report")
    op.drop_index("ix_resume_render_run_revision", table_name="resume_render_run")
    op.drop_table("resume_render_run")
    op.drop_table("resume_template_registration")
    op.drop_table("resume_target_patch_ref")
    op.drop_index("ix_resume_target_profile_resume_id", table_name="resume_target_profile")
    op.drop_table("resume_target_profile")
