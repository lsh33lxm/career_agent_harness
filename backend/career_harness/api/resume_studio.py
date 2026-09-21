from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Query, Response, status
from pydantic import Field

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef, FrozenModel, OpaqueId
from career_harness.core.resume import (
    ResumeAtsReport,
    ResumePatch,
    ResumePatchOperation,
    ResumePatchStatus,
    ResumeRenderRun,
    ResumeRevision,
    ResumeStudioDiff,
    ResumeTargetProfile,
    ResumeTemplateRegistration,
    RevisionRef,
)
from career_harness.services.resume_studio_service import ResumeStudioService

IdempotencyHeader = Annotated[
    str, Header(alias="X-Idempotency-Key", min_length=8, max_length=255)
]


class TargetProfileRequest(FrozenModel):
    target_profile_id: OpaqueId
    resume_id: OpaqueId
    title: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    opportunity_id: OpaqueId | None = None
    opportunity_revision: int | None = Field(default=None, ge=1)
    requirement_refs: tuple[RevisionRef, ...] = ()
    keyword_gaps: tuple[str, ...] = ()


class PatchProposalRequest(FrozenModel):
    command_id: OpaqueId
    patch_id: OpaqueId
    target_profile_id: OpaqueId
    resume_id: OpaqueId
    base_revision: int = Field(ge=1)
    operations: tuple[ResumePatchOperation, ...] = Field(min_length=1, max_length=128)
    generator_run_id: OpaqueId | None = None
    actor: str = Field(default="agent:resume-studio", min_length=1, max_length=255)


class PatchReviewRequest(FrozenModel):
    command_id: OpaqueId
    expected_revision: int = Field(ge=1)
    decision: ResumePatchStatus
    review_reason: str = Field(min_length=1, max_length=2048)


class ResumeRevisionRequest(FrozenModel):
    command_id: OpaqueId
    resume_id: OpaqueId
    base_revision: int = Field(ge=1)
    accepted_patch_refs: tuple[RevisionRef, ...] = ()


class RenderRequest(FrozenModel):
    resume_revision_id: OpaqueId
    target_profile_id: OpaqueId | None = None
    template_id: OpaqueId | None = None
    actor: str = Field(default="user", min_length=1, max_length=255)


@dataclass(frozen=True, slots=True)
class ResumeStudioApi:
    service: ResumeStudioService


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, ValueError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    if isinstance(error, RuntimeError):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "resume studio operation failed")


def _command(
    *,
    command_id: str,
    kind: EntityKind,
    entity_id: str,
    expected_revision: int,
    idempotency_key: str,
    actor: str,
    command_type: str,
) -> Command:
    return Command(
        command_id=command_id,
        command_type=command_type,
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=idempotency_key,
        actor=actor,
    )


