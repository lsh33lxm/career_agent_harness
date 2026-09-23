from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    IdempotencyRecordRow,
    OpportunityRecordRow,
    OutboxMessageRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from tests.support.job_data import seed_job_revision


class FailingTransactionalWrite:
    def idempotency_payload(self) -> dict[str, Any]:
        return {"contract": "failing-test-write-v1"}

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        session.add(
            OpportunityRecordRow(
                opportunity_id="opportunity_rollback",
                job_id="job_rollback",
                job_revision=1,
                state="qualified",
                revision=entity_revision,
                schema_version=1,
                admitted_at=occurred_at,
                admitted_by="user",
            )
        )
        raise RuntimeError("typed write failed")


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

    first = service.commit(
        _command(),
        {"display_name": "Candidate"},
        event_type="candidate.created",
        outbox_destination="test",
    )
    replay = service.commit(
        _command(),
        {"display_name": "Candidate"},
        event_type="candidate.created",
        outbox_destination="test",
    )

    assert replay == first
    assert first.revision == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EntityRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(DomainEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(OutboxMessageRow)) == 1
        assert session.scalar(select(DomainEventRow.event_type)) == "candidate.created"


def test_idempotency_key_reuse_with_different_input_is_rejected(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "conflict.db")
    upgrade_to_head(database_url)
    service = CommandService(create_sqlite_engine(database_url))
    service.commit(_command(), {"display_name": "First"}, event_type="candidate.created")

    with pytest.raises(IdempotencyConflict):
        service.commit(
            _command(),
            {"display_name": "Different"},
            event_type="candidate.created",
        )


def test_idempotency_key_cannot_be_reused_for_a_different_event_type(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "event-type-conflict.db")
    upgrade_to_head(database_url)
    service = CommandService(create_sqlite_engine(database_url))
    service.commit(_command(), {"display_name": "Candidate"}, event_type="candidate.created")

    with pytest.raises(IdempotencyConflict):
        service.commit(_command(), {"display_name": "Candidate"}, event_type="candidate.updated")


def test_transactional_write_failure_rolls_back_every_record(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "rollback.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    seed_job_revision(engine, "job_rollback", 1)
    service = CommandService(engine)

    with pytest.raises(RuntimeError, match="typed write failed"):
        service.commit(
            _command(),
            {"display_name": "Candidate"},
            event_type="candidate.created",
            event_payload={"source": "test"},
            transactional_write=FailingTransactionalWrite(),
        )

    with Session(engine) as session:
        for row_type in (
            EntityStateRow,
            EntityRevisionRow,
            DomainEventRow,
            IdempotencyRecordRow,
            OpportunityRecordRow,
        ):
            assert session.scalar(select(func.count()).select_from(row_type)) == 0


def test_event_payload_cannot_override_revision_identity(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "event-payload.db")
    upgrade_to_head(database_url)
    service = CommandService(create_sqlite_engine(database_url))

    with pytest.raises(ValueError, match="cannot override revision_id"):
        service.commit(
            _command(),
            {"display_name": "Candidate"},
            event_type="candidate.created",
            event_payload={"revision_id": "revision_forged"},
        )


def test_get_returns_typed_current_state_and_rejects_kind_mismatch(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "get-current.db")
    upgrade_to_head(database_url)
    service = CommandService(create_sqlite_engine(database_url))
    command = _command()
    service.commit(command, {"display_name": "Candidate"}, event_type="candidate.created")

    current = service.get(command.target)
    assert current is not None
    assert current.revision == 1
    assert current.state == {"display_name": "Candidate"}

    with pytest.raises(ValueError, match="different kind"):
        service.get(EntityRef(entity_id="candidate_001", kind=EntityKind.OPPORTUNITY))
