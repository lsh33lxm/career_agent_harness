from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from career_harness.core.common import FrozenModel, OpaqueId


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
    state: ApplicationState
    submission_authority: SubmissionAuthority | None = None

    @model_validator(mode="after")
    def submitted_state_requires_authority(self) -> Application:
        submitted_or_later = self.state not in {
            ApplicationState.PREPARING,
            ApplicationState.READY_FOR_REVIEW,
        }
        if submitted_or_later and self.submission_authority is None:
            raise ValueError("submitted application state requires user confirmation or receipt")
        if not submitted_or_later and self.submission_authority is not None:
            raise ValueError("prepared application cannot carry submission authority")
        return self


class FormPreparation(FrozenModel):
    preparation_id: OpaqueId
    opportunity_id: OpaqueId
    ready_for_review: bool = False


class Interview(DomainEntity):
    application_id: OpaqueId


class Prep(DomainEntity):
    pass


class Outcome(DomainEntity):
    pass


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

