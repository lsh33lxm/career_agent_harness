from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from career_harness.core.capability import (
    CapabilityGraphVersion,
    CapabilityLayer,
    CapabilityNode,
    CapabilityRelation,
    CapabilityRelationType,
    EvidenceBinding,
    InvestmentFactors,
    MarketBinding,
    MarketBindingScope,
    PersonalCapabilityState,
    recommend_capability_investment,
)
from career_harness.core.capability_workspace import (
    CapabilityProjection,
    CapabilityWorkspace,
    WorkspaceInputKind,
    WorkspaceInputRef,
    build_capability_workspace,
)
from career_harness.core.lifecycle import ActorKind

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def _graph() -> CapabilityGraphVersion:
    return CapabilityGraphVersion(
        graph_version_id="graph_001",
        version_label="1.0",
        change_note="Initial graph.",
        released_at=NOW,
        released_by="user",
        released_by_kind=ActorKind.USER,
    )


def _node(capability_id: str, name: str, layer: CapabilityLayer) -> CapabilityNode:
    return CapabilityNode(
        capability_id=capability_id,
        canonical_name=name,
        description=f"{name} description",
        layer=layer,
        graph_version_id="graph_001",
    )


def _state(state_id: str, revision: int, updated_at: datetime) -> PersonalCapabilityState:
    return PersonalCapabilityState(
        personal_state_id=state_id,
        candidate_id="candidate_001",
        capability_id="capability_alpha",
        understand=True,
        explain=revision > 1,
        revision=revision,
        updated_at=updated_at,
        updated_by="user",
        updated_by_kind=ActorKind.USER,
    )


def _investment(*, candidate_id: str = "candidate_001", capability_id: str = "capability_alpha"):
    return recommend_capability_investment(
        investment_state_id=f"investment_{candidate_id}",
        candidate_id=candidate_id,
        capability_id=capability_id,
        factors=InvestmentFactors(
            target_market_demand=0.8,
            opportunity_importance=0.8,
            cross_opportunity_reuse=0.8,
            project_proximity=0.8,
            evidence_feasibility=0.8,
            personal_interest=0.8,
            learning_cost=0.2,
        ),
        calculation_inputs={
            "graph_version_id": "graph_001",
            "personal_state_id": "state_latest",
            "personal_state_revision": 2,
            "market_binding_ids": ("market_target",),
        },
    )


def _graph_input_ref() -> WorkspaceInputRef:
    return WorkspaceInputRef(
        kind=WorkspaceInputKind.GRAPH_VERSION,
        entity_id="graph_001",
    )


def test_empty_workspace_is_explicit_and_does_not_fabricate_graph_data() -> None:
    workspace = build_capability_workspace(candidate_id="candidate_001", graph_version=None)

    assert workspace.graph_version is None
    assert workspace.nodes == ()
    assert workspace.projections == ()
    assert workspace.input_revisions == ()


def test_workspace_is_deterministic_and_keeps_authority_layers_separate() -> None:
    graph = _graph()
    alpha = _node("capability_alpha", "Alpha", CapabilityLayer.COMMON_CORE)
    beta = _node("capability_beta", "Beta", CapabilityLayer.TRACK)
    older = _state("state_old", 1, NOW - timedelta(days=1))
    latest = _state("state_latest", 2, NOW)
    stale_binding = EvidenceBinding(
        binding_id="evidence_stale",
        personal_state_id=older.personal_state_id,
        personal_state_revision=older.revision,
        capability_id=alpha.capability_id,
        evidence_ref_id="evidence_ref_old",
        authority="document_supported",
        scopes=("understand",),
        bound_by="user",
    )
    latest_binding = EvidenceBinding(
        binding_id="evidence_latest",
        personal_state_id=latest.personal_state_id,
        personal_state_revision=latest.revision,
        capability_id=alpha.capability_id,
        evidence_ref_id="evidence_ref_latest",
        authority="user_confirmed",
        scopes=("explain",),
        bound_by="user",
    )
    target = MarketBinding(
        binding_id="market_target",
        capability_id=alpha.capability_id,
        market_scope=MarketBindingScope.TARGET,
        source_evidence_refs=("target_source",),
        opportunity_id="opportunity_001",
    )
    broad = MarketBinding(
        binding_id="market_broad",
        capability_id=alpha.capability_id,
        market_scope=MarketBindingScope.BROAD,
        source_evidence_refs=("broad_source",),
    )
    relation = CapabilityRelation(
        relation_id="relation_001",
        source_capability_id=alpha.capability_id,
        target_capability_id=beta.capability_id,
        relation_type=CapabilityRelationType.PREREQUISITE,
        graph_version_id=graph.graph_version_id,
    )

    workspace = build_capability_workspace(
        candidate_id="candidate_001",
        graph_version=graph,
        nodes=(beta, alpha),
        relations=(relation,),
        personal_states=(older, latest),
        evidence_bindings=(stale_binding, latest_binding),
        market_bindings=(broad, target),
    )
    reversed_workspace = build_capability_workspace(
        candidate_id="candidate_001",
        graph_version=graph,
        nodes=(alpha, beta),
        relations=(relation,),
        personal_states=(latest, older),
        evidence_bindings=(latest_binding, stale_binding),
        market_bindings=(target, broad),
    )

    assert workspace == reversed_workspace
    assert [node.capability_id for node in workspace.nodes] == [
        "capability_alpha",
        "capability_beta",
    ]
    projection = workspace.projections[0]
    assert projection.personal_state == latest
    assert projection.evidence_bindings == (latest_binding,)
    assert projection.target_market_bindings == (target,)
    assert projection.broad_market_bindings == (broad,)
    assert workspace.projections[1].personal_state is None
    assert {(ref.kind, ref.entity_id, ref.revision) for ref in workspace.input_revisions} == {
        (WorkspaceInputKind.GRAPH_VERSION, "graph_001", None),
        (WorkspaceInputKind.PERSONAL_STATE, "state_latest", 2),
        (WorkspaceInputKind.EVIDENCE_BINDING, "evidence_latest", None),
        (WorkspaceInputKind.TARGET_MARKET_BINDING, "market_target", None),
        (WorkspaceInputKind.BROAD_MARKET_BINDING, "market_broad", None),
    }


