"""Keep a personal capability state identity stable across revisions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_capability_personal_state_identity"
down_revision: str | None = "0005_context_manifest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    drifted_id = connection.execute(
        sa.text(
            "SELECT personal_state_id FROM personal_capability_state "
            "GROUP BY personal_state_id "
            "HAVING count(DISTINCT candidate_id) > 1 "
            "OR count(DISTINCT capability_id) > 1 LIMIT 1"
        )
    ).scalar_one_or_none()
    if drifted_id is not None:
        raise RuntimeError(
            "personal capability state identity drift must be reconciled before upgrade: "
            f"{drifted_id}"
        )

    op.execute(
        "CREATE TRIGGER trg_personal_capability_state_stable_identity_insert "
        "BEFORE INSERT ON personal_capability_state WHEN EXISTS ("
        "SELECT 1 FROM personal_capability_state history "
        "WHERE history.personal_state_id = NEW.personal_state_id "
        "AND (history.candidate_id != NEW.candidate_id "
        "OR history.capability_id != NEW.capability_id)) BEGIN "
        "SELECT RAISE(ABORT, 'personal capability state identity cannot change'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_personal_capability_state_stable_identity_update "
        "BEFORE UPDATE OF candidate_id, capability_id ON personal_capability_state "
        "WHEN OLD.candidate_id != NEW.candidate_id OR OLD.capability_id != NEW.capability_id "
        "BEGIN SELECT RAISE(ABORT, 'personal capability state identity cannot change'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_personal_capability_state_stable_identity_update")
    op.execute("DROP TRIGGER trg_personal_capability_state_stable_identity_insert")
