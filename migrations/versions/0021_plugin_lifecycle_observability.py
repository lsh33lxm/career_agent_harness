"""Persist lifecycle latency and evidence provenance metrics."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_plugin_lifecycle_observability"
down_revision: str | None = "0020_opportunity_radar_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPTY_PROVENANCE_HASH = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"


def _run_constraints(*, include_observability: bool = True) -> tuple[sa.CheckConstraint, ...]:
    constraints = [
        sa.CheckConstraint(
            "status IN ('ok', 'proposal', 'blocked', 'error')",
            name="ck_plugin_run_status",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_plugin_run_input_hash",
        ),
        sa.CheckConstraint(
            "output_hash IS NULL OR (length(output_hash) = 64 AND "
            "output_hash NOT GLOB '*[^0-9a-f]*')",
            name="ck_plugin_run_output_hash",
        ),
    ]
    if include_observability:
        constraints.extend(
            (
                sa.CheckConstraint("latency_ms >= 0", name="ck_plugin_run_latency"),
                sa.CheckConstraint(
                    "length(provenance_hash) = 64 AND provenance_hash NOT GLOB '*[^0-9a-f]*'",
                    name="ck_plugin_run_provenance_hash",
                ),
            )
        )
    return tuple(constraints)


def _restore_trigger() -> None:
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_plugin_runs_no_update "
        "BEFORE UPDATE ON plugin_runs BEGIN "
        "SELECT RAISE(ABORT, 'plugin_runs is immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER IF NOT EXISTS trg_plugin_runs_no_delete "
        "BEFORE DELETE ON plugin_runs BEGIN "
        "SELECT RAISE(ABORT, 'plugin_runs is immutable'); END"
    )


def upgrade() -> None:
    with op.batch_alter_table(
        "plugin_runs",
        recreate="always",
        table_args=_run_constraints(),
    ) as batch:
        batch.add_column(
            sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column(
                "provenance_hash",
                sa.String(64),
                nullable=False,
                server_default=EMPTY_PROVENANCE_HASH,
            )
        )
    _restore_trigger()


def downgrade() -> None:
    with op.batch_alter_table(
        "plugin_runs",
        recreate="always",
        table_args=_run_constraints(include_observability=False),
    ) as batch:
        batch.drop_constraint("ck_plugin_run_latency", type_="check")
        batch.drop_constraint("ck_plugin_run_provenance_hash", type_="check")
        batch.drop_column("provenance_hash")
        batch.drop_column("latency_ms")
    _restore_trigger()
