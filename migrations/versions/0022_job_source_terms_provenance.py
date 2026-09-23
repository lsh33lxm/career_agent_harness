"""Persist source terms and robots/ToS notes with each source run."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_job_source_terms_provenance"
down_revision: str | None = "0021_plugin_lifecycle_observability"
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


def _restore_triggers() -> None:
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
            sa.Column("terms_note", sa.String(2048), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "terms_checked_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
    _restore_triggers()


def downgrade() -> None:
    with op.batch_alter_table(
        "job_source_run", recreate="always", table_args=_source_run_constraints()
    ) as batch:
        batch.drop_column("terms_checked_at")
        batch.drop_column("terms_note")
    _restore_triggers()
