from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from career_harness.core.capability import CandidateCapabilityNode
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef, OpaqueId
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.services.capability_review_service import (
    CandidateReviewCommit,
    CapabilityReviewService,
)
from career_harness.services.command_service import CommandService


class InboxItem(BaseModel):
    candidate: CandidateCapabilityNode
    revision: int = Field(ge=1)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: OpaqueId
    expected_revision: int = Field(ge=1, strict=True)
    decision: Literal["accept", "reject"]
    reason: str = Field(min_length=1, max_length=2048)

    @field_validator("reason")
    @classmethod
    def reason_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review reason must be nonblank")
        return value


@dataclass(frozen=True, slots=True)
class CapabilityInboxApi:
    repository: CapabilityRepository
    commands: CommandService
    service: CapabilityReviewService


def _conflict() -> HTTPException:
    return HTTPException(409, "capability inbox conflicts with canonical state; refresh required")


def create_capability_inbox_router(api: CapabilityInboxApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/capability-inbox", tags=["capability-inbox"])

    def read_items() -> tuple[InboxItem, ...]:
        try:
            items = []
            for candidate in api.repository.list_candidates():
                ref = EntityRef(
                    entity_id=candidate.candidate_node_id, kind=EntityKind.CAPABILITY_CANDIDATE
                )
                current = api.commands.get(ref)
                if (
                    current is None
                    or current.entity != ref
                    or CandidateCapabilityNode.model_validate(current.state) != candidate
                ):
                    raise ValueError("inconsistent candidate audit")
                items.append(InboxItem(candidate=candidate, revision=current.revision))
            return tuple(sorted(items, key=lambda item: item.candidate.candidate_node_id))
        except (ValueError, RuntimeError, TypeError, SQLAlchemyError):
            raise _conflict() from None

    def find_item(candidate_id: str) -> InboxItem:
        item = next(
            (item for item in read_items() if item.candidate.candidate_node_id == candidate_id),
            None,
        )
        if item is None:
            raise HTTPException(404, "capability candidate not found")
        return item

    @router.get("", response_model=tuple[InboxItem, ...])
    def list_candidates() -> tuple[InboxItem, ...]:
        return read_items()

    @router.get("/{candidate_id}", response_model=InboxItem)
    def get_candidate(candidate_id: OpaqueId) -> InboxItem:
        return find_item(candidate_id)

    @router.post("/{candidate_id}/review", response_model=CandidateReviewCommit)
    def review_candidate(
        candidate_id: OpaqueId,
        request: ReviewRequest,
        idempotency_key: Annotated[
            str, Header(alias="X-Idempotency-Key", min_length=8, max_length=255)
        ],
    ) -> CandidateReviewCommit:
        find_item(candidate_id)  # Validate provenance without pre-rejecting terminal replay.
        command = Command(
            command_id=request.command_id,
            command_type="capability_candidate.review",
            target=EntityRef(entity_id=candidate_id, kind=EntityKind.CAPABILITY_CANDIDATE),
            expected_revision=request.expected_revision,
            idempotency_key=idempotency_key,
            actor="user",
        )
        try:
            return api.service.review_candidate(
                command,
                candidate_node_id=candidate_id,
                decision=request.decision,
                reason=request.reason,
            )
        except (ValueError, RuntimeError, SQLAlchemyError):
            raise _conflict() from None

    return router
