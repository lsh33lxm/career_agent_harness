from __future__ import annotations

from typing import Literal

from career_harness.core.capability import (
    CandidateCapabilityNode,
    CandidateCapabilityStatus,
    CapabilityGraphVersion,
    CapabilityLayer,
    CapabilityNode,
    CapabilityRelation,
    promote_candidate_to_official,
)
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.lifecycle import ActorKind
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.capability_writes import (
    CandidateCapabilityProposeWrite,
    CandidateCapabilityReviewWrite,
    CapabilityGraphRelease,
)
from career_harness.services.command_service import CommandService


class CandidateProposalCommit(FrozenModel):
    candidate: CandidateCapabilityNode
    commit: CommandCommitResult


class CandidateReviewCommit(FrozenModel):
    candidate: CandidateCapabilityNode
    commit: CommandCommitResult
    capability_id: OpaqueId | None = None
    graph_version: CapabilityGraphVersion | None = None


def _actor_kind(actor: str) -> ActorKind:
    if actor == ActorKind.USER.value:
        return ActorKind.USER
    if actor.startswith(f"{ActorKind.RULE.value}:"):
        return ActorKind.RULE
    return ActorKind.AGENT


class CapabilityReviewService:
    """User-gated review flow that promotes inbox candidates into the official graph."""

    def __init__(self, commands: CommandService, repository: CapabilityRepository) -> None:
        self.commands = commands
        self.repository = repository

    def propose_candidate(
        self,
        command: Command,
        *,
        proposed_canonical_name: str,
        proposed_description: str,
        proposed_layer: CapabilityLayer,
        source_evidence_refs: tuple[OpaqueId, ...],
    ) -> CandidateProposalCommit:
        self._require_target(command)
        if command.expected_revision != 0:
            raise ValueError("a new capability candidate requires expected revision zero")
        candidate = CandidateCapabilityNode(
            candidate_node_id=command.target.entity_id,
            proposed_canonical_name=proposed_canonical_name,
            proposed_description=proposed_description,
            proposed_layer=proposed_layer,
            source_evidence_refs=source_evidence_refs,
            discovered_by=command.actor,
        )
        commit = self.commands.commit(
            command,
            candidate.model_dump(mode="json"),
            event_type="capability_candidate.proposed",
            event_payload={
                "candidate_node_id": candidate.candidate_node_id,
                "proposed_layer": candidate.proposed_layer.value,
                "discovered_by_kind": _actor_kind(command.actor).value,
                "evidence_count": len(candidate.source_evidence_refs),
                "status": candidate.status.value,
            },
            transactional_write=CandidateCapabilityProposeWrite(candidate),
        )
        persisted = self._get_candidate(candidate.candidate_node_id)
        if persisted is None:
            raise RuntimeError("candidate proposal commit did not persist the typed row")
        return CandidateProposalCommit(candidate=persisted, commit=commit)

    def review_candidate(
        self,
        command: Command,
        *,
        candidate_node_id: OpaqueId,
        decision: Literal["accept", "reject"],
        reason: str,
        merge_target: OpaqueId | None = None,
    ) -> CandidateReviewCommit:
        self._require_target(command)
        if command.target.entity_id != candidate_node_id:
            raise ValueError("the review command target must be the reviewed candidate")
        reviewer_kind = _actor_kind(command.actor)
        if reviewer_kind is ActorKind.AGENT:
            raise ValueError("an agent cannot decide a capability candidate review")
        if decision == "accept":
            if reviewer_kind is not ActorKind.USER:
                raise ValueError("accepting a capability candidate requires a user actor")
            status = (
                CandidateCapabilityStatus.MERGED
                if merge_target is not None
                else CandidateCapabilityStatus.ACCEPTED
            )
        elif decision == "reject":
            if merge_target is not None:
                raise ValueError("a rejection cannot carry a merge target")
            status = CandidateCapabilityStatus.IGNORED
        else:
            raise ValueError("review decision must be accept or reject")

        candidate = self._get_candidate(candidate_node_id)
        if candidate is None:
            raise ValueError("review requires a pending capability candidate")
        if candidate.status is not CandidateCapabilityStatus.PENDING:
            return self._replay_review(
                command, candidate, status, reason, merge_target, reviewer_kind
            )
        if command.actor == candidate.discovered_by:
            raise ValueError("the discovering actor can never review its own candidate")

        reviewed = CandidateCapabilityNode(
            candidate_node_id=candidate.candidate_node_id,
            proposed_canonical_name=candidate.proposed_canonical_name,
            proposed_description=candidate.proposed_description,
            proposed_layer=candidate.proposed_layer,
            source_evidence_refs=candidate.source_evidence_refs,
            discovered_by=candidate.discovered_by,
            status=status,
            reviewed_by=command.actor,
            reviewed_by_kind=reviewer_kind,
            review_reason=reason,
            merge_target_capability_id=merge_target,
        )
        release = None
        if status is CandidateCapabilityStatus.ACCEPTED:
            release = self._plan_release(command, reviewed)
        return self._commit_review(command, reviewed, release)

    def _commit_review(
        self,
        command: Command,
        reviewed: CandidateCapabilityNode,
        release: CapabilityGraphRelease | None,
    ) -> CandidateReviewCommit:
        commit = self.commands.commit(
            command,
            reviewed.model_dump(mode="json"),
            event_type="capability_candidate.reviewed",
            event_payload={
                "candidate_node_id": reviewed.candidate_node_id,
                "status": reviewed.status.value,
                "reviewed_by_kind": (
                    reviewed.reviewed_by_kind.value if reviewed.reviewed_by_kind else None
                ),
                "merge_target_capability_id": reviewed.merge_target_capability_id,
                "capability_id": (release.new_node.capability_id if release is not None else None),
                "graph_version_id": (
                    release.graph_version.graph_version_id if release is not None else None
                ),
                "parent_graph_version_id": (
                    release.graph_version.parent_graph_version_id if release is not None else None
                ),
            },
            transactional_write=CandidateCapabilityReviewWrite(reviewed, release),
        )
        persisted = self._get_candidate(reviewed.candidate_node_id)
        if persisted is None or persisted.status is CandidateCapabilityStatus.PENDING:
            raise RuntimeError("candidate review commit did not persist the typed row")
        graph_version = None
        capability_id = None
        if release is not None:
            graph_version = self.repository.get_graph_version(
                release.graph_version.graph_version_id
            )
            if graph_version is None:
                raise RuntimeError("candidate review commit did not persist the graph release")
            capability_id = release.new_node.capability_id
        return CandidateReviewCommit(
            candidate=persisted,
            commit=commit,
            capability_id=capability_id,
            graph_version=graph_version,
        )

    def _replay_review(
        self,
        command: Command,
        candidate: CandidateCapabilityNode,
        status: CandidateCapabilityStatus,
        reason: str,
        merge_target: OpaqueId | None,
        reviewer_kind: ActorKind,
    ) -> CandidateReviewCommit:
        """Reconstruct the original review write so the kernel can replay its receipt."""
        if (
            candidate.status is not status
            or candidate.reviewed_by != command.actor
            or candidate.reviewed_by_kind is not reviewer_kind
            or candidate.review_reason != reason
            or candidate.merge_target_capability_id != merge_target
        ):
            raise ValueError("this capability candidate was already reviewed")
        release = None
        if status is CandidateCapabilityStatus.ACCEPTED:
            graph_version_id = f"graph_version_{candidate.candidate_node_id}"
            capability_id = f"capability_{candidate.candidate_node_id}"
            graph_version = self.repository.get_graph_version(graph_version_id)
            if graph_version is None:
                raise ValueError("this capability candidate was already reviewed")
            nodes = self.repository.list_nodes(graph_version_id)
            new_node = next((node for node in nodes if node.capability_id == capability_id), None)
            if new_node is None:
                raise ValueError("this capability candidate was already reviewed")
            release = CapabilityGraphRelease(
                graph_version=graph_version,
                carried_nodes=tuple(node for node in nodes if node.capability_id != capability_id),
                carried_relations=self.repository.list_relations(graph_version_id),
                new_node=new_node,
            )
        return self._commit_review(command, candidate, release)

    def _plan_release(
        self, command: Command, candidate: CandidateCapabilityNode
    ) -> CapabilityGraphRelease:
        parent = self.repository.get_latest_graph_version()
        parent_id = parent.graph_version_id if parent is not None else None
        graph_version_id = f"graph_version_{candidate.candidate_node_id}"
        graph_version = CapabilityGraphVersion(
            graph_version_id=graph_version_id,
            version_label=f"inbox-{candidate.candidate_node_id}",
            parent_graph_version_id=parent_id,
            change_note=(
                f"Accept capability candidate {candidate.candidate_node_id} into the "
                "official ontology."
            ),
            released_by=command.actor,
            released_by_kind=ActorKind.USER,
        )
        carried_nodes: tuple[CapabilityNode, ...] = ()
        carried_relations: tuple[CapabilityRelation, ...] = ()
        if parent_id is not None:
            carried_nodes = tuple(
                node.model_copy(update={"graph_version_id": graph_version_id})
                for node in self.repository.list_nodes(parent_id)
            )
            carried_relations = tuple(
                relation.model_copy(
                    update={
                        "relation_id": f"{relation.relation_id}__{graph_version_id}",
                        "graph_version_id": graph_version_id,
                    }
                )
                for relation in self.repository.list_relations(parent_id)
            )
        new_node = promote_candidate_to_official(
            candidate,
            capability_id=f"capability_{candidate.candidate_node_id}",
            graph_version=graph_version,
        )
        return CapabilityGraphRelease(
            graph_version=graph_version,
            carried_nodes=carried_nodes,
            carried_relations=carried_relations,
            new_node=new_node,
        )

    def _get_candidate(self, candidate_node_id: str) -> CandidateCapabilityNode | None:
        return next(
            (
                candidate
                for candidate in self.repository.list_candidates()
                if candidate.candidate_node_id == candidate_node_id
            ),
            None,
        )

    @staticmethod
    def _require_target(command: Command) -> None:
        if command.target.kind is not EntityKind.CAPABILITY_CANDIDATE:
            raise ValueError(f"command requires a {EntityKind.CAPABILITY_CANDIDATE.value} target")
