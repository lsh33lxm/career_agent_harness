from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.core.approval import ActorKind
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.opportunity import JobRef, OpportunityAdmissionProposal
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    IdempotencyRecordRow,
    OpportunityAdmissionDecisionRow,
    OpportunityAdmissionProposalRow,
    OpportunityRecordRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.opportunity_service import OpportunityService
from tests.support.job_data import seed_job_revision


def admission_command(*, actor: str = "user", key: str = "opportunity-admit-001") -> Command:
    return Command(
        command_id="command_opportunity_admit_001",
        command_type="opportunity.admit",
        target=EntityRef(entity_id="opportunity_001", kind=EntityKind.OPPORTUNITY),
        expected_revision=0,
        idempotency_key=key,
        actor=actor,
    )


def test_manual_admission_commits_typed_truth_and_audit_atomically(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "manual-admission.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    seed_job_revision(engine, "job_001", 2)
    service = OpportunityService(CommandService(engine))

    first = service.admit_manually(
        admission_command(),
        JobRef(job_id="job_001", revision=2),
        opportunity_id="opportunity_001",
        decision_id="decision_001",
        reason="User chose to invest in this role.",
    )
    replay = service.admit_manually(
        admission_command(),
        JobRef(job_id="job_001", revision=2),
        opportunity_id="opportunity_001",
        decision_id="decision_001",
        reason="User chose to invest in this role.",
    )

    assert replay.commit == first.commit
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EntityStateRow)) == 1
        assert session.scalar(select(func.count()).select_from(EntityRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(DomainEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 1
        assert session.scalar(select(func.count()).select_from(OpportunityRecordRow)) == 1
        assert (
            session.scalar(select(func.count()).select_from(OpportunityAdmissionDecisionRow)) == 1
        )
        event = session.scalar(select(DomainEventRow))
        assert event is not None
        assert event.event_type == "opportunity.admitted"
        assert event.payload["decision_id"] == "decision_001"
        typed = session.get(OpportunityRecordRow, "opportunity_001")
        assert typed is not None
        assert typed.revision == first.commit.revision == 1


def test_reviewed_ai_proposal_is_persisted_only_with_user_admission(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "proposal-admission.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    seed_job_revision(engine, "job_001", 3)
    service = OpportunityService(CommandService(engine))
    proposal = OpportunityAdmissionProposal(
        proposal_id="proposal_001",
        job=JobRef(job_id="job_001", revision=3),
        proposed_by=ActorKind.AGENT,
        reason="Strong target direction fit.",
    )

    service.review_proposal(
        admission_command(),
        proposal,
        decision_id="decision_001",
        opportunity_id="opportunity_001",
        reason="User confirmed focused preparation.",
    )

    with Session(engine) as session:
        assert session.get(OpportunityAdmissionProposalRow, "proposal_001") is not None
        decision = session.get(OpportunityAdmissionDecisionRow, "decision_001")
        assert decision is not None
        assert decision.decided_by == "user"
        assert decision.proposal_id == "proposal_001"


def test_agent_command_cannot_admit_an_opportunity(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "agent-admission.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    service = OpportunityService(CommandService(engine))

    with pytest.raises(ValueError, match="only a user command"):
        service.admit_manually(
            admission_command(actor="agent"),
            JobRef(job_id="job_001", revision=1),
            opportunity_id="opportunity_001",
            decision_id="decision_001",
        )

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EntityStateRow)) == 0
        assert session.scalar(select(func.count()).select_from(OpportunityRecordRow)) == 0


def test_idempotency_rejects_changed_typed_admission_input(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "typed-idempotency.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    seed_job_revision(engine, "job_001", 1)
    service = OpportunityService(CommandService(engine))
    command = admission_command()
    service.admit_manually(
        command,
        JobRef(job_id="job_001", revision=1),
        opportunity_id="opportunity_001",
        decision_id="decision_001",
        reason="Initial user decision.",
    )

    with pytest.raises(IdempotencyConflict):
        service.admit_manually(
            command,
            JobRef(job_id="job_001", revision=2),
            opportunity_id="opportunity_001",
            decision_id="decision_001",
            reason="Changed typed input.",
        )
