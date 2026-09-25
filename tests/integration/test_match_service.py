from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from career_harness.core.capability import (
    CapabilityEvidenceAuthority,
    CapabilityEvidenceScope,
    CapabilityLayer,
    CapabilityNode,
    EvidenceBinding,
    PersonalCapabilityState,
)
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.evidence import EvidenceRef
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind, Opportunity, OpportunityState
from career_harness.core.match_gap import (
    ExactRevisionRef,
    MatchClassification,
    MatchPolicyInput,
    assess_match,
)
from career_harness.core.opportunity import OpportunityDetail
from career_harness.db.match_repository import MatchGapRecord, MatchRepository
from career_harness.db.match_writes import MatchAssessmentWrite
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
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
    SuggestedPriorityRow,
    UserPriorityRow,
)
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.match_service import MatchService
from tests.support.job_data import seed_job_revision_rows

CAPABILITY_ID = "capability_agents"
GRAPH_VERSION_ID = "graph_001"
EVIDENCE_REF_ID = "evidence_job_001_1"


def _command(assessment_id: str, *, command_id: str, key: str | None = None) -> Command:
    return Command(
        command_id=command_id,
        command_type="match_assessment.record",
        target=EntityRef(entity_id=assessment_id, kind=EntityKind.MATCH_ASSESSMENT),
        expected_revision=0,
        idempotency_key=key or f"idempotency-{command_id}",
        actor="agent:match",
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


def _seed_opportunity(
    connection,  # type: ignore[no-untyped-def]
    opportunity_id: str = "opportunity_001",
    *,
    revision: int = 1,
    job_id: str = "job_001",
    job_revision: int = 1,
    state: str = "qualified",
) -> None:
    now = datetime.now(UTC)
    state_payload = {
        "entity_id": opportunity_id,
        "revision": revision,
        "schema_version": 1,
        "state": state,
    }
    if revision == 1:
        connection.execute(
            EntityStateRow.__table__.insert(),
            {
                "entity_id": opportunity_id,
                "entity_kind": "opportunity",
                "revision": revision,
                "schema_version": 1,
                "state": state_payload,
                "updated_at": now,
            },
        )
        connection.execute(
            OpportunityRecordRow.__table__.insert(),
            {
                "opportunity_id": opportunity_id,
                "job_id": job_id,
                "job_revision": job_revision,
                "state": state,
                "revision": revision,
                "schema_version": 1,
                "admitted_at": now,
                "admitted_by": "user",
            },
        )
    else:
        connection.execute(
            EntityStateRow.__table__.update()
            .where(EntityStateRow.entity_id == opportunity_id)
            .values(revision=revision, state=state_payload, updated_at=now)
        )
        connection.execute(
            OpportunityRecordRow.__table__.update()
            .where(OpportunityRecordRow.opportunity_id == opportunity_id)
            .values(revision=revision, state=state)
        )
    connection.execute(
        EntityRevisionRow.__table__.insert(),
        {
            "revision_id": f"revision_{opportunity_id}_{revision}",
            "entity_id": opportunity_id,
            "revision": revision,
            "schema_version": 1,
            "state": state_payload,
            "created_at": now,
            "created_by": "user",
        },
    )


def _seed_accepted_requirement(
    connection,  # type: ignore[no-untyped-def]
    requirement_id: str,
    *,
    job_id: str = "job_001",
    job_revision: int = 1,
    scopes: tuple[str, ...] = ("understand", "apply"),
    status: str = "accepted",
) -> None:
    now = datetime.now(UTC)
    connection.execute(
        JobRequirementIdentityRow.__table__.insert(),
        {"requirement_id": requirement_id, "job_id": job_id},
    )
    for ordinal, scope in enumerate(scopes):
        connection.execute(
            JobRequirementScopeRow.__table__.insert(),
            {
                "requirement_id": requirement_id,
                "requirement_revision": 1,
                "ordinal": ordinal,
                "scope": scope,
            },
        )
    connection.execute(
        JobRequirementEvidenceRefRow.__table__.insert(),
        {
            "requirement_id": requirement_id,
            "requirement_revision": 1,
            "ordinal": 0,
            "evidence_ref_id": EVIDENCE_REF_ID,
        },
    )
    review = (
        {
            "reviewed_by": "user",
            "reviewed_by_kind": "user",
            "review_reason": "Confirmed against the captured job description.",
            "reviewed_at": now,
        }
        if status != "proposed"
        else {
            "reviewed_by": None,
            "reviewed_by_kind": None,
            "review_reason": None,
            "reviewed_at": None,
        }
    )
    connection.execute(
        JobRequirementRevisionRow.__table__.insert(),
        {
            "requirement_id": requirement_id,
            "revision": 1,
            "schema_version": 1,
            "job_id": job_id,
            "job_revision": job_revision,
            "requirement_text": f"Requirement text for {requirement_id}.",
            "importance": "required",
            "capability_id": CAPABILITY_ID,
            "graph_version_id": GRAPH_VERSION_ID,
            "required_scope_count": len(scopes),
            "source_evidence_count": 1,
            "status": status,
            "proposed_by": "agent:extractor",
            "proposed_by_kind": "agent",
            "proposed_at": now,
            **review,
        },
    )


def _engine(tmp_path: Path) -> Engine:
    database_url = sqlite_url(tmp_path / "match-persistence.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        seed_job_revision_rows(connection, "job_001", 1)
        _seed_capability(connection)
        _seed_opportunity(connection)
        _seed_accepted_requirement(connection, "requirement_001", scopes=("understand", "apply"))
        _seed_accepted_requirement(connection, "requirement_002", scopes=("explain",))
        _seed_accepted_requirement(connection, "requirement_003", scopes=("understand",))
    return engine


def _services(engine: Engine) -> tuple[MatchRepository, MatchService]:
    repository = MatchRepository(engine)
    return repository, MatchService(CommandService(engine), repository)


def _requirement(
    requirement_id: str, scopes: tuple[CapabilityEvidenceScope, ...]
) -> JobRequirement:
    return JobRequirement(
        requirement_id=requirement_id,
        revision=1,
        job=JobRef(job_id="job_001", revision=1),
        requirement_text=f"Requirement text for {requirement_id}.",
        importance=JobRequirementImportance.REQUIRED,
        capability_id=CAPABILITY_ID,
        graph_version_id=GRAPH_VERSION_ID,
        required_scopes=scopes,
        source_evidence_refs=(EVIDENCE_REF_ID,),
        status=JobRequirementStatus.ACCEPTED,
        proposed_by="agent:extractor",
        proposed_by_kind=ActorKind.AGENT,
        reviewed_by="user",
        reviewed_by_kind=ActorKind.USER,
        review_reason="Confirmed against the captured job description.",
        reviewed_at=datetime.now(UTC),
    )


def _policy_input(
    requirements: tuple[JobRequirement, ...] | None = None,
) -> MatchPolicyInput:
    if requirements is None:
        requirements = (
            _requirement(
                "requirement_001",
                (CapabilityEvidenceScope.UNDERSTAND, CapabilityEvidenceScope.APPLY),
            ),
            _requirement("requirement_002", (CapabilityEvidenceScope.EXPLAIN,)),
            _requirement("requirement_003", (CapabilityEvidenceScope.UNDERSTAND,)),
        )
    return MatchPolicyInput(
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
        requirements=requirements,
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
        personal_states=(
            PersonalCapabilityState(
                personal_state_id="personal_agents",
                candidate_id="candidate_001",
                capability_id=CAPABILITY_ID,
                understand=True,
                apply=True,
                revision=4,
                updated_by="user",
                updated_by_kind=ActorKind.USER,
            ),
        ),
        evidence_bindings=(
            EvidenceBinding(
                binding_id="binding_001",
                personal_state_id="personal_agents",
                personal_state_revision=4,
                capability_id=CAPABILITY_ID,
                evidence_ref_id=EVIDENCE_REF_ID,
                authority=CapabilityEvidenceAuthority.DOCUMENT_SUPPORTED,
                scopes=(CapabilityEvidenceScope.UNDERSTAND,),
                bound_by="user",
            ),
        ),
        evidence_refs=(
            EvidenceRef(
                evidence_ref_id=EVIDENCE_REF_ID,
                snapshot_id=f"snapshot_{EVIDENCE_REF_ID}",
                artifact_id=f"artifact_{EVIDENCE_REF_ID}",
            ),
        ),
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
                MatchAssessmentRow,
                MatchRequirementResultRow,
                MatchGapRow,
            )
        )


def test_policy_output_persists_as_immutable_typed_aggregate(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    assert [result.classification for result in assessment.requirements] == [
        MatchClassification.QUICK_TO_STRENGTHEN,
        MatchClassification.CLEAR_GAP,
        MatchClassification.COVERED,
    ]

    recorded = service.record_assessment(
        _command("assessment_001", command_id="command_assessment_001"),
        assessment=assessment,
        candidate_id="candidate_001",
    )

    persisted = repository.get_assessment("assessment_001")
    assert persisted is not None
    assert recorded.assessment == persisted
    assert persisted.manifest == assessment.inputs
    assert persisted.results == assessment.requirements
    assert persisted.header.opportunity_id == "opportunity_001"
    assert persisted.header.opportunity_revision == 1
    assert persisted.header.job_id == "job_001"
    assert persisted.header.job_revision == 1
    assert persisted.header.candidate_id == "candidate_001"
    assert persisted.header.policy_version == "match-policy-v1"
    assert persisted.header.created_by == "agent:match"

    gaps = persisted.gaps
    assert len(gaps) == 2
    assert {gap.classification for gap in gaps} == {
        MatchClassification.QUICK_TO_STRENGTHEN,
        MatchClassification.CLEAR_GAP,
    }
    for gap in gaps:
        assert repository.get_gap(gap.gap_id) == gap
    assert repository.list_gaps_for_assessment("assessment_001") == gaps
    assert repository.get_gap("gap_missing") is None
    assert repository.get_assessment("assessment_missing") is None

    with Session(engine) as session:
        state = session.get(EntityStateRow, "assessment_001")
        assert state is not None
        assert state.entity_kind == "match_assessment"
        assert state.revision == 1
        event = session.scalars(
            select(DomainEventRow).where(DomainEventRow.entity_id == "assessment_001")
        ).one()
        assert event.event_type == "match.assessed"
        assert event.payload == {
            "revision_id": recorded.commit.revision_id,
            "assessment_id": "assessment_001",
            "opportunity_id": "opportunity_001",
            "opportunity_revision": 1,
            "job_id": "job_001",
            "job_revision": 1,
            "candidate_id": "candidate_001",
            "policy_version": "match-policy-v1",
            "requirement_count": 3,
            "covered_count": 1,
            "quick_to_strengthen_count": 1,
            "clear_gap_count": 1,
            "gap_ids": [gap.gap_id for gap in gaps],
        }


def test_record_assessment_is_idempotent_and_conflicts_on_different_input(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    command = _command("assessment_001", command_id="command_assessment_001")

    first = service.record_assessment(command, assessment=assessment, candidate_id="candidate_001")
    replay = service.record_assessment(command, assessment=assessment, candidate_id="candidate_001")

    assert replay.commit == first.commit
    assert replay.assessment == first.assessment
    assert replay.assessment.gaps == first.assessment.gaps
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(MatchAssessmentRow)) == 1
        assert session.scalar(select(func.count()).select_from(MatchGapRow)) == 2
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 1

    other = assess_match(_policy_input())
    conflicting = Command(
        command_id="command_assessment_001",
        command_type="match_assessment.record",
        target=EntityRef(entity_id="assessment_002", kind=EntityKind.MATCH_ASSESSMENT),
        expected_revision=0,
        idempotency_key="idempotency-command_assessment_001",
        actor="agent:match",
    )
    with pytest.raises(IdempotencyConflict):
        service.record_assessment(conflicting, assessment=other, candidate_id="candidate_001")


def test_dangling_requirement_rolls_back_everything(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(
        _policy_input(
            requirements=(
                _requirement(
                    "requirement_001",
                    (CapabilityEvidenceScope.UNDERSTAND, CapabilityEvidenceScope.APPLY),
                ),
            )
        )
    )
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={
                    "requirements": (
                        *assessment.inputs.requirements,
                        assessment.inputs.requirements[0].model_copy(
                            update={"requirement_id": "requirement_missing"}
                        ),
                    )
                }
            ),
            "requirements": (
                *assessment.requirements,
                assessment.requirements[0].model_copy(
                    update={
                        "requirement": assessment.requirements[0].requirement.model_copy(
                            update={"entity_id": "requirement_missing"}
                        )
                    }
                ),
            ),
        }
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="exact persisted JobRequirement revision"):
        service.record_assessment(
            _command("assessment_dangling", command_id="command_assessment_dangling"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_dangling") is None


def test_frozen_job_revision_and_candidate_mismatch_fail_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        seed_job_revision_rows(connection, "job_001", 2)
        _seed_accepted_requirement(
            connection, "requirement_other_job", job_revision=2, scopes=("understand",)
        )
    repository, service = _services(engine)
    other_job_assessment = assess_match(
        _policy_input(
            requirements=(
                _requirement("requirement_other_job", (CapabilityEvidenceScope.UNDERSTAND,)),
            )
        )
    )
    with pytest.raises(ValueError, match="frozen Job revision"):
        service.record_assessment(
            _command("assessment_other_job", command_id="command_assessment_other_job"),
            assessment=other_job_assessment,
            candidate_id="candidate_001",
        )
    assert repository.get_assessment("assessment_other_job") is None

    assessment = assess_match(_policy_input())
    with pytest.raises(ValueError, match="another candidate"):
        service.record_assessment(
            _command("assessment_candidate", command_id="command_assessment_candidate"),
            assessment=assessment,
            candidate_id="candidate_002",
        )
    assert repository.get_assessment("assessment_candidate") is None


def test_gap_for_covered_result_is_rejected_and_rolled_back(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    covered = next(
        result
        for result in assessment.requirements
        if result.classification is MatchClassification.COVERED
    )
    write = MatchAssessmentWrite(
        assessment_id="assessment_bad_gap",
        candidate_id="candidate_001",
        assessment=assessment,
        gaps=(
            MatchGapRecord(
                gap_id="gap_on_covered",
                assessment_id="assessment_bad_gap",
                requirement_id=covered.requirement.entity_id,
                requirement_revision=covered.requirement.revision,
                capability_id=CAPABILITY_ID,
                classification=MatchClassification.QUICK_TO_STRENGTHEN,
            ),
        ),
        created_by="agent:match",
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="covered"):
        service.commands.commit(
            _command("assessment_bad_gap", command_id="command_assessment_bad_gap"),
            {},
            event_type="match.assessed",
            transactional_write=write,
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_bad_gap") is None


def test_missing_gap_for_non_covered_result_is_rejected(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    write = MatchAssessmentWrite(
        assessment_id="assessment_no_gaps",
        candidate_id="candidate_001",
        assessment=assessment,
        gaps=(),
        created_by="agent:match",
    )
    with pytest.raises(ValueError, match="exactly one Gap"):
        service.commands.commit(
            _command("assessment_no_gaps", command_id="command_assessment_no_gaps"),
            {},
            event_type="match.assessed",
            transactional_write=write,
        )
    assert repository.get_assessment("assessment_no_gaps") is None


def test_manifest_without_frozen_opportunity_revision_fails(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={
                    "opportunity": assessment.inputs.opportunity.model_copy(update={"revision": 2})
                }
            )
        }
    )
    with pytest.raises(ValueError, match="exact frozen Opportunity revision"):
        service.record_assessment(
            _command("assessment_no_opportunity", command_id="command_assessment_no_opportunity"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert repository.get_assessment("assessment_no_opportunity") is None


def test_malformed_persisted_manifest_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    service.record_assessment(
        _command("assessment_001", command_id="command_assessment_001"),
        assessment=assess_match(_policy_input()),
        candidate_id="candidate_001",
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO match_assessment "
            "(assessment_id, opportunity_id, opportunity_revision, job_id, job_revision, "
            "candidate_id, policy_version, manifest, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "assessment_malformed",
                "opportunity_001",
                1,
                "job_001",
                1,
                "candidate_001",
                "match-policy-v1",
                '{"policy_version": "match-policy-v1", "requirements": '
                '[{"requirement_id": "requirement_001"}]}',
                datetime.now(UTC).isoformat(),
                "agent:match",
            ),
        )
    with pytest.raises(RuntimeError, match="manifest is malformed"):
        repository.get_assessment("assessment_malformed")


def test_tampered_gap_capability_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    service.record_assessment(
        _command("assessment_001", command_id="command_assessment_001"),
        assessment=assess_match(_policy_input()),
        candidate_id="candidate_001",
    )
    assert repository.get_assessment("assessment_001") is not None

    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_other"},
        )
        # Simulate a bypassed write path: the immutable trigger is dropped so the UPDATE lands.
        connection.exec_driver_sql("DROP TRIGGER trg_match_gap_no_update")
        connection.exec_driver_sql(
            "UPDATE match_gap SET capability_id = 'capability_other' "
            "WHERE assessment_id = 'assessment_001'"
        )

    with pytest.raises(RuntimeError, match="capability disagrees"):
        repository.get_assessment("assessment_001")


def test_list_assessments_for_opportunity_is_stable_latest_first(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    for assessment_id in ("assessment_a1", "assessment_b2"):
        service.record_assessment(
            _command(assessment_id, command_id=f"command_{assessment_id}"),
            assessment=assess_match(_policy_input()),
            candidate_id="candidate_001",
        )

    headers = repository.list_assessments_for_opportunity("opportunity_001")
    assert [header.assessment_id for header in headers] == ["assessment_b2", "assessment_a1"]
    assert repository.list_assessments_for_opportunity("opportunity_missing") == ()


def test_opportunity_get_revision_reads_exact_frozen_revision(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_opportunity(connection, revision=2, state="preparing")
        connection.execute(
            SuggestedPriorityRow.__table__.insert(),
            {
                "opportunity_id": "opportunity_001",
                "revision": 2,
                "level": "high",
                "score": None,
                "rank": None,
                "reasons": ["Strong capability fit."],
                "input_revisions": [{"entity_id": "job_001", "revision": 1}],
                "calculated_at": datetime.now(UTC),
            },
        )
        connection.execute(
            UserPriorityRow.__table__.insert(),
            {
                "opportunity_id": "opportunity_001",
                "revision": 2,
                "level": "urgent",
                "actor": "user",
                "set_at": datetime.now(UTC),
                "reason": "Apply this week.",
            },
        )
    repository = OpportunityRepository(engine)

    first = repository.get_revision("opportunity_001", 1)
    assert first is not None
    assert first.opportunity.revision == 1
    assert first.opportunity.state is OpportunityState.QUALIFIED
    assert first.job == JobRef(job_id="job_001", revision=1)
    assert first.suggested_priority is None
    assert first.user_priority is None

    second = repository.get_revision("opportunity_001", 2)
    assert second is not None
    assert second.opportunity.revision == 2
    assert second.opportunity.state is OpportunityState.PREPARING
    assert second.suggested_priority is not None
    assert second.suggested_priority.level.value == "high"
    assert second.user_priority is not None
    assert second.user_priority.level.value == "urgent"

    assert repository.get_revision("opportunity_001", 3) is None
    assert repository.get_revision("opportunity_missing", 1) is None

    current = repository.get("opportunity_001")
    assert current is not None
    assert current.opportunity.revision == 2
    assert current.user_priority is not None


def test_manifest_job_must_match_frozen_opportunity_job_ref(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={"job": ExactRevisionRef(entity_id="job_001", revision=2)}
            )
        }
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="frozen Opportunity JobRef"):
        service.record_assessment(
            _command("assessment_job_mismatch", command_id="command_assessment_job_mismatch"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_job_mismatch") is None


def test_missing_official_capability_membership_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(_policy_input())
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={
                    "official_capabilities": (
                        assessment.inputs.official_capabilities[0].model_copy(
                            update={"graph_version_id": "graph_missing"}
                        ),
                    )
                }
            )
        }
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="official capability membership"):
        service.record_assessment(
            _command("assessment_node_missing", command_id="command_assessment_node_missing"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_node_missing") is None


def test_graph_version_drift_from_persisted_requirement_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(
        _policy_input(
            requirements=(
                _requirement(
                    "requirement_001",
                    (CapabilityEvidenceScope.UNDERSTAND, CapabilityEvidenceScope.APPLY),
                ),
            )
        )
    )
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={
                    "requirements": (
                        assessment.inputs.requirements[0].model_copy(
                            update={"graph_version_id": "graph_other"}
                        ),
                    )
                }
            )
        }
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="graph version disagrees"):
        service.record_assessment(
            _command("assessment_graph_drift", command_id="command_assessment_graph_drift"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_graph_drift") is None


def test_non_accepted_requirement_revision_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_accepted_requirement(
            connection,
            "requirement_pending",
            scopes=("understand", "apply"),
            status="proposed",
        )
    repository, service = _services(engine)
    assessment = assess_match(
        _policy_input(
            requirements=(
                _requirement(
                    "requirement_001",
                    (CapabilityEvidenceScope.UNDERSTAND, CapabilityEvidenceScope.APPLY),
                ),
            )
        )
    )
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={
                    "requirements": (
                        assessment.inputs.requirements[0].model_copy(
                            update={"requirement_id": "requirement_pending"}
                        ),
                    )
                }
            ),
            "requirements": (
                assessment.requirements[0].model_copy(
                    update={
                        "requirement": assessment.requirements[0].requirement.model_copy(
                            update={"entity_id": "requirement_pending"}
                        )
                    }
                ),
            ),
        }
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="accepted JobRequirement revision"):
        service.record_assessment(
            _command("assessment_pending", command_id="command_assessment_pending"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_pending") is None


def test_manifest_scope_drift_from_persisted_requirement_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    assessment = assess_match(
        _policy_input(
            requirements=(
                _requirement(
                    "requirement_001",
                    (CapabilityEvidenceScope.UNDERSTAND, CapabilityEvidenceScope.APPLY),
                ),
            )
        )
    )
    tampered = assessment.model_copy(
        update={
            "inputs": assessment.inputs.model_copy(
                update={
                    "requirements": (
                        assessment.inputs.requirements[0].model_copy(
                            update={"required_scopes": (CapabilityEvidenceScope.UNDERSTAND,)}
                        ),
                    )
                }
            )
        }
    )
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="scopes drifted"):
        service.record_assessment(
            _command("assessment_scope_drift", command_id="command_assessment_scope_drift"),
            assessment=tampered,
            candidate_id="candidate_001",
        )
    assert _write_counts(engine) == before
    assert repository.get_assessment("assessment_scope_drift") is None
