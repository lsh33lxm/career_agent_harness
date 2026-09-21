from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Path
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCreatedBy,
    KnowledgeSearchPage,
    KnowledgeStatus,
    ProposalStatus,
)
from career_harness.db.knowledge_repository import KnowledgeRepository


class KnowledgeImportRequest(FrozenModel):
    content: str | None = None
    content_base64: str | None = None
    media_type: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=128)
    source_locator: str = Field(min_length=1, max_length=4096)
    category: KnowledgeCategory
    title: str = Field(min_length=1, max_length=512)
    authority: KnowledgeAuthority = KnowledgeAuthority.DOCUMENT_SUPPORTED
    created_by: KnowledgeCreatedBy = KnowledgeCreatedBy.IMPORTER
    labels: tuple[str, ...] = ()
    confidence: float = Field(default=1.0, ge=0, le=1)

    def bytes(self) -> bytes:
        if self.content_base64 is not None:
            try:
                return base64.b64decode(self.content_base64, validate=True)
            except ValueError as exc:
                raise ValueError("content_base64 is invalid") from exc
        if self.content is None:
            raise ValueError("content or content_base64 is required")
        return self.content.encode("utf-8")


class KnowledgeSearchRequest(FrozenModel):
    query: str = Field(default="", max_length=512)
    categories: tuple[KnowledgeCategory, ...] = ()
    statuses: tuple[KnowledgeStatus, ...] = (
        KnowledgeStatus.APPROVED,
        KnowledgeStatus.PROPOSED,
    )
    limit: int = Field(default=20, ge=1, le=100)
    after: str | None = Field(default=None, max_length=128)
    mode: str = Field(default="hybrid", pattern=r"^(lexical|hybrid)$")
    include_flagged: bool = False
    allowed_categories: tuple[KnowledgeCategory, ...] = ()
    redact_sensitive: bool = False


class KnowledgeProposalRequest(FrozenModel):
    category: KnowledgeCategory
    title: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1)
    authority: KnowledgeAuthority = KnowledgeAuthority.AI_INFERRED
    created_by: KnowledgeCreatedBy = KnowledgeCreatedBy.LLM
    evidence_refs: tuple[str, ...] = ()
    target_knowledge_id: str | None = None
    base_revision: int | None = Field(default=None, ge=1)


class KnowledgeReviewRequest(FrozenModel):
    decision: ProposalStatus
    reviewer: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=2048)


class KnowledgeRollbackRequest(FrozenModel):
    target_revision: int = Field(ge=1)
    reviewer: str = Field(min_length=1, max_length=255)


IdempotencyHeader = Annotated[
    str | None, Header(alias="X-Idempotency-Key", min_length=8, max_length=255)
]


@dataclass(frozen=True, slots=True)
class KnowledgeApi:
    repository: KnowledgeRepository


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    if isinstance(error, RuntimeError):
        return HTTPException(409, str(error))
    return HTTPException(500, "knowledge operation failed")


def create_knowledge_router(api: KnowledgeApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["knowledge"])

    @router.post("/knowledge/import")
    def import_document(request: KnowledgeImportRequest) -> Any:
        try:
            return api.repository.import_document(
                content=request.bytes(),
                media_type=request.media_type,
                source_type=request.source_type,
                source_locator=request.source_locator,
                category=request.category,
                title=request.title,
                authority=request.authority,
                created_by=request.created_by,
                labels=request.labels,
                confidence=request.confidence,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post("/knowledge/search", response_model=KnowledgeSearchPage)
    def search(request: KnowledgeSearchRequest) -> KnowledgeSearchPage:
        try:
            return api.repository.search(
                query=request.query,
                categories=request.categories,
                statuses=request.statuses,
                limit=request.limit,
                after=request.after,
                mode=request.mode,
                include_flagged=request.include_flagged,
                allowed_categories=request.allowed_categories,
                redact_sensitive=request.redact_sensitive,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post("/knowledge/proposals")
    def create_proposal(request: KnowledgeProposalRequest) -> Any:
        try:
            return api.repository.create_proposal(**request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.get("/knowledge/proposals/{proposal_id}")
    def get_proposal(proposal_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.get_proposal(proposal_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/knowledge/proposals/{proposal_id}/review")
    def review_proposal(
        request: KnowledgeReviewRequest,
        proposal_id: str = Path(min_length=3, max_length=128),
    ) -> Any:
        try:
            return api.repository.review_proposal(proposal_id, **request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.get("/wiki/pages/{knowledge_id}/revisions")
    def revisions(knowledge_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.list_revisions(knowledge_id)
        except Exception as error:
            raise _error(error) from error

    @router.get("/wiki/graph")
    def wiki_graph() -> Any:
        return api.repository.wiki_graph()

    @router.get("/wiki/health")
    def wiki_health() -> Any:
        return api.repository.wiki_health()

    @router.get("/wiki/pages/{knowledge_id}/diff")
    def diff(
        knowledge_id: str = Path(min_length=3, max_length=128),
        left_revision: int = 1,
        right_revision: int = 1,
    ) -> dict[str, str]:
        try:
            return {
                "knowledge_id": knowledge_id,
                "diff": api.repository.diff(knowledge_id, left_revision, right_revision),
            }
        except Exception as error:
            raise _error(error) from error

    @router.post("/wiki/pages/{knowledge_id}/rollback")
    def rollback(
        request: KnowledgeRollbackRequest,
        knowledge_id: str = Path(min_length=3, max_length=128),
    ) -> Any:
        try:
            return api.repository.rollback(knowledge_id, **request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.post("/knowledge/index/rebuild")
    def rebuild_index(knowledge_id: str | None = None) -> dict[str, int]:
        try:
            return {"revisions": api.repository.rebuild_index(knowledge_id)}
        except Exception as error:
            raise _error(error) from error

    return router
