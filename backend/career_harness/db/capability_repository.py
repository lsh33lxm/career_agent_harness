from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.capability import (
    CandidateCapabilityNode,
    CandidateCapabilityStatus,
    CapabilityEvidenceAuthority,
    CapabilityEvidenceScope,
    CapabilityGraphVersion,
    CapabilityLayer,
    CapabilityLifecycleStatus,
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
    PersonalCapabilityState,
)
from career_harness.core.common import FrozenModel
from career_harness.core.lifecycle import ActorKind
from career_harness.db.models import (
    CandidateCapabilityNodeRow,
    CapabilityEvidenceBindingRow,
    CapabilityGraphVersionRow,
    CapabilityInvestmentStateRow,
    CapabilityMarketBindingRow,
    CapabilityNodeRow,
    CapabilityRelationRow,
    PersonalCapabilityStateRow,
)


class OfficialCapabilityGraphRead(FrozenModel):
    graph_version: CapabilityGraphVersion
    nodes: tuple[CapabilityNode, ...]
    relations: tuple[CapabilityRelation, ...]


class CapabilityRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_graph_version(self, graph_version_id: str) -> CapabilityGraphVersion | None:
        with Session(self.engine) as session:
            row = session.get(CapabilityGraphVersionRow, graph_version_id)
            return self._to_graph_version(row) if row is not None else None

    def get_latest_graph_version(self) -> CapabilityGraphVersion | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(CapabilityGraphVersionRow)
                .order_by(
                    CapabilityGraphVersionRow.released_at.desc(),
                    CapabilityGraphVersionRow.graph_version_id.desc(),
                )
                .limit(1)
            )
            return self._to_graph_version(row) if row is not None else None

    def get_official_graph(self, graph_version_id: str) -> OfficialCapabilityGraphRead | None:
        with Session(self.engine) as session:
            version_row = session.get(CapabilityGraphVersionRow, graph_version_id)
            if version_row is None:
                return None
            return OfficialCapabilityGraphRead(
                graph_version=self._to_graph_version(version_row),
                nodes=self._list_nodes(session, graph_version_id),
                relations=self._list_relations(session, graph_version_id),
            )

    def get_latest_official_graph(self) -> OfficialCapabilityGraphRead | None:
        with Session(self.engine) as session:
            version_row = session.scalar(
                select(CapabilityGraphVersionRow)
                .order_by(
                    CapabilityGraphVersionRow.released_at.desc(),
                    CapabilityGraphVersionRow.graph_version_id.desc(),
                )
                .limit(1)
            )
            if version_row is None:
                return None
            return OfficialCapabilityGraphRead(
                graph_version=self._to_graph_version(version_row),
                nodes=self._list_nodes(session, version_row.graph_version_id),
                relations=self._list_relations(session, version_row.graph_version_id),
            )

    def list_nodes(self, graph_version_id: str) -> tuple[CapabilityNode, ...]:
        with Session(self.engine) as session:
            return self._list_nodes(session, graph_version_id)

    def list_relations(self, graph_version_id: str) -> tuple[CapabilityRelation, ...]:
        with Session(self.engine) as session:
            return self._list_relations(session, graph_version_id)

    def list_candidates(
        self, status: CandidateCapabilityStatus | None = None
    ) -> tuple[CandidateCapabilityNode, ...]:
        statement = select(CandidateCapabilityNodeRow)
        if status is not None:
            statement = statement.where(CandidateCapabilityNodeRow.status == status.value)
        statement = statement.order_by(CandidateCapabilityNodeRow.candidate_node_id)
        with Session(self.engine) as session:
            return tuple(self._to_candidate(row) for row in session.scalars(statement).all())

    def list_candidate_ids(self) -> tuple[str, ...]:
        """List identities that already own a personal capability overlay."""

        with Session(self.engine) as session:
            return tuple(
                session.scalars(
                    select(PersonalCapabilityStateRow.candidate_id)
                    .distinct()
                    .order_by(PersonalCapabilityStateRow.candidate_id)
                ).all()
            )

    def list_candidate_inbox(self) -> tuple[CandidateCapabilityNode, ...]:
        return self.list_candidates(CandidateCapabilityStatus.PENDING)

    def get_personal_state(
        self, *, personal_state_id: str, revision: int
    ) -> PersonalCapabilityState | None:
        with Session(self.engine) as session:
            row = session.get(
                PersonalCapabilityStateRow,
                (personal_state_id, revision),
            )
            return self._to_personal_state(row) if row is not None else None

    def get_latest_personal_state(
        self, *, personal_state_id: str
    ) -> PersonalCapabilityState | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(PersonalCapabilityStateRow)
                .where(PersonalCapabilityStateRow.personal_state_id == personal_state_id)
                .order_by(PersonalCapabilityStateRow.revision.desc())
                .limit(1)
            )
            return self._to_personal_state(row) if row is not None else None

    def list_personal_states(
        self, *, candidate_id: str, capability_id: str
    ) -> tuple[PersonalCapabilityState, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(PersonalCapabilityStateRow)
                .where(
                    PersonalCapabilityStateRow.candidate_id == candidate_id,
                    PersonalCapabilityStateRow.capability_id == capability_id,
                )
                .order_by(
                    PersonalCapabilityStateRow.personal_state_id,
                    PersonalCapabilityStateRow.revision,
                )
            ).all()
            return tuple(self._to_personal_state(row) for row in rows)

    def list_latest_personal_states(
        self, *, candidate_id: str
    ) -> tuple[PersonalCapabilityState, ...]:
        """Return one deterministic latest state per capability for one candidate."""

        with Session(self.engine) as session:
            rows = session.scalars(
                select(PersonalCapabilityStateRow)
                .where(PersonalCapabilityStateRow.candidate_id == candidate_id)
                .order_by(
                    PersonalCapabilityStateRow.capability_id,
                    PersonalCapabilityStateRow.updated_at.desc(),
                    PersonalCapabilityStateRow.revision.desc(),
                    PersonalCapabilityStateRow.personal_state_id,
                )
            ).all()
        latest: dict[str, PersonalCapabilityState] = {}
        for row in rows:
            latest.setdefault(row.capability_id, self._to_personal_state(row))
        return tuple(latest.values())

    def list_evidence_bindings(
        self, *, personal_state_id: str, personal_state_revision: int
    ) -> tuple[EvidenceBinding, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(CapabilityEvidenceBindingRow)
                .where(
                    CapabilityEvidenceBindingRow.personal_state_id == personal_state_id,
                    CapabilityEvidenceBindingRow.personal_state_revision == personal_state_revision,
                )
                .order_by(
                    CapabilityEvidenceBindingRow.bound_at,
                    CapabilityEvidenceBindingRow.binding_id,
                )
            ).all()
            return tuple(self._to_evidence_binding(row) for row in rows)

    def list_market_bindings(
        self, *, capability_id: str, market_scope: MarketBindingScope
    ) -> tuple[MarketBinding, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(CapabilityMarketBindingRow)
                .where(
                    CapabilityMarketBindingRow.capability_id == capability_id,
                    CapabilityMarketBindingRow.market_scope == market_scope.value,
                )
                .order_by(
                    CapabilityMarketBindingRow.observed_at,
                    CapabilityMarketBindingRow.binding_id,
                )
            ).all()
            return tuple(self._to_market_binding(row) for row in rows)

    def get_investment_state(self, investment_state_id: str) -> InvestmentState | None:
        with Session(self.engine) as session:
            row = session.get(CapabilityInvestmentStateRow, investment_state_id)
            return self._to_investment_state(row) if row is not None else None

    def list_investment_states(
        self, *, candidate_id: str, capability_id: str | None = None
    ) -> tuple[InvestmentState, ...]:
        statement = select(CapabilityInvestmentStateRow).where(
            CapabilityInvestmentStateRow.candidate_id == candidate_id
        )
        if capability_id is not None:
            statement = statement.where(CapabilityInvestmentStateRow.capability_id == capability_id)
        statement = statement.order_by(
            CapabilityInvestmentStateRow.calculated_at.desc(),
            CapabilityInvestmentStateRow.investment_state_id,
        )
        with Session(self.engine) as session:
            return tuple(self._to_investment_state(row) for row in session.scalars(statement).all())

    @staticmethod
    def _list_nodes(session: Session, graph_version_id: str) -> tuple[CapabilityNode, ...]:
        rows = session.scalars(
            select(CapabilityNodeRow)
            .where(CapabilityNodeRow.graph_version_id == graph_version_id)
            .order_by(CapabilityNodeRow.capability_id)
        ).all()
        return tuple(CapabilityRepository._to_node(row) for row in rows)

    @staticmethod
    def _list_relations(session: Session, graph_version_id: str) -> tuple[CapabilityRelation, ...]:
        rows = session.scalars(
            select(CapabilityRelationRow)
            .where(CapabilityRelationRow.graph_version_id == graph_version_id)
            .order_by(
                CapabilityRelationRow.source_capability_id,
                CapabilityRelationRow.target_capability_id,
                CapabilityRelationRow.relation_type,
                CapabilityRelationRow.relation_id,
            )
        ).all()
        return tuple(CapabilityRepository._to_relation(row) for row in rows)

    @staticmethod
    def _to_graph_version(row: CapabilityGraphVersionRow) -> CapabilityGraphVersion:
        return CapabilityGraphVersion(
            graph_version_id=row.graph_version_id,
            version_label=row.version_label,
            parent_graph_version_id=row.parent_graph_version_id,
            change_note=row.change_note,
            released_at=row.released_at,
            released_by=row.released_by,
            released_by_kind=ActorKind(row.released_by_kind),
        )

    @staticmethod
    def _to_node(row: CapabilityNodeRow) -> CapabilityNode:
        return CapabilityNode(
            capability_id=row.capability_id,
            canonical_name=row.canonical_name,
            description=row.description,
            layer=CapabilityLayer(row.layer),
            lifecycle_status=CapabilityLifecycleStatus(row.lifecycle_status),
            graph_version_id=row.graph_version_id,
        )

    @staticmethod
    def _to_relation(row: CapabilityRelationRow) -> CapabilityRelation:
        return CapabilityRelation(
            relation_id=row.relation_id,
            source_capability_id=row.source_capability_id,
            target_capability_id=row.target_capability_id,
            relation_type=CapabilityRelationType(row.relation_type),
            graph_version_id=row.graph_version_id,
        )

    @staticmethod
    def _to_candidate(row: CandidateCapabilityNodeRow) -> CandidateCapabilityNode:
        return CandidateCapabilityNode(
            candidate_node_id=row.candidate_node_id,
            proposed_canonical_name=row.proposed_canonical_name,
            proposed_description=row.proposed_description,
            proposed_layer=CapabilityLayer(row.proposed_layer),
            source_evidence_refs=tuple(row.source_evidence_refs),
            discovered_by=row.discovered_by,
            status=CandidateCapabilityStatus(row.status),
            reviewed_by=row.reviewed_by,
            reviewed_by_kind=(
                ActorKind(row.reviewed_by_kind) if row.reviewed_by_kind is not None else None
            ),
            review_reason=row.review_reason,
            merge_target_capability_id=row.merge_target_capability_id,
        )

    @staticmethod
    def _to_personal_state(row: PersonalCapabilityStateRow) -> PersonalCapabilityState:
        return PersonalCapabilityState(
            personal_state_id=row.personal_state_id,
            candidate_id=row.candidate_id,
            capability_id=row.capability_id,
            understand=row.understand,
            explain=row.explain,
            apply=row.apply,
            evidence=row.evidence,
            interview_ready=row.interview_ready,
            revision=row.revision,
            schema_version=row.schema_version,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
            updated_by_kind=ActorKind(row.updated_by_kind),
        )

    @staticmethod
    def _to_evidence_binding(row: CapabilityEvidenceBindingRow) -> EvidenceBinding:
        return EvidenceBinding(
            binding_id=row.binding_id,
            personal_state_id=row.personal_state_id,
            personal_state_revision=row.personal_state_revision,
            capability_id=row.capability_id,
            evidence_ref_id=row.evidence_ref_id,
            project_evidence_id=row.project_evidence_id,
            project_evidence_revision=row.project_evidence_revision,
            authority=CapabilityEvidenceAuthority(row.authority),
            scopes=tuple(CapabilityEvidenceScope(scope) for scope in row.scopes),
            bound_at=row.bound_at,
            bound_by=row.bound_by,
        )

    @staticmethod
    def _to_market_binding(row: CapabilityMarketBindingRow) -> MarketBinding:
        return MarketBinding(
            binding_id=row.binding_id,
            capability_id=row.capability_id,
            market_scope=MarketBindingScope(row.market_scope),
            source_evidence_refs=tuple(row.source_evidence_refs),
            opportunity_id=row.opportunity_id,
            job_requirement_id=row.job_requirement_id,
            observed_at=row.observed_at,
        )

    @staticmethod
    def _to_investment_state(row: CapabilityInvestmentStateRow) -> InvestmentState:
        return InvestmentState(
            investment_state_id=row.investment_state_id,
            candidate_id=row.candidate_id,
            capability_id=row.capability_id,
            factors=InvestmentFactors(
                target_market_demand=row.target_market_demand,
                opportunity_importance=row.opportunity_importance,
                cross_opportunity_reuse=row.cross_opportunity_reuse,
                project_proximity=row.project_proximity,
                evidence_feasibility=row.evidence_feasibility,
                personal_interest=row.personal_interest,
                learning_cost=row.learning_cost,
            ),
            recommendation=InvestmentRecommendation(row.recommendation),
            score=row.score,
            reasons=tuple(row.reasons),
            calculation_inputs=InvestmentCalculationInputs(
                graph_version_id=row.graph_version_id,
                personal_state_id=row.personal_state_id,
                personal_state_revision=row.personal_state_revision,
                market_binding_ids=tuple(row.market_binding_ids),
                opportunity_ids=tuple(row.opportunity_ids),
            ),
            rule_version=row.rule_version,
            calculated_at=row.calculated_at,
        )
