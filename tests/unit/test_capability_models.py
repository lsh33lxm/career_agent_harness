from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_harness.core.capability import (
    CandidateCapabilityNode,
    CandidateCapabilityStatus,
    CapabilityEvidenceAuthority,
    CapabilityEvidenceScope,
    CapabilityGraphVersion,
    CapabilityLayer,
    CapabilityNode,
    CapabilityRelation,
    CapabilityRelationType,
    EvidenceBinding,
    InvestmentCalculationInputs,
    InvestmentFactors,
    InvestmentRecommendation,
    InvestmentState,
    MarketBinding,
    MarketBindingScope,
    PersonalCapabilityDisplayStatus,
    PersonalCapabilityState,
    promote_candidate_to_official,
    recommend_capability_investment,
)
from career_harness.core.lifecycle import ActorKind


def graph_version(version_id: str = "graph_version_001") -> CapabilityGraphVersion:
    return CapabilityGraphVersion(
        graph_version_id=version_id,
        version_label="1.0",
        change_note="Initial reviewed capability graph.",
        released_by="policy-review",
        released_by_kind=ActorKind.RULE,
    )


def personal_state(**dimensions: bool) -> PersonalCapabilityState:
    return PersonalCapabilityState(
        personal_state_id="personal_state_001",
        candidate_id="candidate_001",
        capability_id="capability_observability",
        revision=1,
        updated_by="user",
        updated_by_kind=ActorKind.USER,
        **dimensions,
    )


def test_official_graph_and_personal_overlay_cannot_overwrite_each_other() -> None:
    original_node = CapabilityNode(
        capability_id="capability_observability",
        canonical_name="Observability",
        description="Logging, metrics, and tracing.",
        layer=CapabilityLayer.COMMON_CORE,
        graph_version_id="graph_version_001",
    )
    overlay = personal_state(understand=True, explain=True, apply=True)
    upgraded_node = CapabilityNode(
        capability_id=original_node.capability_id,
        canonical_name=original_node.canonical_name,
        description="Logging, metrics, tracing, and operational feedback.",
        layer=original_node.layer,
        graph_version_id="graph_version_002",
    )

    assert upgraded_node.capability_id == overlay.capability_id
    assert upgraded_node.graph_version_id == "graph_version_002"
    assert overlay.revision == 1
    assert overlay.display_status is PersonalCapabilityDisplayStatus.APPLIED
    with pytest.raises(ValidationError):
        CapabilityNode(
            capability_id="capability_observability",
            canonical_name="Observability",
            description="Operational feedback.",
            layer=CapabilityLayer.COMMON_CORE,
            graph_version_id="graph_version_002",
            understand=True,
        )
    with pytest.raises(ValidationError):
        PersonalCapabilityState(
            personal_state_id="personal_state_001",
            candidate_id="candidate_001",
            capability_id="capability_observability",
            revision=2,
            updated_by="user",
            updated_by_kind=ActorKind.USER,
            canonical_name="Overwritten name",
        )


def test_official_graph_release_and_relation_enforce_reviewed_structure() -> None:
    with pytest.raises(ValidationError, match="agent cannot release"):
        CapabilityGraphVersion(
            graph_version_id="graph_version_001",
            version_label="1.0",
            change_note="Unreviewed generated graph.",
            released_by="model-run-001",
            released_by_kind=ActorKind.AGENT,
        )
    with pytest.raises(ValidationError, match="same node twice"):
        CapabilityRelation(
            relation_id="relation_001",
            source_capability_id="capability_observability",
            target_capability_id="capability_observability",
            relation_type=CapabilityRelationType.PREREQUISITE,
            graph_version_id="graph_version_001",
        )


def test_pending_candidate_cannot_enter_official_graph() -> None:
    candidate = CandidateCapabilityNode(
        candidate_node_id="candidate_node_001",
        proposed_canonical_name="Agent Evaluation",
        proposed_description="Evaluation methods for agent systems.",
        proposed_layer=CapabilityLayer.TRACK,
        source_evidence_refs=("evidence_001",),
        discovered_by="model-run-001",
    )

    with pytest.raises(ValueError, match="only an accepted candidate"):
        promote_candidate_to_official(
            candidate,
            capability_id="capability_agent_evaluation",
            graph_version=graph_version(),
        )


