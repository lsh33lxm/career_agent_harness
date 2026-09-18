from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, computed_field, model_validator

from career_harness.core.common import FrozenModel, OpaqueId, utc_now
from career_harness.core.lifecycle import ActorKind

CONTRACT_VERSION = "v1.4-contract-0.1.0"
INVESTMENT_RULE_VERSION = "capability-investment-v1"


class CapabilityLayer(StrEnum):
    COMMON_CORE = "common_core"
    TRACK = "track"
    OPPORTUNITY_SPECIFIC = "opportunity_specific"


class CapabilityLifecycleStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class CapabilityRelationType(StrEnum):
    PREREQUISITE = "prerequisite"
    PART_OF = "part_of"
    RELATED_TO = "related_to"


class CandidateCapabilityStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    MERGED = "merged"
    IGNORED = "ignored"
    DEFERRED = "deferred"


class PersonalCapabilityDisplayStatus(StrEnum):
    UNKNOWN = "unknown"
    UNDERSTOOD = "understood"
    PRACTICED = "practiced"
    APPLIED = "applied"
    VERIFIED = "verified"
    RESUME_READY = "resume_ready"


class CapabilityEvidenceAuthority(StrEnum):
    CODE_VERIFIED = "code_verified"
    DOCUMENT_SUPPORTED = "document_supported"
    USER_CONFIRMED = "user_confirmed"
    AI_INFERRED = "ai_inferred"


class CapabilityEvidenceScope(StrEnum):
    UNDERSTAND = "understand"
    EXPLAIN = "explain"
    APPLY = "apply"
    EVIDENCE = "evidence"
    INTERVIEW_READY = "interview_ready"


class MarketBindingScope(StrEnum):
    TARGET = "target"
    BROAD = "broad"


class InvestmentRecommendation(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CapabilityGraphVersion(FrozenModel):
    graph_version_id: OpaqueId
    version_label: str = Field(min_length=1, max_length=64)
    parent_graph_version_id: OpaqueId | None = None
    change_note: str = Field(min_length=1, max_length=2048)
    released_at: datetime = Field(default_factory=utc_now)
    released_by: str = Field(min_length=1, max_length=255)
    released_by_kind: ActorKind

    @model_validator(mode="after")
    def official_release_requires_authority(self) -> Self:
        if self.parent_graph_version_id == self.graph_version_id:
            raise ValueError("graph version cannot be its own parent")
        if self.released_by_kind is ActorKind.AGENT:
            raise ValueError("an agent cannot release an official capability graph")
        return self


class CapabilityNode(FrozenModel):
    capability_id: OpaqueId
    canonical_name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2048)
    layer: CapabilityLayer
    lifecycle_status: CapabilityLifecycleStatus = CapabilityLifecycleStatus.ACTIVE
    graph_version_id: OpaqueId


class CapabilityRelation(FrozenModel):
    relation_id: OpaqueId
    source_capability_id: OpaqueId
    target_capability_id: OpaqueId
    relation_type: CapabilityRelationType
    graph_version_id: OpaqueId

    @model_validator(mode="after")
    def relation_must_connect_distinct_nodes(self) -> Self:
        if self.source_capability_id == self.target_capability_id:
            raise ValueError("capability relation cannot reference the same node twice")
        return self


class CandidateCapabilityNode(FrozenModel):
    candidate_node_id: OpaqueId
    proposed_canonical_name: str = Field(min_length=1, max_length=255)
    proposed_description: str = Field(min_length=1, max_length=2048)
    proposed_layer: CapabilityLayer
    source_evidence_refs: tuple[OpaqueId, ...] = Field(min_length=1)
    discovered_by: str = Field(min_length=1, max_length=255)
    status: CandidateCapabilityStatus = CandidateCapabilityStatus.PENDING
    reviewed_by: str | None = Field(default=None, min_length=1, max_length=255)
    reviewed_by_kind: ActorKind | None = None
    review_reason: str | None = Field(default=None, min_length=1, max_length=2048)
    merge_target_capability_id: OpaqueId | None = None

    @model_validator(mode="after")
    def review_state_is_explicit(self) -> Self:
        review_fields = (self.reviewed_by, self.reviewed_by_kind, self.review_reason)
        if self.status is CandidateCapabilityStatus.PENDING:
            if any(value is not None for value in review_fields):
                raise ValueError("pending candidate cannot carry a review decision")
        else:
            if any(value is None for value in review_fields):
                raise ValueError("reviewed candidate requires reviewer, authority, and reason")
            if self.reviewed_by_kind is ActorKind.AGENT:
                raise ValueError("an agent cannot decide a capability candidate review")

        if self.status is CandidateCapabilityStatus.MERGED:
            if self.merge_target_capability_id is None:
                raise ValueError("merged candidate requires a target capability")
        elif self.merge_target_capability_id is not None:
            raise ValueError("only a merged candidate may carry a merge target")
        return self


