from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.services.offline_career_loop_service import OfflineCareerLoopService


class OfflineCareerLoopRequest(FrozenModel):
    resume_id: str = Field(min_length=3, max_length=128)
    resume_revision_id: str = Field(min_length=3, max_length=128)
    candidate_id: str = Field(min_length=3, max_length=128)
    query: str = Field(default="platform", max_length=128)
    desired_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OfflineCareerLoopApi:
    service: OfflineCareerLoopService


def create_offline_career_loop_router(api: OfflineCareerLoopApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/career-loop", tags=["offline-career-loop"])

    @router.post("/offline", status_code=status.HTTP_201_CREATED)
    def run(request: OfflineCareerLoopRequest):
        try:
            return api.service.run(
                resume_id=request.resume_id,
                resume_revision_id=request.resume_revision_id,
                candidate_id=request.candidate_id,
                query=request.query,
                desired_terms=request.desired_terms or ("Python", "SQLite"),
            )
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return router
