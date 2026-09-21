"""Resume content, patch proposal, revision, and render boundary."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Resume
from career_harness.core.resume.models import (
    ResumeBase,
    ResumePatch,
    ResumePatchAction,
    ResumePatchOperation,
    ResumePatchStatus,
    ResumeRevision,
    RevisionRef,
)
from career_harness.core.resume.studio_models import (
    AtsReportStatus,
    RenderRunStatus,
    ResumeAtsReport,
    ResumeRenderReview,
    ResumeRenderRun,
    ResumeStudioDiff,
    ResumeTargetPatchRef,
    ResumeTargetProfile,
    ResumeTemplateRegistration,
    TargetProfileStatus,
    TemplateRenderer,
)

ENTITY_KIND = EntityKind.RESUME

__all__ = [
    "ENTITY_KIND",
    "Resume",
    "ResumeBase",
    "ResumePatch",
    "ResumePatchAction",
    "ResumePatchOperation",
    "ResumePatchStatus",
    "ResumeRevision",
    "RevisionRef",
    "AtsReportStatus",
    "RenderRunStatus",
    "ResumeAtsReport",
    "ResumeRenderRun",
    "ResumeRenderReview",
    "ResumeStudioDiff",
    "ResumeTargetPatchRef",
    "ResumeTargetProfile",
    "ResumeTemplateRegistration",
    "TargetProfileStatus",
    "TemplateRenderer",
]
