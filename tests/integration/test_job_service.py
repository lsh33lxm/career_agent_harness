from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.commands import Command, RevisionConflict
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.job import (
    JobRef,
    JobRequirementImportance,
    JobRequirementStatus,
)
from career_harness.core.lifecycle import ActorKind
from career_harness.db.job_repository import JobRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityNodeRow,
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    EvidenceArtifactRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    IdempotencyRecordRow,
    JobRequirementRevisionRow,
    JobRevisionRow,
    SourceSnapshotRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.job_service import JobService


def _command(
    entity_id: str,
    kind: EntityKind,
    expected_revision: int,
    *,
    command_id: str,
    actor: str,
    key: str | None = None,
) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.test",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=key or f"idempotency-{command_id}",
        actor=actor,
    )


def _seed_evidence(engine, evidence_ref_id: str = "evidence_job_001") -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    suffix = evidence_ref_id.removeprefix("evidence_")
    with engine.begin() as connection:
        connection.execute(
            EvidenceArtifactRow.__table__.insert(),
            {
                "artifact_id": f"artifact_{suffix}",
                "sha256": "a" * 64,
                "media_type": "text/html",
                "artifact_class": "public_source",
                "byte_length": 100,
            },
        )
        connection.execute(
            EvidenceSourceRow.__table__.insert(),
            {
                "source_id": f"source_{suffix}",
                "source_type": "job_board",
                "locator": f"https://example.invalid/{suffix}",
            },
        )
        connection.execute(
            SourceSnapshotRow.__table__.insert(),
            {
                "snapshot_id": f"snapshot_{suffix}",
                "source_id": f"source_{suffix}",
                "captured_at": now,
                "artifact_id": f"artifact_{suffix}",
            },
        )
        connection.execute(
            EvidenceRefRow.__table__.insert(),
            {
                "evidence_ref_id": evidence_ref_id,
                "snapshot_id": f"snapshot_{suffix}",
                "artifact_id": f"artifact_{suffix}",
                "selector": "section.requirements",
            },
        )


def _seed_capability(engine) -> None:  # type: ignore[no-untyped-def]
    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_agents"},
        )
        connection.execute(
            CapabilityNodeRow.__table__.insert(),
            {
                "capability_id": "capability_agents",
                "graph_version_id": "graph_jobs",
                "canonical_name": "Agent Engineering",
                "description": "Build reliable agent systems.",
                "layer": "track",
                "lifecycle_status": "active",
            },
        )
        connection.execute(
            CapabilityGraphVersionRow.__table__.insert(),
            {
                "graph_version_id": "graph_jobs",
                "version_label": "jobs-service-1",
                "change_note": "Service test graph.",
                "released_at": datetime.now(UTC),
                "released_by": "test-policy",
                "released_by_kind": "rule",
            },
        )


def _service(tmp_path: Path):  # type: ignore[no-untyped-def]
    database_url = sqlite_url(tmp_path / "job-service.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    _seed_evidence(engine)
    _seed_capability(engine)
    repository = JobRepository(engine)
    return engine, repository, JobService(CommandService(engine), repository)


def _write_counts(engine) -> tuple[int, int, int, int]:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        return (
            session.scalar(select(func.count()).select_from(EntityStateRow)) or 0,
            session.scalar(select(func.count()).select_from(EntityRevisionRow)) or 0,
            session.scalar(select(func.count()).select_from(DomainEventRow)) or 0,
            session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) or 0,
        )


def _record_job(service: JobService):  # type: ignore[no-untyped-def]
    command = _command(
        "job_001",
        EntityKind.JOB,
        0,
        command_id="command_job_001",
        actor="agent:job-capture",
    )
    return service.record_revision(
        command,
        content_sha256="b" * 64,
        source_evidence_refs=("evidence_job_001",),
    )


def _propose(service: JobService):  # type: ignore[no-untyped-def]
    command = _command(
        "requirement_001",
        EntityKind.JOB_REQUIREMENT,
        0,
        command_id="command_requirement_propose_001",
        actor="agent:requirement-extractor",
    )
    return service.propose_requirement(
        command,
        job=JobRef(job_id="job_001", revision=1),
        requirement_text="Build reliable agent workflows.",
        importance=JobRequirementImportance.REQUIRED,
        required_scopes=(CapabilityEvidenceScope.APPLY,),
        source_evidence_refs=("evidence_job_001",),
    )


