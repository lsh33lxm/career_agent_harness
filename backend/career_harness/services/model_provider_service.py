from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4

from career_harness.db.model_provider_repository import ModelProviderRepository
from career_harness.platform.secure_store import WritableSecretStore

PROVIDER_DEFAULTS = {
    "openai": ("https://api.openai.com/v1", "gpt-4.1-mini"),
    "anthropic": ("https://api.anthropic.com/v1", "claude-sonnet-4-5"),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "openai_compatible": ("http://127.0.0.1:11434/v1", ""),
}


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    success: bool
    status_code: int | None
    error_code: str | None
    latency_ms: int


class ProviderConnector(Protocol):
    def test(self, config: dict[str, object], api_key: str) -> ConnectionResult: ...


class HttpProviderConnector:
    def test(self, config: dict[str, object], api_key: str) -> ConnectionResult:
        started = time.monotonic()
        kind = str(config["provider_kind"])
        base_url = str(config["base_url"]).rstrip("/")
        headers = {"Accept": "application/json", "User-Agent": "AgentCareerHarness/0.1"}
        if kind == "anthropic":
            headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        elif api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(f"{base_url}/models", headers=headers, method="GET")
        try:
            with urllib.request.urlopen(
                request, timeout=int(config["timeout_seconds"])
            ) as response:
                response.read(4096)
                return ConnectionResult(
                    True, response.status, None, int((time.monotonic() - started) * 1000)
                )
        except urllib.error.HTTPError as error:
            error.read(4096)
            code = "authentication_failed" if error.code in (401, 403) else "provider_http_error"
            return ConnectionResult(
                False, error.code, code, int((time.monotonic() - started) * 1000)
            )
        except (urllib.error.URLError, TimeoutError, OSError):
            return ConnectionResult(
                False, None, "connection_failed", int((time.monotonic() - started) * 1000)
            )


class ModelProviderService:
    def __init__(
        self,
        repository: ModelProviderRepository,
        secrets: WritableSecretStore,
        connector: ProviderConnector | None = None,
    ) -> None:
        self.repository = repository
        self.secrets = secrets
        self.connector = connector or HttpProviderConnector()

    @staticmethod
    def _secret_name(provider_id: str) -> str:
        return f"model-provider/{provider_id}"

    @staticmethod
    def _public(row: dict[str, object]) -> dict[str, object]:
        public = dict(row)
        has_api_key = bool(public.pop("has_secret", False))
        public["has_api_key"] = has_api_key
        public["masked_api_key"] = "••••••••" if has_api_key else None
        return public

    def list(self) -> list[dict[str, object]]:
        return [self._public(row) for row in self.repository.list()]

    def configure(self, values: dict[str, object], api_key: str | None) -> dict[str, object]:
        provider_id = str(values["provider_id"])
        kind = str(values["provider_kind"])
        if kind not in PROVIDER_DEFAULTS:
            raise ValueError("unsupported provider kind")
        base_url = str(values["base_url"]).rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("provider URL must use HTTPS unless it is local")
        current = self.repository.get(provider_id)
        has_secret = bool(current and current["has_secret"])
        if api_key:
            self.secrets.set(self._secret_name(provider_id), api_key)
            has_secret = True
        saved = self.repository.save({**values, "base_url": base_url, "has_secret": has_secret})
        return self._public(saved)

    def test_connection(self, provider_id: str, confirmed: bool) -> dict[str, object]:
        if not confirmed:
            raise ValueError("external request confirmation is required")
        config = self.repository.get(provider_id)
        if config is None:
            raise LookupError("provider is not configured")
        secret = self.secrets.get(self._secret_name(provider_id))
        parsed = urlparse(str(config["base_url"]))
        local_compatible = config["provider_kind"] == "openai_compatible" and parsed.hostname in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
        if secret is None and not local_compatible:
            raise LookupError("provider API key is not configured")
        result = self.connector.test(config, secret.reveal() if secret else "")
        saved = self.repository.record_test(
            provider_id,
            success=result.success,
            status_code=result.status_code,
            error_code=result.error_code,
            latency_ms=result.latency_ms,
            audit_id=f"provider_test_{uuid4().hex}",
        )
        return {
            **self._public(saved),
            "test": {
                "success": result.success,
                "status_code": result.status_code,
                "error_code": result.error_code,
                "latency_ms": result.latency_ms,
            },
        }
