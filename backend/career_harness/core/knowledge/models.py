from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId, utc_now


class KnowledgeCategory(StrEnum):
    PERSONAL_FACT = "personal_fact"
    PROJECT_EVIDENCE = "project_evidence"
    SKILL = "skill"
    STAR_STORY = "star_story"
    INTERVIEW_STORY = "interview_story"
    PREFERENCE = "preference"
    TARGET_ROLE = "target_role"
    COMPANY = "company"
    MARKET_SIGNAL = "market_signal"
    TEMPLATE = "template"
    APPLICATION_HISTORY = "application_history"


class KnowledgeAuthority(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    DOCUMENT_SUPPORTED = "document_supported"
    EXTERNAL_SOURCE = "external_source"
    AI_INFERRED = "ai_inferred"
    RULE_VERIFIED = "rule_verified"


class KnowledgeStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class KnowledgeCreatedBy(StrEnum):
    USER = "USER"
    LLM = "LLM"
    PLUGIN = "PLUGIN"
    IMPORTER = "IMPORTER"
    RULE = "RULE"


class KnowledgeEntry(FrozenModel):
    knowledge_id: OpaqueId
    category: KnowledgeCategory
    title: str = Field(min_length=1, max_length=512)
    status: KnowledgeStatus
    authority: KnowledgeAuthority
    created_by: KnowledgeCreatedBy
    current_revision: int = Field(ge=1)
    labels: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeRevision(FrozenModel):
    knowledge_id: OpaqueId
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_type: str = Field(min_length=1, max_length=128)
    source_locator: str = Field(min_length=1, max_length=4096)
    artifact_id: str | None = None
    evidence_refs: tuple[OpaqueId, ...] = ()
    authority: KnowledgeAuthority
    confidence: float = Field(ge=0, le=1)
    created_by: KnowledgeCreatedBy
    status: KnowledgeStatus
    prompt_injection_flag: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class KnowledgeLink(FrozenModel):
    link_id: OpaqueId
    source_knowledge_id: OpaqueId
    source_revision: int = Field(ge=1)
    target_knowledge_id: OpaqueId
    target_revision: int = Field(ge=1)
    relation: str = Field(min_length=1, max_length=64)
    evidence_refs: tuple[OpaqueId, ...] = ()
    created_by: KnowledgeCreatedBy
    created_at: datetime = Field(default_factory=utc_now)


class KnowledgeProposal(FrozenModel):
    proposal_id: OpaqueId
    target_knowledge_id: str | None = None
    base_revision: int | None = Field(default=None, ge=1)
    category: KnowledgeCategory
    title: str = Field(min_length=1, max_length=512)
    proposed_content: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_refs: tuple[OpaqueId, ...] = ()
    authority: KnowledgeAuthority
    created_by: KnowledgeCreatedBy
    status: ProposalStatus
    reviewed_by: str | None = None
    review_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    reviewed_at: datetime | None = None


class KnowledgeCitation(FrozenModel):
    knowledge_id: OpaqueId
    revision: int = Field(ge=1)
    evidence_refs: tuple[OpaqueId, ...] = ()
    source_type: str
    source_locator: str
    authority: KnowledgeAuthority


class KnowledgeSearchResult(FrozenModel):
    knowledge_id: OpaqueId
    revision: int = Field(ge=1)
    title: str
    snippet: str
    score: float = Field(ge=0)
    lexical_score: float = Field(ge=0)
    semantic_score: float = Field(ge=0, le=1)
    search_mode: str = Field(pattern=r"^(lexical|hybrid)$")
    category: KnowledgeCategory
    status: KnowledgeStatus
    citation: KnowledgeCitation


class KnowledgeSearchPage(FrozenModel):
    items: tuple[KnowledgeSearchResult, ...]
    query: str
    evidence_sufficient: bool
    message: str | None = None
    next_cursor: str | None = None