def test_job_and_requirement_commands_are_atomic_and_replayable(tmp_path: Path) -> None:
    engine, repository, service = _service(tmp_path)
    job = _record_job(service)
    job_replay = _record_job(service)
    proposal = _propose(service)
    proposal_replay = _propose(service)
    review_command = _command(
        "requirement_001",
        EntityKind.JOB_REQUIREMENT,
        1,
        command_id="command_requirement_review_001",
        actor="user",
    )
    reviewed = service.review_requirement(
        review_command,
        decision=JobRequirementStatus.ACCEPTED,
        review_reason="Confirmed against the captured job description.",
        capability_id="capability_agents",
        graph_version_id="graph_jobs",
    )
    reviewed_replay = service.review_requirement(
        review_command,
        decision=JobRequirementStatus.ACCEPTED,
        review_reason="Confirmed against the captured job description.",
        capability_id="capability_agents",
        graph_version_id="graph_jobs",
    )

    assert job_replay == job
    assert proposal_replay == proposal
    assert proposal.requirement.proposed_by_kind is ActorKind.AGENT
    assert reviewed_replay == reviewed
    assert reviewed.requirement.status is JobRequirementStatus.ACCEPTED
    assert reviewed.requirement.reviewed_at != review_command.issued_at
    assert repository.get_job("job_001", 1) == job.job
    assert repository.get_requirement("requirement_001", 1) == proposal.requirement
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(JobRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(JobRequirementRevisionRow)) == 2
        assert session.scalar(select(func.count()).select_from(EntityStateRow)) == 2
        assert session.scalar(select(func.count()).select_from(EntityRevisionRow)) == 3
        assert session.scalar(select(func.count()).select_from(DomainEventRow)) == 3
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 3
        assert [
            event_type
            for event_type in session.scalars(
                select(DomainEventRow.event_type).order_by(DomainEventRow.occurred_at)
            )
        ] == [
            "job.revision_created",
            "job_requirement.proposed",
            "job_requirement.reviewed",
        ]


def test_agent_cannot_review_or_claim_rule_authority(tmp_path: Path) -> None:
    engine, _, service = _service(tmp_path)
    _record_job(service)
    _propose(service)
    before = None
    with Session(engine) as session:
        before = (
            session.scalar(select(func.count()).select_from(EntityRevisionRow)),
            session.scalar(select(func.count()).select_from(JobRequirementRevisionRow)),
        )

    with pytest.raises(ValueError, match="requires a user command"):
        service.review_requirement(
            _command(
                "requirement_001",
                EntityKind.JOB_REQUIREMENT,
                1,
                command_id="command_agent_review_001",
                actor="agent",
            ),
            decision=JobRequirementStatus.ACCEPTED,
            review_reason="Agent cannot approve this.",
            capability_id="capability_agents",
            graph_version_id="graph_jobs",
        )
    with pytest.raises(ValueError, match="requires a user command"):
        service.review_requirement(
            _command(
                "requirement_001",
                EntityKind.JOB_REQUIREMENT,
                1,
                command_id="command_fake_rule_review_001",
                actor="rule",
            ),
            decision=JobRequirementStatus.ACCEPTED,
            review_reason="Untrusted caller claimed rule authority.",
            capability_id="capability_agents",
            graph_version_id="graph_jobs",
        )
    with Session(engine) as session:
        assert before == (
            session.scalar(select(func.count()).select_from(EntityRevisionRow)),
            session.scalar(select(func.count()).select_from(JobRequirementRevisionRow)),
        )


def test_proposal_authority_is_derived_from_the_command_actor(tmp_path: Path) -> None:
    _, _, service = _service(tmp_path)
    _record_job(service)

    proposals = []
    for requirement_id, actor in (
        ("requirement_rule_claim", "rule"),
        ("requirement_user", ActorKind.USER.value),
    ):
        proposals.append(
            service.propose_requirement(
                _command(
                    requirement_id,
                    EntityKind.JOB_REQUIREMENT,
                    0,
                    command_id=f"command_{requirement_id}",
                    actor=actor,
                ),
                job=JobRef(job_id="job_001", revision=1),
                requirement_text="Build reliable agent workflows.",
                importance=JobRequirementImportance.REQUIRED,
                required_scopes=(CapabilityEvidenceScope.APPLY,),
                source_evidence_refs=("evidence_job_001",),
            ).requirement
        )

    assert proposals[0].proposed_by_kind is ActorKind.AGENT
    assert proposals[1].proposed_by_kind is ActorKind.USER


