"""Complete Resume Studio renderer provenance and review records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_resume_studio_completion"
down_revision: str | None = "0017_opportunity_radar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER trg_resume_template_registration_no_delete")
    op.execute("DROP TRIGGER trg_resume_template_registration_no_update")
    with op.batch_alter_table("resume_template_registration", recreate="always") as batch:
        batch.drop_constraint("ck_resume_template_renderer", type_="check")
        batch.create_check_constraint(
            "ck_resume_template_renderer",
            "renderer IN ('html_css', 'typst_worker')",
        )
    op.execute(
        "CREATE TRIGGER trg_resume_template_registration_no_update "
        "BEFORE UPDATE ON resume_template_registration BEGIN "
        "SELECT RAISE(ABORT, 'resume_template_registration is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_resume_template_registration_no_delete "
        "BEFORE DELETE ON resume_template_registration BEGIN "
        "SELECT RAISE(ABORT, 'resume_template_registration is immutable'); END"
    )
    op.execute("DROP TRIGGER trg_resume_render_run_no_delete")
    op.execute("DROP TRIGGER trg_resume_render_run_no_update")
    with op.batch_alter_table("resume_render_run", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "template_version", sa.String(64), nullable=True
            )
        )
        batch.add_column(
            sa.Column(
                "renderer", sa.String(32), nullable=True
            )
        )
        batch.add_column(
            sa.Column(
                "renderer_plugin_id",
                sa.String(128),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "renderer_plugin_version",
                sa.String(64),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "input_sha256",
                sa.String(64),
                nullable=True,
            )
        )
        batch.create_check_constraint(
            "ck_resume_render_renderer",
            "renderer IS NULL OR renderer IN ('html_css', 'typst_worker')",
        )
        batch.create_check_constraint(
            "ck_resume_render_input_hash",
            "input_sha256 IS NULL OR (length(input_sha256) = 64 "
            "AND input_sha256 NOT GLOB '*[^0-9a-f]*')",
        )
    op.execute(
        "CREATE TRIGGER trg_resume_render_run_no_update BEFORE UPDATE ON "
        "resume_render_run BEGIN SELECT RAISE(ABORT, 'resume_render_run is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_resume_render_run_no_delete BEFORE DELETE ON "
        "resume_render_run BEGIN SELECT RAISE(ABORT, 'resume_render_run is immutable'); END"
    )
    op.create_table(
        "resume_render_review",
        sa.Column("render_run_id", sa.String(128), primary_key=True),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reviewer", sa.String(255), nullable=False),
        sa.Column("reason", sa.String(2048), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["render_run_id"], ["resume_render_run.render_run_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_resume_render_review_decision",
        ),
    )
    op.execute(
        "CREATE TRIGGER trg_resume_render_review_no_update BEFORE UPDATE ON "
        "resume_render_review BEGIN "
        "SELECT RAISE(ABORT, 'resume_render_review is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_resume_render_review_no_delete BEFORE DELETE ON "
        "resume_render_review BEGIN "
        "SELECT RAISE(ABORT, 'resume_render_review is immutable'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_resume_render_review_no_delete")
    op.execute("DROP TRIGGER trg_resume_render_review_no_update")
    op.drop_table("resume_render_review")
    op.execute("DROP TRIGGER trg_resume_render_run_no_delete")
    op.execute("DROP TRIGGER trg_resume_render_run_no_update")
    with op.batch_alter_table("resume_render_run", recreate="always") as batch:
        batch.drop_constraint("ck_resume_render_input_hash", type_="check")
        batch.drop_constraint("ck_resume_render_renderer", type_="check")
        batch.drop_column("input_sha256")
        batch.drop_column("renderer_plugin_version")
        batch.drop_column("renderer_plugin_id")
        batch.drop_column("renderer")
        batch.drop_column("template_version")
    op.execute(
        "CREATE TRIGGER trg_resume_render_run_no_update BEFORE UPDATE ON "
        "resume_render_run BEGIN SELECT RAISE(ABORT, 'resume_render_run is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_resume_render_run_no_delete BEFORE DELETE ON "
        "resume_render_run BEGIN SELECT RAISE(ABORT, 'resume_render_run is immutable'); END"
    )
    op.execute("DROP TRIGGER trg_resume_template_registration_no_delete")
    op.execute("DROP TRIGGER trg_resume_template_registration_no_update")
    with op.batch_alter_table("resume_template_registration", recreate="always") as batch:
        batch.drop_constraint("ck_resume_template_renderer", type_="check")
        batch.create_check_constraint(
            "ck_resume_template_renderer",
            "renderer IN ('html_css', 'typst_worker')",
        )
    op.execute(
        "CREATE TRIGGER trg_resume_template_registration_no_update "
        "BEFORE UPDATE ON resume_template_registration BEGIN "
        "SELECT RAISE(ABORT, 'resume_template_registration is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_resume_template_registration_no_delete "
        "BEFORE DELETE ON resume_template_registration BEGIN "
        "SELECT RAISE(ABORT, 'resume_template_registration is immutable'); END"
    )