def create_resume_studio_router(api: ResumeStudioApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/resume", tags=["resume-studio"])

    @router.get("/templates", response_model=list[ResumeTemplateRegistration])
    def list_templates() -> tuple[ResumeTemplateRegistration, ...]:
        api.service.ensure_builtin_template()
        return api.service.repository.list_templates()

    @router.post(
        "/target-profiles",
        response_model=ResumeTargetProfile,
        status_code=status.HTTP_201_CREATED,
    )
    def create_target_profile(request: TargetProfileRequest) -> ResumeTargetProfile:
        try:
            return api.service.create_target_profile(
                target_profile_id=request.target_profile_id,
                resume_id=request.resume_id,
                title=request.title,
                company=request.company,
                opportunity_id=request.opportunity_id,
                opportunity_revision=request.opportunity_revision,
                requirement_refs=request.requirement_refs,
                keyword_gaps=request.keyword_gaps,
                actor="user",
            )
        except Exception as error:
            raise _error(error) from error

    @router.get("/target-profiles", response_model=list[ResumeTargetProfile])
    def list_target_profiles(
        resume_id: str | None = Query(default=None, min_length=3, max_length=128),
    ) -> tuple[ResumeTargetProfile, ...]:
        return api.service.repository.list_target_profiles(resume_id)

    @router.get(
        "/target-profiles/{target_profile_id}", response_model=ResumeTargetProfile
    )
    def get_target_profile(
        target_profile_id: str = Path(min_length=3, max_length=128),
    ) -> ResumeTargetProfile:
        result = api.service.repository.get_target_profile(target_profile_id)
        if result is None:
            raise HTTPException(404, "target profile not found")
        return result

    @router.post(
        "/patch-proposals", response_model=ResumePatch, status_code=status.HTTP_201_CREATED
    )
    def propose_patch(
        request: PatchProposalRequest,
        idempotency_key: IdempotencyHeader,
    ) -> ResumePatch:
        command = _command(
            command_id=request.command_id,
            kind=EntityKind.RESUME_PATCH,
            entity_id=request.patch_id,
            expected_revision=0,
            idempotency_key=idempotency_key,
            actor=request.actor,
            command_type="resume.patch.propose",
        )
        try:
            return api.service.propose_patch(
                command,
                target_profile_id=request.target_profile_id,
                resume_id=request.resume_id,
                base_revision=request.base_revision,
                operations=request.operations,
                generator_run_id=request.generator_run_id,
            )
        except Exception as error:
            raise _error(error) from error

    @router.get("/patches/{patch_id}", response_model=ResumePatch)
    def get_patch(
        patch_id: str = Path(min_length=3, max_length=128),
        revision: int | None = Query(default=None, ge=1),
    ) -> ResumePatch:
        result = api.service.repository.resumes.get_patch(patch_id, revision)
        if result is None:
            raise HTTPException(404, "resume patch not found")
        return result

    @router.post("/patches/{patch_id}/review", response_model=ResumePatch)
    def review_patch(
        request: PatchReviewRequest,
        idempotency_key: IdempotencyHeader,
        patch_id: str = Path(min_length=3, max_length=128),
    ) -> ResumePatch:
        command = _command(
            command_id=request.command_id,
            kind=EntityKind.RESUME_PATCH,
            entity_id=patch_id,
            expected_revision=request.expected_revision,
            idempotency_key=idempotency_key,
            actor="user",
            command_type="resume.patch.review",
        )
        try:
            return api.service.resumes.review_patch(
                command,
                decision=request.decision,
                review_reason=request.review_reason,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post(
        "/revisions", response_model=ResumeRevision, status_code=status.HTTP_201_CREATED
    )
    def create_revision(
        request: ResumeRevisionRequest,
        idempotency_key: IdempotencyHeader,
    ) -> ResumeRevision:
        revision_id = f"{request.command_id}_revision"
        command = _command(
            command_id=request.command_id,
            kind=EntityKind.RESUME_REVISION,
            entity_id=revision_id,
            expected_revision=0,
            idempotency_key=idempotency_key,
            actor="user",
            command_type="resume.revision.create",
        )
        try:
            return api.service.resumes.create_revision(
                command,
                resume_id=request.resume_id,
                base_revision=request.base_revision,
                accepted_patch_refs=request.accepted_patch_refs,
            )
        except Exception as error:
            raise _error(error) from error

    @router.get("/diff/{resume_revision_id}", response_model=ResumeStudioDiff)
    def diff(
        resume_revision_id: str = Path(min_length=3, max_length=128),
    ) -> ResumeStudioDiff:
        try:
            return api.service.diff(resume_revision_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/render", response_model=ResumeRenderRun, status_code=status.HTTP_201_CREATED)
    def render(request: RenderRequest) -> ResumeRenderRun:
        try:
            run, _report = api.service.render(
                resume_revision_id=request.resume_revision_id,
                target_profile_id=request.target_profile_id,
                template_id=request.template_id,
                actor=request.actor,
            )
            return run
        except Exception as error:
            raise _error(error) from error

    @router.get("/render-runs/{render_run_id}", response_model=ResumeRenderRun)
    def get_render(
        render_run_id: str = Path(min_length=3, max_length=128),
    ) -> ResumeRenderRun:
        result = api.service.repository.get_render(render_run_id)
        if result is None:
            raise HTTPException(404, "render run not found")
        return result

    @router.get("/render-runs/{render_run_id}/ats-report", response_model=ResumeAtsReport)
    def get_ats_report(
        render_run_id: str = Path(min_length=3, max_length=128),
    ) -> ResumeAtsReport:
        result = api.service.repository.get_ats_report(render_run_id)
        if result is None:
            raise HTTPException(404, "ATS report not found")
        return result

    @router.get("/render-runs/{render_run_id}/artifact")
    def get_artifact(
        render_run_id: str = Path(min_length=3, max_length=128),
    ) -> Response:
        try:
            content = api.service.repository.read_render_artifact(render_run_id)
        except Exception as error:
            raise _error(error) from error
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{render_run_id}.pdf"'},
        )

    return router
