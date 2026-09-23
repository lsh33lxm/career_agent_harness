from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from career_harness.core.common import FrozenModel, OpaqueId, utc_now

PlanItem = Annotated[str, Field(min_length=1, max_length=2048)]


class ProjectPathError(ValueError):
    """Raised when a project path is not relative to the project root."""


class ProjectScopeViolation(ValueError):
    """Raised when a relative path is outside an explicit scan scope."""


def normalize_project_path(value: str) -> str:
    if not value or not value.strip() or "\x00" in value:
        raise ProjectPathError("project path must be a non-empty relative path")

    windows_path = PureWindowsPath(value)
    normalized_value = value.replace("\\", "/")
    posix_path = PurePosixPath(normalized_value)
    if windows_path.drive or windows_path.root or posix_path.is_absolute():
        raise ProjectPathError("project path must be relative to the project root")
    if ".." in posix_path.parts:
        raise ProjectPathError("project path cannot contain parent traversal")

    parts = tuple(part for part in posix_path.parts if part != ".")
    return "." if not parts else "/".join(parts)


def _normalize_paths(values: object) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise ProjectPathError("project paths must be provided as a sequence")
    return tuple(dict.fromkeys(normalize_project_path(value) for value in values))


def _is_same_or_descendant(path: str, parent: str) -> bool:
    path = path.casefold()
    parent = parent.casefold()
    if parent == ".":
        return True
    return path == parent or path.startswith(f"{parent}/")


class ProjectRecord(FrozenModel):
    revision: int = Field(default=1, ge=1)
    schema_version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(min_length=1, max_length=255)


class Project(ProjectRecord):
    project_id: OpaqueId
    display_name: str = Field(min_length=1, max_length=255)
    root_locator: str = Field(min_length=1, max_length=2048)


class ProjectScanScope(ProjectRecord):
    scope_id: OpaqueId
    project_id: OpaqueId
    allowed_paths: tuple[str, ...] = Field(min_length=1)
    denied_paths: tuple[str, ...] = ()
    follow_symlinks: Literal[False] = False

    @field_validator("allowed_paths", "denied_paths", mode="before")
    @classmethod
    def validate_paths(cls, value: object) -> tuple[str, ...]:
        return _normalize_paths(value)

    def permits(self, relative_path: str) -> bool:
        path = normalize_project_path(relative_path)
        if any(_is_same_or_descendant(path, denied) for denied in self.denied_paths):
            return False
        return any(_is_same_or_descendant(path, allowed) for allowed in self.allowed_paths)

    def require_permitted(self, relative_path: str) -> str:
        path = normalize_project_path(relative_path)
        if not self.permits(path):
            raise ProjectScopeViolation(f"project path is not allowed by scan scope: {path}")
        return path


class ProjectSourceEntry(FrozenModel):
    relative_path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    byte_length: int = Field(ge=0)

    @field_validator("relative_path", mode="before")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return normalize_project_path(value)


class ProjectSourceManifest(FrozenModel):
    manifest_id: OpaqueId
    scan_scope_id: OpaqueId
    scan_scope_revision: int = Field(ge=1)
    entries: tuple[ProjectSourceEntry, ...] = Field(min_length=1)
    generated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def source_paths_are_unique(self) -> ProjectSourceManifest:
        paths = [entry.relative_path for entry in self.entries]
        if len(paths) != len(set(paths)):
            raise ValueError("source manifest paths must be unique")
        return self


class ProjectEvidenceAuthority(StrEnum):
    CODE_VERIFIED = "code_verified"
    DOCUMENT_SUPPORTED = "document_supported"
    USER_CONFIRMED = "user_confirmed"
    AI_INFERRED = "ai_inferred"


class ProjectEvidenceClaimKind(StrEnum):
    TECHNICAL_OBSERVATION = "technical_observation"
    CHANGE = "change"
    VALIDATION = "validation"
    PERFORMANCE = "performance"
    BUSINESS_OUTCOME = "business_outcome"
    PERSONAL_CONTRIBUTION = "personal_contribution"
    OWNERSHIP = "ownership"
    USAGE = "usage"


class ProjectEvidenceFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class ProjectEvidenceReviewStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProjectEvidence(ProjectRecord):
    evidence_id: OpaqueId
    project_id: OpaqueId
    summary: str = Field(min_length=1, max_length=4096)
    claim_kind: ProjectEvidenceClaimKind = ProjectEvidenceClaimKind.TECHNICAL_OBSERVATION
    source_manifest: ProjectSourceManifest
    scanner: str = Field(min_length=1, max_length=255)
    scanner_version: str = Field(min_length=1, max_length=128)
    authority: ProjectEvidenceAuthority
    freshness: ProjectEvidenceFreshness = ProjectEvidenceFreshness.CURRENT
    review_status: ProjectEvidenceReviewStatus = ProjectEvidenceReviewStatus.PROPOSED
    reviewed_by: str | None = Field(default=None, min_length=1, max_length=255)
    reviewed_by_kind: Literal["user", "rule"] | None = None
    review_reason: str | None = Field(default=None, min_length=1, max_length=2048)
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def enforce_evidence_authority(self) -> ProjectEvidence:
        review_fields = (self.reviewed_by, self.reviewed_by_kind, self.review_reason)
        if self.review_status is ProjectEvidenceReviewStatus.PROPOSED:
            if any(item is not None for item in review_fields):
                raise ValueError("proposed project evidence cannot carry a review decision")
        elif any(item is None for item in review_fields):
            raise ValueError("reviewed project evidence requires user or rule authority")

        if (
            self.authority is ProjectEvidenceAuthority.AI_INFERRED
            and self.review_status is ProjectEvidenceReviewStatus.ACCEPTED
        ):
            raise ValueError("AI-inferred project evidence requires explicit promotion")

        code_insufficient_claims = {
            ProjectEvidenceClaimKind.PERFORMANCE,
            ProjectEvidenceClaimKind.BUSINESS_OUTCOME,
            ProjectEvidenceClaimKind.PERSONAL_CONTRIBUTION,
            ProjectEvidenceClaimKind.OWNERSHIP,
            ProjectEvidenceClaimKind.USAGE,
        }
        if (
            self.authority is ProjectEvidenceAuthority.CODE_VERIFIED
            and self.claim_kind in code_insufficient_claims
        ):
            raise ValueError("source code alone cannot verify this project claim")
        return self


class ProjectCapabilityLevel(StrEnum):
    EXISTING = "existing"
    UNDERSTOOD = "understood"
    MODIFIED = "modified"
    EXTENDED = "extended"
    VALIDATED = "validated"
    RESUME_READY = "resume_ready"


class ProjectCapabilityBasisKind(StrEnum):
    CODE_EVIDENCE = "code_evidence"
    DOCUMENT_EVIDENCE = "document_evidence"
    USER_CONFIRMATION = "user_confirmation"
    CHANGE_EVIDENCE = "change_evidence"
    VALIDATION_EVIDENCE = "validation_evidence"
    RESUME_APPROVAL = "resume_approval"


class ProjectCapabilityBasis(FrozenModel):
    kind: ProjectCapabilityBasisKind
    reference_id: OpaqueId
    reference_revision: int = Field(ge=1)


class ProjectCapabilityState(ProjectRecord):
    capability_state_id: OpaqueId
    project_id: OpaqueId
    capability_id: OpaqueId
    state: ProjectCapabilityLevel
    basis: tuple[ProjectCapabilityBasis, ...] = Field(min_length=1)
    finalized_at: datetime

    @model_validator(mode="after")
    def state_requires_appropriate_basis(self) -> ProjectCapabilityState:
        kinds = {item.kind for item in self.basis}
        required: dict[ProjectCapabilityLevel, set[ProjectCapabilityBasisKind]] = {
            ProjectCapabilityLevel.EXISTING: {
                ProjectCapabilityBasisKind.CODE_EVIDENCE,
                ProjectCapabilityBasisKind.DOCUMENT_EVIDENCE,
                ProjectCapabilityBasisKind.USER_CONFIRMATION,
            },
            ProjectCapabilityLevel.UNDERSTOOD: {
                ProjectCapabilityBasisKind.USER_CONFIRMATION,
            },
            ProjectCapabilityLevel.MODIFIED: {
                ProjectCapabilityBasisKind.CHANGE_EVIDENCE,
                ProjectCapabilityBasisKind.USER_CONFIRMATION,
            },
            ProjectCapabilityLevel.EXTENDED: {
                ProjectCapabilityBasisKind.CHANGE_EVIDENCE,
                ProjectCapabilityBasisKind.USER_CONFIRMATION,
            },
            ProjectCapabilityLevel.VALIDATED: {
                ProjectCapabilityBasisKind.VALIDATION_EVIDENCE,
            },
            ProjectCapabilityLevel.RESUME_READY: {
                ProjectCapabilityBasisKind.VALIDATION_EVIDENCE,
                ProjectCapabilityBasisKind.RESUME_APPROVAL,
            },
        }
        expected = required[self.state]
        if self.state is ProjectCapabilityLevel.EXISTING:
            if kinds.isdisjoint(expected):
                raise ValueError("existing capability requires project evidence")
        elif not expected.issubset(kinds):
            raise ValueError(f"{self.state.value} capability lacks required evidence or approval")
        return self


class ProjectEnhancementTaskStatus(StrEnum):
    PROPOSED = "proposed"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    AWAITING_VALIDATION = "awaiting_validation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectEnhancementTask(ProjectRecord):
    task_id: OpaqueId
    project_id: OpaqueId
    target_gap_id: OpaqueId
    target_capability_id: OpaqueId
    learning_plan: tuple[PlanItem, ...] = Field(min_length=1)
    files_to_review: tuple[str, ...] = Field(min_length=1)
    change_plan: tuple[PlanItem, ...] = Field(min_length=1)
    experiment_plan: tuple[PlanItem, ...] = Field(min_length=1)
    validation_plan: tuple[PlanItem, ...] = Field(min_length=1)
    expected_evidence: tuple[PlanItem, ...] = Field(min_length=1)
    status: ProjectEnhancementTaskStatus = ProjectEnhancementTaskStatus.PROPOSED

    @field_validator("files_to_review", mode="before")
    @classmethod
    def validate_files_to_review(cls, value: object) -> tuple[str, ...]:
        return _normalize_paths(value)