def test_missing_evidence_or_official_node_rolls_back_everything(tmp_path: Path) -> None:
    engine, _, service = _service(tmp_path)
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="canonical source EvidenceRefs"):
        service.record_revision(
            _command(
                "job_missing_evidence",
                EntityKind.JOB,
                0,
                command_id="command_job_missing_evidence",
                actor="agent:job-capture",
            ),
            content_sha256="c" * 64,
            source_evidence_refs=("evidence_missing",),
        )
    assert _write_counts(engine) == before
    with Session(engine) as session:
        assert session.get(EntityStateRow, "job_missing_evidence") is None
        assert session.get(JobRevisionRow, ("job_missing_evidence", 1)) is None

    _record_job(service)
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="exact canonical Job revision"):
        service.propose_requirement(
            _command(
                "requirement_missing_job",
                EntityKind.JOB_REQUIREMENT,
                0,
                command_id="command_requirement_missing_job",
                actor="agent:requirement-extractor",
            ),
            job=JobRef(job_id="job_001", revision=2),
            requirement_text="This proposal points to a missing Job revision.",
            importance=JobRequirementImportance.REQUIRED,
            required_scopes=(CapabilityEvidenceScope.APPLY,),
            source_evidence_refs=("evidence_job_001",),
        )
    assert _write_counts(engine) == before

    with pytest.raises(ValueError, match="canonical source EvidenceRefs"):
        service.propose_requirement(
            _command(
                "requirement_missing_evidence",
                EntityKind.JOB_REQUIREMENT,
                0,
                command_id="command_requirement_missing_evidence",
                actor="agent:requirement-extractor",
            ),
            job=JobRef(job_id="job_001", revision=1),
            requirement_text="This proposal has no canonical source evidence.",
            importance=JobRequirementImportance.REQUIRED,
            required_scopes=(CapabilityEvidenceScope.APPLY,),
            source_evidence_refs=("evidence_missing",),
        )
    assert _write_counts(engine) == before

    _propose(service)
    with pytest.raises(ValueError, match="exact official capability membership"):
        service.review_requirement(
            _command(
                "requirement_001",
                EntityKind.JOB_REQUIREMENT,
                1,
                command_id="command_wrong_graph_review",
                actor="user",
            ),
            decision=JobRequirementStatus.ACCEPTED,
            review_reason="Mapping does not exist in this graph.",
            capability_id="capability_agents",
            graph_version_id="graph_missing",
        )
    with Session(engine) as session:
        assert session.get(EntityStateRow, "requirement_001").revision == 1  # type: ignore[union-attr]
        assert session.scalar(select(func.count()).select_from(JobRequirementRevisionRow)) == 1


def test_idempotency_and_expected_revision_conflicts_are_preserved(tmp_path: Path) -> None:
    _, _, service = _service(tmp_path)
    _record_job(service)
    proposal = _propose(service)
    with pytest.raises(IdempotencyConflict):
        service.propose_requirement(
            _command(
                "requirement_001",
                EntityKind.JOB_REQUIREMENT,
                0,
                command_id="command_requirement_propose_001",
                actor="agent:requirement-extractor",
            ),
            job=JobRef(job_id="job_001", revision=1),
            requirement_text="Changed requirement text.",
            importance=JobRequirementImportance.REQUIRED,
            required_scopes=(CapabilityEvidenceScope.APPLY,),
            source_evidence_refs=("evidence_job_001",),
        )
    service.review_requirement(
        _command(
            "requirement_001",
            EntityKind.JOB_REQUIREMENT,
            proposal.commit.revision,
            command_id="command_requirement_review_first",
            actor="user",
        ),
        decision=JobRequirementStatus.REJECTED,
        review_reason="Not relevant to this target.",
    )
    with pytest.raises(RevisionConflict):
        service.review_requirement(
            _command(
                "requirement_001",
                EntityKind.JOB_REQUIREMENT,
                proposal.commit.revision,
                command_id="command_requirement_review_stale",
                actor="user",
            ),
            decision=JobRequirementStatus.REJECTED,
            review_reason="Stale second review.",
        )
