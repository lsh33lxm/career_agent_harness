from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, JsonValue, field_validator, model_validator

from career_harness.core.common import FrozenModel, OpaqueId, utc_now

CONTRACT_VERSION = "v1.4-contract-0.1.0"
SELECTION_POLICY_VERSION = "context-relevance-v1"
COMPRESSION_POLICY_VERSION = "context-no-compression-v1"


class ContextAssetClass(StrEnum):
    PERSONAL_CONTEXT = "personal_context"
    CAREER_STATE = "career_state"
    PROJECT_EVIDENCE = "project_evidence"
    MARKET_EVIDENCE = "market_evidence"
    CAREER_HISTORY_OUTCOME = "career_history_outcome"


class MarketEvidenceScope(StrEnum):
    TARGET = "target"
    BROAD = "broad"


class SelectionReason(StrEnum):
    EXPLICIT_REFERENCE = "explicit_reference"
    RELEVANCE_TERM_MATCH = "relevance_term_match"


class ExclusionReason(StrEnum):
    ASSET_CLASS_NOT_ALLOWED = "asset_class_not_allowed"
    NO_RELEVANCE_MATCH = "no_relevance_match"
    SELECTION_LIMIT = "selection_limit"


def _normalize_terms(value: object) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError("relevance terms must be provided as a sequence")
    if any(not isinstance(term, str) for term in value):
        raise ValueError("relevance terms must be strings")
    normalized = tuple(dict.fromkeys(term.strip().casefold() for term in value if term.strip()))
    return normalized


def _normalize_names(value: object) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError("capability and skill names must be provided as a sequence")
    if any(not isinstance(name, str) or not name.strip() for name in value):
        raise ValueError("capability and skill names cannot be empty")
    normalized = tuple(sorted(name.strip() for name in value))
    if len(set(normalized)) != len(normalized):
        raise ValueError("capability and skill names must be unique")
    return normalized


class ContextAssetRef(FrozenModel):
    asset_id: OpaqueId
    asset_class: ContextAssetClass
    revision: int = Field(ge=1)


class ContextAsset(FrozenModel):
    ref: ContextAssetRef
    title: str = Field(min_length=1, max_length=255)
    payload: dict[str, JsonValue]
    relevance_terms: tuple[str, ...] = ()
    market_scope: MarketEvidenceScope | None = None

    @field_validator("relevance_terms", mode="before")
    @classmethod
    def normalize_relevance_terms(cls, value: object) -> tuple[str, ...]:
        return _normalize_terms(value)

    @model_validator(mode="after")
    def market_scope_matches_asset_class(self) -> Self:
        if self.ref.asset_class is ContextAssetClass.MARKET_EVIDENCE:
            if self.market_scope is None:
                raise ValueError("market evidence requires target or broad scope")
        elif self.market_scope is not None:
            raise ValueError("only market evidence may declare a market scope")
        return self


class VerticalKnowledgeRef(FrozenModel):
    knowledge_id: OpaqueId
    revision: int = Field(ge=1)


class VerticalKnowledgeAsset(FrozenModel):
    ref: VerticalKnowledgeRef
    payload: dict[str, JsonValue]


class IncludedContextAsset(FrozenModel):
    ref: ContextAssetRef
    reason: SelectionReason
    matched_terms: tuple[str, ...] = ()

    @field_validator("matched_terms", mode="before")
    @classmethod
    def normalize_matched_terms(cls, value: object) -> tuple[str, ...]:
        return _normalize_terms(value)

    @model_validator(mode="after")
    def reason_matches_terms(self) -> Self:
        if self.reason is SelectionReason.RELEVANCE_TERM_MATCH and not self.matched_terms:
            raise ValueError("relevance selection requires at least one matched term")
        if self.reason is SelectionReason.EXPLICIT_REFERENCE and self.matched_terms:
            raise ValueError("explicit selection cannot claim relevance term matches")
        return self


class ExcludedContextAsset(FrozenModel):
    ref: ContextAssetRef
    reason: ExclusionReason


class ContextSelectionResult(FrozenModel):
    included: tuple[IncludedContextAsset, ...]
    excluded: tuple[ExcludedContextAsset, ...]

    @model_validator(mode="after")
    def every_asset_has_one_disposition(self) -> Self:
        included = {item.ref.asset_id for item in self.included}
        excluded = {item.ref.asset_id for item in self.excluded}
        if len(included) != len(self.included) or len(excluded) != len(self.excluded):
            raise ValueError("context selection asset references must be unique")
        if included & excluded:
            raise ValueError("an asset cannot be both included and excluded")
        return self


