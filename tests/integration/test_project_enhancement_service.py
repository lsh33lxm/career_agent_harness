from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from career_harness.core.capability import CapabilityEvidenceScope, CapabilityLayer, CapabilityNode
from career_harness.core.commands import Command, RevisionConflict
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind, Opportunity, OpportunityState
from career_harness.core.match_gap import MatchClassification, MatchPolicyInput, assess_match
from career_harness.core.opportunity import OpportunityDetail
from career_harness.core.project import ProjectEnhancementTask, ProjectEnhancementTaskStatus
from career_harness.db.match_repository import MatchRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CapabilityEvidenceBindingRow,
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityNodeRow,
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    IdempotencyRecordRow,
    JobRequirementEvidenceRefRow,
    JobRequirementIdentityRow,
    JobRequirementRevisionRow,
    JobRequirementScopeRow,
    MatchAssessmentRow,
    MatchGapRow,
    MatchRequirementResultRow,
    OpportunityRecordRow,
    PersonalCapabilityStateRow,
    ProjectCapabilityBasisRow,
    ProjectCapabilityStateRow,
    ProjectEnhancementTaskRow,
    ProjectEvidenceRow,
    ProjectIdentityRow,
    ProjectRecordRow,
)
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.match_service import MatchService
from career_harness.services.project_service import ProjectService
from tests.support.job_data import seed_job_revision_rows

CAPABILITY_ID = "capability_agents"
GRAPH_VERSION_ID = "graph_001"
EVIDENCE_REF_ID = "evidence_job_001_1"
PROJECT_ID = "project_001"


def _command(
    task_id: str,
    *,
    command_id: str,
    command_type: str = "project_enhancement.propose",
    expected_revision: int = 0,
    key: str | None = None,
) -> Command:
    return Command(
        command_id=command_id,
        command_type=command_type,
        target=EntityRef(entity_id=task_id, kind=EntityKind.PROJECT_ENHANCEMENT_TASK),
        expected_revision=expected_revision,
        idempotency_key=key or f"idempotency-{command_id}",
        actor="agent:planner",
    )


def _seed_capability(connection) -> None:  # type: ignore[no-untyped-def]
    connection.execute(
        CapabilityIdentityRow.__table__.insert(),
        {"capability_id": CAPABILITY_ID},
    )
    connection.execute(
        CapabilityNodeRow.__table__.insert(),
        {
            "capability_id": CAPABILITY_ID,
            "graph_version_id": GRAPH_VERSION_ID,
            "canonical_name": "Agent Engineering",
            "description": "Build reliable agent systems.",
            "layer": "track",
            "lifecycle_status": "active",
        },
    )
    connection.execute(
        CapabilityGraphVersionRow.__table__.insert(),
        {
            "graph_version_id": GRAPH_VERSION_ID,
            "version_label": "graph-1",
            "change_note": "Initial graph.",
            "released_at": datetime.now(UTC),
            "released_by": "user",
            "released_by_kind": "user",
        },
    )


def _seed_opportunity(connection) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    state_payload = {
        "entity_id": "opportunity_001",
        "revision": 1,
        "schema_version": 1,
        "state": "qualified",
    }
    connection.execute(
        EntityStateRow.__table__.insert(),
        {
            "entity_id": "opportunity_001",
            "entity_kind": "opportunity",
            "revision": 1,
            "schema_version": 1,
            "state": state_payload,
            "updated_at": now,
        },
    )
    connection.execute(
        OpportunityRecordRow.__table__.insert(),
        {
            "opportunity_id": "opportunity_001",
            "job_id": "job_001",
            "job_revision": 1,
            "state": "qualified",
            "revision": 1,
            "schema_version": 1,
            "admitted_at": now,
            "admitted_by": "user",
        },
    )
    connection.execute(
        EntityRevisionRow.__table__.insert(),
        {
            "revision_id": "revision_opportunity_001_1",
            "entity_id": "opportunity_001",
            "revision": 1,
            "schema_version": 1,
            "state": state_payload,
            "created_at": now,
            "created_by": "user",
        },
    )


