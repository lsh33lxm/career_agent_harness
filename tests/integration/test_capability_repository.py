from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import Connection

from career_harness.core.capability import (
    CandidateCapabilityStatus,
    InvestmentFactors,
    InvestmentRecommendation,
    MarketBindingScope,
    PersonalCapabilityDisplayStatus,
    recommend_capability_investment,
)
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CandidateCapabilityNodeRow,
    CapabilityEvidenceBindingRow,
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityInvestmentStateRow,
    CapabilityMarketBindingRow,
    CapabilityNodeRow,
    CapabilityRelationRow,
    OpportunityRecordRow,
    PersonalCapabilityStateRow,
    ProjectEvidenceRow,
    ProjectIdentityRow,
    ProjectRecordRow,
    ProjectScanScopeRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from tests.support.job_data import seed_job_revision_rows


def _repository(tmp_path: Path) -> tuple[CapabilityRepository, Connection]:
    database_url = sqlite_url(tmp_path / "capability-repository.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    return CapabilityRepository(engine), engine.connect()


def _insert_project_evidence(connection: Connection, now: datetime) -> None:
    connection.execute(ProjectIdentityRow.__table__.insert(), {"project_id": "project_001"})
    connection.execute(
        ProjectRecordRow.__table__.insert(),
        {
            "project_id": "project_001",
            "revision": 1,
            "display_name": "Agent Gateway",
            "root_locator": "D:/projects/agent-gateway",
            "schema_version": 1,
            "created_at": now,
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
            "denied_paths": ["src/secrets"],
            "follow_symlinks": False,
            "schema_version": 1,
            "created_at": now,
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
            "generated_at": now,
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
            "evidence_id": "project_evidence_001",
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
            "observed_at": now,
            "schema_version": 1,
            "created_at": now,
            "created_by": "rule:project-scan",
        },
    )


def _seed_capability_data(connection: Connection) -> None:
    now = datetime.now(UTC)
    earlier = now - timedelta(days=1)
    seed_job_revision_rows(connection, "job_001", 1)
    connection.execute(
        CapabilityIdentityRow.__table__.insert(),
        [
            {"capability_id": "capability_a"},
            {"capability_id": "capability_b"},
        ],
    )
    connection.execute(
        CapabilityNodeRow.__table__.insert(),
        [
            {
                "capability_id": "capability_a",
                "graph_version_id": "graph_version_001",
                "canonical_name": "Alpha v1",
                "description": "First graph version.",
                "layer": "common_core",
                "lifecycle_status": "active",
            },
            {
                "capability_id": "capability_b",
                "graph_version_id": "graph_version_002",
                "canonical_name": "Beta",
                "description": "Ordered before no other node.",
                "layer": "track",
                "lifecycle_status": "active",
            },
            {
                "capability_id": "capability_a",
                "graph_version_id": "graph_version_002",
                "canonical_name": "Alpha v2",
                "description": "Second graph version.",
                "layer": "common_core",
                "lifecycle_status": "active",
            },
        ],
    )
    connection.execute(
        CapabilityRelationRow.__table__.insert(),
        {
            "relation_id": "relation_001",
            "source_capability_id": "capability_a",
            "target_capability_id": "capability_b",
            "relation_type": "prerequisite",
            "graph_version_id": "graph_version_002",
        },
    )
    connection.execute(
        CapabilityGraphVersionRow.__table__.insert(),
        [
            {
                "graph_version_id": "graph_version_001",
                "version_label": "1.0",
                "change_note": "Initial graph.",
                "released_at": earlier,
                "released_by": "policy",
                "released_by_kind": "rule",
            },
            {
                "graph_version_id": "graph_version_002",
                "version_label": "1.1",
                "parent_graph_version_id": "graph_version_001",
                "change_note": "Add Beta.",
                "released_at": now,
                "released_by": "user",
                "released_by_kind": "user",
            },
        ],
    )
    connection.execute(
        CandidateCapabilityNodeRow.__table__.insert(),
        [
            {
                "candidate_node_id": "candidate_node_b",
                "proposed_canonical_name": "Inbox B",
                "proposed_description": "Pending candidate B.",
                "proposed_layer": "track",
                "source_evidence_refs": ["evidence_b"],
                "discovered_by": "model-run-001",
                "status": "pending",
            },
            {
                "candidate_node_id": "candidate_node_a",
                "proposed_canonical_name": "Inbox A",
                "proposed_description": "Pending candidate A.",
                "proposed_layer": "track",
                "source_evidence_refs": ["evidence_a"],
                "discovered_by": "model-run-001",
                "status": "pending",
            },
        ],
    )
    connection.execute(
        CandidateCapabilityNodeRow.__table__.insert(),
        {
            "candidate_node_id": "candidate_node_ignored",
            "proposed_canonical_name": "Ignored",
            "proposed_description": "Reviewed duplicate.",
            "proposed_layer": "track",
            "source_evidence_refs": ["evidence_c"],
            "discovered_by": "model-run-001",
            "status": "ignored",
            "reviewed_by": "user",
            "reviewed_by_kind": "user",
            "review_reason": "Duplicate concept.",
        },
    )
    connection.execute(
        PersonalCapabilityStateRow.__table__.insert(),
        [
            {
                "personal_state_id": "personal_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": True,
                "apply": False,
                "evidence": False,
                "interview_ready": False,
                "revision": 1,
                "schema_version": 1,
                "updated_at": earlier,
                "updated_by": "user",
                "updated_by_kind": "user",
            },
            {
                "personal_state_id": "personal_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": True,
                "apply": True,
                "evidence": True,
                "interview_ready": False,
                "revision": 2,
                "schema_version": 1,
                "updated_at": now,
                "updated_by": "policy",
                "updated_by_kind": "rule",
            },
            {
                "personal_state_id": "personal_state_002",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": False,
                "apply": False,
                "evidence": False,
                "interview_ready": False,
                "revision": 1,
                "schema_version": 1,
                "updated_at": earlier,
                "updated_by": "user",
                "updated_by_kind": "user",
            },
            {
                "personal_state_id": "personal_state_002",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": True,
                "apply": False,
                "evidence": False,
                "interview_ready": False,
                "revision": 3,
                "schema_version": 1,
                "updated_at": now,
                "updated_by": "user",
                "updated_by_kind": "user",
            },
        ],
    )
    _insert_project_evidence(connection, now)
    connection.execute(
        CapabilityEvidenceBindingRow.__table__.insert(),
        {
            "binding_id": "binding_evidence_ref",
            "personal_state_id": "personal_state_001",
            "personal_state_revision": 1,
            "capability_id": "capability_a",
            "evidence_ref_id": "evidence_ref_001",
            "authority": "document_supported",
            "scopes": ["understand"],
            "bound_at": earlier,
            "bound_by": "user",
        },
    )
    connection.execute(
        CapabilityEvidenceBindingRow.__table__.insert(),
        {
            "binding_id": "binding_project",
            "personal_state_id": "personal_state_001",
            "personal_state_revision": 2,
            "capability_id": "capability_a",
            "project_evidence_id": "project_evidence_001",
            "project_evidence_revision": 1,
            "authority": "code_verified",
            "scopes": ["apply", "evidence"],
            "bound_at": now,
            "bound_by": "rule:project-evidence",
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
        CapabilityMarketBindingRow.__table__.insert(),
        [
            {
                "binding_id": "market_target_b",
                "capability_id": "capability_a",
                "market_scope": "target",
                "source_evidence_refs": ["evidence_target_b"],
                "opportunity_id": "opportunity_001",
                "job_requirement_id": None,
                "observed_at": now,
            },
            {
                "binding_id": "market_target_a",
                "capability_id": "capability_a",
                "market_scope": "target",
                "source_evidence_refs": ["evidence_target_a"],
                "opportunity_id": None,
                "job_requirement_id": "requirement_001",
                "observed_at": now,
            },
            {
                "binding_id": "market_broad",
                "capability_id": "capability_a",
                "market_scope": "broad",
                "source_evidence_refs": ["evidence_broad"],
                "opportunity_id": None,
                "job_requirement_id": None,
                "observed_at": earlier,
            },
        ],
    )
    factors = InvestmentFactors(
        target_market_demand=0.9,
        opportunity_importance=0.8,
        cross_opportunity_reuse=0.9,
        project_proximity=0.8,
        evidence_feasibility=0.9,
        personal_interest=0.8,
        learning_cost=0.2,
    )
    investment = recommend_capability_investment(
        investment_state_id="investment_001",
        candidate_id="candidate_001",
        capability_id="capability_a",
        factors=factors,
        calculation_inputs={
            "graph_version_id": "graph_version_002",
            "personal_state_id": "personal_state_001",
            "personal_state_revision": 2,
            "market_binding_ids": ("market_target_a", "market_target_b"),
            "opportunity_ids": ("opportunity_001",),
        },
    )
    connection.execute(
        CapabilityInvestmentStateRow.__table__.insert(),
        [
            {
                "investment_state_id": investment.investment_state_id,
                "candidate_id": investment.candidate_id,
                "capability_id": investment.capability_id,
                **investment.factors.model_dump(),
                "recommendation": investment.recommendation.value,
                "score": investment.score,
                "reasons": list(investment.reasons),
                "graph_version_id": investment.calculation_inputs.graph_version_id,
                "personal_state_id": investment.calculation_inputs.personal_state_id,
                "personal_state_revision": investment.calculation_inputs.personal_state_revision,
                "market_binding_ids": list(investment.calculation_inputs.market_binding_ids),
                "opportunity_ids": list(investment.calculation_inputs.opportunity_ids),
                "rule_version": investment.rule_version,
                "calculated_at": now,
            },
            {
                "investment_state_id": "investment_older",
                "candidate_id": investment.candidate_id,
                "capability_id": investment.capability_id,
                **investment.factors.model_dump(),
                "recommendation": investment.recommendation.value,
                "score": investment.score,
                "reasons": list(investment.reasons),
                "graph_version_id": investment.calculation_inputs.graph_version_id,
                "personal_state_id": "personal_state_001",
                "personal_state_revision": 1,
                "market_binding_ids": list(investment.calculation_inputs.market_binding_ids),
                "opportunity_ids": list(investment.calculation_inputs.opportunity_ids),
                "rule_version": investment.rule_version,
                "calculated_at": earlier,
            },
        ],
    )


def test_empty_repository_returns_none_and_empty_tuples(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    connection.close()

    assert repository.get_graph_version("graph_missing") is None
    assert repository.get_latest_graph_version() is None
    assert repository.get_official_graph("graph_missing") is None
    assert repository.get_latest_official_graph() is None
    assert repository.list_nodes("graph_missing") == ()
    assert repository.list_relations("graph_missing") == ()
    assert repository.list_candidate_inbox() == ()
    assert repository.get_latest_personal_state(personal_state_id="state_missing") is None
    assert repository.list_personal_states(
        candidate_id="candidate_001", capability_id="capability_a"
    ) == ()
    assert repository.list_evidence_bindings(
        personal_state_id="state_missing", personal_state_revision=1
    ) == ()
    assert repository.list_market_bindings(
        capability_id="capability_a", market_scope=MarketBindingScope.TARGET
    ) == ()
    assert repository.get_investment_state("investment_missing") is None


def test_graph_exact_latest_and_version_isolation(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    with connection.begin():
        _seed_capability_data(connection)
    connection.close()

    exact = repository.get_official_graph("graph_version_001")
    latest = repository.get_latest_official_graph()

    assert exact is not None
    assert exact.graph_version.graph_version_id == "graph_version_001"
    assert [(node.capability_id, node.canonical_name) for node in exact.nodes] == [
        ("capability_a", "Alpha v1")
    ]
    assert exact.relations == ()
    assert latest is not None
    assert latest.graph_version.graph_version_id == "graph_version_002"
    assert [node.capability_id for node in latest.nodes] == ["capability_a", "capability_b"]
    assert [relation.relation_id for relation in latest.relations] == ["relation_001"]
    assert repository.get_latest_graph_version() == latest.graph_version


def test_candidate_status_and_deterministic_ordering(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    with connection.begin():
        _seed_capability_data(connection)
    connection.close()

    inbox = repository.list_candidate_inbox()
    ignored = repository.list_candidates(CandidateCapabilityStatus.IGNORED)

    assert [candidate.candidate_node_id for candidate in inbox] == [
        "candidate_node_a",
        "candidate_node_b",
    ]
    assert [candidate.candidate_node_id for candidate in ignored] == [
        "candidate_node_ignored"
    ]


def test_personal_state_exact_latest_and_evidence_revision(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    with connection.begin():
        _seed_capability_data(connection)
    connection.close()

    exact = repository.get_personal_state(
        personal_state_id="personal_state_001", revision=1
    )
    exact_second_identity = repository.get_personal_state(
        personal_state_id="personal_state_002", revision=1
    )
    latest_first_identity = repository.get_latest_personal_state(
        personal_state_id="personal_state_001"
    )
    latest_second_identity = repository.get_latest_personal_state(
        personal_state_id="personal_state_002"
    )
    discovered = repository.list_personal_states(
        candidate_id="candidate_001", capability_id="capability_a"
    )
    revision_one_bindings = repository.list_evidence_bindings(
        personal_state_id="personal_state_001", personal_state_revision=1
    )
    revision_two_bindings = repository.list_evidence_bindings(
        personal_state_id="personal_state_001", personal_state_revision=2
    )

    assert exact is not None
    assert exact.personal_state_id == "personal_state_001"
    assert exact.revision == 1
    assert exact.display_status is PersonalCapabilityDisplayStatus.PRACTICED
    assert exact_second_identity is not None
    assert exact_second_identity.personal_state_id == "personal_state_002"
    assert exact_second_identity.revision == 1
    assert exact_second_identity.display_status is PersonalCapabilityDisplayStatus.UNDERSTOOD
    assert latest_first_identity is not None
    assert latest_first_identity.personal_state_id == "personal_state_001"
    assert latest_first_identity.revision == 2
    assert latest_first_identity.display_status is PersonalCapabilityDisplayStatus.VERIFIED
    assert latest_second_identity is not None
    assert latest_second_identity.personal_state_id == "personal_state_002"
    assert latest_second_identity.revision == 3
    assert latest_second_identity.display_status is PersonalCapabilityDisplayStatus.PRACTICED
    assert [(state.personal_state_id, state.revision) for state in discovered] == [
        ("personal_state_001", 1),
        ("personal_state_001", 2),
        ("personal_state_002", 1),
        ("personal_state_002", 3),
    ]
    assert [item.binding_id for item in revision_one_bindings] == ["binding_evidence_ref"]
    assert revision_one_bindings[0].project_evidence_revision is None
    assert [item.binding_id for item in revision_two_bindings] == ["binding_project"]
    assert revision_two_bindings[0].project_evidence_revision == 1
    assert revision_two_bindings[0].personal_state_revision == 2


def test_market_layers_and_investment_inputs_remain_separate(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    with connection.begin():
        _seed_capability_data(connection)
    connection.close()

    target = repository.list_market_bindings(
        capability_id="capability_a", market_scope=MarketBindingScope.TARGET
    )
    broad = repository.list_market_bindings(
        capability_id="capability_a", market_scope=MarketBindingScope.BROAD
    )
    investment = repository.get_investment_state("investment_001")
    investments = repository.list_investment_states(candidate_id="candidate_001")
    capability_investments = repository.list_investment_states(
        candidate_id="candidate_001", capability_id="capability_a"
    )

    assert [binding.binding_id for binding in target] == ["market_target_a", "market_target_b"]
    assert [binding.binding_id for binding in broad] == ["market_broad"]
    assert all(binding.market_scope is MarketBindingScope.TARGET for binding in target)
    assert all(binding.market_scope is MarketBindingScope.BROAD for binding in broad)
    assert investment is not None
    assert investment.recommendation is InvestmentRecommendation.HIGH
    assert investment.calculation_inputs.graph_version_id == "graph_version_002"
    assert investment.calculation_inputs.personal_state_revision == 2
    assert investment.calculation_inputs.market_binding_ids == (
        "market_target_a",
        "market_target_b",
    )
    assert investment.calculation_inputs.opportunity_ids == ("opportunity_001",)
    assert not hasattr(investment, "user_priority")
    assert [state.investment_state_id for state in investments] == [
        "investment_001",
        "investment_older",
    ]
    assert capability_investments == investments
    assert repository.list_investment_states(candidate_id="candidate_missing") == ()
