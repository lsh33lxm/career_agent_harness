"""Pure Capability Workspace projection (contract 0.13.0, D-023).

The stable total order is layer, case-insensitive canonical name and capability
ID for nodes/projections; source, target, relation type and relation ID for
relations; and binding ID for binding collections. Input refs are ordered by
kind, entity ID and revision. The builder never derives a new business score.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from career_harness.core.capability import (
    CapabilityGraphVersion,
    CapabilityLayer,
    CapabilityNode,
    CapabilityRelation,
    EvidenceBinding,
    InvestmentState,
    MarketBinding,
    MarketBindingScope,
    PersonalCapabilityState,
)
from career_harness.core.common import FrozenModel, OpaqueId

CAPABILITY_WORKSPACE_VERSION = "capability-workspace-v1"

_LAYER_ORDER = {
    CapabilityLayer.COMMON_CORE: 0,
    CapabilityLayer.TRACK: 1,
    CapabilityLayer.OPPORTUNITY_SPECIFIC: 2,
}


class WorkspaceInputKind(StrEnum):
    GRAPH_VERSION = "graph_version"
    PERSONAL_STATE = "personal_state"
    EVIDENCE_BINDING = "evidence_binding"
    TARGET_MARKET_BINDING = "target_market_binding"
    BROAD_MARKET_BINDING = "broad_market_binding"
    INVESTMENT_STATE = "investment_state"


class WorkspaceInputRef(FrozenModel):
    kind: WorkspaceInputKind
    entity_id: OpaqueId
    revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def revision_matches_input_kind(self) -> WorkspaceInputRef:
        if (self.kind is WorkspaceInputKind.PERSONAL_STATE) != (self.revision is not None):
            raise ValueError("only personal state input refs carry a numeric revision")
        return self


class CapabilityProjection(FrozenModel):
    capability_id: OpaqueId
    personal_state: PersonalCapabilityState | None = None
    evidence_bindings: tuple[EvidenceBinding, ...] = ()
    target_market_bindings: tuple[MarketBinding, ...] = ()
    broad_market_bindings: tuple[MarketBinding, ...] = ()
    investment_state: InvestmentState | None = None


class CapabilityWorkspace(FrozenModel):
    candidate_id: OpaqueId
    graph_version: CapabilityGraphVersion | None = None
    nodes: tuple[CapabilityNode, ...] = ()
    relations: tuple[CapabilityRelation, ...] = ()
    projections: tuple[CapabilityProjection, ...] = ()
    input_revisions: tuple[WorkspaceInputRef, ...] = ()
    workspace_version: Literal["capability-workspace-v1"] = CAPABILITY_WORKSPACE_VERSION

    @model_validator(mode="after")
    def projection_matches_graph(self) -> CapabilityWorkspace:
        node_ids = tuple(node.capability_id for node in self.nodes)
        if tuple(item.capability_id for item in self.projections) != node_ids:
            raise ValueError("workspace requires exactly one ordered projection per official node")
        if self.graph_version is None and (self.nodes or self.relations or self.input_revisions):
            raise ValueError("an empty workspace cannot contain graph data or input refs")
        return self


def _node_key(node: CapabilityNode) -> tuple[int, str, str]:
    return (_LAYER_ORDER[node.layer], node.canonical_name.casefold(), node.capability_id)


def _latest_investments(
    investments: Iterable[InvestmentState], *, candidate_id: str
) -> dict[str, InvestmentState]:
    ordered = sorted(
        (item for item in investments if item.candidate_id == candidate_id),
        key=lambda item: (
            item.capability_id,
            -item.calculated_at.timestamp(),
            item.investment_state_id,
        ),
    )
    latest: dict[str, InvestmentState] = {}
    for item in ordered:
        latest.setdefault(item.capability_id, item)
    return latest


def _latest_personal_states(
    states: Iterable[PersonalCapabilityState], *, candidate_id: str
) -> dict[str, PersonalCapabilityState]:
    ordered = sorted(
        (state for state in states if state.candidate_id == candidate_id),
        key=lambda state: (
            state.capability_id,
            -state.updated_at.timestamp(),
            -state.revision,
            state.personal_state_id,
        ),
    )
    latest: dict[str, PersonalCapabilityState] = {}
    for state in ordered:
        latest.setdefault(state.capability_id, state)
    return latest


def build_capability_workspace(
    *,
    candidate_id: str,
    graph_version: CapabilityGraphVersion | None,
    nodes: Iterable[CapabilityNode] = (),
    relations: Iterable[CapabilityRelation] = (),
    personal_states: Iterable[PersonalCapabilityState] = (),
    evidence_bindings: Iterable[EvidenceBinding] = (),
    market_bindings: Iterable[MarketBinding] = (),
    investment_states: Iterable[InvestmentState] = (),
) -> CapabilityWorkspace:
    """Build one deterministic read-only workspace from canonical typed inputs."""

    if graph_version is None:
        return CapabilityWorkspace(candidate_id=candidate_id)

    ordered_nodes = tuple(
        sorted(
            (node for node in nodes if node.graph_version_id == graph_version.graph_version_id),
            key=_node_key,
        )
    )
    node_ids = {node.capability_id for node in ordered_nodes}
    ordered_relations = tuple(
        sorted(
            (
                relation
                for relation in relations
                if relation.graph_version_id == graph_version.graph_version_id
                and relation.source_capability_id in node_ids
                and relation.target_capability_id in node_ids
            ),
            key=lambda relation: (
                relation.source_capability_id,
                relation.target_capability_id,
                relation.relation_type.value,
                relation.relation_id,
            ),
        )
    )
    states = _latest_personal_states(personal_states, candidate_id=candidate_id)
    investments = _latest_investments(investment_states, candidate_id=candidate_id)
    evidence = tuple(evidence_bindings)
    market = tuple(market_bindings)

    projections: list[CapabilityProjection] = []
    input_refs: set[tuple[WorkspaceInputKind, str, int | None]] = {
        (WorkspaceInputKind.GRAPH_VERSION, graph_version.graph_version_id, None)
    }
    for node in ordered_nodes:
        state = states.get(node.capability_id)
        state_evidence = tuple(
            sorted(
                (
                    binding
                    for binding in evidence
                    if state is not None
                    and binding.capability_id == node.capability_id
                    and binding.personal_state_id == state.personal_state_id
                    and binding.personal_state_revision == state.revision
                ),
                key=lambda binding: binding.binding_id,
            )
        )
        target = tuple(
            sorted(
                (
                    binding
                    for binding in market
                    if binding.capability_id == node.capability_id
                    and binding.market_scope is MarketBindingScope.TARGET
                ),
                key=lambda binding: binding.binding_id,
            )
        )
        broad = tuple(
            sorted(
                (
                    binding
                    for binding in market
                    if binding.capability_id == node.capability_id
                    and binding.market_scope is MarketBindingScope.BROAD
                ),
                key=lambda binding: binding.binding_id,
            )
        )
        investment = investments.get(node.capability_id)
        projections.append(
            CapabilityProjection(
                capability_id=node.capability_id,
                personal_state=state,
                evidence_bindings=state_evidence,
                target_market_bindings=target,
                broad_market_bindings=broad,
                investment_state=investment,
            )
        )
        if state is not None:
            input_refs.add(
                (WorkspaceInputKind.PERSONAL_STATE, state.personal_state_id, state.revision)
            )
        input_refs.update(
            (WorkspaceInputKind.EVIDENCE_BINDING, item.binding_id, None) for item in state_evidence
        )
        input_refs.update(
            (WorkspaceInputKind.TARGET_MARKET_BINDING, item.binding_id, None) for item in target
        )
        input_refs.update(
            (WorkspaceInputKind.BROAD_MARKET_BINDING, item.binding_id, None) for item in broad
        )
        if investment is not None:
            input_refs.add(
                (WorkspaceInputKind.INVESTMENT_STATE, investment.investment_state_id, None)
            )

    return CapabilityWorkspace(
        candidate_id=candidate_id,
        graph_version=graph_version,
        nodes=ordered_nodes,
        relations=ordered_relations,
        projections=tuple(projections),
        input_revisions=tuple(
            WorkspaceInputRef(kind=kind, entity_id=entity_id, revision=revision)
            for kind, entity_id, revision in sorted(
                input_refs, key=lambda item: (item[0].value, item[1], item[2] or 0)
            )
        ),
    )
