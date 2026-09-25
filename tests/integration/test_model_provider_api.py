from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from career_harness.api.app import create_app
from career_harness.api.model_providers import ModelProviderApi
from career_harness.config import Settings
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.model_provider_repository import ModelProviderRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform.secure_store import MemorySecretStore
from career_harness.services.model_provider_service import ConnectionResult, ModelProviderService


class _Connector:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def test(self, config: dict[str, object], api_key: str) -> ConnectionResult:
        assert config["base_url"] == "https://api.openai.com/v1"
        self.keys.append(api_key)
        return ConnectionResult(True, 200, None, 12)


@pytest.mark.asyncio
async def test_model_provider_secret_is_redacted_and_connection_requires_confirmation(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "core.db")
    upgrade_to_head(database_url)
    repository = ModelProviderRepository(create_sqlite_engine(database_url))
    secrets = MemorySecretStore()
    connector = _Connector()
    service = ModelProviderService(repository, secrets, connector)
    app = create_app(
        Settings.for_test("model-provider-test-token"),
        model_provider_api=ModelProviderApi(service),
    )
    headers = {"Authorization": "Bearer model-provider-test-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        configured = await client.post(
            "/api/v1/model-providers/configure",
            headers=headers,
            json={
                "provider_id": "openai",
                "provider_kind": "openai",
                "base_url": "https://api.openai.com/v1/",
                "default_model": "gpt-4.1-mini",
                "timeout_seconds": 20,
                "api_key": "synthetic-secret-key",
            },
        )
        assert configured.status_code == 200
        assert configured.json()["has_api_key"] is True
        assert "synthetic-secret-key" not in configured.text

        denied = await client.post(
            "/api/v1/model-providers/openai/test",
            headers=headers,
            json={"confirm_external_request": False},
        )
        assert denied.status_code == 422
        assert connector.keys == []

        tested = await client.post(
            "/api/v1/model-providers/openai/test",
            headers=headers,
            json={"confirm_external_request": True},
        )
        assert tested.status_code == 200
        assert tested.json()["connection_status"] == "connected"
        assert connector.keys == ["synthetic-secret-key"]
        assert "synthetic-secret-key" not in tested.text

        listed = await client.get("/api/v1/model-providers", headers=headers)
        assert listed.json()[0]["masked_api_key"] == "••••••••"


@pytest.mark.asyncio
async def test_model_provider_rejects_insecure_remote_url(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "core.db")
    upgrade_to_head(database_url)
    service = ModelProviderService(
        ModelProviderRepository(create_sqlite_engine(database_url)),
        MemorySecretStore(),
    )
    app = create_app(
        Settings.for_test("model-provider-test-token"),
        model_provider_api=ModelProviderApi(service),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/model-providers/configure",
            headers={"Authorization": "Bearer model-provider-test-token"},
            json={
                "provider_id": "custom",
                "provider_kind": "openai_compatible",
                "base_url": "http://example.com/v1",
                "default_model": "model",
                "timeout_seconds": 20,
                "api_key": "synthetic-secret-key",
            },
        )
        assert response.status_code == 422
