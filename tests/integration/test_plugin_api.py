from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.platform import AppPaths


@pytest.mark.asyncio
async def test_plugin_api_echo_acceptance(tmp_path: Path) -> None:
    token = "plugin-api-test-token"
    app = create_runtime_app(
        Settings.for_test(token=token),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        catalog = await client.get("/api/v1/plugins", headers=headers)
        assert catalog.status_code == 200
        echo = next(item for item in catalog.json() if item["manifest"]["id"] == "echo-fixture")
        manifest = echo["manifest"]
        preview = await client.post(
            "/api/v1/plugins/install-preview",
            json={"manifest": manifest},
            headers=headers,
        )
        assert preview.status_code == 200
        installed = await client.post(
            "/api/v1/plugins/install",
            json={"manifest": manifest},
            headers={**headers, "X-Idempotency-Key": "api-install-001"},
        )
        assert installed.status_code == 200
        assert installed.json()["status"] == "installed"
        assert (
            await client.post("/api/v1/plugins/echo-fixture/enable", headers=headers)
        ).json()["enabled"] is True
        invocation = await client.post(
            "/api/v1/plugins/echo-fixture/invoke",
            json={
                "request_id": "api-echo-request-001",
                "capability": "fixture.echo",
                "payload": {"source": "api"},
            },
            headers=headers,
        )
        assert invocation.status_code == 200
        assert invocation.json()["status"] == "ok"
        health = await client.post(
            "/api/v1/plugins/echo-fixture/healthcheck",
            headers=headers,
        )
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert (
            await client.post("/api/v1/plugins/echo-fixture/disable", headers=headers)
        ).json()["enabled"] is False
        rollback = await client.post(
            "/api/v1/plugins/echo-fixture/rollback", headers=headers
        )
        assert rollback.status_code == 200
        audit = await client.get(
            "/api/v1/plugins/echo-fixture/audit", headers=headers
        )
        assert audit.status_code == 200
        assert {entry["action"] for entry in audit.json()} >= {
            "install",
            "enable",
            "healthcheck",
            "disable",
            "rollback",
        }


@pytest.mark.asyncio
async def test_plugin_api_requires_launch_token(tmp_path: Path) -> None:
    app = create_runtime_app(
        Settings.for_test(token="plugin-api-test-token"),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/plugins")).status_code == 401
