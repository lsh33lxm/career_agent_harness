from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.engine import Connection

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
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind, Opportunity, OpportunityState
from career_harness.core.match_gap import (
    MATCH_POLICY_VERSION,
    MatchClassification,
    MatchPolicyInput,
)
from career_harness.core.opportunity import OpportunityDetail
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.evidence_repository import EvidenceRepository
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
    ProjectEvidenceRow,
    ProjectIdentityRow,
    ProjectRecordRow,
    ProjectScanScopeRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
    SuggestedPriorityRow,
    UserPriorityRow,
)
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService
from career_harness.services.match_resolver import MatchInputResolver, MatchResolutionError
from career_harness.services.match_service import MatchReplayError, MatchService
from tests.support.job_data import seed_job_revision_rows

CAPABILITY_ID = "capability_agents"
GRAPH_VERSION_ID = "graph_001"
JOB_EVIDENCE_REF_ID = "evidence_job_001_1"
PROJECT_EVIDENCE_ID = "project_evidence_001"
CANDIDATE_ID = "candidate_001"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


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
            "released_at": NOW,
            "released_by": "user",
            "released_by_kind": "user",
        },
    )


def _seed_opportunity(
    connection: Connection,
    *,
    revision: int = 1,
    state: str = "qualified",
) -> None:
    state_payload = {
        "entity_id": "opportunity_001",
        "revision": revision,
        "schema_version": 1,
        "state": state,
    }
    if revision == 1:
        connection.execute(
            EntityStateRow.__table__.insert(),
            {
                "entity_id": "opportunity_001",
                "entity_kind": "opportunity",
                "revision": revision,
                "schema_version": 1,
                "state": state_payload,
                "updated_at": NOW,
            },
        )
        connection.execute(
            OpportunityRecordRow.__table__.insert(),
            {
                "opportunity_id": "opportunity_001",
                "job_id": "job_001",
                "job_revision": 1,
                "state": state,
                "revision": revision,
                "schema_version": 1,
                "admitted_at": NOW,
                "admitted_by": "user",
            },
        )
    else:
        connection.execute(
            EntityStateRow.__table__.update()
            .where(EntityStateRow.entity_id == "opportunity_001")
            .values(revision=revision, state=state_payload, updated_at=NOW)
        )
        connection.execute(
            OpportunityRecordRow.__table__.update()
            .where(OpportunityRecordRow.opportunity_id == "opportunity_001")
            .values(revision=revision, state=state)
        )
    connection.execute(
        EntityRevisionRow.__table__.insert(),
        {
            "revision_id": f"revision_opportunity_001_{revision}",
            "entity_id": "opportunity_001",
            "revision": revision,
            "schema_version": 1,
            "state": state_payload,
            "created_at": NOW,
            "created_by": "user",
        },
    )


def _seed_requirement(
    connection: Connection,
    requirement_id: str,
    *,
    revision: int = 1,
    scopes: tuple[str, ...] = ("understand", "apply"),
    status: str = "accepted",
) -> None:
    connection.execute(
        JobRequirementIdentityRow.__table__.insert().prefix_with("OR IGNORE"),
        {"requirement_id": requirement_id, "job_id": "job_001"},
    )
    for ordinal, scope in enumerate(scopes):
        connection.execute(
            JobRequirementScopeRow.__table__.insert(),
            {
                "requirement_id": requirement_id,
                "requirement_revision": revision,
                "ordinal": ordinal,
                "scope": scope,
            },
        )
    connection.execute(
        JobRequirementEvidenceRefRow.__table__.insert(),
        {
            "requirement_id": requirement_id,
            "requirement_revision": revision,
            "ordinal": 0,
            "evidence_ref_id": JOB_EVIDENCE_REF_ID,
        },
    )
    review = (
        {
            "reviewed_by": "user",
            "reviewed_by_kind": "user",
            "review_reason": "Confirmed against the captured job description.",
            "reviewed_at": NOW,
        }
        if status == "accepted"
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
            "revision": revision,
            "schema_version": 1,
            "job_id": "job_001",
            "job_revision": 1,
            "requirement_text": f"Requirement text for {requirement_id}@{revision}.",
            "importance": "required",
            "capability_id": CAPABILITY_ID,
            "graph_version_id": GRAPH_VERSION_ID,
            "required_scope_count": len(scopes),
            "source_evidence_count": 1,
            "status": status,
            "proposed_by": "agent:extractor",
            "proposed_by_kind": "agent",
            "proposed_at": NOW,
            **review,
        },
    )


