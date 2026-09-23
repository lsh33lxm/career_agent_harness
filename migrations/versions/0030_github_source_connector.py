"""Allow governed read-only GitHub source connectors."""

from collections.abc import Sequence

from alembic import op

revision: str = "0030_github_source_connector"
down_revision: str | None = "0029_legacy_source_connector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_type_constraint(allowed: str) -> None:
    with op.batch_alter_table("source_connector") as batch:
        batch.drop_constraint("ck_source_connector_type", type_="check")
        batch.create_check_constraint(
            "ck_source_connector_type",
            f"connector_type IN ({allowed})",
        )


def upgrade() -> None:
    _replace_type_constraint("'local_folder','legacy_agent_radar','github'")


def downgrade() -> None:
    op.execute(
        "DELETE FROM source_sync_run WHERE connector_id IN "
        "(SELECT connector_id FROM source_connector WHERE connector_type='github')"
    )
    op.execute(
        "DELETE FROM source_resource WHERE connector_id IN "
        "(SELECT connector_id FROM source_connector WHERE connector_type='github')"
    )
    op.execute("DELETE FROM source_connector WHERE connector_type='github'")
    _replace_type_constraint("'local_folder','legacy_agent_radar'")
