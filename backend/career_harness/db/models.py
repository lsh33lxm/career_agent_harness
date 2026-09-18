from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EntityStateRow(Base):
    __tablename__ = "entity_state"

    entity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EntityRevisionRow(Base):
    __tablename__ = "entity_revision"
    __table_args__ = (UniqueConstraint("entity_id", "revision"),)

    revision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entity_state.entity_id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class DomainEventRow(Base):
    __tablename__ = "domain_event"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    command_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyRecordRow(Base):
    __tablename__ = "idempotency_record"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    command_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxMessageRow(Base):
    __tablename__ = "outbox_message"

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("domain_event.event_id", ondelete="RESTRICT"), nullable=False
    )
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MigrationMismatchRow(Base):
    __tablename__ = "migration_mismatch"

    mismatch_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    legacy_key: Mapped[str | None] = mapped_column(String(512))
    candidate_core_identity: Mapped[str | None] = mapped_column(String(128))
    mismatch: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class WatchlistItemRow(Base):
    __tablename__ = "watchlist_item"
    __table_args__ = (UniqueConstraint("job_id", "job_revision"),)

    watchlist_item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    added_by: Mapped[str] = mapped_column(String(32), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OpportunityAdmissionProposalRow(Base):
    __tablename__ = "opportunity_admission_proposal"

    proposal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OpportunityRecordRow(Base):
    __tablename__ = "opportunity_record"
    __table_args__ = (UniqueConstraint("job_id", "job_revision"),)

    opportunity_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    admitted_by: Mapped[str] = mapped_column(String(32), nullable=False)


class OpportunityAdmissionDecisionRow(Base):
    __tablename__ = "opportunity_admission_decision"
    __table_args__ = (
        CheckConstraint("decided_by = 'user'", name="ck_opportunity_decision_user"),
        CheckConstraint(
            "(path = 'proposal' AND proposal_id IS NOT NULL) "
            "OR (path = 'manual' AND proposal_id IS NULL)",
            name="ck_opportunity_decision_path",
        ),
        CheckConstraint(
            "(decision = 'admitted' AND opportunity_id IS NOT NULL) "
            "OR (decision = 'rejected' AND opportunity_id IS NULL)",
            name="ck_opportunity_decision_result",
        ),
        CheckConstraint(
            "path != 'manual' OR decision = 'admitted'",
            name="ck_opportunity_manual_admission",
        ),
    )

    decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    path: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(32), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_admission_proposal.proposal_id", ondelete="RESTRICT")
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SuggestedPriorityRow(Base):
    __tablename__ = "suggested_priority"
    __table_args__ = (
        CheckConstraint(
            "level IN ('low', 'medium', 'high', 'urgent')",
            name="ck_suggested_priority_level",
        ),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1)", name="ck_priority_score"),
        CheckConstraint("rank IS NULL OR rank >= 1", name="ck_priority_rank"),
    )

    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_revisions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPriorityRow(Base):
    __tablename__ = "user_priority"
    __table_args__ = (
        CheckConstraint(
            "level IN ('low', 'medium', 'high', 'urgent')",
            name="ck_user_priority_level",
        ),
        CheckConstraint("actor = 'user'", name="ck_user_priority_actor"),
    )

    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class CapabilityIdentityRow(Base):
    __tablename__ = "capability_identity"

    capability_id: Mapped[str] = mapped_column(String(128), primary_key=True)


class CapabilityGraphVersionRow(Base):
    __tablename__ = "capability_graph_version"
    __table_args__ = (
        CheckConstraint(
            "parent_graph_version_id IS NULL OR parent_graph_version_id != graph_version_id",
            name="ck_capability_graph_parent_not_self",
        ),
        CheckConstraint(
            "released_by_kind IN ('user', 'rule')",
            name="ck_capability_graph_release_authority",
        ),
    )

    graph_version_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    parent_graph_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("capability_graph_version.graph_version_id", ondelete="RESTRICT")
    )
    change_note: Mapped[str] = mapped_column(Text, nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_by: Mapped[str] = mapped_column(String(255), nullable=False)
    released_by_kind: Mapped[str] = mapped_column(String(32), nullable=False)


class CapabilityNodeRow(Base):
    __tablename__ = "capability_node"
    __table_args__ = (
        CheckConstraint(
            "layer IN ('common_core', 'track', 'opportunity_specific')",
            name="ck_capability_node_layer",
        ),
        CheckConstraint(
            "lifecycle_status IN ('active', 'deprecated', 'retired')",
            name="ck_capability_node_lifecycle",
        ),
    )

    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), primary_key=True
    )
    graph_version_id: Mapped[str] = mapped_column(
        ForeignKey(
            "capability_graph_version.graph_version_id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        primary_key=True,
    )
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    layer: Mapped[str] = mapped_column(String(32), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), nullable=False)


