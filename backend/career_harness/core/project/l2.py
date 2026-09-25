"""Transient, non-authorizing L2 invocation preparation (contract 0.15.0)."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from career_harness.core.common import FrozenModel, OpaqueId
from career_harness.core.project.models import normalize_project_path

MAX_FILE_BYTES = 65_536
MAX_CONTEXT_BYTES = 262_144
MAX_PROMPT_BYTES = 524_288
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelName = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z][a-zA-Z0-9._-]*$")
]


class PreparationError(ValueError):
    """Stable preparation failure; never includes caller content."""


class UnsupportedProviderError(PreparationError):
    pass


class PrivateModel(FrozenModel):
    model_config = ConfigDict(hide_input_in_errors=True)


class AnalysisProvider(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"


class ExactRef(PrivateModel):
    entity_id: OpaqueId
    revision: int = Field(ge=1, strict=True)


class ContextFile(PrivateModel):
    relative_path: str = Field(min_length=1, max_length=1024, repr=False)
    content: str = Field(max_length=MAX_FILE_BYTES, repr=False)

    @field_validator("relative_path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        path = normalize_project_path(value)
        if path == "." or any(ord(char) < 32 for char in path) or ":" in path:
            raise ValueError("context requires a relative file path")
        return path

    @field_validator("content")
    @classmethod
    def valid_utf8(cls, value: str) -> str:
        try:
            content = value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("context must be valid UTF-8") from None
        if len(content) > MAX_FILE_BYTES:
            raise ValueError("context file exceeds the byte limit")
        return value


class AnalysisRequest(PrivateModel):
    task: ExactRef
    project: ExactRef
    scope: ExactRef
    manifest_id: OpaqueId
    provider: AnalysisProvider
    model: ModelName
    max_budget_usd: Decimal = Field(gt=0, le=100, max_digits=7, decimal_places=4)
    timeout_seconds: int = Field(ge=1, le=3600, strict=True)
    max_output_bytes: int = Field(default=65_536, ge=1, le=262_144, strict=True)
    files: tuple[ContextFile, ...] = Field(min_length=1, max_length=32, repr=False)

    @model_validator(mode="after")
    def context_is_bounded_and_unique(self) -> AnalysisRequest:
        paths = [file.relative_path.casefold() for file in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("context paths must be unique without case collisions")
        if sum(len(file.content.encode("utf-8")) for file in self.files) > MAX_CONTEXT_BYTES:
            raise ValueError("context exceeds the aggregate byte limit")
        return self


class PreparedPermissions(PrivateModel):
    execution_authorized: Literal[False] = False
    provider_inference_requires_authorization: Literal[True] = True
    model_shell_tools: Literal[False] = False
    model_file_read_tools: Literal[False] = False
    model_file_write_tools: Literal[False] = False
    model_network_tools: Literal[False] = False
    process_egress_isolated: Literal[False] = False
    runtime_zero_host_writes_guaranteed: Literal[False] = False
    output_authority: Literal["unreviewed_proposal"] = "unreviewed_proposal"


class PreparedInvocation(PrivateModel):
    task: ExactRef
    project: ExactRef
    scope: ExactRef
    manifest_id: OpaqueId
    provider: Literal[AnalysisProvider.CLAUDE]
    model: ModelName
    max_budget_usd: Decimal = Field(gt=0, le=100)
    timeout_seconds: int = Field(ge=1, le=3600)
    max_output_bytes: int = Field(ge=1, le=262_144)
    argv: tuple[str, ...] = Field(min_length=1, max_length=24)
    stdin: str = Field(max_length=MAX_PROMPT_BYTES, repr=False)
    context_digest: Digest
    request_digest: Digest
    permissions: PreparedPermissions = Field(default_factory=PreparedPermissions)
