from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from career_harness.core.common import EntityRef, FrozenModel, OpaqueId, utc_now


class ArtifactClass(StrEnum):
    PUBLIC_SOURCE = "public_source"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    CREDENTIAL_SESSION = "credential_session"


class ClaimStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class FactAuthority(StrEnum):
    USER_ASSERTED = "user_asserted"
    DOCUMENT_SUPPORTED = "document_supported"
    RULE_VERIFIED = "rule_verified"


class Artifact(FrozenModel):
    artifact_id: OpaqueId
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    media_type: str = Field(min_length=1, max_length=255)
    artifact_class: ArtifactClass
    byte_length: int = Field(ge=0)


class Source(FrozenModel):
    source_id: OpaqueId
    source_type: str = Field(min_length=1, max_length=128)
    locator: str = Field(min_length=1, max_length=2048)


class SourceSnapshot(FrozenModel):
    snapshot_id: OpaqueId
    source_id: OpaqueId
    captured_at: datetime = Field(default_factory=utc_now)
    artifact_id: OpaqueId


class EvidenceRef(FrozenModel):
    evidence_ref_id: OpaqueId
    snapshot_id: OpaqueId
    artifact_id: OpaqueId
    selector: str | None = Field(default=None, max_length=2048)


class ExtractedClaim(FrozenModel):
    claim_id: OpaqueId
    claim_type: str = Field(min_length=1, max_length=128)
    subject: EntityRef
    proposed_value: Any
    evidence_refs: tuple[OpaqueId, ...] = Field(min_length=1)
    extractor: str = Field(min_length=1, max_length=255)
    extractor_version: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0, le=1)
    status: ClaimStatus = ClaimStatus.PROPOSED
    review_reason: str | None = Field(default=None, max_length=2048)


class Fact(FrozenModel):
    fact_id: OpaqueId
    subject: EntityRef
    fact_type: str = Field(min_length=1, max_length=128)
    value: Any
    authority: FactAuthority
    evidence_refs: tuple[OpaqueId, ...] = ()
    revision: int = Field(ge=1)
    verified_at: datetime = Field(default_factory=utc_now)
    verified_by: str = Field(min_length=1, max_length=255)


def promote_claim_to_fact(*args: object, **kwargs: object) -> Fact:
    raise TypeError("ExtractedClaim requires an explicit reviewed promotion command")

