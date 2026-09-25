from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId


class MemoryType(StrEnum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    FACT = "fact"
    TASK = "task"
    INTEREST = "interest"


class MemoryScope(StrEnum):
    USER = "user"
    WORKSPACE = "workspace"
    SESSION = "session"


class MemoryCreator(StrEnum):
    USER = "USER"
    LLM = "LLM"
    PLUGIN = "PLUGIN"
    IMPORTER = "IMPORTER"
    RULE = "RULE"


class MemoryProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MemoryRevision(FrozenModel):
    memory_id: OpaqueId
    revision: int = Field(ge=1)
    memory_type: MemoryType
    scope_kind: MemoryScope
    scope_id: str
    status: str = Field(pattern=r"^(confirmed|tombstoned)$")
    content: str
    source_type: str
    source_locator: str
    source_refs: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    created_by: MemoryCreator
    confirmed_by: str
    created_at: datetime


class MemoryProposal(FrozenModel):
    proposal_id: OpaqueId
    target_memory_id: str | None
    base_revision: int | None
    memory_type: MemoryType
    scope_kind: MemoryScope
    scope_id: str
    content: str
    source_type: str
    source_locator: str
    source_refs: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    created_by: MemoryCreator
    status: MemoryProposalStatus
    reviewed_by: str | None
    review_reason: str | None
    approved_content: str | None
    created_at: datetime
    reviewed_at: datetime | None


class MemorySearchResult(FrozenModel):
    memory: MemoryRevision
    relevance: float = Field(ge=0, le=1)
