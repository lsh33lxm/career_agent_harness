from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_harness.core.capability import (
    CandidateCapabilityNode,
    CandidateCapabilityStatus,
    CapabilityGraphVersion,
    CapabilityNode,
    CapabilityRelation,
)
from career_harness.core.common import FrozenModel
from career_harness.core.lifecycle import ActorKind
from career_harness.db.models import (
    CandidateCapabilityNodeRow,
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityNodeRow,
    CapabilityRelationRow,
    EvidenceRefRow,
)


class CapabilityGraphRelease(FrozenModel):
    """Plan for releasing one new official graph version inside the review transaction."""

    graph_version: CapabilityGraphVersion
    carried_nodes: tuple[CapabilityNode, ...]
    carried_relations: tuple[CapabilityRelation, ...]
    new_node: CapabilityNode


def _require_evidence_refs(session: Session, evidence_ref_ids: tuple[str, ...]) -> None:
    for evidence_ref_id in evidence_ref_ids:
        if session.get(EvidenceRefRow, evidence_ref_id) is None:
            raise ValueError("every source evidence ref must resolve to a canonical EvidenceRef")


class CandidateCapabilityProposeWrite:
    """Stage a new pending CandidateCapabilityNode inbox entry."""

    def __init__(self, candidate: CandidateCapabilityNode) -> None:
        self.candidate = candidate

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "capability-candidate-propose-v1",
            "candidate": self.candidate.model_dump(mode="json"),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        candidate = self.candidate
        if entity_revision != 1:
            raise ValueError("the first candidate revision must be revision one")
        if candidate.status is not CandidateCapabilityStatus.PENDING:
            raise ValueError("a new capability candidate starts as pending")
        _require_evidence_refs(session, candidate.source_evidence_refs)
        if session.get(CandidateCapabilityNodeRow, candidate.candidate_node_id) is not None:
            raise ValueError("candidate capability node already exists")
        session.add(
            CandidateCapabilityNodeRow(
                candidate_node_id=candidate.candidate_node_id,
                proposed_canonical_name=candidate.proposed_canonical_name,
                proposed_description=candidate.proposed_description,
                proposed_layer=candidate.proposed_layer.value,
                source_evidence_refs=list(candidate.source_evidence_refs),
                discovered_by=candidate.discovered_by,
                status=candidate.status.value,
            )
        )


