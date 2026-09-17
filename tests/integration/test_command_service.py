from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import DomainEventRow, EntityRevisionRow, OutboxMessageRow
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict


def _command(key: str = "candidate-create-001") -> Command:
    return Command(
        command_id="command_candidate_001",
        command_type="candidate.create",
        target=EntityRef(entity_id="candidate_001", kind=EntityKind.CANDIDATE),
        expected_revision=0,
        idempotency_key=key,
        actor="user",
    )


def test_command_commits_revision_event_outbox_and_idempotency(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "command.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    service = CommandService(engine)

    first = service.commit(_command(), {"display_name": "Candidate"}, outbox_destination="test")
    replay = service.commit(_command(), {"display_name": "Candidate"}, outbox_destination="test")

    assert replay == first
    assert first["revision"] == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EntityRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(DomainEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(OutboxMessageRow)) == 1


def test_idempotency_key_reuse_with_different_input_is_rejected(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "conflict.db")
    upgrade_to_head(database_url)
    service = CommandService(create_sqlite_engine(database_url))
    service.commit(_command(), {"display_name": "First"})

    with pytest.raises(IdempotencyConflict):
        service.commit(_command(), {"display_name": "Different"})

