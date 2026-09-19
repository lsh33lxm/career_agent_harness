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


class EvidenceArtifactRow(Base):
    __tablename__ = "evidence_artifact"
    __table_args__ = (
        CheckConstraint(
            "length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_evidence_artifact_sha256",
        ),
        CheckConstraint("length(trim(media_type)) > 0", name="ck_evidence_artifact_media_type"),
        CheckConstraint(
            "artifact_class IN ('public_source', 'personal', 'sensitive')",
            name="ck_evidence_artifact_class",
        ),
        CheckConstraint("byte_length >= 0", name="ck_evidence_artifact_byte_length"),
    )

    artifact_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_class: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_length: Mapped[int] = mapped_column(Integer, nullable=False)


class EvidenceSourceRow(Base):
    __tablename__ = "evidence_source"
    __table_args__ = (
        CheckConstraint(
            "length(trim(source_type)) > 0 AND length(source_type) <= 128",
            name="ck_evidence_source_type",
        ),
        CheckConstraint(
            "length(trim(locator)) > 0 AND length(locator) <= 2048",
            name="ck_evidence_source_locator",
        ),
    )

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)


class SourceSnapshotRow(Base):
    __tablename__ = "source_snapshot"
    __table_args__ = (UniqueConstraint("snapshot_id", "artifact_id"),)

    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_source.source_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_artifact.artifact_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class EvidenceRefRow(Base):
    __tablename__ = "evidence_ref"
    __table_args__ = (
        CheckConstraint(
            "selector IS NULL OR length(selector) <= 2048",
            name="ck_evidence_ref_selector",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "artifact_id"],
            ["source_snapshot.snapshot_id", "source_snapshot.artifact_id"],
            ondelete="RESTRICT",
        ),
    )

    evidence_ref_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    selector: Mapped[str | None] = mapped_column(Text)


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
    project_evidence_revision: Mapped[int | None] = mapped_column(Integer)
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


class ProjectIdentityRow(Base):
    __tablename__ = "project_identity"

    project_id: Mapped[str] = mapped_column(String(128), primary_key=True)


