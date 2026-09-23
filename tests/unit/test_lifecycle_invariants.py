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
from career_harness.core.outcome import Outcome, OutcomeAuthority, OutcomeType
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
        opportunity_revision=1,
        state=ApplicationState.READY_FOR_REVIEW,
    )

    assert application.submission_authority is None
    with pytest.raises(ValidationError, match="exact ResumeRevision, time and authority"):
        Application(
            entity_id="application_001",
            revision=2,
            opportunity_id="opportunity_001",
            opportunity_revision=1,
            state=ApplicationState.SUBMITTED_BY_USER,
        )


def test_verified_submission_requires_explicit_authority() -> None:
    application = Application(
        entity_id="application_001",
        revision=2,
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        state=ApplicationState.SUBMITTED_BY_USER,
        resume_revision_id="resume_revision_001",
        submission_authority=SubmissionAuthority.USER_CONFIRMED,
        submitted_at="2026-09-20T00:00:00Z",
    )

    assert application.submission_authority is SubmissionAuthority.USER_CONFIRMED


def test_workflow_state_does_not_change_business_state() -> None:
    application = Application(
        entity_id="application_001",
        revision=1,
        opportunity_id="opportunity_001",
        opportunity_revision=1,
        state=ApplicationState.PREPARING,
    )
    run = Run(entity_id="run_001", revision=1, state=RunState.WAITING_HUMAN)

    assert run.state is RunState.WAITING_HUMAN
    assert application.state is ApplicationState.PREPARING


def test_portal_receipt_submission_requires_exact_evidence() -> None:
    with pytest.raises(ValidationError, match="exact EvidenceRef"):
        Application(
            entity_id="application_001",
            revision=2,
            opportunity_id="opportunity_001",
            opportunity_revision=1,
            state=ApplicationState.SUBMITTED_BY_USER,
            resume_revision_id="resume_revision_001",
            submission_authority=SubmissionAuthority.PORTAL_RECEIPT,
            submitted_at="2026-09-20T00:00:00Z",
        )


def test_outcome_is_exact_single_revision_truth() -> None:
    outcome = Outcome(
        entity_id="outcome_001",
        application_id="application_001",
        application_revision=3,
        result=OutcomeType.OFFER,
        authority=OutcomeAuthority.USER_CONFIRMED,
        recorded_by="user",
    )
    assert outcome.revision == 1
    assert outcome.application_revision == 3

    with pytest.raises(ValidationError, match="exact EvidenceRefs"):
        Outcome(
            entity_id="outcome_002",
            application_id="application_001",
            application_revision=3,
            result=OutcomeType.REJECTION,
            authority=OutcomeAuthority.PORTAL_RECEIPT,
            recorded_by="adapter:portal",
        )


def test_agent_cannot_provide_final_approval() -> None:
    with pytest.raises(ValidationError, match="only the user"):
        Approval(
            entity_id="approval_001",
            revision=1,
            subject_id="project_capability_001",
            subject_revision=2,
            purpose="project_capability_resume_ready",
            status=ApprovalStatus.APPROVED,
            proposer_kind=ActorKind.AGENT,
            approver_kind=ActorKind.AGENT,
        )


def test_test_data_cannot_enter_prod() -> None:
    with pytest.raises(ValidationError, match="TEST data"):
        RuntimeScope(environment=Environment.PROD, data_class=DataClass.TEST)