def test_workspace_never_borrows_another_candidate_overlay() -> None:
    other_state = _state("state_other", 1, NOW).model_copy(
        update={"candidate_id": "candidate_other"}
    )
    workspace = build_capability_workspace(
        candidate_id="candidate_001",
        graph_version=_graph(),
        nodes=(_node("capability_alpha", "Alpha", CapabilityLayer.COMMON_CORE),),
        personal_states=(other_state,),
    )

    assert workspace.projections[0].personal_state is None
    assert [ref.kind for ref in workspace.input_revisions] == [WorkspaceInputKind.GRAPH_VERSION]


def test_projection_rejects_malformed_or_duplicate_nested_refs() -> None:
    state = _state("state_latest", 2, NOW)
    evidence = EvidenceBinding(
        binding_id="evidence_latest",
        personal_state_id=state.personal_state_id,
        personal_state_revision=state.revision,
        capability_id="capability_alpha",
        evidence_ref_id="evidence_ref_latest",
        authority="user_confirmed",
        scopes=("evidence",),
        bound_by="user",
    )
    target = MarketBinding(
        binding_id="market_target",
        capability_id="capability_alpha",
        market_scope=MarketBindingScope.TARGET,
        source_evidence_refs=("target_source",),
        opportunity_id="opportunity_001",
    )
    broad = MarketBinding(
        binding_id="market_broad",
        capability_id="capability_alpha",
        market_scope=MarketBindingScope.BROAD,
        source_evidence_refs=("broad_source",),
    )

    with pytest.raises(ValidationError, match="personal state capability"):
        CapabilityProjection(
            capability_id="capability_beta",
            personal_state=state,
        )
    with pytest.raises(ValidationError, match="pin the projected personal state revision"):
        CapabilityProjection(
            capability_id="capability_alpha",
            personal_state=state,
            evidence_bindings=(evidence.model_copy(update={"personal_state_revision": 1}),),
        )
    with pytest.raises(ValidationError, match="evidence binding capability"):
        CapabilityProjection(
            capability_id="capability_alpha",
            personal_state=state,
            evidence_bindings=(evidence.model_copy(update={"capability_id": "capability_beta"}),),
        )
    with pytest.raises(ValidationError, match="evidence binding ids must be unique"):
        CapabilityProjection(
            capability_id="capability_alpha",
            personal_state=state,
            evidence_bindings=(evidence, evidence),
        )
    with pytest.raises(ValidationError, match="target market binding"):
        CapabilityProjection(
            capability_id="capability_alpha",
            target_market_bindings=(broad,),
        )
    with pytest.raises(ValidationError, match="target market binding"):
        CapabilityProjection(
            capability_id="capability_alpha",
            target_market_bindings=(
                target.model_copy(update={"capability_id": "capability_beta"}),
            ),
        )
    with pytest.raises(ValidationError, match="broad market binding"):
        CapabilityProjection(
            capability_id="capability_alpha",
            broad_market_bindings=(broad.model_copy(update={"capability_id": "capability_beta"}),),
        )
    with pytest.raises(ValidationError, match="investment state capability"):
        CapabilityProjection(
            capability_id="capability_alpha",
            investment_state=_investment(capability_id="capability_beta"),
        )
    with pytest.raises(ValidationError, match="both target and broad"):
        CapabilityProjection(
            capability_id="capability_alpha",
            target_market_bindings=(target,),
            broad_market_bindings=(broad.model_copy(update={"binding_id": target.binding_id}),),
        )