class ProjectRecordRow(Base):
    __tablename__ = "project_record"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_project_record_revision"),
        CheckConstraint("schema_version >= 1", name="ck_project_record_schema_version"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("project_identity.project_id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_locator: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ProjectScanScopeRow(Base):
    __tablename__ = "project_scan_scope"
    __table_args__ = (
        UniqueConstraint("scope_id", "revision", "project_id"),
        CheckConstraint("revision >= 1", name="ck_project_scope_revision"),
        CheckConstraint("schema_version >= 1", name="ck_project_scope_schema_version"),
        CheckConstraint(
            "json_type(allowed_paths) = 'array' AND json_array_length(allowed_paths) > 0",
            name="ck_project_scope_allowed_paths",
        ),
        CheckConstraint(
            "json_type(denied_paths) = 'array'",
            name="ck_project_scope_denied_paths",
        ),
        CheckConstraint("follow_symlinks = 0", name="ck_project_scope_no_symlinks"),
    )

    scope_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project_identity.project_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    allowed_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    denied_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    follow_symlinks: Mapped[bool] = mapped_column(Boolean, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ProjectSourceManifestRow(Base):
    __tablename__ = "project_source_manifest"
    __table_args__ = (
        UniqueConstraint("manifest_id", "project_id"),
        CheckConstraint("scan_scope_revision >= 1", name="ck_project_manifest_scope_revision"),
        ForeignKeyConstraint(
            ["scan_scope_id", "scan_scope_revision", "project_id"],
            [
                "project_scan_scope.scope_id",
                "project_scan_scope.revision",
                "project_scan_scope.project_id",
            ],
            ondelete="RESTRICT",
        ),
    )

    manifest_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scan_scope_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scan_scope_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectSourceEntryRow(Base):
    __tablename__ = "project_source_entry"
    __table_args__ = (
        CheckConstraint("length(relative_path) > 0", name="ck_project_source_relative_path"),
        CheckConstraint(
            "length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_project_source_sha256",
        ),
        CheckConstraint("byte_length >= 0", name="ck_project_source_byte_length"),
    )

    manifest_id: Mapped[str] = mapped_column(
        ForeignKey("project_source_manifest.manifest_id", ondelete="RESTRICT"), primary_key=True
    )
    relative_path: Mapped[str] = mapped_column(Text, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(Integer, nullable=False)


class ProjectEvidenceRow(Base):
    __tablename__ = "project_evidence"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_project_evidence_revision"),
        CheckConstraint("schema_version >= 1", name="ck_project_evidence_schema_version"),
        CheckConstraint(
            "claim_kind IN ('technical_observation', 'change', 'validation', 'performance', "
            "'business_outcome', 'personal_contribution', 'ownership', 'usage')",
            name="ck_project_evidence_claim_kind",
        ),
        CheckConstraint(
            "authority IN ('code_verified', 'document_supported', 'user_confirmed', "
            "'ai_inferred')",
            name="ck_project_evidence_authority",
        ),
        CheckConstraint(
            "freshness IN ('current', 'stale', 'unknown')",
            name="ck_project_evidence_freshness",
        ),
        CheckConstraint(
            "review_status IN ('proposed', 'accepted', 'rejected', 'superseded')",
            name="ck_project_evidence_review_status",
        ),
        CheckConstraint(
            "(review_status = 'proposed' AND reviewed_by IS NULL "
            "AND reviewed_by_kind IS NULL AND review_reason IS NULL) OR "
            "(review_status != 'proposed' AND reviewed_by IS NOT NULL "
            "AND trim(reviewed_by) != '' AND reviewed_by_kind IN ('user', 'rule') "
            "AND review_reason IS NOT NULL AND trim(review_reason) != '')",
            name="ck_project_evidence_review_authority",
        ),
        CheckConstraint(
            "NOT (authority = 'ai_inferred' AND review_status = 'accepted')",
            name="ck_project_evidence_ai_requires_promotion",
        ),
        CheckConstraint(
            "NOT (authority = 'code_verified' AND claim_kind IN "
            "('performance', 'business_outcome', 'personal_contribution', "
            "'ownership', 'usage'))",
            name="ck_project_evidence_code_authority_limit",
        ),
        ForeignKeyConstraint(
            ["manifest_id", "project_id"],
            ["project_source_manifest.manifest_id", "project_source_manifest.project_id"],
            ondelete="RESTRICT",
        ),
    )

    evidence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    claim_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scanner: Mapped[str] = mapped_column(String(255), nullable=False)
    scanner_version: Mapped[str] = mapped_column(String(128), nullable=False)
    authority: Mapped[str] = mapped_column(String(32), nullable=False)
    freshness: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_by_kind: Mapped[str | None] = mapped_column(String(32))
    review_reason: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ProjectCapabilityStateRow(Base):
    __tablename__ = "project_capability_state"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_project_capability_revision"),
        CheckConstraint("schema_version >= 1", name="ck_project_capability_schema_version"),
        CheckConstraint(
            "state IN ('existing', 'understood', 'modified', 'extended', "
            "'validated', 'resume_ready')",
            name="ck_project_capability_lifecycle",
        ),
    )

    capability_state_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project_identity.project_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ProjectCapabilityBasisRow(Base):
    __tablename__ = "project_capability_basis"
    __table_args__ = (
        CheckConstraint("state_revision >= 1", name="ck_project_basis_state_revision"),
        CheckConstraint(
            "basis_kind IN ('code_evidence', 'document_evidence', 'user_confirmation', "
            "'change_evidence', 'validation_evidence', 'resume_approval')",
            name="ck_project_basis_kind",
        ),
        CheckConstraint(
            "(basis_kind = 'resume_approval' AND project_evidence_id IS NULL "
            "AND project_evidence_revision IS NULL AND approval_id IS NOT NULL "
            "AND approval_revision >= 1) OR (basis_kind != 'resume_approval' "
            "AND project_evidence_id IS NOT NULL AND project_evidence_revision >= 1 "
            "AND approval_id IS NULL AND approval_revision IS NULL)",
            name="ck_project_basis_typed_reference",
        ),
        ForeignKeyConstraint(
            ["capability_state_id", "state_revision"],
            [
                "project_capability_state.capability_state_id",
                "project_capability_state.revision",
            ],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["project_evidence_id", "project_evidence_revision"],
            ["project_evidence.evidence_id", "project_evidence.revision"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["approval_id", "approval_revision"],
            ["entity_revision.entity_id", "entity_revision.revision"],
            ondelete="RESTRICT",
        ),
    )

    basis_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    capability_state_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    basis_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    project_evidence_id: Mapped[str | None] = mapped_column(String(128), index=True)
    project_evidence_revision: Mapped[int | None] = mapped_column(Integer)
    approval_id: Mapped[str | None] = mapped_column(String(128), index=True)
    approval_revision: Mapped[int | None] = mapped_column(Integer)


class ProjectEnhancementTaskRow(Base):
    __tablename__ = "project_enhancement_task"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_project_enhancement_revision"),
        CheckConstraint("schema_version >= 1", name="ck_project_enhancement_schema_version"),
        CheckConstraint(
            "status IN ('proposed', 'ready', 'in_progress', 'awaiting_validation', "
            "'completed', 'cancelled')",
            name="ck_project_enhancement_status",
        ),
        CheckConstraint(
            "json_type(learning_plan) = 'array' AND json_array_length(learning_plan) > 0 "
            "AND json_type(files_to_review) = 'array' "
            "AND json_array_length(files_to_review) > 0 "
            "AND json_type(change_plan) = 'array' AND json_array_length(change_plan) > 0 "
            "AND json_type(experiment_plan) = 'array' "
            "AND json_array_length(experiment_plan) > 0 "
            "AND json_type(validation_plan) = 'array' "
            "AND json_array_length(validation_plan) > 0 "
            "AND json_type(expected_evidence) = 'array' "
            "AND json_array_length(expected_evidence) > 0",
            name="ck_project_enhancement_plans",
        ),
    )

    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project_identity.project_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_gap_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_capability_id: Mapped[str] = mapped_column(
        ForeignKey("capability_identity.capability_id", ondelete="RESTRICT"), nullable=False
    )
    learning_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    files_to_review: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    change_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    experiment_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    validation_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    expected_evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class ContextManifestRow(Base):
    __tablename__ = "context_manifest"
    __table_args__ = (
        CheckConstraint(
            "selection_policy_version = 'context-relevance-v1'",
            name="ck_context_manifest_selection_policy",
        ),
        CheckConstraint(
            "compression_policy_version = 'context-no-compression-v1'",
            name="ck_context_manifest_compression_policy",
        ),
        CheckConstraint(
            "length(trim(contract_version)) > 0 AND length(trim(task_type)) > 0 "
            "AND length(trim(provider)) > 0 AND length(trim(model_id)) > 0 "
            "AND length(trim(actor)) > 0",
            name="ck_context_manifest_required_text",
        ),
        CheckConstraint(
            "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_context_manifest_input_hash",
        ),
        CheckConstraint(
            "json_type(capabilities) = 'array' AND json_array_length(capabilities) <= 64",
            name="ck_context_capabilities",
        ),
        CheckConstraint(
            "json_type(skills) = 'array' AND json_array_length(skills) <= 64",
            name="ck_context_skills",
        ),
        CheckConstraint(
            "included_count >= 0 AND excluded_count >= 0 AND knowledge_ref_count >= 0",
            name="ck_context_manifest_counts",
        ),
    )

    manifest_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    selection_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    compression_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    included_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_ref_count: Mapped[int] = mapped_column(Integer, nullable=False)


class ContextManifestAssetRefRow(Base):
    __tablename__ = "context_manifest_asset_ref"
    __table_args__ = (
        UniqueConstraint("manifest_id", "disposition", "ordinal"),
        CheckConstraint(
            "asset_class IN ('personal_context', 'career_state', 'project_evidence', "
            "'market_evidence', 'career_history_outcome')",
            name="ck_context_asset_class",
        ),
        CheckConstraint("asset_revision >= 1", name="ck_context_asset_revision"),
        CheckConstraint("ordinal >= 0", name="ck_context_asset_ordinal"),
        CheckConstraint(
            "disposition IN ('included', 'excluded')",
            name="ck_context_asset_disposition",
        ),
        CheckConstraint(
            "(disposition = 'included' AND reason IN "
            "('explicit_reference', 'relevance_term_match')) OR "
            "(disposition = 'excluded' AND reason IN "
            "('asset_class_not_allowed', 'no_relevance_match', 'selection_limit'))",
            name="ck_context_asset_reason",
        ),
        CheckConstraint(
            "json_type(matched_terms) = 'array' "
            "AND json_array_length(matched_terms) <= 64 AND "
            "((reason = 'relevance_term_match' AND json_array_length(matched_terms) > 0) "
            "OR (reason != 'relevance_term_match' AND json_array_length(matched_terms) = 0))",
            name="ck_context_asset_matched_terms",
        ),
        ForeignKeyConstraint(
            ["manifest_id"],
            ["context_manifest.manifest_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    manifest_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class ContextManifestKnowledgeRefRow(Base):
    __tablename__ = "context_manifest_knowledge_ref"
    __table_args__ = (
        UniqueConstraint("manifest_id", "knowledge_id", "knowledge_revision"),
        CheckConstraint("knowledge_revision >= 1", name="ck_context_knowledge_revision"),
        CheckConstraint("ordinal >= 0", name="ck_context_knowledge_ordinal"),
        ForeignKeyConstraint(
            ["manifest_id"],
            ["context_manifest.manifest_id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    manifest_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    knowledge_revision: Mapped[int] = mapped_column(Integer, nullable=False)