def promote_candidate_to_official(
    candidate: CandidateCapabilityNode,
    *,
    capability_id: OpaqueId,
    graph_version: CapabilityGraphVersion,
) -> CapabilityNode:
    if candidate.status is not CandidateCapabilityStatus.ACCEPTED:
        raise ValueError("only an accepted candidate can become an official capability node")
    return CapabilityNode(
        capability_id=capability_id,
        canonical_name=candidate.proposed_canonical_name,
        description=candidate.proposed_description,
        layer=candidate.proposed_layer,
        graph_version_id=graph_version.graph_version_id,
    )


class PersonalCapabilityState(FrozenModel):
    personal_state_id: OpaqueId
    candidate_id: OpaqueId
    capability_id: OpaqueId
    understand: bool = False
    explain: bool = False
    apply: bool = False
    evidence: bool = False
    interview_ready: bool = False
    revision: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)
    updated_at: datetime = Field(default_factory=utc_now)
    updated_by: str = Field(min_length=1, max_length=255)
    updated_by_kind: ActorKind

    @model_validator(mode="after")
    def canonical_state_requires_user_or_rule_authority(self) -> Self:
        if self.updated_by_kind is ActorKind.AGENT:
            raise ValueError("an agent cannot own canonical personal capability state")
        return self

    @computed_field
    @property
    def display_status(self) -> PersonalCapabilityDisplayStatus:
        return derive_personal_capability_status(
            understand=self.understand,
            explain=self.explain,
            apply=self.apply,
            evidence=self.evidence,
            interview_ready=self.interview_ready,
        )


def derive_personal_capability_status(
    *,
    understand: bool,
    explain: bool,
    apply: bool,
    evidence: bool,
    interview_ready: bool,
) -> PersonalCapabilityDisplayStatus:
    if understand and explain and apply and evidence and interview_ready:
        return PersonalCapabilityDisplayStatus.RESUME_READY
    if understand and explain and apply and evidence:
        return PersonalCapabilityDisplayStatus.VERIFIED
    if understand and apply:
        return PersonalCapabilityDisplayStatus.APPLIED
    if understand and explain:
        return PersonalCapabilityDisplayStatus.PRACTICED
    if understand:
        return PersonalCapabilityDisplayStatus.UNDERSTOOD
    return PersonalCapabilityDisplayStatus.UNKNOWN


class EvidenceBinding(FrozenModel):
    binding_id: OpaqueId
    personal_state_id: OpaqueId
    personal_state_revision: int = Field(ge=1)
    capability_id: OpaqueId
    evidence_ref_id: OpaqueId | None = None
    project_evidence_id: OpaqueId | None = None
    authority: CapabilityEvidenceAuthority
    scopes: tuple[CapabilityEvidenceScope, ...] = Field(min_length=1)
    bound_at: datetime = Field(default_factory=utc_now)
    bound_by: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def exactly_one_evidence_source(self) -> Self:
        source_count = sum(
            source is not None for source in (self.evidence_ref_id, self.project_evidence_id)
        )
        if source_count != 1:
            raise ValueError("binding requires exactly one Evidence or Project Evidence source")
        if len(set(self.scopes)) != len(self.scopes):
            raise ValueError("evidence binding scopes must be unique")
        return self


class MarketBinding(FrozenModel):
    binding_id: OpaqueId
    capability_id: OpaqueId
    market_scope: MarketBindingScope
    source_evidence_refs: tuple[OpaqueId, ...] = Field(min_length=1)
    opportunity_id: OpaqueId | None = None
    job_requirement_id: OpaqueId | None = None
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def scope_matches_target_references(self) -> Self:
        has_target = self.opportunity_id is not None or self.job_requirement_id is not None
        if self.market_scope is MarketBindingScope.TARGET and not has_target:
            raise ValueError("target market binding requires an opportunity or job requirement")
        if self.market_scope is MarketBindingScope.BROAD and has_target:
            raise ValueError("broad market binding cannot carry target opportunity references")
        return self