def test_workspace_rejects_duplicate_mismatched_and_dangling_graph_content() -> None:
    graph = _graph()
    alpha = _node("capability_alpha", "Alpha", CapabilityLayer.COMMON_CORE)
    beta = _node("capability_beta", "Beta", CapabilityLayer.TRACK)
    alpha_projection = CapabilityProjection(capability_id=alpha.capability_id)
    beta_projection = CapabilityProjection(capability_id=beta.capability_id)
    relation = CapabilityRelation(
        relation_id="relation_001",
        source_capability_id=alpha.capability_id,
        target_capability_id=beta.capability_id,
        relation_type=CapabilityRelationType.PREREQUISITE,
        graph_version_id=graph.graph_version_id,
    )

    with pytest.raises(ValidationError, match="node ids must be unique"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha, alpha),
            projections=(alpha_projection, alpha_projection),
            input_revisions=(_graph_input_ref(),),
        )
    with pytest.raises(ValidationError, match="projection capability ids must be unique"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha, beta),
            projections=(alpha_projection, alpha_projection),
            input_revisions=(_graph_input_ref(),),
        )
    with pytest.raises(ValidationError, match="relation ids must be unique"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha, beta),
            relations=(relation, relation),
            projections=(alpha_projection, beta_projection),
            input_revisions=(_graph_input_ref(),),
        )
    with pytest.raises(ValidationError, match="relation edges must be unique"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha, beta),
            relations=(relation, relation.model_copy(update={"relation_id": "relation_002"})),
            projections=(alpha_projection, beta_projection),
            input_revisions=(_graph_input_ref(),),
        )
    with pytest.raises(ValidationError, match="outside the graph"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha, beta),
            relations=(relation.model_copy(update={"target_capability_id": "capability_missing"}),),
            projections=(alpha_projection, beta_projection),
            input_revisions=(_graph_input_ref(),),
        )
    with pytest.raises(ValidationError, match="nodes must belong"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha.model_copy(update={"graph_version_id": "graph_other"}),),
            projections=(alpha_projection,),
            input_revisions=(_graph_input_ref(),),
        )
    with pytest.raises(ValidationError, match="relations must belong"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha, beta),
            relations=(relation.model_copy(update={"graph_version_id": "graph_other"}),),
            projections=(alpha_projection, beta_projection),
            input_revisions=(_graph_input_ref(),),
        )


def test_workspace_rejects_candidate_leaks_and_non_exact_input_refs() -> None:
    graph = _graph()
    alpha = _node("capability_alpha", "Alpha", CapabilityLayer.COMMON_CORE)
    state = _state("state_latest", 2, NOW)
    valid = build_capability_workspace(
        candidate_id="candidate_001",
        graph_version=graph,
        nodes=(alpha,),
        personal_states=(state,),
        investment_states=(_investment(),),
    )

    other_state_projection = CapabilityProjection(
        capability_id=alpha.capability_id,
        personal_state=state.model_copy(update={"candidate_id": "candidate_other"}),
    )
    with pytest.raises(ValidationError, match="personal state candidate"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha,),
            projections=(other_state_projection,),
            input_revisions=valid.input_revisions,
        )

    other_investment_projection = CapabilityProjection(
        capability_id=alpha.capability_id,
        investment_state=_investment(candidate_id="candidate_other"),
    )
    with pytest.raises(ValidationError, match="investment state candidate"):
        CapabilityWorkspace(
            candidate_id="candidate_001",
            graph_version=graph,
            nodes=(alpha,),
            projections=(other_investment_projection,),
            input_revisions=valid.input_revisions,
        )

    with pytest.raises(ValidationError, match="exactly match"):
        CapabilityWorkspace(
            candidate_id=valid.candidate_id,
            graph_version=valid.graph_version,
            nodes=valid.nodes,
            relations=valid.relations,
            projections=valid.projections,
            input_revisions=valid.input_revisions[:-1],
        )
    with pytest.raises(ValidationError, match="input revision refs must be unique"):
        CapabilityWorkspace(
            candidate_id=valid.candidate_id,
            graph_version=valid.graph_version,
            nodes=valid.nodes,
            relations=valid.relations,
            projections=valid.projections,
            input_revisions=valid.input_revisions + (valid.input_revisions[0],),
        )
    with pytest.raises(ValidationError, match="exactly match"):
        CapabilityWorkspace(
            candidate_id=valid.candidate_id,
            graph_version=valid.graph_version,
            nodes=valid.nodes,
            relations=valid.relations,
            projections=valid.projections,
            input_revisions=valid.input_revisions
            + (
                WorkspaceInputRef(
                    kind=WorkspaceInputKind.EVIDENCE_BINDING,
                    entity_id="evidence_extra",
                ),
            ),
        )
