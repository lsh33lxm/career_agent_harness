from types import SimpleNamespace

import pytest

from career_harness.services.outcome_insight_service import OutcomeInsightService


class _Applications:
    def __init__(self, applications, outcomes):
        self.applications = applications
        self.outcomes = outcomes

    def get(self, application_id):
        return next((item for item in self.applications if item.entity_id == application_id), None)

    def list(self):
        return tuple(self.applications)

    def list_outcomes(self, application_id):
        return tuple(self.outcomes.get(application_id, ()))


class _Knowledge:
    def __init__(self):
        self.calls = []

    def create_proposal(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(**kwargs)


def _outcome(outcome_id, result, refs=()):
    return SimpleNamespace(
        entity_id=outcome_id, result=SimpleNamespace(value=result), evidence_refs=refs
    )


def test_offer_preparation_is_evidence_bounded_proposal():
    knowledge = _Knowledge()
    service = OutcomeInsightService(
        _Applications(
            [SimpleNamespace(entity_id="application_1")],
            {"application_1": [_outcome("offer_1", "offer", ("e1",))]},
        ),
        knowledge,
    )
    proposal = service.propose_offer_preparation("application_1")
    assert proposal.evidence_refs == ("e1",)
    assert "待用户审核" in proposal.content
    assert "薪资" in proposal.content
    replay = service.propose_offer_preparation("application_1")
    assert replay.proposal_id == proposal.proposal_id
    assert knowledge.calls[0]["proposal_id"] == "proposal_outcome_offer_application_1"


def test_rejection_pattern_never_invents_reason():
    knowledge = _Knowledge()
    service = OutcomeInsightService(
        _Applications(
            [
                SimpleNamespace(entity_id="application_1"),
                SimpleNamespace(entity_id="application_2"),
            ],
            {
                "application_1": [_outcome("reject_1", "rejection")],
                "application_2": [_outcome("reject_2", "rejection")],
            },
        ),
        knowledge,
    )
    proposal = service.propose_rejection_pattern()
    assert "拒信数量：2" in proposal.content
    assert "原因已知" in proposal.content
    assert knowledge.calls[0]["proposal_id"] == "proposal_outcome_rejection_pattern"


def test_offer_preparation_requires_recorded_offer():
    service = OutcomeInsightService(
        _Applications(
            [SimpleNamespace(entity_id="application_1")],
            {"application_1": [_outcome("reject_1", "rejection")]},
        ),
        _Knowledge(),
    )
    with pytest.raises(ValueError, match="Offer"):
        service.propose_offer_preparation("application_1")
