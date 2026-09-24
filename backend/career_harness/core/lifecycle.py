from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from career_harness.core.common import FrozenModel, OpaqueId, utc_now


class DomainEntity(FrozenModel):
    entity_id: OpaqueId
    revision: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)


class Candidate(DomainEntity):
    pass


class Market(DomainEntity):
    pass


class OpportunityState(StrEnum):
    DISCOVERED = "discovered"
    WATCHING = "watching"
    QUALIFIED = "qualified"
    PREPARING = "preparing"
    DECLINED = "declined"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class Opportunity(DomainEntity):
    state: OpportunityState


class Resume(DomainEntity):
    pass


class ApplicationState(StrEnum):
    PREPARING = "preparing"
    READY_FOR_REVIEW = "ready_for_review"
    SUBMITTED_BY_USER = "submitted_by_user"
    SCREEN = "screen"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CLOSED = "closed"


class SubmissionAuthority(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    PORTAL_RECEIPT = "portal_receipt"


class Application(DomainEntity):
    opportunity_id: OpaqueId
    opportunity_revision: int = Field(ge=1)
    state: ApplicationState
    resume_revision_id: OpaqueId | None = None
    submission_authority: SubmissionAuthority | None = None
    submission_evidence_ref_id: OpaqueId | None = None
    submitted_at: datetime | None = None

    @model_validator(mode="after")
    def submitted_state_requires_authority(self) -> Application:
        pre_submission = self.state in {
            ApplicationState.PREPARING,
            ApplicationState.READY_FOR_REVIEW,
        }
        submission = (
            self.resume_revision_id,
            self.submission_authority,
            self.submission_evidence_ref_id,
            self.submitted_at,
        )
        if pre_submission and any(value is not None for value in submission[1:]):
            raise ValueError("pre-submission application cannot carry submission metadata")
        if not pre_submission and any(
            value is None
            for value in (
                self.resume_revision_id,
                self.submission_authority,
                self.submitted_at,
            )
        ):
            raise ValueError(
                "submitted application requires an exact ResumeRevision, time and authority"
            )
        if (
            self.submission_authority is SubmissionAuthority.PORTAL_RECEIPT
            and self.submission_evidence_ref_id is None
        ):
            raise ValueError("portal receipt authority requires an exact EvidenceRef")
        return self


class FormPreparation(FrozenModel):
    preparation_id: OpaqueId
    opportunity_id: OpaqueId
    ready_for_review: bool = False


class InterviewRound(StrEnum):
    SCREEN = "screen"
    TECHNICAL = "technical"
    LOOP = "loop"
    OFFER_TALK = "offer_talk"


class InterviewStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Interview(DomainEntity):
    application_id: OpaqueId
    application_revision: int = Field(ge=1)
    round: InterviewRound
    scheduled_at: datetime
    status: InterviewStatus = InterviewStatus.SCHEDULED
    evidence_refs: tuple[OpaqueId, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def evidence_refs_are_unique(self) -> Interview:
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("Interview evidence refs must be unique")
        if self.revision == 1 and self.status is not InterviewStatus.SCHEDULED:
            raise ValueError("the first Interview revision must be scheduled")
        return self


class Prep(DomainEntity):
    pass


class OutcomeType(StrEnum):
    OFFER = "offer"
    REJECTION = "rejection"
    WITHDRAWAL = "withdrawal"
    CLOSED = "closed"


class OutcomeAuthority(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    PORTAL_RECEIPT = "portal_receipt"


class Outcome(DomainEntity):
    revision: int = Field(default=1, ge=1, le=1)
    application_id: OpaqueId
    application_revision: int = Field(ge=1)
    result: OutcomeType
    occurred_at: datetime = Field(default_factory=utc_now)
    authority: OutcomeAuthority
    evidence_refs: tuple[OpaqueId, ...] = ()
    recorded_by: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def receipt_authority_requires_evidence(self) -> Outcome:
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("Outcome evidence refs must be unique")
        if self.authority is OutcomeAuthority.PORTAL_RECEIPT and not self.evidence_refs:
            raise ValueError("portal receipt Outcome requires exact EvidenceRefs")
        return self


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActorKind(StrEnum):
    USER = "user"
    AGENT = "agent"
    RULE = "rule"


class ApprovalPurpose(StrEnum):
    PROJECT_CAPABILITY_RESUME_READY = "project_capability_resume_ready"


class Approval(DomainEntity):
    subject_id: OpaqueId
    subject_revision: int = Field(ge=1)
    purpose: ApprovalPurpose
    status: ApprovalStatus
    proposer_kind: ActorKind
    approver_kind: ActorKind | None = None

    @model_validator(mode="after")
    def agent_cannot_approve(self) -> Approval:
        if self.status is ApprovalStatus.APPROVED and self.approver_kind is not ActorKind.USER:
            raise ValueError("only the user may provide final approval")
        return self


class RunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Run(DomainEntity):
    state: RunState


class Snapshot(DomainEntity):
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class Environment(StrEnum):
    TEST = "TEST"
    STAGING = "STAGING"
    PROD = "PROD"


class DataClass(StrEnum):
    TEST = "TEST"
    REAL = "REAL"


class RuntimeScope(FrozenModel):
    environment: Environment
    data_class: DataClass

    @model_validator(mode="after")
    def test_data_cannot_enter_prod(self) -> RuntimeScope:
        if self.environment is Environment.PROD and self.data_class is DataClass.TEST:
            raise ValueError("TEST data cannot enter PROD")
        return self