def _seed_personal_state(
    connection: Connection,
    *,
    personal_state_id: str = "personal_agents",
    revision: int,
    understand: bool,
    apply: bool,
) -> None:
    connection.execute(
        PersonalCapabilityStateRow.__table__.insert(),
        {
            "personal_state_id": personal_state_id,
            "candidate_id": CANDIDATE_ID,
            "capability_id": CAPABILITY_ID,
            "understand": understand,
            "explain": False,
            "apply": apply,
            "evidence": False,
            "interview_ready": False,
            "revision": revision,
            "schema_version": 1,
            "updated_at": NOW + timedelta(seconds=revision),
            "updated_by": "user",
            "updated_by_kind": "user",
        },
    )


def _seed_binding(
    connection: Connection,
    binding_id: str,
    *,
    personal_state_revision: int,
    scopes: list[str],
    evidence_ref_id: str | None = None,
    project_evidence: tuple[str, int] | None = None,
    authority: str = "document_supported",
    bound_at: datetime = NOW,
) -> None:
    connection.execute(
        CapabilityEvidenceBindingRow.__table__.insert(),
        {
            "binding_id": binding_id,
            "personal_state_id": "personal_agents",
            "personal_state_revision": personal_state_revision,
            "capability_id": CAPABILITY_ID,
            "evidence_ref_id": evidence_ref_id,
            "project_evidence_id": project_evidence[0] if project_evidence else None,
            "project_evidence_revision": project_evidence[1] if project_evidence else None,
            "authority": authority,
            "scopes": scopes,
            "bound_at": bound_at,
            "bound_by": "user",
        },
    )


def _seed_project_evidence(connection: Connection) -> None:
    connection.execute(ProjectIdentityRow.__table__.insert(), {"project_id": "project_001"})
    connection.execute(
        ProjectRecordRow.__table__.insert(),
        {
            "project_id": "project_001",
            "revision": 1,
            "display_name": "Agent Gateway",
            "root_locator": "D:/projects/agent-gateway",
            "schema_version": 1,
            "created_at": NOW,
            "created_by": "user",
        },
    )
    connection.execute(
        ProjectScanScopeRow.__table__.insert(),
        {
            "scope_id": "scope_001",
            "revision": 1,
            "project_id": "project_001",
            "allowed_paths": ["src"],
            "denied_paths": [],
            "follow_symlinks": False,
            "schema_version": 1,
            "created_at": NOW,
            "created_by": "user",
        },
    )
    connection.execute(
        ProjectSourceManifestRow.__table__.insert(),
        {
            "manifest_id": "manifest_001",
            "project_id": "project_001",
            "scan_scope_id": "scope_001",
            "scan_scope_revision": 1,
            "generated_at": NOW,
        },
    )
    connection.execute(
        ProjectSourceEntryRow.__table__.insert(),
        {
            "manifest_id": "manifest_001",
            "relative_path": "src/router.py",
            "sha256": "a" * 64,
            "byte_length": 128,
        },
    )
    connection.execute(
        ProjectEvidenceRow.__table__.insert(),
        {
            "evidence_id": PROJECT_EVIDENCE_ID,
            "revision": 1,
            "project_id": "project_001",
            "summary": "Router emits tracing spans.",
            "claim_kind": "technical_observation",
            "manifest_id": "manifest_001",
            "scanner": "fixture-scanner",
            "scanner_version": "1",
            "authority": "code_verified",
            "freshness": "current",
            "review_status": "accepted",
            "reviewed_by": "project-evidence-policy-v1",
            "reviewed_by_kind": "rule",
            "review_reason": "The source manifest supports this observation.",
            "observed_at": NOW,
            "schema_version": 1,
            "created_at": NOW,
            "created_by": "rule:project-scan",
        },
    )


