"""User-qualified opportunity boundary; not an application."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Opportunity, OpportunityState
from career_harness.core.opportunity.models import (
    AdmissionDecision,
    AdmissionPath,
    JobRef,
    OpportunityAdmissionDecision,
    OpportunityAdmissionProposal,
    OpportunityAdmissionResult,
    OpportunityPriority,
    PriorityInputRevision,
    PriorityLevel,
    SuggestedPriority,
    UserPriority,
    WatchlistItem,
)
from career_harness.core.opportunity.policies import (
    admit_opportunity_manually,
    recompute_suggested_priority,
    review_admission_proposal,
)

ENTITY_KIND = EntityKind.OPPORTUNITY

__all__ = [
    "AdmissionDecision",
    "AdmissionPath",
    "ENTITY_KIND",
    "JobRef",
    "Opportunity",
    "OpportunityAdmissionDecision",
    "OpportunityAdmissionProposal",
    "OpportunityAdmissionResult",
    "OpportunityPriority",
    "OpportunityState",
    "PriorityInputRevision",
    "PriorityLevel",
    "SuggestedPriority",
    "UserPriority",
    "WatchlistItem",
    "admit_opportunity_manually",
    "recompute_suggested_priority",
    "review_admission_proposal",
]
