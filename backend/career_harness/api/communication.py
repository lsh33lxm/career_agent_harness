from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.communication import (
    CommunicationChannel,
    CommunicationDraft,
    CommunicationStatus,
)
from career_harness.db.communication_repository import CommunicationRepository


class CommunicationDraftRequest(FrozenModel):
    draft_id: str = Field(min_length=3, max_length=128)
    opportunity_id: str = Field(min_length=3, max_length=128)
    source_staging_id: str | None = Field(default=None, max_length=128)
    channel: CommunicationChannel
    recipient: str | None = Field(default=None, max_length=512)
    body: str = Field(min_length=1, max_length=10000)
    provenance: dict[str, str] = Field(default_factory=dict)


class CommunicationReviewRequest(FrozenModel):
    decision: CommunicationStatus
    reason: str = Field(min_length=1, max_length=2048)


@dataclass(frozen=True, slots=True)
class CommunicationApi:
    repository: CommunicationRepository


def create_communication_router(api: CommunicationApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/communications", tags=["communications"])

    @router.post("/drafts", status_code=201)
    def create(request: CommunicationDraftRequest):
        try:
            return api.repository.create(
                CommunicationDraft(**request.model_dump(), created_by="user")
            )
        except Exception as error:
            raise HTTPException(422, str(error)) from error

    @router.get("/drafts")
    def list_drafts(status: CommunicationStatus | None = None):
        return api.repository.list(status)

    @router.post("/drafts/{draft_id}/review")
    def review(draft_id: str, request: CommunicationReviewRequest):
        try:
            return api.repository.review(draft_id, decision=request.decision, reason=request.reason)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    return router
