from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.opportunity import JobRef, PriorityInputRevision, PriorityLevel
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    EntityStateRow,
    OpportunityRecordRow,
    SuggestedPriorityRow,
    UserPriorityRow,
)
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService
from career_harness.services.opportunity_service import OpportunityService


def command(command_id: str, command_type: str, revision: int, *, actor: str) -> Command:
    return Command(
        command_id=command_id,
        command_type=command_type,
        target=EntityRef(entity_id="opportunity_001", kind=EntityKind.OPPORTUNITY),
        expected_revision=revision,
        idempotency_key=f"idempotency-{command_id}",
        actor=actor,
    )


def setup_opportunity(tmp_path: Path):
    database_url = sqlite_url(tmp_path / "priorities.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    service = OpportunityService(CommandService(engine))
    service.admit_manually(
        command("command_admit_001", "opportunity.admit", 0, actor="user"),
        JobRef(job_id="job_001", revision=2),
        opportunity_id="opportunity_001",
        decision_id="decision_001",
    )
    return engine, service


def test_suggested_and_user_priority_updates_are_atomic_and_independent(tmp_path: Path) -> None:
    engine, service = setup_opportunity(tmp_path)
    service.set_suggested_priority(
        command("command_suggest_001", "opportunity.suggest_priority", 1, actor="rule"),
        level=PriorityLevel.HIGH,
        reasons=("Strong target market overlap.",),
        input_revisions=(PriorityInputRevision(entity_id="job_001", revision=2),),
        score=0.82,
    )
    service.set_user_priority(
        command("command_user_001", "opportunity.set_user_priority", 2, actor="user"),
        level=PriorityLevel.MEDIUM,
        reason="Balanced against another role.",
    )
    service.set_suggested_priority(
        command("command_suggest_002", "opportunity.suggest_priority", 3, actor="rule"),
        level=PriorityLevel.URGENT,
        reasons=("Deadline is approaching.",),
        input_revisions=(PriorityInputRevision(entity_id="job_001", revision=2),),
        score=0.94,
    )

    detail = OpportunityRepository(engine).get("opportunity_001")
    assert detail is not None
    assert detail.opportunity.revision == 4
    assert detail.suggested_priority is not None
    assert detail.suggested_priority.level is PriorityLevel.URGENT
    assert detail.user_priority is not None
    assert detail.user_priority.level is PriorityLevel.MEDIUM
    with Session(engine) as session:
        assert session.get(OpportunityRecordRow, "opportunity_001").revision == 4
        assert session.get(EntityStateRow, "opportunity_001").state["revision"] == 4
        assert session.get(SuggestedPriorityRow, "opportunity_001").revision == 4
        assert session.get(UserPriorityRow, "opportunity_001").revision == 3


def test_agent_cannot_set_user_priority(tmp_path: Path) -> None:
    engine, service = setup_opportunity(tmp_path)

    with pytest.raises(ValueError, match="only a user command"):
        service.set_user_priority(
            command("command_user_001", "opportunity.set_user_priority", 1, actor="agent"),
            level=PriorityLevel.HIGH,
        )

    detail = OpportunityRepository(engine).get("opportunity_001")
    assert detail is not None
    assert detail.suggested_priority is None
    assert detail.user_priority is None


def test_user_priority_does_not_require_a_suggested_priority(tmp_path: Path) -> None:
    engine, service = setup_opportunity(tmp_path)
    service.set_user_priority(
        command("command_user_001", "opportunity.set_user_priority", 1, actor="user"),
        level=PriorityLevel.HIGH,
    )

    detail = OpportunityRepository(engine).get("opportunity_001")
    assert detail is not None
    assert detail.suggested_priority is None
    assert detail.user_priority is not None
    assert detail.user_priority.level is PriorityLevel.HIGH


def test_priority_command_requires_matching_expected_revision(tmp_path: Path) -> None:
    _, service = setup_opportunity(tmp_path)

    with pytest.raises(RuntimeError, match="expected revision 7, found 1"):
        service.set_suggested_priority(
            command("command_suggest_001", "opportunity.suggest_priority", 7, actor="rule"),
            level=PriorityLevel.HIGH,
            reasons=("Target market demand.",),
            input_revisions=(PriorityInputRevision(entity_id="job_001", revision=2),),
        )
