import pytest
from pydantic import ValidationError

from career_harness.core.application import Application
from career_harness.core.approval import ActorKind
from career_harness.core.opportunity import (
    AdmissionDecision,
    JobRef,
    Opportunity,
    OpportunityAdmissionProposal,
    OpportunityPriority,
    OpportunityState,
    PriorityInputRevision,
    PriorityLevel,
    SuggestedPriority,
    UserPriority,
    WatchlistItem,
    admit_opportunity_manually,
    recompute_suggested_priority,
    review_admission_proposal,
)


def job_ref() -> JobRef:
    return JobRef(job_id="job_001", revision=3)


def suggested_priority(level: PriorityLevel) -> SuggestedPriority:
    return SuggestedPriority(
        opportunity_id="opportunity_001",
        level=level,
        reasons=("deadline changed",),
        input_revisions=(
            PriorityInputRevision(entity_id="job_001", revision=3),
        ),
    )


def test_watchlist_item_is_not_an_opportunity_or_application() -> None:
    watchlist_item = WatchlistItem(
        watchlist_item_id="watchlist_001",
        job=job_ref(),
        added_by=ActorKind.USER,
    )

    assert not isinstance(watchlist_item, Opportunity)
    assert not isinstance(watchlist_item, Application)


def test_ai_proposal_cannot_admit_an_opportunity() -> None:
    proposal = OpportunityAdmissionProposal(
        proposal_id="proposal_001",
        job=job_ref(),
        proposed_by=ActorKind.AGENT,
        reason="Strong fit with the user's target direction",
    )

    with pytest.raises(ValidationError, match="only the user may decide"):
        review_admission_proposal(
            proposal,
            decision_id="decision_001",
            decision=AdmissionDecision.ADMITTED,
            decided_by=ActorKind.AGENT,
            opportunity_id="opportunity_001",
        )


def test_user_can_admit_an_ai_proposal() -> None:
    proposal = OpportunityAdmissionProposal(
        proposal_id="proposal_001",
        job=job_ref(),
        proposed_by=ActorKind.AGENT,
        reason="Strong fit with the user's target direction",
    )

    result = review_admission_proposal(
        proposal,
        decision_id="decision_001",
        decision=AdmissionDecision.ADMITTED,
        decided_by=ActorKind.USER,
        opportunity_id="opportunity_001",
        reason="Worth focused preparation",
    )

    assert result.decision.proposal_id == proposal.proposal_id
    assert result.opportunity is not None
    assert result.opportunity.state is OpportunityState.QUALIFIED


def test_user_rejection_does_not_create_an_opportunity() -> None:
    proposal = OpportunityAdmissionProposal(
        proposal_id="proposal_001",
        job=job_ref(),
        proposed_by=ActorKind.AGENT,
        reason="Potential fit",
    )

    result = review_admission_proposal(
        proposal,
        decision_id="decision_001",
        decision=AdmissionDecision.REJECTED,
        decided_by=ActorKind.USER,
        reason="Not worth the current investment",
    )

    assert result.decision.decision is AdmissionDecision.REJECTED
    assert result.opportunity is None


def test_user_can_manually_admit_without_a_proposal() -> None:
    result = admit_opportunity_manually(
        job_ref(),
        decision_id="decision_001",
        opportunity_id="opportunity_001",
        decided_by=ActorKind.USER,
        reason="Added directly by the user",
    )

    assert result.decision.proposal_id is None
    assert result.opportunity is not None
    assert result.opportunity.entity_id == "opportunity_001"


def test_suggested_and_user_priorities_are_independent() -> None:
    user_priority = UserPriority(
        opportunity_id="opportunity_001",
        level=PriorityLevel.MEDIUM,
        actor=ActorKind.USER,
        reason="Balanced against another role",
    )
    priorities = OpportunityPriority(
        opportunity_id="opportunity_001",
        suggested=suggested_priority(PriorityLevel.HIGH),
        user=user_priority,
    )

    assert priorities.suggested.level is PriorityLevel.HIGH
    assert priorities.user is not None
    assert priorities.user.level is PriorityLevel.MEDIUM


def test_recomputing_suggested_priority_preserves_user_priority() -> None:
    user_priority = UserPriority(
        opportunity_id="opportunity_001",
        level=PriorityLevel.HIGH,
        actor=ActorKind.USER,
    )
    priorities = OpportunityPriority(
        opportunity_id="opportunity_001",
        suggested=suggested_priority(PriorityLevel.MEDIUM),
        user=user_priority,
    )

    recomputed = recompute_suggested_priority(
        priorities,
        suggested_priority(PriorityLevel.URGENT),
    )

    assert recomputed.suggested.level is PriorityLevel.URGENT
    assert recomputed.user == user_priority


def test_suggested_priority_for_another_opportunity_cannot_be_recomputed() -> None:
    priorities = OpportunityPriority(
        opportunity_id="opportunity_001",
        suggested=suggested_priority(PriorityLevel.MEDIUM),
    )
    unrelated_suggestion = SuggestedPriority(
        opportunity_id="opportunity_002",
        level=PriorityLevel.HIGH,
        reasons=("different opportunity",),
        input_revisions=(
            PriorityInputRevision(entity_id="job_002", revision=1),
        ),
    )

    with pytest.raises(ValidationError, match="must belong to the opportunity"):
        recompute_suggested_priority(priorities, unrelated_suggestion)


def test_agent_cannot_set_user_priority() -> None:
    with pytest.raises(ValidationError, match="only the user may set"):
        UserPriority(
            opportunity_id="opportunity_001",
            level=PriorityLevel.HIGH,
            actor=ActorKind.AGENT,
        )
