from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId, utc_now


class JobSourceTermsStatus(StrEnum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class JobStagingStatus(StrEnum):
    STAGED = "staged"
    DUPLICATE = "duplicate"
    ADMITTED = "admitted"
    REJECTED = "rejected"


class RawJobRecord(FrozenModel):
    source_ref: str = Field(min_length=1, max_length=4096)
    raw_text: str = Field(min_length=1, max_length=1_000_000)
    captured_at: datetime = Field(default_factory=utc_now)


class NormalizedJobRecord(FrozenModel):
    title: str = Field(min_length=1, max_length=512)
    company: str = Field(min_length=1, max_length=512)
    location: str | None = Field(default=None, max_length=512)
    remote: bool | None = None
    salary: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    deadline_at: datetime | None = None
    requirements: tuple[str, ...] = ()
    source_url: str | None = Field(default=None, max_length=4096)


class JobSourceTerms(FrozenModel):
    source_id: OpaqueId
    status: JobSourceTermsStatus
    note: str = Field(min_length=1, max_length=2048)
    checked_at: datetime = Field(default_factory=utc_now)


class JobSourceHealth(FrozenModel):
    status: str = Field(pattern=r"^(ok|blocked|error)$")
    message: str


class JobSourcePolicy(FrozenModel):
    source_id: OpaqueId
    rate_limit_ms: int = Field(ge=0, le=300_000)
    max_retries: int = Field(ge=0, le=5)
    failure_threshold: int = Field(ge=1, le=20)
    failure_count: int = Field(ge=0)
    disabled: bool = False
    last_error: str | None = Field(default=None, max_length=2048)
    updated_at: datetime = Field(default_factory=utc_now)


class JobStagingRecord(FrozenModel):
    staging_id: OpaqueId
    source_id: OpaqueId
    source_ref: str
    raw_artifact_id: OpaqueId
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    url_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    normalized: NormalizedJobRecord
    terms_status: JobSourceTermsStatus
    status: JobStagingStatus
    duplicate_of: OpaqueId | None = None
    suggested_score: float = Field(ge=0, le=1)
    suggested_reasons: tuple[str, ...]
    gaps: tuple[str, ...]
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    ranking_inputs: dict[str, Any] = Field(default_factory=dict)
    ranking_policy_version: str = Field(default="v1", min_length=1, max_length=32)
    evaluated_at: datetime = Field(default_factory=utc_now)
    admitted_job_id: OpaqueId | None = None
    admitted_opportunity_id: OpaqueId | None = None
    created_at: datetime = Field(default_factory=utc_now)


class JobResumeProposalSeed(FrozenModel):
    staging_id: OpaqueId
    opportunity_id: OpaqueId
    title: str
    company: str
    requirement_texts: tuple[str, ...]
    keyword_gaps: tuple[str, ...]
    evidence_ref_id: OpaqueId
    status: str = Field(default="proposal_only", pattern=r"^proposal_only$")


class JobSource(Protocol):
    source_id: str

    def search(self, query: str) -> tuple[RawJobRecord, ...]: ...

    def fetch_detail(self, ref: str) -> RawJobRecord: ...

    def normalize(self, raw: RawJobRecord) -> NormalizedJobRecord: ...

    def health(self) -> JobSourceHealth: ...

    def terms(self) -> JobSourceTerms: ...