def _seed_accepted_requirement(connection) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    connection.execute(
        JobRequirementIdentityRow.__table__.insert(),
        {"requirement_id": "requirement_001", "job_id": "job_001"},
    )
    connection.execute(
        JobRequirementScopeRow.__table__.insert(),
        {
            "requirement_id": "requirement_001",
            "requirement_revision": 1,
            "ordinal": 0,
            "scope": "understand",
        },
    )
    connection.execute(
        JobRequirementEvidenceRefRow.__table__.insert(),
        {
            "requirement_id": "requirement_001",
            "requirement_revision": 1,
            "ordinal": 0,
            "evidence_ref_id": EVIDENCE_REF_ID,
        },
    )
    connection.execute(
        JobRequirementRevisionRow.__table__.insert(),
        {
            "requirement_id": "requirement_001",
            "revision": 1,
            "schema_version": 1,
            "job_id": "job_001",
            "job_revision": 1,
            "requirement_text": "Requirement text for requirement_001.",
            "importance": "required",
            "capability_id": CAPABILITY_ID,
            "graph_version_id": GRAPH_VERSION_ID,
            "required_scope_count": 1,
            "source_evidence_count": 1,
            "status": "accepted",
            "proposed_by": "agent:extractor",
            "proposed_by_kind": "agent",
            "proposed_at": now,
            "reviewed_by": "user",
            "reviewed_by_kind": "user",
            "review_reason": "Confirmed against the captured job description.",
            "reviewed_at": now,
        },
    )


def _seed_project(connection, project_id: str = PROJECT_ID) -> None:  # type: ignore[no-untyped-def]
    connection.execute(ProjectIdentityRow.__table__.insert(), {"project_id": project_id})
    connection.execute(
        ProjectRecordRow.__table__.insert(),
        {
            "project_id": project_id,
            "revision": 1,
            "display_name": "Harness Project",
            "root_locator": "projects/harness",
            "schema_version": 1,
            "created_at": datetime.now(UTC),
            "created_by": "user",
        },
    )


def _record_gap(engine: Engine) -> str:
    """Record a CLEAR_GAP assessment so a canonical Gap exists for task linkage."""
    service = MatchService(CommandService(engine), MatchRepository(engine))
    policy_input = MatchPolicyInput(
        opportunity=OpportunityDetail(
            opportunity=Opportunity(
                entity_id="opportunity_001",
                revision=1,
                state=OpportunityState.QUALIFIED,
            ),
            job=JobRef(job_id="job_001", revision=1),
        ),
        job=JobRevision(
            job_id="job_001",
            revision=1,
            content_sha256=hashlib.sha256(b"job_001_1").hexdigest(),
            source_evidence_refs=(EVIDENCE_REF_ID,),
        ),
        requirements=(
            JobRequirement(
                requirement_id="requirement_001",
                revision=1,
                job=JobRef(job_id="job_001", revision=1),
                requirement_text="Requirement text for requirement_001.",
                importance=JobRequirementImportance.REQUIRED,
                capability_id=CAPABILITY_ID,
                graph_version_id=GRAPH_VERSION_ID,
                required_scopes=(CapabilityEvidenceScope.UNDERSTAND,),
                source_evidence_refs=(EVIDENCE_REF_ID,),
                status=JobRequirementStatus.ACCEPTED,
                proposed_by="agent:extractor",
                proposed_by_kind=ActorKind.AGENT,
                reviewed_by="user",
                reviewed_by_kind=ActorKind.USER,
                review_reason="Confirmed against the captured job description.",
                reviewed_at=datetime.now(UTC),
            ),
        ),
        official_capabilities=(
            CapabilityNode(
                capability_id=CAPABILITY_ID,
                canonical_name="Agent Engineering",
                description="Build reliable agent systems.",
                layer=CapabilityLayer.TRACK,
                graph_version_id=GRAPH_VERSION_ID,
            ),
        ),
        candidate_id="candidate_001",
    )
    assessment = assess_match(policy_input)
    assert [result.classification for result in assessment.requirements] == [
        MatchClassification.CLEAR_GAP
    ]
    recorded = service.record_assessment(
        Command(
            command_id="command_assessment_001",
            command_type="match_assessment.record",
            target=EntityRef(entity_id="assessment_001", kind=EntityKind.MATCH_ASSESSMENT),
            expected_revision=0,
            idempotency_key="idempotency-command_assessment_001",
            actor="agent:match",
        ),
        assessment=assessment,
        candidate_id="candidate_001",
    )
    (gap,) = recorded.assessment.gaps
    return gap.gap_id


def _engine(tmp_path: Path) -> tuple[Engine, str]:
    database_url = sqlite_url(tmp_path / "project-enhancement.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        seed_job_revision_rows(connection, "job_001", 1)
        _seed_capability(connection)
        _seed_opportunity(connection)
        _seed_accepted_requirement(connection)
        _seed_project(connection)
    return engine, _record_gap(engine)


def _services(engine: Engine) -> tuple[ProjectRepository, ProjectService]:
    repository = ProjectRepository(engine)
    return repository, ProjectService(CommandService(engine), repository)


def _task(
    task_id: str,
    gap_id: str,
    *,
    project_id: str = PROJECT_ID,
    capability_id: str = CAPABILITY_ID,
    status: ProjectEnhancementTaskStatus = ProjectEnhancementTaskStatus.PROPOSED,
    revision: int = 1,
) -> ProjectEnhancementTask:
    return ProjectEnhancementTask(
        task_id=task_id,
        project_id=project_id,
        target_gap_id=gap_id,
        target_capability_id=capability_id,
        learning_plan=("Study the match policy module.",),
        files_to_review=("src/policy.py",),
        change_plan=("Add a regression test for gap classification.",),
        experiment_plan=("Run the policy on frozen inputs.",),
        validation_plan=("Re-run the assessment and compare output.",),
        expected_evidence=("Passing regression test output.",),
        status=status,
        revision=revision,
        created_by="agent:planner",
    )


def _write_counts(engine: Engine) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(row)) or 0
            for row in (
                EntityStateRow,
                EntityRevisionRow,
                DomainEventRow,
                IdempotencyRecordRow,
                ProjectEnhancementTaskRow,
            )
        )


