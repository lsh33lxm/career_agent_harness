from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from career_harness.core.approval import ActorKind
from career_harness.core.common import FrozenModel, OpaqueId, utc_now
from career_harness.core.lifecycle import Opportunity


class JobRef(FrozenModel):
    job_id: OpaqueId
    revision: int = Field(ge=1)


class WatchlistItem(FrozenModel):
    watchlist_item_id: OpaqueId
    job: JobRef
    added_by: ActorKind
    added_at: datetime = Field(default_factory=utc_now)


class AdmissionDecision(StrEnum):
    ADMITTED = "admitted"
    REJECTED = "rejected"


class AdmissionPath(StrEnum):
    PROPOSAL = "proposal"
    MANUAL = "manual"


class OpportunityAdmissionProposal(FrozenModel):
    proposal_id: OpaqueId
    job: JobRef
    proposed_by: ActorKind
    reason: str = Field(min_length=1, max_length=2048)
    proposed_at: datetime = Field(default_factory=utc_now)


class OpportunityAdmissionDecision(FrozenModel):
    decision_id: OpaqueId
    job: JobRef
    decision: AdmissionDecision
    path: AdmissionPath
    decided_by: ActorKind
    proposal_id: OpaqueId | None = None
    opportunity_id: OpaqueId | None = None
    reason: str | None = Field(default=None, max_length=2048)
    decided_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_user_authority_and_result(self) -> OpportunityAdmissionDecision:
        if self.decided_by is not ActorKind.USER:
            raise ValueError("only the user may decide opportunity admission")
        if self.path is AdmissionPath.PROPOSAL and self.proposal_id is None:
            raise ValueError("proposal admission decision requires a proposal")
        if self.path is AdmissionPath.MANUAL and self.proposal_id is not None:
            raise ValueError("manual admission decision cannot reference a proposal")
        if self.path is AdmissionPath.MANUAL and self.decision is not AdmissionDecision.ADMITTED:
            raise ValueError("manual admission path only represents an explicit admission")
        if self.decision is AdmissionDecision.ADMITTED and self.opportunity_id is None:
            raise ValueError("admitted decision requires an opportunity id")
        if self.decision is AdmissionDecision.REJECTED and self.opportunity_id is not None:
            raise ValueError("rejected decision cannot create an opportunity")
        return self


class OpportunityAdmissionResult(FrozenModel):
    decision: OpportunityAdmissionDecision
    opportunity: Opportunity | None = None

    @model_validator(mode="after")
    def validate_opportunity_matches_decision(self) -> OpportunityAdmissionResult:
        if self.decision.decision is AdmissionDecision.ADMITTED:
            if self.opportunity is None:
                raise ValueError("admitted decision must return an opportunity")
            if self.opportunity.entity_id != self.decision.opportunity_id:
                raise ValueError("admitted opportunity must match the decision")
        elif self.opportunity is not None:
            raise ValueError("rejected decision cannot return an opportunity")
        return self


class PriorityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class PriorityInputRevision(FrozenModel):
    entity_id: OpaqueId
    revision: int = Field(ge=1)


class SuggestedPriority(FrozenModel):
    opportunity_id: OpaqueId
    level: PriorityLevel
    reasons: tuple[str, ...] = Field(min_length=1)
    input_revisions: tuple[PriorityInputRevision, ...] = Field(min_length=1)
    calculated_at: datetime = Field(default_factory=utc_now)
    score: float | None = Field(default=None, ge=0, le=1)
    rank: int | None = Field(default=None, ge=1)


class UserPriority(FrozenModel):
    opportunity_id: OpaqueId
    level: PriorityLevel
    actor: ActorKind
    set_at: datetime = Field(default_factory=utc_now)
    reason: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def require_user_actor(self) -> UserPriority:
        if self.actor is not ActorKind.USER:
            raise ValueError("only the user may set user priority")
        return self


class OpportunityPriority(FrozenModel):
    opportunity_id: OpaqueId
    suggested: SuggestedPriority
    user: UserPriority | None = None

    @model_validator(mode="after")
    def require_matching_opportunity_ids(self) -> OpportunityPriority:
        if self.suggested.opportunity_id != self.opportunity_id:
            raise ValueError("suggested priority must belong to the opportunity")
        if self.user is not None and self.user.opportunity_id != self.opportunity_id:
            raise ValueError("user priority must belong to the opportunity")
        return self
