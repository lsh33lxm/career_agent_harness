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
]