def _canonical_counts(engine: Engine) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(row)) or 0
            for row in (
                OpportunityRecordRow,
                MatchAssessmentRow,
                MatchRequirementResultRow,
                MatchGapRow,
                CapabilityIdentityRow,
                CapabilityNodeRow,
                PersonalCapabilityStateRow,
                CapabilityEvidenceBindingRow,
                ProjectIdentityRow,
                ProjectRecordRow,
                ProjectEvidenceRow,
                ProjectCapabilityStateRow,
                ProjectCapabilityBasisRow,
            )
        )


def test_propose_enhancement_task_links_canonical_gap(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    repository, service = _services(engine)
    canonical_before = _canonical_counts(engine)

    proposed = service.propose_enhancement_task(
        _command("task_001", command_id="command_task_001"),
        task=_task("task_001", gap_id),
    )

    task = proposed.task
    assert task.task_id == "task_001"
    assert task.revision == 1
    assert proposed.commit.revision == 1
    assert task.status is ProjectEnhancementTaskStatus.PROPOSED
    assert task.target_gap_id == gap_id
    assert task.target_capability_id == CAPABILITY_ID
    assert repository.get_enhancement_task("task_001") == task
    assert repository.get_enhancement_task("task_missing") is None
    assert repository.list_enhancement_tasks(PROJECT_ID) == (task,)
    assert repository.list_enhancement_tasks(PROJECT_ID, target_gap_id=gap_id) == (task,)

    with Session(engine) as session:
        state = session.get(EntityStateRow, "task_001")
        assert state is not None
        assert state.entity_kind == "project_enhancement_task"
        assert state.revision == 1
        event = session.scalars(
            select(DomainEventRow).where(DomainEventRow.entity_id == "task_001")
        ).one()
        assert event.event_type == "project_enhancement.proposed"
        assert event.payload == {
            "revision_id": proposed.commit.revision_id,
            "task_id": "task_001",
            "project_id": PROJECT_ID,
            "target_gap_id": gap_id,
            "target_capability_id": CAPABILITY_ID,
            "status": "proposed",
        }
    assert _canonical_counts(engine) == canonical_before


def test_dangling_target_gap_fails_loud_and_rolls_back(tmp_path: Path) -> None:
    engine, _ = _engine(tmp_path)
    _, service = _services(engine)
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="canonical Gap"):
        service.propose_enhancement_task(
            _command("task_dangling", command_id="command_task_dangling"),
            task=_task("task_dangling", "gap_missing"),
        )
    assert _write_counts(engine) == before


def test_target_capability_mismatch_fails_loud_and_rolls_back(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_other"},
        )
    _, service = _services(engine)
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="target Gap capability"):
        service.propose_enhancement_task(
            _command("task_mismatch", command_id="command_task_mismatch"),
            task=_task("task_mismatch", gap_id, capability_id="capability_other"),
        )
    assert _write_counts(engine) == before


def test_missing_project_fails_loud_and_rolls_back(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    _, service = _services(engine)
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="canonical Project"):
        service.propose_enhancement_task(
            _command("task_orphan", command_id="command_task_orphan"),
            task=_task("task_orphan", gap_id, project_id="project_missing"),
        )
    assert _write_counts(engine) == before


def test_non_proposed_status_and_revision_mismatch_fail_loud(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    _, service = _services(engine)
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="must start as proposed"):
        service.propose_enhancement_task(
            _command("task_ready", command_id="command_task_ready"),
            task=_task("task_ready", gap_id, status=ProjectEnhancementTaskStatus.READY),
        )
    with pytest.raises(ValueError, match="revisions must match"):
        service.propose_enhancement_task(
            _command("task_revision", command_id="command_task_revision"),
            task=_task("task_revision", gap_id, revision=2),
        )
    assert _write_counts(engine) == before


