from __future__ import annotations

from career_harness.core.approval import ActorKind
from career_harness.core.common import OpaqueId
from career_harness.core.lifecycle import Opportunity, OpportunityState
from career_harness.core.opportunity.models import (
    AdmissionDecision,
    AdmissionPath,
    JobRef,
    OpportunityAdmissionDecision,
    OpportunityAdmissionProposal,
    OpportunityAdmissionResult,
    OpportunityPriority,
    SuggestedPriority,
)


def review_admission_proposal(
    proposal: OpportunityAdmissionProposal,
    *,
    decision_id: OpaqueId,
    decision: AdmissionDecision,
    decided_by: ActorKind,
    opportunity_id: OpaqueId | None = None,
    reason: str | None = None,
) -> OpportunityAdmissionResult:
    admission_decision = OpportunityAdmissionDecision(
        decision_id=decision_id,
        job=proposal.job,
        decision=decision,
        path=AdmissionPath.PROPOSAL,
        decided_by=decided_by,
        proposal_id=proposal.proposal_id,
        opportunity_id=opportunity_id,
        reason=reason,
    )
    opportunity = _create_opportunity(admission_decision)
    return OpportunityAdmissionResult(
        decision=admission_decision,
        opportunity=opportunity,
    )


def admit_opportunity_manually(
    job: JobRef,
    *,
    decision_id: OpaqueId,
    opportunity_id: OpaqueId,
    decided_by: ActorKind,
    reason: str | None = None,
) -> OpportunityAdmissionResult:
    admission_decision = OpportunityAdmissionDecision(
        decision_id=decision_id,
        job=job,
        decision=AdmissionDecision.ADMITTED,
        path=AdmissionPath.MANUAL,
        decided_by=decided_by,
        opportunity_id=opportunity_id,
        reason=reason,
    )
    return OpportunityAdmissionResult(
        decision=admission_decision,
        opportunity=_create_opportunity(admission_decision),
    )


def recompute_suggested_priority(
    current: OpportunityPriority,
    suggested: SuggestedPriority,
) -> OpportunityPriority:
    return OpportunityPriority(
        opportunity_id=current.opportunity_id,
        suggested=suggested,
        user=current.user,
    )


def _create_opportunity(decision: OpportunityAdmissionDecision) -> Opportunity | None:
    if decision.decision is AdmissionDecision.REJECTED:
        return None
    if decision.opportunity_id is None:  # Enforced by the decision model.
        raise ValueError("admitted decision requires an opportunity id")
    return Opportunity(
        entity_id=decision.opportunity_id,
        revision=1,
        state=OpportunityState.QUALIFIED,
    )
