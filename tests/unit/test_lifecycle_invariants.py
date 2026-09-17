import pytest
from pydantic import ValidationError

from career_harness.core.application import (
    Application,
    ApplicationState,
    FormPreparation,
    SubmissionAuthority,
)
from career_harness.core.approval import ActorKind, Approval, ApprovalStatus
from career_harness.core.lifecycle import DataClass, Environment, RuntimeScope
from career_harness.core.opportunity import Opportunity, OpportunityState
from career_harness.core.run import Run, RunState


def test_opportunity_and_application_are_distinct_types() -> None:
    opportunity = Opportunity(
        entity_id="opportunity_001", revision=1, state=OpportunityState.QUALIFIED
    )

    assert not isinstance(opportunity, Application)


def test_prepared_is_not_submitted() -> None:
    preparation = FormPreparation(
        preparation_id="preparation_001",
        opportunity_id="opportunity_001",
        ready_for_review=True,
    )
    application = Application(
        entity_id="application_001",
        revision=1,
        opportunity_id=preparation.opportunity_id,
        state=ApplicationState.READY_FOR_REVIEW,
    )

    assert application.submission_authority is None
    with pytest.raises(ValidationError, match="requires user confirmation or receipt"):
        Application(
            entity_id="application_001",
            revision=2,
            opportunity_id="opportunity_001",
            state=ApplicationState.SUBMITTED_BY_USER,
        )


def test_verified_submission_requires_explicit_authority() -> None:
    application = Application(
        entity_id="application_001",
        revision=2,
        opportunity_id="opportunity_001",
        state=ApplicationState.SUBMITTED_BY_USER,
        submission_authority=SubmissionAuthority.USER_CONFIRMED,
    )

    assert application.submission_authority is SubmissionAuthority.USER_CONFIRMED


def test_workflow_state_does_not_change_business_state() -> None:
    application = Application(
        entity_id="application_001",
        revision=1,
        opportunity_id="opportunity_001",
        state=ApplicationState.PREPARING,
    )
    run = Run(entity_id="run_001", revision=1, state=RunState.WAITING_HUMAN)

    assert run.state is RunState.WAITING_HUMAN
    assert application.state is ApplicationState.PREPARING


def test_agent_cannot_provide_final_approval() -> None:
    with pytest.raises(ValidationError, match="only the user"):
        Approval(
            entity_id="approval_001",
            revision=1,
            status=ApprovalStatus.APPROVED,
            proposer_kind=ActorKind.AGENT,
            approver_kind=ActorKind.AGENT,
        )


def test_test_data_cannot_enter_prod() -> None:
    with pytest.raises(ValidationError, match="TEST data"):
        RuntimeScope(environment=Environment.PROD, data_class=DataClass.TEST)