class CapabilityRelationRow(Base):
    __tablename__ = "capability_relation"
    __table_args__ = (
        CheckConstraint(
            "source_capability_id != target_capability_id",
            name="ck_capability_relation_distinct_nodes",
        ),
        CheckConstraint(
            "relation_type IN ('prerequisite', 'part_of', 'related_to')",
            name="ck_capability_relation_type",
        ),
        ForeignKeyConstraint(
            ["source_capability_id", "graph_version_id"],
            ["capability_node.capability_id", "capability_node.graph_version_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["target_capability_id", "graph_version_id"],
            ["capability_node.capability_id", "capability_node.graph_version_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    relation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_capability_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_capability_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    graph_version_id: Mapped[str] = mapped_column(String(128), nullable=False)


class CandidateCapabilityNodeRow(Base):
    __tablename__ = "candidate_capability_node"
    __table_args__ = (
        CheckConstraint(
            "proposed_layer IN ('common_core', 'track', 'opportunity_specific')",
            name="ck_candidate_capability_layer",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'merged', 'ignored', 'deferred')",
            name="ck_candidate_capability_status",
        ),
        CheckConstraint(
            "json_type(source_evidence_refs) = 'array' "
            "AND json_array_length(source_evidence_refs) > 0",
            name="ck_candidate_capability_evidence_refs",
        ),
        CheckConstraint(
            "(status = 'pending' AND reviewed_by IS NULL AND reviewed_by_kind IS NULL "
            "AND review_reason IS NULL) OR (status != 'pending' AND reviewed_by IS NOT NULL "
            "AND reviewed_by_kind IN ('user', 'rule') "
            "AND review_reason IS NOT NULL)",
            name="ck_candidate_capability_review",
        ),
        CheckConstraint(
            "(status = 'merged' AND merge_target_capability_id IS NOT NULL) "
            "OR (status != 'merged' AND merge_target_capability_id IS NULL)",
            name="ck_candidate_capability_merge_target",
        ),
    )

    candidate_node_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    proposed_canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    proposed_description: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_layer: Mapped[str] = mapped_column(String(32), nullable=False)
    source_evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    discovered_by: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_by_kind: Mapped[str | None] = mapped_column(String(32))
    review_reason: Mapped[str | None] = mapped_column(Text)
    merge_target_capability_id: Mapped[str | None] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT")
    )


class PersonalCapabilityStateRow(Base):
    __tablename__ = "personal_capability_state"
    __table_args__ = (
        UniqueConstraint("personal_state_id", "revision", "capability_id"),
        UniqueConstraint("personal_state_id", "revision", "candidate_id", "capability_id"),
        CheckConstraint("revision >= 1", name="ck_personal_capability_revision"),
        CheckConstraint("schema_version >= 1", name="ck_personal_capability_schema_version"),
        CheckConstraint(
            "updated_by_kind IN ('user', 'rule')",
            name="ck_personal_capability_update_authority",
        ),
    )

    personal_state_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), nullable=False
    )
    understand: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explain: Mapped[bool] = mapped_column(Boolean, nullable=False)
    apply: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    interview_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by_kind: Mapped[str] = mapped_column(String(32), nullable=False)