class ContextCompilationRequest(FrozenModel):
    manifest_id: OpaqueId
    task_type: str = Field(min_length=1, max_length=128)
    task_input: dict[str, JsonValue] = Field(default_factory=dict)
    candidates: tuple[ContextAsset, ...] = ()
    allowed_asset_classes: tuple[ContextAssetClass, ...] = Field(min_length=1)
    relevance_terms: tuple[str, ...] = ()
    explicit_asset_ids: tuple[OpaqueId, ...] = ()
    max_assets: int = Field(default=12, ge=1, le=100)
    vertical_knowledge: tuple[VerticalKnowledgeAsset, ...] = ()
    provider: str = Field(min_length=1, max_length=255)
    model_id: str = Field(min_length=1, max_length=255)
    capabilities: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    actor: str = Field(min_length=1, max_length=255)
    run_id: OpaqueId

    @field_validator("relevance_terms", mode="before")
    @classmethod
    def normalize_relevance_terms(cls, value: object) -> tuple[str, ...]:
        return _normalize_terms(value)

    @field_validator("capabilities", "skills", mode="before")
    @classmethod
    def normalize_names(cls, value: object) -> tuple[str, ...]:
        return _normalize_names(value)

    @model_validator(mode="after")
    def validate_selection_boundary(self) -> Self:
        if len(set(self.allowed_asset_classes)) != len(self.allowed_asset_classes):
            raise ValueError("allowed asset classes must be unique")

        candidate_ids = [asset.ref.asset_id for asset in self.candidates]
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("context candidates must have unique asset ids")
        if len(set(self.explicit_asset_ids)) != len(self.explicit_asset_ids):
            raise ValueError("explicit asset ids must be unique")
        unknown_ids = set(self.explicit_asset_ids) - set(candidate_ids)
        if unknown_ids:
            raise ValueError("explicit asset ids must refer to supplied candidates")

        allowed_classes = set(self.allowed_asset_classes)
        allowed_explicit_count = sum(
            asset.ref.asset_id in self.explicit_asset_ids
            and asset.ref.asset_class in allowed_classes
            for asset in self.candidates
        )
        if allowed_explicit_count > self.max_assets:
            raise ValueError("max assets cannot discard explicitly requested allowed assets")

        knowledge_refs = [asset.ref for asset in self.vertical_knowledge]
        if len(set(knowledge_refs)) != len(knowledge_refs):
            raise ValueError("vertical knowledge references must be unique")
        return self


class ContextManifest(FrozenModel):
    manifest_id: OpaqueId
    contract_version: Literal["v1.4-contract-0.1.0"] = CONTRACT_VERSION
    task_type: str = Field(min_length=1, max_length=128)
    included: tuple[IncludedContextAsset, ...]
    excluded: tuple[ExcludedContextAsset, ...]
    selection_policy_version: Literal["context-relevance-v1"] = SELECTION_POLICY_VERSION
    compression_policy_version: Literal["context-no-compression-v1"] = (
        COMPRESSION_POLICY_VERSION
    )
    vertical_knowledge_refs: tuple[VerticalKnowledgeRef, ...]
    provider: str = Field(min_length=1, max_length=255)
    model_id: str = Field(min_length=1, max_length=255)
    capabilities: tuple[str, ...]
    skills: tuple[str, ...]
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    actor: str = Field(min_length=1, max_length=255)
    run_id: OpaqueId
    created_at: datetime = Field(default_factory=utc_now)
    authorizes_fact_mutation: Literal[False] = False

    @field_validator("capabilities", "skills", mode="before")
    @classmethod
    def normalize_names(cls, value: object) -> tuple[str, ...]:
        return _normalize_names(value)

    @model_validator(mode="after")
    def validate_audit_references(self) -> Self:
        ContextSelectionResult(included=self.included, excluded=self.excluded)
        if len(set(self.vertical_knowledge_refs)) != len(self.vertical_knowledge_refs):
            raise ValueError("vertical knowledge references must be unique")
        return self


class CompiledContext(FrozenModel):
    task_type: str = Field(min_length=1, max_length=128)
    task_input: dict[str, JsonValue]
    assets: tuple[ContextAsset, ...]
    vertical_knowledge: tuple[VerticalKnowledgeAsset, ...]
    manifest: ContextManifest

    @model_validator(mode="after")
    def payload_matches_manifest(self) -> Self:
        if self.task_type != self.manifest.task_type:
            raise ValueError("compiled task type must match its manifest")
        if tuple(asset.ref for asset in self.assets) != tuple(
            item.ref for item in self.manifest.included
        ):
            raise ValueError("compiled assets must match manifest included references")
        if tuple(asset.ref for asset in self.vertical_knowledge) != (
            self.manifest.vertical_knowledge_refs
        ):
            raise ValueError("compiled knowledge must match manifest knowledge references")
        return self
