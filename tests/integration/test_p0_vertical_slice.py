"""End-to-end P0 vertical slice over the real services and a disposable SQLite database.

One coherent fixture walks the canonical chain from `docs/v1.4/contracts.md` (0.8.0):

    Job/Requirement (agent propose -> USER review -> accepted)
    -> Opportunity (user-gated admission, independent priorities)
    -> Match/Gap (MatchService.assess: exact resolve -> policy -> persisted + canonical Gaps)
    -> Fact (agent claim -> USER review -> promotion)
    -> Resume (base -> agent patch -> USER review -> immutable ResumeRevision)
    -> Application (prepare -> USER-confirmed submit) -> Outcome
    -> MatchService.replay (stored-manifest replay, zero drift)

The assertions pin the exact references handed from one stage to the next (Opportunity
JobRef, Match manifest requirement refs, ResumePatch fact/requirement refs, Application
resume_revision_id, Outcome application revision) and the P0 invariants: AI proposals
never become truth without a user gate, Prepared is not Submitted, replay has no drift,
and no step in the chain rewrites UserPriority.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.evidence.models import ClaimStatus, FactAuthority
from career_harness.core.job import JobRef, JobRequirementImportance, JobRequirementStatus
from career_harness.core.lifecycle import ActorKind
from career_harness.core.match_gap import MATCH_POLICY_VERSION, MatchClassification
from career_harness.core.opportunity import PriorityInputRevision, PriorityLevel
from career_harness.core.outcome import OutcomeAuthority, OutcomeType
from career_harness.core.resume import (
    ResumePatchAction,
    ResumePatchOperation,
    ResumePatchStatus,
    ResumeRevision,
    RevisionRef,
)
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.fact_repository import FactRepository
from career_harness.db.job_repository import JobRepository
from career_harness.db.match_repository import MatchAssessmentRecord, MatchRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CapabilityEvidenceBindingRow,
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
    MatchAssessmentRow,
    MatchGapRow,
    MatchRequirementResultRow,
    PersonalCapabilityStateRow,
    SourceSnapshotRow,
    SuggestedPriorityRow,
    UserPriorityRow,
)
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.application_service import ApplicationService
from career_harness.services.command_service import CommandService
from career_harness.services.fact_service import FactService
from career_harness.services.job_service import JobService
from career_harness.services.match_resolver import MatchInputResolver
from career_harness.services.match_service import MatchReplayError, MatchService, derive_gap_id
from career_harness.services.opportunity_service import OpportunityService
from career_harness.services.resume_service import ResumeService, canonical_value_hash

CANDIDATE_ID = "candidate_001"
JOB_ID = "job_001"
JOB_REVISION = 1
JOB_EVIDENCE_REF_ID = "evidence_job_001"
CAPABILITY_ID = "capability_agents"
GRAPH_VERSION_ID = "graph_001"
OPPORTUNITY_ID = "opportunity_001"
# Opportunity revision after admission + user priority + suggested priority.
OPPORTUNITY_FROZEN_REVISION = 3
REQUIREMENT_COVERED_ID = "requirement_covered"
REQUIREMENT_GAP_ID = "requirement_gap"
ACCEPTED_REQUIREMENT_REVISION = 2
ASSESSMENT_ID = "assessment_001"
CLAIM_ID = "claim_001"
FACT_ID = "fact_001"
RESUME_ID = "resume_001"
PATCH_ID = "patch_001"
RESUME_REVISION_ID = "resume_revision_001"
APPLICATION_ID = "application_001"
OUTCOME_ID = "outcome_001"

MATCH_WRITTEN_ROWS = (
    EntityStateRow,
    EntityRevisionRow,
    DomainEventRow,
    IdempotencyRecordRow,
    MatchAssessmentRow,
    MatchRequirementResultRow,
    MatchGapRow,
)


def _command(
    entity_id: str,
    kind: EntityKind,
    command_id: str,
    *,
    actor: str = "user",
    expected_revision: int = 0,
) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=f"idempotency-{command_id}",
        actor=actor,
    )


def _seed_evidence_ref(connection: Connection, evidence_ref_id: str) -> None:
    now = datetime.now(UTC)
    connection.execute(
        EvidenceArtifactRow.__table__.insert(),
        {
            "artifact_id": f"artifact_{evidence_ref_id}",
            "sha256": "a" * 64,
            "media_type": "text/html",
            "artifact_class": "public_source",
            "byte_length": 100,
        },
    )
    connection.execute(
        EvidenceSourceRow.__table__.insert(),
        {
            "source_id": f"source_{evidence_ref_id}",
            "source_type": "job_board",
            "locator": f"https://example.invalid/{evidence_ref_id}",
        },
    )
    connection.execute(
        SourceSnapshotRow.__table__.insert(),
        {
            "snapshot_id": f"snapshot_{evidence_ref_id}",
            "source_id": f"source_{evidence_ref_id}",
            "captured_at": now,
            "artifact_id": f"artifact_{evidence_ref_id}",
        },
    )
    connection.execute(
        EvidenceRefRow.__table__.insert(),
        {
            "evidence_ref_id": evidence_ref_id,
            "snapshot_id": f"snapshot_{evidence_ref_id}",
            "artifact_id": f"artifact_{evidence_ref_id}",
            "selector": "section.requirements",
        },
    )


def _seed_capability(connection: Connection) -> None:
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


def _seed_personal_state(connection: Connection) -> None:
    # understand=True/apply=True with a non-AI binding covering only "understand" yields
    # COVERED for an understand-only requirement and QUICK_TO_STRENGTHEN for one that
    # also requires apply (partial binding coverage, per the P0 match policy).
    now = datetime.now(UTC)
    connection.execute(
        PersonalCapabilityStateRow.__table__.insert(),
        {
            "personal_state_id": "personal_agents",
            "candidate_id": CANDIDATE_ID,
            "capability_id": CAPABILITY_ID,
            "understand": True,
            "explain": False,
            "apply": True,
            "evidence": False,
            "interview_ready": False,
            "revision": 1,
            "schema_version": 1,
            "updated_at": now,
            "updated_by": "user",
            "updated_by_kind": "user",
        },
    )
    connection.execute(
        CapabilityEvidenceBindingRow.__table__.insert(),
        {
            "binding_id": "binding_001",
            "personal_state_id": "personal_agents",
            "personal_state_revision": 1,
            "capability_id": CAPABILITY_ID,
            "evidence_ref_id": JOB_EVIDENCE_REF_ID,
            "project_evidence_id": None,
            "project_evidence_revision": None,
            "authority": "document_supported",
            "scopes": ["understand"],
            "bound_at": now,
            "bound_by": "user",
        },
    )


@dataclass
class _World:
    engine: Engine
    jobs: JobService
    opportunities: OpportunityService
    match: MatchService
    match_repository: MatchRepository
    facts: FactService
    fact_repository: FactRepository
    resumes: ResumeService
    applications: ApplicationService


@dataclass
class _Staged:
    assessment: MatchAssessmentRecord
    resume_revision: ResumeRevision
    priority_snapshot: tuple[tuple, tuple]


def _world(tmp_path: Path) -> _World:
    database_url = sqlite_url(tmp_path / "p0-vertical-slice.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        _seed_evidence_ref(connection, JOB_EVIDENCE_REF_ID)
        _seed_capability(connection)
        _seed_personal_state(connection)
    commands = CommandService(engine)
    match_repository = MatchRepository(engine)
    resolver = MatchInputResolver(
        opportunities=OpportunityRepository(engine),
        jobs=JobRepository(engine),
        capabilities=CapabilityRepository(engine),
        evidence=EvidenceRepository(engine),
        projects=ProjectRepository(engine),
    )
    return _World(
        engine=engine,
        jobs=JobService(commands, JobRepository(engine)),
        opportunities=OpportunityService(commands),
        match=MatchService(commands, match_repository, resolver),
        match_repository=match_repository,
        facts=FactService(commands, FactRepository(engine)),
        fact_repository=FactRepository(engine),
        resumes=ResumeService(commands),
        applications=ApplicationService(commands),
    )


def _priority_snapshot(engine: Engine) -> tuple[tuple, tuple]:
    with Session(engine) as session:
        user = session.get(UserPriorityRow, OPPORTUNITY_ID)
        suggested = session.get(SuggestedPriorityRow, OPPORTUNITY_ID)
        assert user is not None
        assert suggested is not None
        return (
            (user.level, user.revision, user.actor, user.set_at, user.reason),
            (suggested.level, suggested.revision, suggested.score, tuple(suggested.reasons)),
        )


def _row_counts(engine: Engine, rows: tuple[type, ...]) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(session.scalar(select(func.count()).select_from(row)) or 0 for row in rows)


def _stage_job_and_requirements(world: _World) -> None:
    jobs = world.jobs
    job = jobs.record_revision(
        _command(JOB_ID, EntityKind.JOB, "command_job_001", actor="agent:job-capture"),
        content_sha256=hashlib.sha256(b"p0-vertical-slice-job").hexdigest(),
        source_evidence_refs=(JOB_EVIDENCE_REF_ID,),
    )
    assert job.job.revision == JOB_REVISION
    assert job.job.source_evidence_refs == (JOB_EVIDENCE_REF_ID,)

    proposals = (
        (
            REQUIREMENT_COVERED_ID,
            "Explain agent system design trade-offs.",
            (CapabilityEvidenceScope.UNDERSTAND,),
        ),
        (
            REQUIREMENT_GAP_ID,
            "Build and operate production agent workflows.",
            (CapabilityEvidenceScope.UNDERSTAND, CapabilityEvidenceScope.APPLY),
        ),
    )
    for requirement_id, text, scopes in proposals:
        proposed = jobs.propose_requirement(
            _command(
                requirement_id,
                EntityKind.JOB_REQUIREMENT,
                f"command_propose_{requirement_id}",
                actor="agent:requirement-extractor",
            ),
            job=JobRef(job_id=JOB_ID, revision=JOB_REVISION),
            requirement_text=text,
            importance=JobRequirementImportance.REQUIRED,
            required_scopes=scopes,
            source_evidence_refs=(JOB_EVIDENCE_REF_ID,),
        )
        # Agent extraction is a proposal only; it is not canonical Match input yet.
        assert proposed.requirement.status is JobRequirementStatus.PROPOSED
        assert proposed.requirement.proposed_by_kind is ActorKind.AGENT
        assert proposed.requirement.capability_id is None

        reviewed = jobs.review_requirement(
            _command(
                requirement_id,
                EntityKind.JOB_REQUIREMENT,
                f"command_review_{requirement_id}",
                expected_revision=1,
            ),
            decision=JobRequirementStatus.ACCEPTED,
            review_reason="Confirmed against the captured job description.",
            capability_id=CAPABILITY_ID,
            graph_version_id=GRAPH_VERSION_ID,
        )
        assert reviewed.requirement.status is JobRequirementStatus.ACCEPTED
        assert reviewed.requirement.revision == ACCEPTED_REQUIREMENT_REVISION
        assert reviewed.requirement.reviewed_by_kind is ActorKind.USER
        # The proposal revision stays immutable and readable.
        assert jobs.repository.get_requirement(requirement_id, 1) == proposed.requirement


def _stage_opportunity_with_priorities(world: _World) -> tuple[tuple, tuple]:
    admission = world.opportunities.admit_manually(
        _command(OPPORTUNITY_ID, EntityKind.OPPORTUNITY, "command_opportunity_admit"),
        JobRef(job_id=JOB_ID, revision=JOB_REVISION),
        opportunity_id=OPPORTUNITY_ID,
        decision_id="decision_001",
        reason="User chose to invest in this role.",
    )
    assert admission.admission.opportunity is not None
    assert admission.admission.opportunity.revision == 1

    opportunities = OpportunityRepository(world.engine)
    detail = opportunities.get(OPPORTUNITY_ID)
    assert detail is not None
    assert detail.job == JobRef(job_id=JOB_ID, revision=JOB_REVISION)

    world.opportunities.set_user_priority(
        _command(
            OPPORTUNITY_ID, EntityKind.OPPORTUNITY, "command_user_priority", expected_revision=1
        ),
        level=PriorityLevel.HIGH,
        reason="Top target for this quarter.",
    )
    world.opportunities.set_suggested_priority(
        _command(
            OPPORTUNITY_ID,
            EntityKind.OPPORTUNITY,
            "command_suggested_priority",
            actor="rule:priority",
            expected_revision=2,
        ),
        level=PriorityLevel.LOW,
        reasons=("Waiting on referral timing.",),
        input_revisions=(PriorityInputRevision(entity_id=JOB_ID, revision=JOB_REVISION),),
        score=0.41,
    )
    frozen = opportunities.get_revision(OPPORTUNITY_ID, OPPORTUNITY_FROZEN_REVISION)
    assert frozen is not None
    assert frozen.job == JobRef(job_id=JOB_ID, revision=JOB_REVISION)
    return _priority_snapshot(world.engine)


def _stage_match(world: _World) -> MatchAssessmentRecord:
    recorded = world.match.assess(
        _command(
            ASSESSMENT_ID,
            EntityKind.MATCH_ASSESSMENT,
            "command_assessment_001",
            actor="agent:match",
        ),
        candidate_id=CANDIDATE_ID,
        opportunity_id=OPPORTUNITY_ID,
        opportunity_revision=OPPORTUNITY_FROZEN_REVISION,
        requirements=(
            (REQUIREMENT_COVERED_ID, ACCEPTED_REQUIREMENT_REVISION),
            (REQUIREMENT_GAP_ID, ACCEPTED_REQUIREMENT_REVISION),
        ),
    )
    persisted = recorded.assessment
    assert world.match_repository.get_assessment(ASSESSMENT_ID) == persisted
    header = persisted.header
    assert header.opportunity_id == OPPORTUNITY_ID
    assert header.opportunity_revision == OPPORTUNITY_FROZEN_REVISION
    assert header.job_id == JOB_ID
    assert header.job_revision == JOB_REVISION
    assert header.candidate_id == CANDIDATE_ID
    assert header.policy_version == MATCH_POLICY_VERSION

    # The stored manifest pins the exact accepted requirement revisions.
    assert [(item.requirement_id, item.revision) for item in persisted.manifest.requirements] == [
        (REQUIREMENT_COVERED_ID, ACCEPTED_REQUIREMENT_REVISION),
        (REQUIREMENT_GAP_ID, ACCEPTED_REQUIREMENT_REVISION),
    ]
    assert [result.classification for result in persisted.results] == [
        MatchClassification.COVERED,
        MatchClassification.QUICK_TO_STRENGTHEN,
    ]

    # Every non-COVERED result receives a stable canonical Gap in the same transaction.
    assert len(persisted.gaps) == 1
    gap = persisted.gaps[0]
    assert gap.gap_id == derive_gap_id("command_assessment_001", REQUIREMENT_GAP_ID)
    assert gap.assessment_id == ASSESSMENT_ID
    assert gap.requirement_id == REQUIREMENT_GAP_ID
    assert gap.requirement_revision == ACCEPTED_REQUIREMENT_REVISION
    assert gap.capability_id == CAPABILITY_ID
    assert gap.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert world.match_repository.get_gap(gap.gap_id) == gap
    return persisted


def _stage_fact(world: _World) -> None:
    proposed = world.facts.propose_claim(
        _command(
            CLAIM_ID, EntityKind.EXTRACTED_CLAIM, "command_claim_001", actor="agent:extractor"
        ),
        claim_type="skill",
        subject=EntityRef(entity_id=CANDIDATE_ID, kind=EntityKind.CANDIDATE),
        proposed_value={"name": "agent engineering", "depth": "production"},
        evidence_refs=(JOB_EVIDENCE_REF_ID,),
        extractor="agent:extractor",
        extractor_version="extractor-1",
        confidence=0.9,
    )
    assert proposed.claim.claim.status is ClaimStatus.PROPOSED
    # AI/parser output never becomes a Fact implicitly.
    assert world.fact_repository.list_facts_for_subject(CANDIDATE_ID) == ()

    reviewed = world.facts.review_claim(
        _command(CLAIM_ID, EntityKind.EXTRACTED_CLAIM, "command_claim_review", expected_revision=1),
        decision=ClaimStatus.ACCEPTED,
        review_reason="Confirmed against the captured project evidence.",
    )
    assert reviewed.claim.claim.status is ClaimStatus.ACCEPTED

    promoted = world.facts.promote_fact(
        _command(FACT_ID, EntityKind.FACT, "command_fact_promote"),
        source_claim_id=CLAIM_ID,
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
        candidate_id=CANDIDATE_ID,
    )
    assert promoted.fact.fact.authority is FactAuthority.USER_ASSERTED
    assert promoted.fact.fact.evidence_refs == (JOB_EVIDENCE_REF_ID,)


def _stage_resume(world: _World) -> ResumeRevision:
    resumes = world.resumes
    base = resumes.save_base_revision(
        _command(RESUME_ID, EntityKind.RESUME, "command_resume_base"),
        candidate_id=CANDIDATE_ID,
        sections={"summary": "Old summary", "skills": ["Python"]},
    )
    assert base.revision == 1

    operation = ResumePatchOperation(
        action=ResumePatchAction.SET,
        target_path="/summary",
        expected_value_hash=canonical_value_hash("Old summary"),
        proposed_value="Agent systems engineer",
        fact_refs=(RevisionRef(entity_id=FACT_ID, revision=1),),
        evidence_refs=(JOB_EVIDENCE_REF_ID,),
        requirement_refs=(
            RevisionRef(entity_id=REQUIREMENT_GAP_ID, revision=ACCEPTED_REQUIREMENT_REVISION),
        ),
        reason="Align the verified agent experience with the target requirement.",
    )
    proposed = resumes.propose_patch(
        _command(PATCH_ID, EntityKind.RESUME_PATCH, "command_patch_001", actor="agent:resume"),
        resume_id=RESUME_ID,
        base_revision=1,
        operations=(operation,),
        generator_run_id="run_001",
    )
    assert proposed.status is ResumePatchStatus.PROPOSED
    assert proposed.proposed_by_kind is ActorKind.AGENT

    # An unreviewed agent patch cannot become an immutable ResumeRevision.
    with pytest.raises(ValueError, match="exact accepted"):
        resumes.create_revision(
            _command(RESUME_REVISION_ID, EntityKind.RESUME_REVISION, "command_revision_early"),
            resume_id=RESUME_ID,
            base_revision=1,
            accepted_patch_refs=(RevisionRef(entity_id=PATCH_ID, revision=1),),
        )
    assert resumes.repository.get_revision(RESUME_REVISION_ID) is None

    reviewed = resumes.review_patch(
        _command(PATCH_ID, EntityKind.RESUME_PATCH, "command_patch_review", expected_revision=1),
        decision=ResumePatchStatus.ACCEPTED,
        review_reason="Verified against the promoted fact and evidence.",
    )
    assert reviewed.status is ResumePatchStatus.ACCEPTED

    revision = resumes.create_revision(
        _command(RESUME_REVISION_ID, EntityKind.RESUME_REVISION, "command_resume_revision"),
        resume_id=RESUME_ID,
        base_revision=1,
        accepted_patch_refs=(RevisionRef(entity_id=PATCH_ID, revision=2),),
    )
    assert revision.content == {"summary": "Agent systems engineer", "skills": ["Python"]}
    assert revision.content_sha256 == canonical_value_hash(revision.content)
    assert resumes.repository.get_revision(RESUME_REVISION_ID) == revision

    persisted_patch = resumes.repository.get_patch(PATCH_ID, 2)
    assert persisted_patch is not None
    persisted_operation = persisted_patch.operations[0]
    assert persisted_operation.fact_refs == (RevisionRef(entity_id=FACT_ID, revision=1),)
    assert persisted_operation.requirement_refs == (
        RevisionRef(entity_id=REQUIREMENT_GAP_ID, revision=ACCEPTED_REQUIREMENT_REVISION),
    )
    return revision


def _stage(world: _World) -> _Staged:
    _stage_job_and_requirements(world)
    priority_snapshot = _stage_opportunity_with_priorities(world)
    assessment = _stage_match(world)
    _stage_fact(world)
    resume_revision = _stage_resume(world)
    return _Staged(
        assessment=assessment,
        resume_revision=resume_revision,
        priority_snapshot=priority_snapshot,
    )


def test_p0_vertical_slice_end_to_end(tmp_path: Path) -> None:
    world = _world(tmp_path)
    staged = _stage(world)

    # Application: prepare -> user-confirmed submit. Prepared is not Submitted.
    prepared = world.applications.create(
        _command(APPLICATION_ID, EntityKind.APPLICATION, "command_application"),
        opportunity_id=OPPORTUNITY_ID,
        opportunity_revision=OPPORTUNITY_FROZEN_REVISION,
    )
    assert prepared.state is ApplicationState.PREPARING
    assert prepared.resume_revision_id is None
    assert prepared.submitted_at is None
    with pytest.raises(ValueError, match="READY_FOR_REVIEW"):
        world.applications.record_submission(
            _command(
                APPLICATION_ID,
                EntityKind.APPLICATION,
                "command_submit_early",
                expected_revision=1,
            ),
            resume_revision_id=RESUME_REVISION_ID,
            authority=SubmissionAuthority.USER_CONFIRMED,
        )

    ready = world.applications.set_preparation_state(
        _command(APPLICATION_ID, EntityKind.APPLICATION, "command_ready", expected_revision=1),
        state=ApplicationState.READY_FOR_REVIEW,
    )
    assert ready.revision == 2
    assert ready.state is ApplicationState.READY_FOR_REVIEW

    submitted = world.applications.record_submission(
        _command(APPLICATION_ID, EntityKind.APPLICATION, "command_submit", expected_revision=2),
        resume_revision_id=RESUME_REVISION_ID,
        authority=SubmissionAuthority.USER_CONFIRMED,
    )
    assert submitted.state is ApplicationState.SUBMITTED_BY_USER
    assert submitted.resume_revision_id == staged.resume_revision.revision_id
    assert submitted.opportunity_id == OPPORTUNITY_ID
    assert submitted.opportunity_revision == OPPORTUNITY_FROZEN_REVISION

    # Outcome is pinned to the exact submitted Application revision.
    outcome = world.applications.record_outcome(
        _command(OUTCOME_ID, EntityKind.OUTCOME, "command_outcome"),
        application_id=APPLICATION_ID,
        application_revision=submitted.revision,
        result=OutcomeType.OFFER,
        authority=OutcomeAuthority.USER_CONFIRMED,
    )
    assert outcome.application_id == APPLICATION_ID
    assert outcome.application_revision == submitted.revision
    assert world.applications.repository.get_outcome(OUTCOME_ID) == outcome

    # Replay: the stored manifest re-resolves with zero drift and zero writes.
    before = _row_counts(world.engine, MATCH_WRITTEN_ROWS)
    replayed = world.match.replay(ASSESSMENT_ID)
    assert replayed == staged.assessment
    assert _row_counts(world.engine, MATCH_WRITTEN_ROWS) == before

    # UserPriority survived the whole chain untouched; so did SuggestedPriority.
    assert _priority_snapshot(world.engine) == staged.priority_snapshot
    detail = OpportunityRepository(world.engine).get(OPPORTUNITY_ID)
    assert detail is not None
    assert detail.opportunity.revision == OPPORTUNITY_FROZEN_REVISION
    assert detail.user_priority is not None
    assert detail.user_priority.level is PriorityLevel.HIGH
    assert detail.suggested_priority is not None
    assert detail.suggested_priority.level is PriorityLevel.LOW

    # The chain emitted exactly the expected past-tense, metadata-only domain events.
    with Session(world.engine) as session:
        events = list(session.scalars(select(DomainEventRow)))
    assert Counter(event.event_type for event in events) == Counter(
        {
            "job.revision_created": 1,
            "job_requirement.proposed": 2,
            "job_requirement.reviewed": 2,
            "opportunity.admitted": 1,
            "opportunity.user_priority_set": 1,
            "opportunity.suggested_priority_updated": 1,
            "match.assessed": 1,
            "claim.proposed": 1,
            "claim.reviewed": 1,
            "fact.promoted": 1,
            "resume_base.saved": 1,
            "resume_patch.proposed": 1,
            "resume_patch.reviewed": 1,
            "resume_revision.created": 1,
            "application.created": 1,
            "application.state_changed": 1,
            "application.submission_recorded": 1,
            "outcome.recorded": 1,
        }
    )
    match_event = next(event for event in events if event.event_type == "match.assessed")
    assert match_event.payload["gap_ids"] == [gap.gap_id for gap in staged.assessment.gaps]


def test_p0_vertical_slice_rejects_stale_or_dangling_refs(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _stage(world)

    # An Application must pin an exact persisted Opportunity revision.
    with pytest.raises(ValueError, match="exact Opportunity revision"):
        world.applications.create(
            _command(APPLICATION_ID, EntityKind.APPLICATION, "command_application_stale"),
            opportunity_id=OPPORTUNITY_ID,
            opportunity_revision=99,
        )

    # Submission must pin an exact persisted ResumeRevision.
    world.applications.create(
        _command(APPLICATION_ID, EntityKind.APPLICATION, "command_application"),
        opportunity_id=OPPORTUNITY_ID,
        opportunity_revision=OPPORTUNITY_FROZEN_REVISION,
    )
    world.applications.set_preparation_state(
        _command(APPLICATION_ID, EntityKind.APPLICATION, "command_ready", expected_revision=1),
        state=ApplicationState.READY_FOR_REVIEW,
    )
    with pytest.raises(ValueError, match="exact ResumeRevision"):
        world.applications.record_submission(
            _command(
                APPLICATION_ID,
                EntityKind.APPLICATION,
                "command_submit_dangling",
                expected_revision=2,
            ),
            resume_revision_id="resume_revision_missing",
            authority=SubmissionAuthority.USER_CONFIRMED,
        )
    current = world.applications.repository.get(APPLICATION_ID, 2)
    assert current is not None
    assert current.state is ApplicationState.READY_FOR_REVIEW
    assert current.resume_revision_id is None

    # A ResumePatch cannot cite the pre-review (proposed) requirement revision.
    with pytest.raises(ValueError, match="exact accepted JobRequirement refs"):
        world.resumes.propose_patch(
            _command(
                "patch_stale",
                EntityKind.RESUME_PATCH,
                "command_patch_stale",
                actor="agent:resume",
            ),
            resume_id=RESUME_ID,
            base_revision=1,
            operations=(
                ResumePatchOperation(
                    action=ResumePatchAction.SET,
                    target_path="/summary",
                    expected_value_hash=canonical_value_hash("Old summary"),
                    proposed_value="Stale reference",
                    evidence_refs=(JOB_EVIDENCE_REF_ID,),
                    requirement_refs=(RevisionRef(entity_id=REQUIREMENT_GAP_ID, revision=1),),
                    reason="Attempts to cite the unreviewed requirement revision.",
                ),
            ),
        )
    assert world.resumes.repository.get_patch("patch_stale") is None

    # Replay fails loud for an unknown assessment instead of fabricating one.
    with pytest.raises(MatchReplayError, match="unknown match assessment"):
        world.match.replay("assessment_missing")
