from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.memory.models import (
    MemoryCreator,
    MemoryProposalStatus,
    MemoryScope,
    MemoryType,
)
from career_harness.db.memory_repository import MemoryRepository


class MemoryProposalRequest(FrozenModel):
    memory_type: MemoryType
    scope_kind: MemoryScope = MemoryScope.USER
    scope_id: str = Field(default="local-user", min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=10_000)
    source_type: str = Field(default="manual", min_length=1, max_length=64)
    source_locator: str = Field(default="manual://context", min_length=1, max_length=2048)
    source_refs: tuple[str, ...] = ()
    confidence: float = Field(default=1.0, ge=0, le=1)
    created_by: MemoryCreator = MemoryCreator.USER
    target_memory_id: str | None = None
    base_revision: int | None = Field(default=None, ge=1)


class MemoryReviewRequest(FrozenModel):
    decision: MemoryProposalStatus
    reason: str = Field(min_length=1, max_length=2048)
    edited_content: str | None = Field(default=None, max_length=10_000)


class MemoryDeleteRequest(FrozenModel):
    reason: str = Field(min_length=1, max_length=2048)


@dataclass(frozen=True, slots=True)
class MemoryApi:
    repository: MemoryRepository


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    if isinstance(error, RuntimeError):
        return HTTPException(409, str(error))
    return HTTPException(500, "memory operation failed")


def create_memory_router(api: MemoryApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

    @router.post("/proposals")
    def create_proposal(request: MemoryProposalRequest) -> Any:
        try:
            return api.repository.create_proposal(**request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.get("/proposals")
    def proposals(
        scope_kind: MemoryScope = MemoryScope.USER,
        scope_id: str = Query(default="local-user", min_length=1, max_length=128),
        status: MemoryProposalStatus = MemoryProposalStatus.PENDING,
    ) -> Any:
        return api.repository.list_proposals(
            scope_kind=scope_kind, scope_id=scope_id, status=status
        )

    @router.post("/proposals/{proposal_id}/review")
    def review(
        request: MemoryReviewRequest,
        proposal_id: str = Path(min_length=3, max_length=128),
    ) -> Any:
        try:
            return api.repository.review_proposal(
                proposal_id, reviewer="user", **request.model_dump()
            )
        except Exception as error:
            raise _error(error) from error

    @router.get("")
    def search(
        scope_kind: MemoryScope = MemoryScope.USER,
        scope_id: str = Query(default="local-user", min_length=1, max_length=128),
        query: str = Query(default="", max_length=512),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> Any:
        return api.repository.search(
            scope_kind=scope_kind, scope_id=scope_id, query=query, limit=limit
        )

    @router.post("/{memory_id}/delete")
    def delete(
        request: MemoryDeleteRequest,
        memory_id: str = Path(min_length=3, max_length=128),
    ) -> Any:
        try:
            return api.repository.tombstone(memory_id, reason=request.reason, actor="user")
        except Exception as error:
            raise _error(error) from error

    return router
