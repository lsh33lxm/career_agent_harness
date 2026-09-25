from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.common import FrozenModel, OpaqueId, utc_now
from career_harness.core.lifecycle import ActorKind


class JobRequirementImportance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class JobRequirementStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class JobRef(FrozenModel):
    job_id: OpaqueId
    revision: int = Field(ge=1)


class JobRevision(FrozenModel):
    job_id: OpaqueId
    revision: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_evidence_refs: tuple[OpaqueId, ...] = Field(min_length=1)
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def source_evidence_refs_are_unique(self) -> JobRevision:
        if len(set(self.source_evidence_refs)) != len(self.source_evidence_refs):
            raise ValueError("job revision source evidence refs must be unique")
        return self


class JobRequirement(FrozenModel):
    requirement_id: OpaqueId
    revision: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)
    job: JobRef
    requirement_text: str = Field(min_length=1, max_length=4096)
    importance: JobRequirementImportance
    capability_id: OpaqueId | None = None
    graph_version_id: OpaqueId | None = None
    required_scopes: tuple[CapabilityEvidenceScope, ...] = Field(min_length=1)
    source_evidence_refs: tuple[OpaqueId, ...] = Field(min_length=1)
    status: JobRequirementStatus = JobRequirementStatus.PROPOSED
    proposed_by: str = Field(min_length=1, max_length=255)
    proposed_by_kind: ActorKind
    proposed_at: datetime = Field(default_factory=utc_now)
    reviewed_by: str | None = Field(default=None, min_length=1, max_length=255)
    reviewed_by_kind: ActorKind | None = None
    review_reason: str | None = Field(default=None, min_length=1, max_length=2048)
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def evidence_inputs_are_unique(self) -> JobRequirement:
        if len(set(self.required_scopes)) != len(self.required_scopes):
            raise ValueError("job requirement evidence scopes must be unique")
        if len(set(self.source_evidence_refs)) != len(self.source_evidence_refs):
            raise ValueError("job requirement source evidence refs must be unique")
        return self

    @model_validator(mode="after")
    def review_and_official_mapping_are_explicit(self) -> JobRequirement:
        has_capability = self.capability_id is not None
        has_graph_version = self.graph_version_id is not None
        if has_capability != has_graph_version:
            raise ValueError("official capability and graph version must be provided together")

        review_fields = (
            self.reviewed_by,
            self.reviewed_by_kind,
            self.review_reason,
            self.reviewed_at,
        )
        if self.status is JobRequirementStatus.PROPOSED:
            if any(value is not None for value in review_fields):
                raise ValueError("proposed job requirement cannot carry a review decision")
        else:
            if any(value is None for value in review_fields):
                raise ValueError("reviewed job requirement requires complete reviewer metadata")
            if self.reviewed_by_kind is ActorKind.AGENT:
                raise ValueError("an agent cannot review a job requirement")

        if self.status is JobRequirementStatus.ACCEPTED and not has_capability:
            raise ValueError("accepted job requirement requires an official capability mapping")
        return self