def _seed_project_capability_state(connection: Connection) -> None:
    connection.execute(
        ProjectCapabilityBasisRow.__table__.insert(),
        {
            "basis_id": "basis_state_001_r1_code",
            "capability_state_id": "state_001",
            "state_revision": 1,
            "basis_kind": "code_evidence",
            "project_evidence_id": PROJECT_EVIDENCE_ID,
            "project_evidence_revision": 1,
            "approval_id": None,
            "approval_revision": None,
        },
    )
    connection.execute(
        ProjectCapabilityStateRow.__table__.insert(),
        {
            "capability_state_id": "state_001",
            "revision": 1,
            "project_id": "project_001",
            "capability_id": CAPABILITY_ID,
            "state": "existing",
            "finalized_at": NOW,
            "schema_version": 1,
            "created_at": NOW,
            "created_by": "user",
        },
    )


def _engine(tmp_path: Path) -> Engine:
    database_url = sqlite_url(tmp_path / "match-resolver.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        seed_job_revision_rows(connection, "job_001", 1)
        _seed_capability(connection)
        _seed_opportunity(connection)
        _seed_requirement(connection, "requirement_001", scopes=("understand", "apply"))
        _seed_requirement(connection, "requirement_002", scopes=("explain",))
        _seed_requirement(connection, "requirement_003", scopes=("understand",))
        _seed_requirement(
            connection, "requirement_003", revision=2, scopes=("understand", "explain")
        )
        _seed_personal_state(connection, revision=1, understand=True, apply=False)
        _seed_personal_state(connection, revision=2, understand=True, apply=True)
        _seed_binding(
            connection,
            "binding_old",
            personal_state_revision=1,
            evidence_ref_id=JOB_EVIDENCE_REF_ID,
            scopes=["understand"],
        )
        _seed_binding(
            connection,
            "binding_001",
            personal_state_revision=2,
            evidence_ref_id=JOB_EVIDENCE_REF_ID,
            scopes=["understand"],
            bound_at=NOW + timedelta(seconds=1),
        )
        _seed_project_evidence(connection)
        _seed_binding(
            connection,
            "binding_002",
            personal_state_revision=2,
            project_evidence=(PROJECT_EVIDENCE_ID, 1),
            scopes=["apply"],
            authority="code_verified",
            bound_at=NOW + timedelta(seconds=2),
        )
        _seed_project_capability_state(connection)
    return engine


def _resolver(engine: Engine) -> MatchInputResolver:
    return MatchInputResolver(
        opportunities=OpportunityRepository(engine),
        jobs=JobRepository(engine),
        capabilities=CapabilityRepository(engine),
        evidence=EvidenceRepository(engine),
        projects=ProjectRepository(engine),
    )


def _service(engine: Engine) -> tuple[MatchRepository, MatchService]:
    repository = MatchRepository(engine)
    return repository, MatchService(CommandService(engine), repository, _resolver(engine))


def _command(assessment_id: str) -> Command:
    return Command(
        command_id=f"command_{assessment_id}",
        command_type="match_assessment.record",
        target=EntityRef(entity_id=assessment_id, kind=EntityKind.MATCH_ASSESSMENT),
        expected_revision=0,
        idempotency_key=f"idempotency-{assessment_id}",
        actor="agent:match",
    )


def _resolve(resolver: MatchInputResolver) -> MatchPolicyInput:
    return resolver.resolve(
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        candidate_id=CANDIDATE_ID,
        requirements=(("requirement_001", 1), ("requirement_002", 1)),
        project_capability_states=(("state_001", 1),),
    )


def test_resolve_reads_every_source_exactly(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_opportunity(connection, revision=2, state="preparing")
        seed_job_revision_rows(connection, "job_001", 2)

    inputs = _resolver(engine).resolve(
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        candidate_id=CANDIDATE_ID,
        requirements=(("requirement_002", 1), ("requirement_001", 1)),
        project_capability_states=(("state_001", 1),),
    )

    assert inputs.opportunity.opportunity.revision == 1
    assert inputs.opportunity.opportunity.state is OpportunityState.QUALIFIED
    assert inputs.job.job_id == "job_001"
    assert inputs.job.revision == 1
    assert [item.requirement_id for item in inputs.requirements] == [
        "requirement_002",
        "requirement_001",
    ]
    assert [node.capability_id for node in inputs.official_capabilities] == [CAPABILITY_ID]
    assert [(item.personal_state_id, item.revision) for item in inputs.personal_states] == [
        ("personal_agents", 2)
    ]
    # The binding on the superseded personal state revision 1 is not a frozen input.
    assert [item.binding_id for item in inputs.evidence_bindings] == ["binding_001", "binding_002"]
    assert [item.evidence_ref_id for item in inputs.evidence_refs] == [JOB_EVIDENCE_REF_ID]
    assert [(item.evidence_id, item.revision) for item in inputs.project_evidence] == [
        (PROJECT_EVIDENCE_ID, 1)
    ]
    assert [
        (item.capability_state_id, item.revision) for item in inputs.project_capability_states
    ] == [("state_001", 1)]


def test_resolve_uses_exact_requirement_revision(tmp_path: Path) -> None:
    resolver = _resolver(_engine(tmp_path))

    first = resolver.resolve(
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        candidate_id=CANDIDATE_ID,
        requirements=(("requirement_003", 1),),
    )
    second = resolver.resolve(
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        candidate_id=CANDIDATE_ID,
        requirements=(("requirement_003", 2),),
    )

    assert first.requirements[0].required_scopes == (CapabilityEvidenceScope.UNDERSTAND,)
    assert second.requirements[0].required_scopes == (
        CapabilityEvidenceScope.UNDERSTAND,
        CapabilityEvidenceScope.EXPLAIN,
    )


def test_resolve_fails_loud_on_missing_opportunity_revision(tmp_path: Path) -> None:
    resolver = _resolver(_engine(tmp_path))
    with pytest.raises(MatchResolutionError, match="Opportunity revision is missing"):
        resolver.resolve(
            opportunity_id="opportunity_001",
            opportunity_revision=99,
            candidate_id=CANDIDATE_ID,
            requirements=(("requirement_001", 1),),
        )


def test_resolve_fails_loud_on_missing_requirement_revision(tmp_path: Path) -> None:
    resolver = _resolver(_engine(tmp_path))
    with pytest.raises(MatchResolutionError, match="JobRequirement revision is missing"):
        resolver.resolve(
            opportunity_id="opportunity_001",
            opportunity_revision=1,
            candidate_id=CANDIDATE_ID,
            requirements=(("requirement_001", 99),),
        )


def test_resolve_fails_loud_on_ambiguous_personal_identity(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_personal_state(
            connection,
            personal_state_id="personal_agents_other",
            revision=1,
            understand=True,
            apply=False,
        )
    with pytest.raises(MatchResolutionError, match="ambiguous personal capability identity"):
        _resolve(_resolver(engine))


def test_resolve_fails_loud_on_dangling_evidence_ref(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_binding(
            connection,
            "binding_dangling",
            personal_state_revision=2,
            evidence_ref_id="evidence_dangling",
            scopes=["evidence"],
            bound_at=NOW + timedelta(seconds=3),
        )
    with pytest.raises(MatchResolutionError, match="dangling EvidenceRef"):
        _resolve(_resolver(engine))


def test_resolve_fails_loud_on_dangling_project_capability_state_ref(tmp_path: Path) -> None:
    resolver = _resolver(_engine(tmp_path))
    with pytest.raises(MatchResolutionError, match="Project Capability State is missing"):
        resolver.resolve(
            opportunity_id="opportunity_001",
            opportunity_revision=1,
            candidate_id=CANDIDATE_ID,
            requirements=(("requirement_001", 1),),
            project_capability_states=(("state_001", 99),),
        )


def _opportunity_detail() -> OpportunityDetail:
    return OpportunityDetail(
        opportunity=Opportunity(
            entity_id="opportunity_001",
            revision=1,
            state=OpportunityState.QUALIFIED,
        ),
        job=JobRef(job_id="job_001", revision=1),
    )


def _job_revision() -> JobRevision:
    return JobRevision(
        job_id="job_001",
        revision=1,
        content_sha256="0" * 64,
        source_evidence_refs=(JOB_EVIDENCE_REF_ID,),
    )


def _accepted_requirement() -> JobRequirement:
    return JobRequirement(
        requirement_id="requirement_001",
        revision=1,
        job=JobRef(job_id="job_001", revision=1),
        requirement_text="Requirement text.",
        importance=JobRequirementImportance.REQUIRED,
        capability_id=CAPABILITY_ID,
        graph_version_id=GRAPH_VERSION_ID,
        required_scopes=(CapabilityEvidenceScope.APPLY,),
        source_evidence_refs=(JOB_EVIDENCE_REF_ID,),
        status=JobRequirementStatus.ACCEPTED,
        proposed_by="agent:extractor",
        proposed_by_kind=ActorKind.AGENT,
        reviewed_by="user",
        reviewed_by_kind=ActorKind.USER,
        review_reason="Confirmed.",
        reviewed_at=NOW,
    )


def _personal_state(revision: int = 2) -> PersonalCapabilityState:
    return PersonalCapabilityState(
        personal_state_id="personal_agents",
        candidate_id=CANDIDATE_ID,
        capability_id=CAPABILITY_ID,
        apply=True,
        revision=revision,
        updated_by="user",
        updated_by_kind=ActorKind.USER,
    )


def _project_binding() -> EvidenceBinding:
    return EvidenceBinding(
        binding_id="binding_project",
        personal_state_id="personal_agents",
        personal_state_revision=2,
        capability_id=CAPABILITY_ID,
        project_evidence_id=PROJECT_EVIDENCE_ID,
        project_evidence_revision=1,
        authority=CapabilityEvidenceAuthority.CODE_VERIFIED,
        scopes=(CapabilityEvidenceScope.APPLY,),
        bound_by="user",
    )


class _StubOpportunities:
    def get_revision(self, opportunity_id: str, revision: int) -> OpportunityDetail:
        return _opportunity_detail()


class _StubJobs:
    def __init__(self, requirement: JobRequirement) -> None:
        self._requirement = requirement

    def get_job(self, job_id: str, revision: int | None = None) -> JobRevision:
        return _job_revision()

    def get_requirement(self, requirement_id: str, revision: int | None = None) -> JobRequirement:
        return self._requirement


class _StubCapabilities:
    def __init__(
        self,
        *,
        nodes: tuple[CapabilityNode, ...] = (),
        states: tuple[PersonalCapabilityState, ...] = (),
        bindings: tuple[EvidenceBinding, ...] = (),
    ) -> None:
        self._nodes = nodes
        self._states = states
        self._bindings = bindings

    def list_nodes(self, graph_version_id: str) -> tuple[CapabilityNode, ...]:
        return tuple(node for node in self._nodes if node.graph_version_id == graph_version_id)

    def list_personal_states(
        self, *, candidate_id: str, capability_id: str
    ) -> tuple[PersonalCapabilityState, ...]:
        return self._states

    def get_personal_state(
        self, *, personal_state_id: str, revision: int
    ) -> PersonalCapabilityState | None:
        for state in self._states:
            if (state.personal_state_id, state.revision) == (personal_state_id, revision):
                return state
        return None

    def list_evidence_bindings(
        self, *, personal_state_id: str, personal_state_revision: int
    ) -> tuple[EvidenceBinding, ...]:
        return self._bindings


class _StubEvidence:
    def get(self, evidence_ref_id: str) -> None:
        return None


class _StubProjects:
    def get_evidence(self, evidence_id: str, revision: int | None = None) -> None:
        return None

    def get_project_capability_state(
        self, capability_state_id: str, revision: int | None = None
    ) -> None:
        return None


def _stub_resolver(
    *,
    nodes: tuple[CapabilityNode, ...] = (),
    states: tuple[PersonalCapabilityState, ...] = (),
    bindings: tuple[EvidenceBinding, ...] = (),
) -> MatchInputResolver:
    return MatchInputResolver(
        opportunities=_StubOpportunities(),  # type: ignore[arg-type]
        jobs=_StubJobs(_accepted_requirement()),  # type: ignore[arg-type]
        capabilities=_StubCapabilities(nodes=nodes, states=states, bindings=bindings),  # type: ignore[arg-type]
        evidence=_StubEvidence(),  # type: ignore[arg-type]
        projects=_StubProjects(),  # type: ignore[arg-type]
    )


def _node() -> CapabilityNode:
    return CapabilityNode(
        capability_id=CAPABILITY_ID,
        canonical_name="Agent Engineering",
        description="Build reliable agent systems.",
        layer=CapabilityLayer.TRACK,
        graph_version_id=GRAPH_VERSION_ID,
    )


def test_resolve_fails_loud_on_missing_official_node() -> None:
    # The schema forbids an accepted requirement without an exact node, so the missing-node
    # path is exercised against stubbed repositories.
    resolver = _stub_resolver(nodes=())
    with pytest.raises(MatchResolutionError, match="official capability node is missing"):
        resolver.resolve(
            opportunity_id="opportunity_001",
            opportunity_revision=1,
            candidate_id=CANDIDATE_ID,
            requirements=(("requirement_001", 1),),
        )


def test_resolve_fails_loud_on_dangling_project_evidence() -> None:
    # A DB trigger enforces exact project evidence revisions on bindings, so the dangling
    # project-evidence path is exercised against stubbed repositories.
    resolver = _stub_resolver(
        nodes=(_node(),),
        states=(_personal_state(),),
        bindings=(_project_binding(),),
    )
    with pytest.raises(MatchResolutionError, match="dangling Project Evidence"):
        resolver.resolve(
            opportunity_id="opportunity_001",
            opportunity_revision=1,
            candidate_id=CANDIDATE_ID,
            requirements=(("requirement_001", 1),),
        )


def _row_counts(engine: Engine, rows: tuple[type, ...]) -> tuple[int, ...]:
    with engine.connect() as connection:
        return tuple(connection.scalar(select(func.count()).select_from(row)) or 0 for row in rows)


def test_assess_resolves_persists_and_never_mutates_canonical_inputs(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _service(engine)
    canonical_rows = (
        PersonalCapabilityStateRow,
        CapabilityEvidenceBindingRow,
        ProjectCapabilityStateRow,
        CapabilityNodeRow,
        SuggestedPriorityRow,
        UserPriorityRow,
    )
    before = _row_counts(engine, canonical_rows)

    recorded = service.assess(
        _command("assessment_001"),
        candidate_id=CANDIDATE_ID,
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        requirements=(("requirement_001", 1), ("requirement_002", 1)),
        project_capability_states=(("state_001", 1),),
    )

    persisted = repository.get_assessment("assessment_001")
    assert persisted is not None
    assert recorded.assessment == persisted
    assert [result.classification for result in persisted.results] == [
        MatchClassification.COVERED,
        MatchClassification.QUICK_TO_STRENGTHEN,
    ]
    assert persisted.header.policy_version == MATCH_POLICY_VERSION
    assert persisted.manifest.personal_states[0].personal_state_id == "personal_agents"
    assert persisted.manifest.personal_states[0].revision == 2
    assert [item.binding_id for item in persisted.manifest.evidence_bindings] == [
        "binding_001",
        "binding_002",
    ]
    assert len(persisted.gaps) == 1
    assert _row_counts(engine, canonical_rows) == before


def test_replay_reproduces_stored_assessment_and_never_writes(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _service(engine)
    service.assess(
        _command("assessment_001"),
        candidate_id=CANDIDATE_ID,
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        requirements=(("requirement_001", 1), ("requirement_002", 1)),
        project_capability_states=(("state_001", 1),),
    )
    written_rows = (
        EntityStateRow,
        EntityRevisionRow,
        DomainEventRow,
        IdempotencyRecordRow,
        MatchAssessmentRow,
        MatchRequirementResultRow,
        MatchGapRow,
    )
    before = _row_counts(engine, written_rows)

    replayed = service.replay("assessment_001")

    assert replayed == repository.get_assessment("assessment_001")
    assert _row_counts(engine, written_rows) == before


def _stored_manifest(engine: Engine, assessment_id: str) -> str:
    with engine.connect() as connection:
        return connection.exec_driver_sql(
            "SELECT manifest FROM match_assessment WHERE assessment_id = ?",
            (assessment_id,),
        ).scalar_one()


def _insert_tampered_assessment(
    engine: Engine,
    tampered_id: str,
    *,
    manifest: str,
    policy_version: str = MATCH_POLICY_VERSION,
) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO match_assessment (assessment_id, opportunity_id, opportunity_revision, "
            "job_id, job_revision, candidate_id, policy_version, manifest, created_at, "
            "created_by) SELECT ?, opportunity_id, opportunity_revision, job_id, job_revision, "
            "candidate_id, ?, ?, created_at, created_by FROM match_assessment "
            "WHERE assessment_id = 'assessment_001'",
            (tampered_id, policy_version, manifest),
        )


def _assessed_engine(tmp_path: Path) -> tuple[Engine, MatchService]:
    engine = _engine(tmp_path)
    _, service = _service(engine)
    service.assess(
        _command("assessment_001"),
        candidate_id=CANDIDATE_ID,
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        requirements=(("requirement_001", 1), ("requirement_002", 1)),
        project_capability_states=(("state_001", 1),),
    )
    return engine, service


def test_replay_fails_loud_when_stored_results_are_tampered(tmp_path: Path) -> None:
    engine, service = _assessed_engine(tmp_path)
    reasons = json.dumps(
        [
            {
                "code": "personal_scopes_satisfied",
                "scopes": ["explain"],
                "binding_ids": [],
                "project_capability_states": [],
            }
        ]
    )
    _insert_tampered_assessment(
        engine, "assessment_tampered", manifest=_stored_manifest(engine, "assessment_001")
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO match_requirement_result (assessment_id, requirement_id, "
            "requirement_revision, capability_id, classification, covered_scopes, "
            "missing_scopes, reasons) SELECT 'assessment_tampered', requirement_id, "
            "requirement_revision, capability_id, classification, covered_scopes, "
            "missing_scopes, reasons FROM match_requirement_result "
            "WHERE assessment_id = 'assessment_001' AND requirement_id = 'requirement_001'"
        )
        connection.exec_driver_sql(
            "INSERT INTO match_requirement_result (assessment_id, requirement_id, "
            "requirement_revision, capability_id, classification, covered_scopes, "
            "missing_scopes, reasons) VALUES ('assessment_tampered', 'requirement_002', 1, "
            "?, 'covered', '[\"explain\"]', '[]', ?)",
            (CAPABILITY_ID, reasons),
        )

    with pytest.raises(MatchReplayError, match="drift from the stored results"):
        service.replay("assessment_tampered")


def test_replay_fails_loud_when_a_manifest_ref_is_missing(tmp_path: Path) -> None:
    engine, service = _assessed_engine(tmp_path)
    manifest = _stored_manifest(engine, "assessment_001")
    assert manifest.count('"revision":2') == 1
    _insert_tampered_assessment(
        engine,
        "assessment_dangling",
        manifest=manifest.replace('"revision":2', '"revision":99'),
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO match_requirement_result (assessment_id, requirement_id, "
            "requirement_revision, capability_id, classification, covered_scopes, "
            "missing_scopes, reasons) SELECT 'assessment_dangling', requirement_id, "
            "requirement_revision, capability_id, classification, covered_scopes, "
            "missing_scopes, reasons FROM match_requirement_result "
            "WHERE assessment_id = 'assessment_001'"
        )
        connection.exec_driver_sql(
            "INSERT INTO match_gap (gap_id, assessment_id, requirement_id, "
            "requirement_revision, capability_id, classification) SELECT 'gap_dangling', "
            "'assessment_dangling', requirement_id, requirement_revision, capability_id, "
            "classification FROM match_gap WHERE assessment_id = 'assessment_001'"
        )

    with pytest.raises(MatchResolutionError, match="Personal Capability State is missing"):
        service.replay("assessment_dangling")


class _StubMatchRepository:
    def __init__(self, record: MatchAssessmentRecord) -> None:
        self._record = record

    def get_assessment(self, assessment_id: str) -> MatchAssessmentRecord:
        return self._record


def test_replay_fails_loud_on_unknown_policy_version(tmp_path: Path) -> None:
    # migration 0009 pins policy_version with a CHECK constraint, so an unknown stored
    # policy version is exercised through a stubbed repository read.
    engine, service = _assessed_engine(tmp_path)
    record = MatchRepository(engine).get_assessment("assessment_001")
    assert record is not None
    forged = record.model_copy(
        update={"header": record.header.model_copy(update={"policy_version": "match-policy-v0"})}
    )
    service = MatchService(
        CommandService(engine),
        _StubMatchRepository(forged),  # type: ignore[arg-type]
        _resolver(engine),
    )

    with pytest.raises(MatchReplayError, match="unsupported match policy version"):
        service.replay("assessment_001")


def test_replay_fails_loud_on_unknown_assessment(tmp_path: Path) -> None:
    _, service = _service(_engine(tmp_path))
    with pytest.raises(MatchReplayError, match="unknown match assessment"):
        service.replay("assessment_missing")
