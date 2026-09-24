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

    @model_validator(mode="after")
    def nested_refs_match_projection(self) -> CapabilityProjection:
        state = self.personal_state
        if state is not None and state.capability_id != self.capability_id:
            raise ValueError("personal state capability must match its projection")
        if state is None and self.evidence_bindings:
            raise ValueError("evidence bindings require a projected personal state")

        evidence_ids = [binding.binding_id for binding in self.evidence_bindings]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("projection evidence binding ids must be unique")
        for binding in self.evidence_bindings:
            if binding.capability_id != self.capability_id:
                raise ValueError("evidence binding capability must match its projection")
            if state is not None and (
                binding.personal_state_id != state.personal_state_id
                or binding.personal_state_revision != state.revision
            ):
                raise ValueError("evidence binding must pin the projected personal state revision")

        target_ids = [binding.binding_id for binding in self.target_market_bindings]
        broad_ids = [binding.binding_id for binding in self.broad_market_bindings]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("projection target market binding ids must be unique")
        if len(broad_ids) != len(set(broad_ids)):
            raise ValueError("projection broad market binding ids must be unique")
        if set(target_ids) & set(broad_ids):
            raise ValueError("market binding cannot appear in both target and broad projections")
        for binding in self.target_market_bindings:
            if (
                binding.capability_id != self.capability_id
                or binding.market_scope is not MarketBindingScope.TARGET
            ):
                raise ValueError("target market binding must match projection capability and scope")
        for binding in self.broad_market_bindings:
            if (
                binding.capability_id != self.capability_id
                or binding.market_scope is not MarketBindingScope.BROAD
            ):
                raise ValueError("broad market binding must match projection capability and scope")

        if (
            self.investment_state is not None
            and self.investment_state.capability_id != self.capability_id
        ):
            raise ValueError("investment state capability must match its projection")
        return self


def _input_ref_key(ref: WorkspaceInputRef) -> tuple[str, str, int]:
    return (ref.kind.value, ref.entity_id, ref.revision or 0)


def _expected_input_refs(
    graph_version: CapabilityGraphVersion,
    projections: Iterable[CapabilityProjection],
) -> tuple[WorkspaceInputRef, ...]:
    refs = [
        WorkspaceInputRef(
            kind=WorkspaceInputKind.GRAPH_VERSION,
            entity_id=graph_version.graph_version_id,
        )
    ]
    for projection in projections:
        state = projection.personal_state
        if state is not None:
            refs.append(
                WorkspaceInputRef(
                    kind=WorkspaceInputKind.PERSONAL_STATE,
                    entity_id=state.personal_state_id,
                    revision=state.revision,
                )
            )
        refs.extend(
            WorkspaceInputRef(
                kind=WorkspaceInputKind.EVIDENCE_BINDING,
                entity_id=binding.binding_id,
            )
            for binding in projection.evidence_bindings
        )
        refs.extend(
            WorkspaceInputRef(
                kind=WorkspaceInputKind.TARGET_MARKET_BINDING,
                entity_id=binding.binding_id,
            )
            for binding in projection.target_market_bindings
        )
        refs.extend(
            WorkspaceInputRef(
                kind=WorkspaceInputKind.BROAD_MARKET_BINDING,
                entity_id=binding.binding_id,
            )
            for binding in projection.broad_market_bindings
        )
        if projection.investment_state is not None:
            refs.append(
                WorkspaceInputRef(
                    kind=WorkspaceInputKind.INVESTMENT_STATE,
                    entity_id=projection.investment_state.investment_state_id,
                )
            )
    return tuple(sorted(refs, key=_input_ref_key))


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
        projection_ids = tuple(item.capability_id for item in self.projections)
        if self.graph_version is None and (
            self.nodes or self.relations or self.projections or self.input_revisions
        ):
            raise ValueError("an empty workspace cannot contain graph data or input refs")
        if self.graph_version is None:
            return self

        graph_version_id = self.graph_version.graph_version_id
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("workspace capability node ids must be unique")
        if any(node.graph_version_id != graph_version_id for node in self.nodes):
            raise ValueError("workspace nodes must belong to the selected graph version")
        if len(projection_ids) != len(set(projection_ids)):
            raise ValueError("workspace projection capability ids must be unique")
        if projection_ids != node_ids:
            raise ValueError("workspace requires exactly one ordered projection per official node")

        relation_ids = [relation.relation_id for relation in self.relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("workspace relation ids must be unique")
        relation_edges = [
            (
                relation.source_capability_id,
                relation.target_capability_id,
                relation.relation_type,
            )
            for relation in self.relations
        ]
        if len(relation_edges) != len(set(relation_edges)):
            raise ValueError("workspace relation edges must be unique")
        node_id_set = set(node_ids)
        for relation in self.relations:
            if relation.graph_version_id != graph_version_id:
                raise ValueError("workspace relations must belong to the selected graph version")
            if (
                relation.source_capability_id not in node_id_set
                or relation.target_capability_id not in node_id_set
            ):
                raise ValueError("workspace relation cannot reference a node outside the graph")

        for projection in self.projections:
            state = projection.personal_state
            if state is not None and state.candidate_id != self.candidate_id:
                raise ValueError("personal state candidate must match the workspace candidate")
            investment = projection.investment_state
            if investment is not None and investment.candidate_id != self.candidate_id:
                raise ValueError("investment state candidate must match the workspace candidate")

        input_ref_identities = [
            (ref.kind, ref.entity_id, ref.revision) for ref in self.input_revisions
        ]
        if len(input_ref_identities) != len(set(input_ref_identities)):
            raise ValueError("workspace input revision refs must be unique")
        if self.input_revisions != _expected_input_refs(self.graph_version, self.projections):
            raise ValueError(
                "workspace input revisions must exactly match projected canonical inputs"
            )
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

    ordered_nodes = tuple(sorted(nodes, key=_node_key))
    ordered_relations = tuple(
        sorted(
            relations,
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
