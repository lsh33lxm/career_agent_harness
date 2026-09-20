"""Read-only Capability Workspace service (contract 0.13.0, D-023)."""

from __future__ import annotations

from career_harness.core.capability import MarketBindingScope
from career_harness.core.capability_workspace import (
    CapabilityWorkspace,
    build_capability_workspace,
)
from career_harness.db.capability_repository import CapabilityRepository


class CapabilityGraphNotFoundError(LookupError):
    def __init__(self, graph_version_id: str) -> None:
        super().__init__(f"capability graph version not found: {graph_version_id}")
        self.graph_version_id = graph_version_id


class CapabilityWorkspaceService:
    def __init__(self, repository: CapabilityRepository) -> None:
        self.repository = repository

    def get_workspace(
        self, *, candidate_id: str, graph_version_id: str | None = None
    ) -> CapabilityWorkspace:
        graph = (
            self.repository.get_official_graph(graph_version_id)
            if graph_version_id is not None
            else self.repository.get_latest_official_graph()
        )
        if graph is None:
            if graph_version_id is not None:
                raise CapabilityGraphNotFoundError(graph_version_id)
            return build_capability_workspace(candidate_id=candidate_id, graph_version=None)

        personal_states = self.repository.list_latest_personal_states(candidate_id=candidate_id)
        evidence_bindings = tuple(
            binding
            for state in personal_states
            for binding in self.repository.list_evidence_bindings(
                personal_state_id=state.personal_state_id,
                personal_state_revision=state.revision,
            )
        )
        market_bindings = tuple(
            binding
            for node in graph.nodes
            for scope in (MarketBindingScope.TARGET, MarketBindingScope.BROAD)
            for binding in self.repository.list_market_bindings(
                capability_id=node.capability_id, market_scope=scope
            )
        )
        return build_capability_workspace(
            candidate_id=candidate_id,
            graph_version=graph.graph_version,
            nodes=graph.nodes,
            relations=graph.relations,
            personal_states=personal_states,
            evidence_bindings=evidence_bindings,
            market_bindings=market_bindings,
            investment_states=self.repository.list_investment_states(candidate_id=candidate_id),
        )
