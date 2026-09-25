from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from career_harness.core.common import FrozenModel, OpaqueId, utc_now
from career_harness.core.lifecycle import ActorKind


class ResumePatchAction(StrEnum):
    SET = "set"
    INSERT = "insert"
    REMOVE = "remove"


class ResumePatchStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RevisionRef(FrozenModel):
    entity_id: OpaqueId
    revision: int = Field(ge=1)


class ResumeBase(FrozenModel):
    resume_id: OpaqueId
    candidate_id: OpaqueId
    revision: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)
    sections: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(min_length=1, max_length=255)

    @field_validator("sections")
    @classmethod
    def sections_are_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, sort_keys=True, separators=(",", ":"))) > 65536:
            raise ValueError("resume sections exceed the 64 KiB canonical limit")
        return value


class ResumePatchOperation(FrozenModel):
    action: ResumePatchAction
    target_path: str = Field(min_length=1, max_length=1024, pattern=r"^/")
    expected_value_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposed_value: Any = None
    fact_refs: tuple[RevisionRef, ...] = ()
    evidence_refs: tuple[OpaqueId, ...] = ()
    requirement_refs: tuple[RevisionRef, ...] = ()
    reason: str = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def provenance_is_unique(self) -> ResumePatchOperation:
        if not self.fact_refs and not self.evidence_refs:
            raise ValueError(
                "resume patch operation requires qualified fact or evidence provenance"
            )
        for refs, label in (
            (self.fact_refs, "fact"),
            (self.evidence_refs, "evidence"),
            (self.requirement_refs, "requirement"),
        ):
            if len(set(refs)) != len(refs):
                raise ValueError(f"resume patch {label} refs must be unique")
        return self


class ResumePatch(FrozenModel):
    patch_id: OpaqueId
    resume_id: OpaqueId
    base_revision: int = Field(ge=1)
    revision: int = Field(ge=1)
    operations: tuple[ResumePatchOperation, ...] = Field(min_length=1, max_length=128)
    generator_run_id: OpaqueId | None = None
    status: ResumePatchStatus = ResumePatchStatus.PROPOSED
    proposed_by: str = Field(min_length=1, max_length=255)
    proposed_by_kind: ActorKind
    proposed_at: datetime = Field(default_factory=utc_now)
    reviewed_by: str | None = Field(default=None, min_length=1, max_length=255)
    reviewed_by_kind: ActorKind | None = None
    review_reason: str | None = Field(default=None, min_length=1, max_length=2048)
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def review_metadata_matches_status(self) -> ResumePatch:
        review = (self.reviewed_by, self.reviewed_by_kind, self.review_reason, self.reviewed_at)
        if self.status is ResumePatchStatus.PROPOSED:
            if any(value is not None for value in review):
                raise ValueError("proposed resume patch cannot carry review metadata")
        elif any(value is None for value in review):
            raise ValueError("reviewed resume patch requires complete reviewer metadata")
        elif self.reviewed_by_kind is not ActorKind.USER:
            raise ValueError("only the user may review a resume patch")
        return self


class ResumeRevision(FrozenModel):
    revision_id: OpaqueId
    resume_id: OpaqueId
    base_revision: int = Field(ge=1)
    accepted_patch_refs: tuple[RevisionRef, ...]
    content: dict[str, Any]
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(min_length=1, max_length=255)

    @field_validator("accepted_patch_refs")
    @classmethod
    def patch_refs_are_unique(cls, value: tuple[RevisionRef, ...]) -> tuple[RevisionRef, ...]:
        if len(set(value)) != len(value):
            raise ValueError("accepted resume patch refs must be unique")
        return value
