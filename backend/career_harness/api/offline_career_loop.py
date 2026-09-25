from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.resume import ResumePatchStatus
from career_harness.services.offline_career_loop_service import OfflineCareerLoopService


class OfflineCareerLoopRequest(FrozenModel):
    resume_id: str = Field(min_length=3, max_length=128)
    resume_revision_id: str = Field(min_length=3, max_length=128)
    candidate_id: str = Field(min_length=3, max_length=128)
    query: str = Field(default="platform", max_length=128)
    desired_terms: tuple[str, ...] = ()


class DemoCareerLoopRequest(FrozenModel):
    query: str = Field(default="platform", max_length=128)
    desired_terms: tuple[str, ...] = ()
    resume_id: str = Field(default="resume_demo", min_length=3, max_length=128)
    resume_revision_id: str = Field(default="resume_demo_revision", min_length=3, max_length=128)
    candidate_id: str = Field(default="candidate_demo", min_length=3, max_length=128)


class DemoResumeApprovalRequest(FrozenModel):
    patch_id: str = Field(min_length=3, max_length=128)
    application_id: str = Field(min_length=3, max_length=128)
    decision: str = Field(default="accepted", pattern=r"^(accepted|rejected)$")
    edited_value: object | None = None
    review_note: str | None = Field(default=None, max_length=2048)


class DemoResumeRevisionRequest(FrozenModel):
    application_id: str = Field(min_length=3, max_length=128)


@dataclass(frozen=True, slots=True)
class OfflineCareerLoopApi:
    service: OfflineCareerLoopService
    demo_mode: bool = False


def create_offline_career_loop_router(api: OfflineCareerLoopApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/career-loop", tags=["offline-career-loop"])

    def require_demo_mode() -> None:
        if not api.demo_mode:
            raise HTTPException(status_code=403, detail="该演示流程仅在隔离 Demo Mode 中可用")

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

    @router.post("/demo-full", status_code=status.HTTP_201_CREATED)
    def full_demo(request: DemoCareerLoopRequest):
        """Run the isolated, local Demo Story without external writes."""
        require_demo_mode()
        if api.service.resume_studio.commands.engine.dialect.name != "sqlite":
            raise HTTPException(status_code=403, detail="演示闭环仅允许本地 SQLite 数据库")
        try:
            return api.service.run_full_demo(
                resume_id=request.resume_id,
                resume_revision_id=request.resume_revision_id,
                candidate_id=request.candidate_id,
                query=request.query,
                desired_terms=request.desired_terms or ("Python", "SQLite"),
            )
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post("/demo-start", status_code=status.HTTP_201_CREATED)
    def start_demo(request: DemoCareerLoopRequest):
        require_demo_mode()
        try:
            return api.service.start_demo(
                resume_id=request.resume_id,
                resume_revision_id=request.resume_revision_id,
                candidate_id=request.candidate_id,
                query=request.query,
                desired_terms=request.desired_terms or ("Python", "SQLite"),
            )
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post("/demo-approve-resume", status_code=status.HTTP_200_OK)
    def approve_demo_resume(request: DemoResumeApprovalRequest):
        require_demo_mode()
        try:
            return api.service.approve_demo_resume(
                patch_id=request.patch_id,
                application_id=request.application_id,
                decision=ResumePatchStatus(request.decision),
                edited_value=request.edited_value,
                review_note=request.review_note,
            )
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post("/demo-resume-revision", status_code=status.HTTP_201_CREATED)
    def create_demo_revision(request: DemoResumeRevisionRequest):
        require_demo_mode()
        try:
            return api.service.create_demo_resume_revision(application_id=request.application_id)
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.get("/demo-story")
    def demo_story():
        require_demo_mode()
        return api.service.demo_story()

    return router