def test_propose_is_idempotent_and_conflicts_on_different_input(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    _, service = _services(engine)
    command = _command("task_001", command_id="command_task_001")
    task = _task("task_001", gap_id)

    first = service.propose_enhancement_task(command, task=task)
    replay = service.propose_enhancement_task(command, task=task)

    assert replay == first
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ProjectEnhancementTaskRow)) == 1
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 2

    conflicting = _command(
        "task_002",
        command_id="command_task_002",
        key="idempotency-command_task_001",
    )
    with pytest.raises(IdempotencyConflict):
        service.propose_enhancement_task(conflicting, task=_task("task_002", gap_id))


def test_status_transition_walks_the_whitelist(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    repository, service = _services(engine)
    canonical_before = _canonical_counts(engine)
    proposed = service.propose_enhancement_task(
        _command("task_001", command_id="command_task_001"),
        task=_task("task_001", gap_id),
    )
    original = proposed.task

    revisions = [1]
    for step, to_status in enumerate(
        (
            ProjectEnhancementTaskStatus.READY,
            ProjectEnhancementTaskStatus.IN_PROGRESS,
            ProjectEnhancementTaskStatus.AWAITING_VALIDATION,
            ProjectEnhancementTaskStatus.COMPLETED,
        ),
        start=2,
    ):
        transitioned = service.transition_enhancement_task(
            _command(
                "task_001",
                command_id=f"command_task_001_step{step}",
                command_type="project_enhancement.transition",
                expected_revision=step - 1,
            ),
            task_id="task_001",
            to_status=to_status,
        )
        assert transitioned.commit.revision == step
        assert transitioned.task.revision == step
        assert transitioned.task.status is to_status
        # Transitions never rewrite plan content or target references.
        assert transitioned.task.model_dump(
            exclude={"revision", "status", "created_at", "created_by"}
        ) == original.model_dump(exclude={"revision", "status", "created_at", "created_by"})
        revisions.append(step)

    final = repository.get_enhancement_task("task_001")
    assert final is not None
    assert final.status is ProjectEnhancementTaskStatus.COMPLETED
    assert repository.get_enhancement_task("task_001", revision=1) == original

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ProjectEnhancementTaskRow)) == 5
        events = session.scalars(
            select(DomainEventRow)
            .where(DomainEventRow.entity_id == "task_001")
            .order_by(DomainEventRow.entity_revision)
        ).all()
        assert [event.event_type for event in events] == [
            "project_enhancement.proposed",
            *["project_enhancement.status_changed"] * 4,
        ]
        assert events[-1].payload == {
            "revision_id": events[-1].payload["revision_id"],
            "task_id": "task_001",
            "status": "completed",
        }
    assert _canonical_counts(engine) == canonical_before


def test_illegal_and_terminal_transitions_fail_loud(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    _, service = _services(engine)
    service.propose_enhancement_task(
        _command("task_001", command_id="command_task_001"),
        task=_task("task_001", gap_id),
    )

    before = _write_counts(engine)
    with pytest.raises(ValueError, match="cannot transition from proposed to completed"):
        service.transition_enhancement_task(
            _command(
                "task_001",
                command_id="command_task_001_skip",
                command_type="project_enhancement.transition",
                expected_revision=1,
            ),
            task_id="task_001",
            to_status=ProjectEnhancementTaskStatus.COMPLETED,
        )
    assert _write_counts(engine) == before

    service.transition_enhancement_task(
        _command(
            "task_001",
            command_id="command_task_001_cancel",
            command_type="project_enhancement.transition",
            expected_revision=1,
        ),
        task_id="task_001",
        to_status=ProjectEnhancementTaskStatus.CANCELLED,
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="cannot transition from cancelled"):
        service.transition_enhancement_task(
            _command(
                "task_001",
                command_id="command_task_001_reopen",
                command_type="project_enhancement.transition",
                expected_revision=2,
            ),
            task_id="task_001",
            to_status=ProjectEnhancementTaskStatus.READY,
        )
    assert _write_counts(engine) == before


def test_transition_revision_conflict_and_unknown_task_fail_loud(tmp_path: Path) -> None:
    engine, gap_id = _engine(tmp_path)
    _, service = _services(engine)
    service.propose_enhancement_task(
        _command("task_001", command_id="command_task_001"),
        task=_task("task_001", gap_id),
    )

    before = _write_counts(engine)
    with pytest.raises(RevisionConflict):
        service.transition_enhancement_task(
            _command(
                "task_001",
                command_id="command_task_001_stale",
                command_type="project_enhancement.transition",
                expected_revision=0,
            ),
            task_id="task_001",
            to_status=ProjectEnhancementTaskStatus.READY,
        )
    with pytest.raises(ValueError, match="requires an existing task"):
        service.transition_enhancement_task(
            _command(
                "task_missing",
                command_id="command_task_missing",
                command_type="project_enhancement.transition",
                expected_revision=0,
            ),
            task_id="task_missing",
            to_status=ProjectEnhancementTaskStatus.READY,
        )
    assert _write_counts(engine) == before
