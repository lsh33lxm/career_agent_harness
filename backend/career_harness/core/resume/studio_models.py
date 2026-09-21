from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId, utc_now
from career_harness.core.resume.models import RevisionRef


class TargetProfileStatus(StrEnum):
    APPROVED = "approved"
    ARCHIVED = "archived"


class TemplateRenderer(StrEnum):
    HTML_CSS = "html_css"
    TYPST_WORKER = "typst_worker"


class RenderRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AtsReportStatus(StrEnum):
    PASSED = "passed"
    WARNINGS = "warnings"
    FAILED = "failed"


class ResumeTargetProfile(FrozenModel):
    target_profile_id: OpaqueId
    resume_id: OpaqueId
    title: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    opportunity_id: OpaqueId | None = None
    opportunity_revision: int | None = Field(default=None, ge=1)
    requirement_refs: tuple[RevisionRef, ...] = ()
    keyword_gaps: tuple[str, ...] = ()
    status: TargetProfileStatus = TargetProfileStatus.APPROVED
    created_by: str = Field(min_length=1, max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class ResumeTargetPatchRef(FrozenModel):
    target_profile_id: OpaqueId
    patch_id: OpaqueId
    patch_revision: int = Field(ge=1)


class ResumeTemplateRegistration(FrozenModel):
    template_id: OpaqueId
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    renderer: TemplateRenderer
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    description: str = Field(min_length=1, max_length=2048)
    status: str = Field(default="active", pattern=r"^(active|disabled)$")
    created_at: datetime = Field(default_factory=utc_now)


class ResumeAtsReport(FrozenModel):
    render_run_id: OpaqueId
    status: AtsReportStatus
    page_count: int = Field(ge=1)
    checks: dict[str, bool]
    keyword_gaps: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)


class ResumeRenderRun(FrozenModel):
    render_run_id: OpaqueId
    resume_revision_id: OpaqueId
    target_profile_id: OpaqueId | None = None
    template_id: OpaqueId
    template_version: str | None = Field(default=None, min_length=1, max_length=64)
    renderer: TemplateRenderer | None = None
    renderer_plugin_id: OpaqueId | None = None
    renderer_plugin_version: str | None = Field(default=None, min_length=1, max_length=64)
    input_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    status: RenderRunStatus
    output_artifact_id: OpaqueId
    output_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    output_media_type: str = Field(min_length=1, max_length=255)
    page_count: int = Field(ge=1)
    preview_html: str = Field(min_length=1, max_length=1_000_000)
    checks: dict[str, bool]
    created_by: str = Field(min_length=1, max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class ResumeRenderReview(FrozenModel):
    render_run_id: OpaqueId
    decision: str = Field(pattern=r"^(approved|rejected)$")
    reviewer: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=2048)
    reviewed_at: datetime = Field(default_factory=utc_now)


class ResumeStudioDiff(FrozenModel):
    resume_id: OpaqueId
    base_revision: int = Field(ge=1)
    resume_revision_id: OpaqueId
    diff: str
    claim_provenance: tuple[RevisionRef, ...] = ()
    evidence_provenance: tuple[str, ...] = ()
