from __future__ import annotations

from datetime import UTC, datetime, timedelta

from career_harness.core.capability import (
    CapabilityGraphVersion,
    CapabilityLayer,
    CapabilityNode,
    CapabilityRelation,
    CapabilityRelationType,
    EvidenceBinding,
    MarketBinding,
    MarketBindingScope,
    PersonalCapabilityState,
)
from career_harness.core.capability_workspace import (
    WorkspaceInputKind,
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