class CapabilityEvidenceBindingRow(Base):
    __tablename__ = "capability_evidence_binding"
    __table_args__ = (
        CheckConstraint(
            "(evidence_ref_id IS NOT NULL AND project_evidence_id IS NULL) "
            "OR (evidence_ref_id IS NULL AND project_evidence_id IS NOT NULL)",
            name="ck_capability_evidence_exactly_one_source",
        ),
        CheckConstraint(
            "authority IN ('code_verified', 'document_supported', 'user_confirmed', "
            "'ai_inferred')",
            name="ck_capability_evidence_authority",
        ),
        CheckConstraint(
            "json_type(scopes) = 'array' AND json_array_length(scopes) > 0",
            name="ck_capability_evidence_scopes",
        ),
        ForeignKeyConstraint(
            ["personal_state_id", "personal_state_revision", "capability_id"],
            [
                "personal_capability_state.personal_state_id",
                "personal_capability_state.revision",
                "personal_capability_state.capability_id",
            ],
            ondelete="RESTRICT",
        ),
    )

    binding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    personal_state_id: Mapped[str] = mapped_column(String(128), nullable=False)
    personal_state_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), nullable=False
    )
    evidence_ref_id: Mapped[str | None] = mapped_column(String(128))
    project_evidence_id: Mapped[str | None] = mapped_column(String(128))
    authority: Mapped[str] = mapped_column(String(32), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bound_by: Mapped[str] = mapped_column(String(255), nullable=False)


class CapabilityMarketBindingRow(Base):
    __tablename__ = "capability_market_binding"
    __table_args__ = (
        CheckConstraint(
            "market_scope IN ('target', 'broad')",
            name="ck_capability_market_scope",
        ),
        CheckConstraint(
            "json_type(source_evidence_refs) = 'array' "
            "AND json_array_length(source_evidence_refs) > 0",
            name="ck_capability_market_evidence_refs",
        ),
        CheckConstraint(
            "(market_scope = 'target' AND "
            "(opportunity_id IS NOT NULL OR job_requirement_id IS NOT NULL)) "
            "OR (market_scope = 'broad' AND opportunity_id IS NULL "
            "AND job_requirement_id IS NULL)",
            name="ck_capability_market_target_refs",
        ),
    )

    binding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), nullable=False
    )
    market_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    source_evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_record.opportunity_id", ondelete="RESTRICT")
    )
    job_requirement_id: Mapped[str | None] = mapped_column(String(128))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CapabilityInvestmentStateRow(Base):
    __tablename__ = "capability_investment_state"
    __table_args__ = (
        CheckConstraint(
            "target_market_demand BETWEEN 0 AND 1 "
            "AND opportunity_importance BETWEEN 0 AND 1 "
            "AND cross_opportunity_reuse BETWEEN 0 AND 1 "
            "AND project_proximity BETWEEN 0 AND 1 "
            "AND evidence_feasibility BETWEEN 0 AND 1 "
            "AND personal_interest BETWEEN 0 AND 1 "
            "AND learning_cost BETWEEN 0 AND 1 "
            "AND score BETWEEN 0 AND 1",
            name="ck_capability_investment_unit_interval",
        ),
        CheckConstraint(
            "recommendation IN ('low', 'medium', 'high')",
            name="ck_capability_investment_recommendation",
        ),
        CheckConstraint(
            "(score >= 0.6 AND recommendation = 'high') "
            "OR (score >= 0.35 AND score < 0.6 AND recommendation = 'medium') "
            "OR (score < 0.35 AND recommendation = 'low')",
            name="ck_capability_investment_score_recommendation",
        ),
        CheckConstraint(
            "score = round(max(0.0, min(1.0, "
            "target_market_demand * 0.25 + opportunity_importance * 0.20 "
            "+ cross_opportunity_reuse * 0.20 + project_proximity * 0.10 "
            "+ evidence_feasibility * 0.15 + personal_interest * 0.10 "
            "- learning_cost * 0.25)), 3)",
            name="ck_capability_investment_score_factors",
        ),
        CheckConstraint(
            "rule_version = 'capability-investment-v1'",
            name="ck_capability_investment_rule_version",
        ),
        CheckConstraint(
            "json_type(reasons) = 'array' AND json_array_length(reasons) > 0",
            name="ck_capability_investment_reasons",
        ),
        CheckConstraint(
            "json_type(market_binding_ids) = 'array' "
            "AND json_array_length(market_binding_ids) > 0",
            name="ck_capability_investment_market_bindings",
        ),
        CheckConstraint(
            "personal_state_revision >= 1",
            name="ck_capability_investment_personal_revision",
        ),
        ForeignKeyConstraint(
            [
                "personal_state_id",
                "personal_state_revision",
                "candidate_id",
                "capability_id",
            ],
            [
                "personal_capability_state.personal_state_id",
                "personal_capability_state.revision",
                "personal_capability_state.candidate_id",
                "personal_capability_state.capability_id",
            ],
            ondelete="RESTRICT",
        ),
    )

    investment_state_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), nullable=False
    )
    target_market_demand: Mapped[float] = mapped_column(Float, nullable=False)
    opportunity_importance: Mapped[float] = mapped_column(Float, nullable=False)
    cross_opportunity_reuse: Mapped[float] = mapped_column(Float, nullable=False)
    project_proximity: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_feasibility: Mapped[float] = mapped_column(Float, nullable=False)
    personal_interest: Mapped[float] = mapped_column(Float, nullable=False)
    learning_cost: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    graph_version_id: Mapped[str] = mapped_column(
        ForeignKey("capability_graph_version.graph_version_id", ondelete="RESTRICT"),
        nullable=False,
    )
    personal_state_id: Mapped[str] = mapped_column(String(128), nullable=False)
    personal_state_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    market_binding_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    opportunity_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