def test_reviewed_candidate_can_be_promoted_but_agent_cannot_review_it() -> None:
    with pytest.raises(ValidationError, match="agent cannot decide"):
        CandidateCapabilityNode(
            candidate_node_id="candidate_node_001",
            proposed_canonical_name="Agent Evaluation",
            proposed_description="Evaluation methods for agent systems.",
            proposed_layer=CapabilityLayer.TRACK,
            source_evidence_refs=("evidence_001",),
            discovered_by="model-run-001",
            status=CandidateCapabilityStatus.ACCEPTED,
            reviewed_by="same-model-run",
            reviewed_by_kind=ActorKind.AGENT,
            review_reason="Looks useful.",
        )

    candidate = CandidateCapabilityNode(
        candidate_node_id="candidate_node_001",
        proposed_canonical_name="Agent Evaluation",
        proposed_description="Evaluation methods for agent systems.",
        proposed_layer=CapabilityLayer.TRACK,
        source_evidence_refs=("evidence_001",),
        discovered_by="model-run-001",
        status=CandidateCapabilityStatus.ACCEPTED,
        reviewed_by="user",
        reviewed_by_kind=ActorKind.USER,
        review_reason="Distinct and supported by target-market evidence.",
    )

    node = promote_candidate_to_official(
        candidate,
        capability_id="capability_agent_evaluation",
        graph_version=graph_version(),
    )

    assert node.canonical_name == candidate.proposed_canonical_name
    assert node.graph_version_id == "graph_version_001"


@pytest.mark.parametrize(
    ("dimensions", "expected"),
    [
        ({}, PersonalCapabilityDisplayStatus.UNKNOWN),
        ({"understand": True}, PersonalCapabilityDisplayStatus.UNDERSTOOD),
        (
            {"understand": True, "explain": True},
            PersonalCapabilityDisplayStatus.PRACTICED,
        ),
        (
            {"understand": True, "apply": True},
            PersonalCapabilityDisplayStatus.APPLIED,
        ),
        (
            {"understand": True, "explain": True, "apply": True, "evidence": True},
            PersonalCapabilityDisplayStatus.VERIFIED,
        ),
        (
            {
                "understand": True,
                "explain": True,
                "apply": True,
                "evidence": True,
                "interview_ready": True,
            },
            PersonalCapabilityDisplayStatus.RESUME_READY,
        ),
    ],
)
def test_display_status_is_derived_from_dimensions(
    dimensions: dict[str, bool], expected: PersonalCapabilityDisplayStatus
) -> None:
    assert personal_state(**dimensions).display_status is expected


def test_evidence_alone_does_not_claim_personal_mastery() -> None:
    state = personal_state(evidence=True, interview_ready=True)

    assert state.display_status is PersonalCapabilityDisplayStatus.UNKNOWN
    with pytest.raises(ValidationError):
        PersonalCapabilityState(
            personal_state_id="personal_state_001",
            candidate_id="candidate_001",
            capability_id="capability_observability",
            revision=1,
            updated_by="user",
            updated_by_kind=ActorKind.USER,
            display_status=PersonalCapabilityDisplayStatus.RESUME_READY,
        )


def test_agent_cannot_own_personal_capability_state() -> None:
    with pytest.raises(ValidationError, match="agent cannot own"):
        PersonalCapabilityState(
            personal_state_id="personal_state_001",
            candidate_id="candidate_001",
            capability_id="capability_observability",
            revision=1,
            updated_by="model-run-001",
            updated_by_kind=ActorKind.AGENT,
            understand=True,
        )


