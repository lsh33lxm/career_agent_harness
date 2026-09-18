from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from career_harness.core.approval import ActorKind
from career_harness.core.commands import Command, RevisionConflict
from career_harness.core.common import EntityKind, EntityRef, OpaqueId
from career_harness.core.opportunity import (
    JobRef,
    OpportunityAdmissionProposal,
    OpportunityDetail,
    PriorityLevel,
)
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.services.command_service import IdempotencyConflict
from career_harness.services.opportunity_service import (
    OpportunityAdmissionCommit,
    OpportunityService,
)

IdempotencyHeader = Annotated[
    str,
    Header(alias="X-Idempotency-Key", min_length=8, max_length=255),
]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManualAdmissionRequest(ApiModel):
    command_id: OpaqueId
    opportunity_id: OpaqueId | None = None
    decision_id: OpaqueId | None = None
    job_id: OpaqueId
    job_revision: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2048)


class UserPriorityRequest(ApiModel):
    command_id: OpaqueId
    expected_revision: int = Field(ge=1)
    level: PriorityLevel
    reason: str | None = Field(default=None, max_length=2048)


class ProposalAdmissionRequest(ManualAdmissionRequest):
    proposal_id: OpaqueId
    proposal_reason: str = Field(min_length=1, max_length=2048)
    proposed_by: ActorKind = ActorKind.AGENT


@dataclass(frozen=True, slots=True)
class OpportunityApi:
    repository: OpportunityRepository
    service: OpportunityService


def _translate_conflict(error: Exception) -> HTTPException:
    detail = (
        "opportunity conflicts with existing canonical state"
        if isinstance(error, IntegrityError)
        else str(error)
    )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def create_opportunity_router(api: OpportunityApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])

    @router.get("", response_model=list[OpportunityDetail])
    def list_opportunities() -> tuple[OpportunityDetail, ...]:
        return api.repository.list()

    @router.get("/{opportunity_id}", response_model=OpportunityDetail)
    def get_opportunity(opportunity_id: str) -> OpportunityDetail:
        detail = api.repository.get(opportunity_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="opportunity not found",
            )
        return detail

    @router.post(
        "/manual-admissions",
        response_model=OpportunityAdmissionCommit,
        status_code=status.HTTP_201_CREATED,
    )
    def admit_manually(
        request: ManualAdmissionRequest,
        idempotency_key: IdempotencyHeader,
    ) -> OpportunityAdmissionCommit:
        opportunity_id, decision_id = api.service.admission_ids(
            request.command_id,
            opportunity_id=request.opportunity_id,
            decision_id=request.decision_id,
        )
        command = Command(
            command_id=request.command_id,
            command_type="opportunity.admit_manual",
            target=EntityRef(
                entity_id=opportunity_id,
                kind=EntityKind.OPPORTUNITY,
            ),
            expected_revision=0,
            idempotency_key=idempotency_key,
            actor="user",
        )
        try:
            return api.service.admit_manually(
                command,
                JobRef(job_id=request.job_id, revision=request.job_revision),
                opportunity_id=opportunity_id,
                decision_id=decision_id,
                reason=request.reason,
            )
        except (RevisionConflict, IdempotencyConflict, IntegrityError) as error:
            raise _translate_conflict(error) from error

    @router.post(
        "/proposal-admissions",
        response_model=OpportunityAdmissionCommit,
        status_code=status.HTTP_201_CREATED,
    )
    def admit_proposal(
        request: ProposalAdmissionRequest,
        idempotency_key: IdempotencyHeader,
    ) -> OpportunityAdmissionCommit:
        if request.proposed_by is ActorKind.USER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="user-originated opportunities use manual admission",
            )
        opportunity_id, decision_id = api.service.admission_ids(
            request.command_id,
            opportunity_id=request.opportunity_id,
            decision_id=request.decision_id,
        )
        command = Command(
            command_id=request.command_id,
            command_type="opportunity.admit_proposal",
            target=EntityRef(
                entity_id=opportunity_id,
                kind=EntityKind.OPPORTUNITY,
            ),
            expected_revision=0,
            idempotency_key=idempotency_key,
            actor="user",
        )
        proposal = OpportunityAdmissionProposal(
            proposal_id=request.proposal_id,
            job=JobRef(job_id=request.job_id, revision=request.job_revision),
            proposed_by=request.proposed_by,
            reason=request.proposal_reason,
        )
        try:
            return api.service.review_proposal(
                command,
                proposal,
                decision_id=decision_id,
                opportunity_id=opportunity_id,
                reason=request.reason,
            )
        except (RevisionConflict, IdempotencyConflict, IntegrityError) as error:
            raise _translate_conflict(error) from error

    @router.patch("/{opportunity_id}/user-priority", response_model=CommandCommitResult)
    def set_user_priority(
        opportunity_id: str,
        request: UserPriorityRequest,
        idempotency_key: IdempotencyHeader,
    ) -> CommandCommitResult:
        command = Command(
            command_id=request.command_id,
            command_type="opportunity.set_user_priority",
            target=EntityRef(entity_id=opportunity_id, kind=EntityKind.OPPORTUNITY),
            expected_revision=request.expected_revision,
            idempotency_key=idempotency_key,
            actor="user",
        )
        try:
            return api.service.set_user_priority(
                command,
                level=request.level,
                reason=request.reason,
            )
        except (RevisionConflict, IdempotencyConflict) as error:
            raise _translate_conflict(error) from error
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return router
