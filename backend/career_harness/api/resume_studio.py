from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Query, Response, status
from pydantic import Field

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef, FrozenModel, OpaqueId
from career_harness.core.resume import (
    ResumeAtsReport,
    ResumeBase,
    ResumeData,
    ResumePatch,
    ResumePatchOperation,
    ResumePatchStatus,
    ResumeRenderReview,
    ResumeRenderRun,
    ResumeRevision,
    ResumeStudioDiff,
    ResumeTargetProfile,
    ResumeTemplateRegistration,
    ResumeValidationResult,
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


class ResumeRestoreRequest(FrozenModel):
    command_id: OpaqueId
    resume_id: OpaqueId
    revision_id: OpaqueId
    expected_base_revision: int = Field(ge=1)


class RenderRequest(FrozenModel):
    resume_revision_id: OpaqueId
    target_profile_id: OpaqueId | None = None
    template_id: OpaqueId | None = None
    actor: str = Field(default="user", min_length=1, max_length=255)


class RenderReviewRequest(FrozenModel):
    decision: str = Field(pattern=r"^(approved|rejected)$")
    reason: str = Field(min_length=1, max_length=2048)


class ResumeValidationRequest(FrozenModel):
    content: dict[str, object]


class ResumeTextImportRequest(FrozenModel):
    text: str = Field(min_length=1, max_length=100_000)


class ResumeFileImportRequest(FrozenModel):
    media_type: str = Field(
        pattern=r"^(text/plain|text/markdown|application/pdf|image/png|image/jpeg)$"
    )
    content_base64: str = Field(min_length=4, max_length=4_000_000)


class ResumeBaseSaveRequest(FrozenModel):
    command_id: OpaqueId
    resume_id: OpaqueId
    candidate_id: OpaqueId
    sections: dict[str, object]


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
        return api.service.list_templates()

    @router.post("/validate", response_model=ResumeValidationResult)
    def validate_resume(request: ResumeValidationRequest) -> ResumeValidationResult:
        try:
            data = ResumeData.model_validate(request.content)
        except ValueError as error:
            return ResumeValidationResult(valid=False, errors=(str(error),))
        warnings: list[str] = []
        if not data.name:
            warnings.append("尚未填写姓名")
        if not data.experience and not data.projects:
            warnings.append("尚未填写经历或项目")
        if not data.skills:
            warnings.append("尚未填写技能")
        return ResumeValidationResult(valid=True, data=data, warnings=tuple(warnings))

    @router.post("/import-text", response_model=ResumeValidationResult)
    def import_text(request: ResumeTextImportRequest) -> ResumeValidationResult:
        """Parse a local text/Markdown resume into a reviewable, non-canonical shape."""
        lines = [line.strip() for line in request.text.splitlines() if line.strip()]
        sections: dict[str, list[str]] = {}
        current = "summary"
        for line in lines:
            if line.startswith("#"):
                heading = line.lstrip("#").strip().lower()
                current = next(
                    (name for name, aliases in {
                        "experience": ("experience", "经历", "工作经历"),
                        "projects": ("projects", "项目"),
                        "education": ("education", "教育", "教育经历"),
                        "skills": ("skills", "技能"),
                        "certifications": ("certifications", "证书"),
                        "summary": ("summary", "简介", "个人简介"),
                    }.items() if heading in aliases),
                    "custom_sections",
                )
                sections.setdefault(current, [])
            else:
                sections.setdefault(current, []).append(line)
        payload: dict[str, object] = {
            "name": lines[0].lstrip("#").strip() if lines else None,
            "summary": "\n".join(sections.get("summary", ())) or None,
            "contact": next((line for line in lines if "@" in line), None),
            "skills": tuple(sections.get("skills", ())),
            "experience": tuple({"text": value} for value in sections.get("experience", ())),
            "projects": tuple({"text": value} for value in sections.get("projects", ())),
            "education": tuple({"text": value} for value in sections.get("education", ())),
            "certifications": tuple(
                {"text": value} for value in sections.get("certifications", ())
            ),
            "custom_sections": tuple(
                {"title": key, "items": values}
                for key, values in sections.items()
                if key == "custom_sections"
            ),
        }
        try:
            data = ResumeData.model_validate(payload)
        except ValueError as error:
            return ResumeValidationResult(valid=False, errors=(str(error),))
        warnings = ["导入内容仅是待确认草稿，保存前请核对职业事实。"]
        if not data.contact:
            warnings.append("未识别到联系方式")
        return ResumeValidationResult(valid=True, data=data, warnings=tuple(warnings))

    @router.post("/import-file", response_model=ResumeValidationResult)
    def import_file(request: ResumeFileImportRequest) -> ResumeValidationResult:
        try:
            raw = base64.b64decode(request.content_base64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise HTTPException(422, "导入文件内容不是有效的 Base64") from error
        if len(raw) > 2_000_000:
            raise HTTPException(422, "导入文件不能超过 2 MB")
        if request.media_type.startswith("image/"):
            return ResumeValidationResult(
                valid=False,
                warnings=("当前本地构建未启用 OCR 解析器，请先将图片转换为文本后导入。",),
                errors=("图片 OCR 解析器尚未配置",),
            )
        if request.media_type == "application/pdf":
            # Keep the fallback dependency-free: extract visible PDF string literals for review.
            text = "\n".join(
                value.decode("utf-8", "ignore")
                for value in re.findall(rb"\(([^()]*)\)", raw)
                if value.strip()
            )
            if not text.strip():
                return ResumeValidationResult(
                    valid=False,
                    errors=("PDF 未提取到可读文本，请先导出为文本或配置 PDF 解析器。",),
                )
        else:
            text = raw.decode("utf-8", "replace")
        return import_text(ResumeTextImportRequest(text=text))

    @router.post("/bases", response_model=ResumeBase, status_code=status.HTTP_201_CREATED)
    def save_base(
        request: ResumeBaseSaveRequest,
        idempotency_key: IdempotencyHeader,
    ) -> ResumeBase:
        command = _command(
            command_id=request.command_id,
            kind=EntityKind.RESUME,
            entity_id=request.resume_id,
            expected_revision=0,
            idempotency_key=idempotency_key,
            actor="user",
            command_type="resume.base.save",
        )
        try:
            data = ResumeData.model_validate(request.sections)
            return api.service.resumes.save_base_revision(
                command,
                candidate_id=request.candidate_id,
                sections=data.model_dump(mode="json"),
            )
        except Exception as error:
            raise _error(error) from error

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

    @router.post("/restore", response_model=ResumeBase, status_code=status.HTTP_201_CREATED)
    def restore_revision(
        request: ResumeRestoreRequest,
        idempotency_key: IdempotencyHeader,
    ) -> ResumeBase:
        command = _command(
            command_id=request.command_id,
            kind=EntityKind.RESUME,
            entity_id=request.resume_id,
            expected_revision=request.expected_base_revision,
            idempotency_key=idempotency_key,
            actor="user",
            command_type="resume.base.restore",
        )
        try:
            return api.service.resumes.restore_revision(
                command, revision_id=request.revision_id
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

    @router.get("/revisions/{resume_revision_id}/export")
    def export_revision(
        resume_revision_id: str = Path(min_length=3, max_length=128),
        format: str = Query(default="json", pattern="^(json|markdown)$"),
    ) -> Response:
        revision = api.service.repository.resumes.get_revision(resume_revision_id)
        if revision is None:
            raise HTTPException(404, "resume revision not found")
        if format == "json":
            content = revision.model_dump_json(indent=2).encode("utf-8")
            media_type = "application/json"
            filename = f"{resume_revision_id}.json"
        else:
            lines = [f"# {revision.content.get('name', '简历')}"]
            for key, value in revision.content.items():
                if key != "name":
                    rendered = value if isinstance(value, str) else str(value)
                    lines.append(f"\n## {key}\n\n{rendered}")
            content = "\n".join(lines).encode("utf-8")
            media_type = "text/markdown"
            filename = f"{resume_revision_id}.md"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

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

    @router.post(
        "/render-runs/{render_run_id}/review", response_model=ResumeRenderReview
    )
    def review_render(
        request: RenderReviewRequest,
        render_run_id: str = Path(min_length=3, max_length=128),
    ) -> ResumeRenderReview:
        try:
            return api.service.review_render(
                render_run_id=render_run_id,
                decision=request.decision,
                reason=request.reason,
                actor="user",
            )
        except Exception as error:
            raise _error(error) from error

    @router.get(
        "/render-runs/{render_run_id}/review", response_model=ResumeRenderReview
    )
    def get_render_review(
        render_run_id: str = Path(min_length=3, max_length=128),
    ) -> ResumeRenderReview:
        result = api.service.repository.get_render_review(render_run_id)
        if result is None:
            raise HTTPException(404, "render review not found")
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