class CandidateCapabilityReviewWrite:
    """Stage a review decision, releasing a new graph version on plain acceptance."""

    def __init__(
        self,
        candidate: CandidateCapabilityNode,
        release: CapabilityGraphRelease | None = None,
    ) -> None:
        self.candidate = candidate
        self.release = release

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "capability-candidate-review-v1",
            "candidate": self.candidate.model_dump(mode="json"),
            "release": (
                self.release.model_dump(mode="json", exclude={"graph_version": {"released_at"}})
                if self.release is not None
                else None
            ),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        candidate = self.candidate
        if entity_revision != 2:
            raise ValueError("a candidate review must be revision two")
        if candidate.status is CandidateCapabilityStatus.PENDING:
            raise ValueError("a candidate review revision must carry a review decision")
        if candidate.reviewed_by_kind not in {ActorKind.USER, ActorKind.RULE}:
            raise ValueError("only a user or an explicit deterministic rule may review a candidate")
        if (
            candidate.status
            in {CandidateCapabilityStatus.ACCEPTED, CandidateCapabilityStatus.MERGED}
            and candidate.reviewed_by_kind is not ActorKind.USER
        ):
            raise ValueError("accepting a capability candidate requires a user actor")

        row = session.get(CandidateCapabilityNodeRow, candidate.candidate_node_id)
        if row is None:
            raise ValueError("candidate capability node does not exist")
        if row.status != CandidateCapabilityStatus.PENDING.value:
            raise ValueError("only a pending capability candidate can be reviewed")
        if (
            row.proposed_canonical_name != candidate.proposed_canonical_name
            or row.proposed_description != candidate.proposed_description
            or row.proposed_layer != candidate.proposed_layer.value
            or tuple(row.source_evidence_refs) != candidate.source_evidence_refs
            or row.discovered_by != candidate.discovered_by
        ):
            raise ValueError("candidate review must carry the exact proposed candidate")
        if candidate.reviewed_by == row.discovered_by:
            raise ValueError("the discovering actor can never review its own candidate")

        if candidate.status is CandidateCapabilityStatus.MERGED:
            if self.release is not None:
                raise ValueError("a merge decision must not release a graph version")
            if session.get(CapabilityIdentityRow, candidate.merge_target_capability_id) is None:
                raise ValueError("merge target must be an existing canonical capability identity")
        elif candidate.status is CandidateCapabilityStatus.ACCEPTED:
            if self.release is None:
                raise ValueError("acceptance requires a new capability graph release")
            self._stage_release(session, occurred_at)
        elif self.release is not None:
            raise ValueError("a rejection must not release a graph version")

        row.status = candidate.status.value
        row.reviewed_by = candidate.reviewed_by
        row.reviewed_by_kind = (
            candidate.reviewed_by_kind.value if candidate.reviewed_by_kind else None
        )
        row.review_reason = candidate.review_reason
        row.merge_target_capability_id = candidate.merge_target_capability_id

    def _stage_release(self, session: Session, occurred_at: datetime) -> None:
        assert self.release is not None
        release = self.release
        version = release.graph_version
        latest = session.scalar(
            select(CapabilityGraphVersionRow)
            .order_by(
                CapabilityGraphVersionRow.released_at.desc(),
                CapabilityGraphVersionRow.graph_version_id.desc(),
            )
            .limit(1)
        )
        latest_id = latest.graph_version_id if latest is not None else None
        if latest_id != version.parent_graph_version_id:
            raise ValueError("the released capability graph changed during review")
        if session.get(CapabilityGraphVersionRow, version.graph_version_id) is not None:
            raise ValueError("capability graph version already exists")
        if session.get(CapabilityIdentityRow, release.new_node.capability_id) is not None:
            raise ValueError("capability identity already exists")
        session.add(CapabilityIdentityRow(capability_id=release.new_node.capability_id))
        session.flush()
        # D-007 release order: child rows first, the graph version row last; the
        # deferred FK and the seal triggers close the version once it exists.
        for node in (*release.carried_nodes, release.new_node):
            if node.graph_version_id != version.graph_version_id:
                raise ValueError("release nodes must belong to the new graph version")
            session.add(
                CapabilityNodeRow(
                    capability_id=node.capability_id,
                    graph_version_id=node.graph_version_id,
                    canonical_name=node.canonical_name,
                    description=node.description,
                    layer=node.layer.value,
                    lifecycle_status=node.lifecycle_status.value,
                )
            )
        for relation in release.carried_relations:
            if relation.graph_version_id != version.graph_version_id:
                raise ValueError("release relations must belong to the new graph version")
            session.add(
                CapabilityRelationRow(
                    relation_id=relation.relation_id,
                    source_capability_id=relation.source_capability_id,
                    target_capability_id=relation.target_capability_id,
                    relation_type=relation.relation_type.value,
                    graph_version_id=relation.graph_version_id,
                )
            )
        # Explicit flush preserves the D-007 order: the ORM would otherwise sort the
        # graph version row before its nodes via the FK dependency and trip the seal.
        session.flush()
        session.add(
            CapabilityGraphVersionRow(
                graph_version_id=version.graph_version_id,
                version_label=version.version_label,
                parent_graph_version_id=version.parent_graph_version_id,
                change_note=version.change_note,
                released_at=occurred_at,
                released_by=version.released_by,
                released_by_kind=version.released_by_kind.value,
            )
        )
