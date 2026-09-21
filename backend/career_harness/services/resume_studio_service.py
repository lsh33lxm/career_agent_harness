from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from career_harness.core.commands import Command
from career_harness.core.common import OpaqueId
from career_harness.core.resume import (
    AtsReportStatus,
    RenderRunStatus,
    ResumeAtsReport,
    ResumePatch,
    ResumePatchOperation,
    ResumeRenderRun,
    ResumeTargetProfile,
    ResumeTemplateRegistration,
    RevisionRef,
    TemplateRenderer,
)
from career_harness.db.resume_studio_repository import ResumeStudioRepository
from career_harness.services.resume_renderer import (
    TEMPLATE_CSS,
    TEMPLATE_DEFINITION,
    TEMPLATE_DESCRIPTION,
    TEMPLATE_ID,
    TEMPLATE_VERSION,
    keyword_gaps,
    render_html,
    render_pdf,
)
from career_harness.services.resume_service import ResumeService


def _template_hash() -> str:
    return hashlib.sha256(
        (TEMPLATE_ID + TEMPLATE_VERSION + TEMPLATE_CSS).encode("utf-8")
    ).hexdigest()


class ResumeStudioService:
    def __init__(self, commands: Any, repository: ResumeStudioRepository) -> None:
        self.commands = commands
        self.repository = repository
        self.resumes = ResumeService(commands)

    def ensure_builtin_template(self) -> ResumeTemplateRegistration:
        return self.repository.ensure_template(
            ResumeTemplateRegistration(
                template_id=TEMPLATE_ID,
                name="观复简历 / Warm Paper",
                version=TEMPLATE_VERSION,
                renderer=TemplateRenderer.HTML_CSS,
                content_sha256=_template_hash(),
                description=TEMPLATE_DESCRIPTION,
            ),
            TEMPLATE_DEFINITION,
        )

    def create_target_profile(
        self,
        *,
        target_profile_id: OpaqueId,
        resume_id: OpaqueId,
        title: str,
        company: str | None,
        opportunity_id: OpaqueId | None,
        opportunity_revision: int | None,
        requirement_refs: tuple[RevisionRef, ...],
        keyword_gaps: tuple[str, ...],
        actor: str,
    ) -> ResumeTargetProfile:
        if actor != "user":
            raise ValueError("only the user may create a ResumeTargetProfile")
        return self.repository.create_target_profile(
            ResumeTargetProfile(
                target_profile_id=target_profile_id,
                resume_id=resume_id,
                title=title,
                company=company,
                opportunity_id=opportunity_id,
                opportunity_revision=opportunity_revision,
                requirement_refs=requirement_refs,
                keyword_gaps=keyword_gaps,
                created_by=actor,
            )
        )

    def propose_patch(
        self,
        command: Command,
        *,
        target_profile_id: OpaqueId,
        resume_id: OpaqueId,
        base_revision: int,
        operations: tuple[ResumePatchOperation, ...],
        generator_run_id: OpaqueId | None = None,
    ) -> ResumePatch:
        profile = self.repository.get_target_profile(target_profile_id)
        if profile is None:
            raise ValueError("ResumePatch requires an exact target profile")
        if profile.resume_id != resume_id:
            raise ValueError("ResumePatch target profile does not belong to the Resume")
        patch = self.resumes.propose_patch(
            command,
            resume_id=resume_id,
            base_revision=base_revision,
            operations=operations,
            generator_run_id=generator_run_id,
        )
        self.repository.link_patch(target_profile_id, patch.patch_id, patch.revision)
        return patch

    def render(
        self,
        *,
        resume_revision_id: OpaqueId,
        target_profile_id: OpaqueId | None,
        template_id: OpaqueId | None,
        actor: str,
    ) -> tuple[ResumeRenderRun, ResumeAtsReport]:
        revision = self.repository.resumes.get_revision(resume_revision_id)
        if revision is None:
            raise ValueError("render requires an exact ResumeRevision")
        profile = None
        requirement_texts: tuple[str, ...] = ()
        if target_profile_id is not None:
            profile = self.repository.get_target_profile(target_profile_id)
            if profile is None:
                raise ValueError("render target profile does not exist")
            if profile.resume_id != revision.resume_id:
                raise ValueError("render target profile does not belong to the Resume")
            requirement_texts = tuple(
                requirement.requirement_text
                for ref in profile.requirement_refs
                if (
                    requirement := self.repository.jobs.get_requirement(ref.entity_id, ref.revision)
                )
                is not None
            )
        template = (
            self.ensure_builtin_template()
            if template_id is None
            else self.repository.get_template(template_id)
        )
        if template is None:
            raise ValueError("resume template is not registered")
        if template.status != "active":
            raise ValueError("resume template is disabled")
        html_output = render_html(revision.content, title=profile.title if profile else "Resume")
        pdf_output, page_count = render_pdf(revision.content)
        gaps = tuple(
            dict.fromkeys(
                (*keyword_gaps(revision.content, requirement_texts),
                 *(profile.keyword_gaps if profile else ()))
            )
        )
        checks = {
            "text_layer": b" Tj" in pdf_output,
            "reading_order": bool(revision.content),
            "layout": page_count <= 3,
            "contact": self._has_contact(revision.content),
            "provenance": True,
        }
        report_status = (
            AtsReportStatus.FAILED
            if not checks["text_layer"] or not checks["layout"] or not checks["provenance"]
            else AtsReportStatus.WARNINGS
            if gaps or not checks["contact"]
            else AtsReportStatus.PASSED
        )
        digest = hashlib.sha256(
            (
                resume_revision_id
                + (target_profile_id or "")
                + template.template_id
                + revision.content_sha256
            ).encode()
        ).hexdigest()
        run = ResumeRenderRun(
            render_run_id=f"render_{digest[:32]}",
            resume_revision_id=resume_revision_id,
            target_profile_id=target_profile_id,
            template_id=template.template_id,
            status=RenderRunStatus.COMPLETED,
            output_artifact_id=f"artifact_resume_render_{hashlib.sha256(pdf_output).hexdigest()[:32]}",
            output_sha256=hashlib.sha256(pdf_output).hexdigest(),
            output_media_type="application/pdf",
            page_count=page_count,
            preview_html=html_output,
            checks=checks,
            created_by=actor,
            created_at=datetime.now(UTC),
        )
        report = ResumeAtsReport(
            render_run_id=run.render_run_id,
            status=report_status,
            page_count=page_count,
            checks=checks,
            keyword_gaps=gaps,
            created_at=run.created_at,
        )
        persisted = self.repository.persist_render(run, report, pdf_output)
        persisted_report = self.repository.get_ats_report(persisted.render_run_id)
        if persisted_report is None:
            raise RuntimeError("Resume render did not persist its ATS report")
        return persisted, persisted_report

    @staticmethod
    def _has_contact(content: dict[str, Any]) -> bool:
        rendered = str(content.get("contact", ""))
        return "@" in rendered or any(character.isdigit() for character in rendered)

    def diff(self, resume_revision_id: OpaqueId):
        return self.repository.diff(resume_revision_id)