class InvestmentFactors(FrozenModel):
    target_market_demand: float = Field(ge=0, le=1)
    opportunity_importance: float = Field(ge=0, le=1)
    cross_opportunity_reuse: float = Field(ge=0, le=1)
    project_proximity: float = Field(ge=0, le=1)
    evidence_feasibility: float = Field(ge=0, le=1)
    personal_interest: float = Field(ge=0, le=1)
    learning_cost: float = Field(ge=0, le=1)


class InvestmentCalculationInputs(FrozenModel):
    graph_version_id: OpaqueId
    personal_state_id: OpaqueId
    personal_state_revision: int = Field(ge=1)
    market_binding_ids: tuple[OpaqueId, ...] = Field(min_length=1)
    opportunity_ids: tuple[OpaqueId, ...] = ()

    @model_validator(mode="after")
    def references_are_unique(self) -> Self:
        if len(set(self.market_binding_ids)) != len(self.market_binding_ids):
            raise ValueError("market binding inputs must be unique")
        if len(set(self.opportunity_ids)) != len(self.opportunity_ids):
            raise ValueError("opportunity inputs must be unique")
        return self


class InvestmentState(FrozenModel):
    investment_state_id: OpaqueId
    candidate_id: OpaqueId
    capability_id: OpaqueId
    factors: InvestmentFactors
    recommendation: InvestmentRecommendation
    score: float = Field(ge=0, le=1)
    reasons: tuple[str, ...] = Field(min_length=1)
    calculation_inputs: InvestmentCalculationInputs
    rule_version: Literal["capability-investment-v1"] = INVESTMENT_RULE_VERSION
    calculated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def result_matches_explainable_rule(self) -> Self:
        expected_score = calculate_investment_score(self.factors)
        expected_recommendation = recommendation_for_score(expected_score)
        expected_reasons = explain_investment_factors(self.factors)
        if self.score != expected_score:
            raise ValueError("investment score does not match the declared factors")
        if self.recommendation is not expected_recommendation:
            raise ValueError("investment recommendation does not match the calculated score")
        if self.reasons != expected_reasons:
            raise ValueError("investment reasons do not match the declared factors")
        return self


def calculate_investment_score(factors: InvestmentFactors) -> float:
    benefit = (
        factors.target_market_demand * 0.25
        + factors.opportunity_importance * 0.20
        + factors.cross_opportunity_reuse * 0.20
        + factors.project_proximity * 0.10
        + factors.evidence_feasibility * 0.15
        + factors.personal_interest * 0.10
    )
    score = benefit - factors.learning_cost * 0.25
    return round(max(0.0, min(1.0, score)), 3)


def recommendation_for_score(score: float) -> InvestmentRecommendation:
    if score >= 0.6:
        return InvestmentRecommendation.HIGH
    if score >= 0.35:
        return InvestmentRecommendation.MEDIUM
    return InvestmentRecommendation.LOW


def explain_investment_factors(factors: InvestmentFactors) -> tuple[str, ...]:
    reasons: list[str] = []
    if factors.target_market_demand >= 0.6:
        reasons.append("Target market demand is strong.")
    if factors.opportunity_importance >= 0.6:
        reasons.append("The capability matters to important target opportunities.")
    if factors.cross_opportunity_reuse >= 0.6:
        reasons.append("The capability is reusable across target opportunities.")
    if factors.project_proximity >= 0.6:
        reasons.append("Existing projects make the capability relatively close to practice.")
    if factors.evidence_feasibility >= 0.6:
        reasons.append("The investment is likely to produce verifiable evidence.")
    if factors.personal_interest >= 0.6:
        reasons.append("The capability aligns with the candidate's stated interest.")
    if factors.learning_cost >= 0.7:
        reasons.append("The estimated learning or project cost is high.")
    elif factors.learning_cost <= 0.3:
        reasons.append("The estimated learning or project cost is manageable.")
    if not reasons:
        reasons.append("No single factor is strong enough to dominate the recommendation.")
    return tuple(reasons)


def recommend_capability_investment(
    *,
    investment_state_id: OpaqueId,
    candidate_id: OpaqueId,
    capability_id: OpaqueId,
    factors: InvestmentFactors,
    calculation_inputs: InvestmentCalculationInputs,
) -> InvestmentState:
    score = calculate_investment_score(factors)
    return InvestmentState(
        investment_state_id=investment_state_id,
        candidate_id=candidate_id,
        capability_id=capability_id,
        factors=factors,
        recommendation=recommendation_for_score(score),
        score=score,
        reasons=explain_investment_factors(factors),
        calculation_inputs=calculation_inputs,
    )
