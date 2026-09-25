from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from career_harness.core.common import FrozenModel


class PluginType(StrEnum):
    BUILTIN_ADAPTER = "builtin_adapter"
    WORKER_PLUGIN = "worker_plugin"
    MCP_PLUGIN = "mcp_plugin"
    CLI_SKILL = "cli_skill"
    PROJECTION_PLUGIN = "projection_plugin"


class PluginStatus(StrEnum):
    DISCOVERED = "discovered"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class PluginEnvelopeStatus(StrEnum):
    OK = "ok"
    PROPOSAL = "proposal"
    BLOCKED = "blocked"
    ERROR = "error"


class PluginError(FrozenModel):
    code: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_.-]+$")
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class PluginSource(FrozenModel):
    repo: str = Field(min_length=1, max_length=2048)
    ref: str = Field(min_length=1, max_length=256)
    commit: str = Field(min_length=7, max_length=128)
    license: str = Field(min_length=1, max_length=128)


class PluginPermissions(FrozenModel):
    network: tuple[str, ...] = ()
    filesystem: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()
    external_write: bool = False
    scope: tuple[str, ...] = ()

    @field_validator("network", "filesystem", "secrets", "scope")
    @classmethod
    def non_empty_entries(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in values):
            raise ValueError("permission entries must not be blank")
        if len(set(values)) != len(values):
            raise ValueError("permission entries must be unique")
        return values


class PluginHealthcheck(FrozenModel):
    command: str = Field(min_length=1, max_length=128)
    timeout_ms: int = Field(ge=100, le=120_000)


class PluginReplacement(FrozenModel):
    compatible_capabilities: tuple[str, ...] = ()


class CoreCompatibility(FrozenModel):
    min_version: str = Field(min_length=1, max_length=64)
    max_version: str = Field(min_length=1, max_length=64)


class PluginCostLimits(FrozenModel):
    max_runtime_ms: int = Field(ge=100, le=300_000)
    max_output_bytes: int = Field(ge=1, le=10_000_000)


class PluginManifest(FrozenModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9-]{2,63}$")
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(
        min_length=5,
        max_length=128,
        pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$",
    )
    api_version: str = Field(pattern=r"^1$")
    type: PluginType
    source: PluginSource
    capabilities: tuple[str, ...] = Field(min_length=1)
    permissions: PluginPermissions = PluginPermissions()
    data_contracts: tuple[str, ...] = ()
    healthcheck: PluginHealthcheck
    replacement: PluginReplacement = PluginReplacement()
    dependencies: tuple[str, ...] = ()
    core_compatibility: CoreCompatibility
    config_schema: dict[str, Any] = Field(default_factory=dict)
    data_migration_version: int = Field(ge=0)
    cost_limits: PluginCostLimits
    user_visible_description: str = Field(min_length=1, max_length=4000)
    security_url: str = Field(min_length=1, max_length=2048)
    terms_url: str = Field(min_length=1, max_length=2048)

    @field_validator("capabilities", "data_contracts", "dependencies")
    @classmethod
    def unique_non_empty_entries(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in values):
            raise ValueError("manifest entries must not be blank")
        if len(set(values)) != len(values):
            raise ValueError("manifest entries must be unique")
        return values

    def canonical_json(self) -> bytes:
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()


class PluginEnvelope(FrozenModel):
    request_id: str = Field(min_length=8, max_length=128)
    plugin_id: str
    plugin_version: str
    capability: str
    status: PluginEnvelopeStatus
    data: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    error: PluginError | None = None
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    started_at: datetime
    finished_at: datetime

    @field_validator("started_at", "finished_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("envelope timestamps must include timezone")
        return value.astimezone(UTC)

    @classmethod
    def error_envelope(
        cls,
        *,
        request_id: str,
        plugin_id: str,
        plugin_version: str,
        capability: str,
        input_hash: str,
        started_at: datetime,
        error: PluginError,
        status: PluginEnvelopeStatus = PluginEnvelopeStatus.ERROR,
        warnings: tuple[str, ...] = (),
    ) -> PluginEnvelope:
        return cls(
            request_id=request_id,
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            capability=capability,
            status=status,
            input_hash=input_hash,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            error=error,
            warnings=warnings,
        )


def stable_payload_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