def test_evidence_binding_requires_exactly_one_source() -> None:
    binding_fields = {
        "binding_id": "binding_001",
        "personal_state_id": "personal_state_001",
        "personal_state_revision": 1,
        "capability_id": "capability_observability",
        "authority": CapabilityEvidenceAuthority.CODE_VERIFIED,
        "scopes": (CapabilityEvidenceScope.APPLY,),
        "bound_by": "project-scanner",
    }

    with pytest.raises(ValidationError, match="exactly one"):
        EvidenceBinding(**binding_fields)
    with pytest.raises(ValidationError, match="exactly one"):
        EvidenceBinding(
            **binding_fields,
            evidence_ref_id="evidence_001",
            project_evidence_id="project_evidence_001",
            project_evidence_revision=1,
        )
    with pytest.raises(ValidationError, match="exact revision"):
        EvidenceBinding(**binding_fields, project_evidence_id="project_evidence_001")
    with pytest.raises(ValidationError, match="exact revision"):
        EvidenceBinding(
            **binding_fields,
            evidence_ref_id="evidence_001",
            project_evidence_revision=1,
        )

    binding = EvidenceBinding(
        **binding_fields,
        project_evidence_id="project_evidence_001",
        project_evidence_revision=1,
    )
    assert binding.project_evidence_id == "project_evidence_001"
    assert binding.project_evidence_revision == 1


def test_market_binding_distinguishes_target_and_broad_sources() -> None:
    with pytest.raises(ValidationError, match="requires an opportunity"):
        MarketBinding(
            binding_id="market_binding_001",
            capability_id="capability_observability",
            market_scope=MarketBindingScope.TARGET,
            source_evidence_refs=("evidence_001",),
        )
    with pytest.raises(ValidationError, match="cannot carry target"):
        MarketBinding(
            binding_id="market_binding_002",
            capability_id="capability_observability",
            market_scope=MarketBindingScope.BROAD,
            source_evidence_refs=("evidence_002",),
            opportunity_id="opportunity_001",
        )

    target = MarketBinding(
        binding_id="market_binding_003",
        capability_id="capability_observability",
        market_scope=MarketBindingScope.TARGET,
        source_evidence_refs=("evidence_003",),
        job_requirement_id="job_requirement_001",
    )
    broad = MarketBinding(
        binding_id="market_binding_004",
        capability_id="capability_observability",
        market_scope=MarketBindingScope.BROAD,
        source_evidence_refs=("evidence_004",),
    )
    assert target.market_scope is MarketBindingScope.TARGET
    assert broad.market_scope is MarketBindingScope.BROAD


def test_investment_recommendation_preserves_explainable_factors_and_inputs() -> None:
    factors = InvestmentFactors(
        target_market_demand=0.9,
        opportunity_importance=0.8,
        cross_opportunity_reuse=0.9,
        project_proximity=0.8,
        evidence_feasibility=0.9,
        personal_interest=0.8,
        learning_cost=0.2,
    )
    inputs = InvestmentCalculationInputs(
        graph_version_id="graph_version_001",
        personal_state_id="personal_state_001",
        personal_state_revision=3,
        market_binding_ids=("market_binding_001", "market_binding_002"),
        opportunity_ids=("opportunity_001",),
    )

    investment = recommend_capability_investment(
        investment_state_id="investment_state_001",
        candidate_id="candidate_001",
        capability_id="capability_observability",
        factors=factors,
        calculation_inputs=inputs,
    )

    assert investment.recommendation is InvestmentRecommendation.HIGH
    assert investment.factors == factors
    assert investment.calculation_inputs == inputs
    assert "Target market demand is strong." in investment.reasons
    assert "The estimated learning or project cost is manageable." in investment.reasons
    assert not hasattr(investment, "user_priority")


def test_investment_result_cannot_disagree_with_its_factors() -> None:
    factors = InvestmentFactors(
        target_market_demand=0.1,
        opportunity_importance=0.1,
        cross_opportunity_reuse=0.1,
        project_proximity=0.1,
        evidence_feasibility=0.1,
        personal_interest=0.1,
        learning_cost=0.9,
    )
    inputs = InvestmentCalculationInputs(
        graph_version_id="graph_version_001",
        personal_state_id="personal_state_001",
        personal_state_revision=1,
        market_binding_ids=("market_binding_001",),
    )

    with pytest.raises(ValidationError, match="recommendation does not match"):
        InvestmentState(
            investment_state_id="investment_state_001",
            candidate_id="candidate_001",
            capability_id="capability_observability",
            factors=factors,
            recommendation=InvestmentRecommendation.HIGH,
            score=0.0,
            reasons=("The estimated learning or project cost is high.",),
            calculation_inputs=inputs,
        )
