from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.platform import AppPaths


@pytest.mark.asyncio
async def test_runtime_app_bootstraps_local_database_and_business_routes(tmp_path: Path) -> None:
    paths = AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "app-data")})
    app = create_runtime_app(Settings.for_test(token="test-launch-token-value"), paths)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/opportunities",
            headers={"Authorization": "Bearer test-launch-token-value"},
        )
        unauthorized_today = await client.get("/api/v1/today")
        today_response = await client.get(
            "/api/v1/today",
            headers={"Authorization": "Bearer test-launch-token-value"},
        )
        capability_response = await client.get(
            "/api/v1/capabilities/candidate_001",
            headers={"Authorization": "Bearer test-launch-token-value"},
        )

    assert unauthorized_today.status_code == 401
    assert today_response.status_code == 200
    assert today_response.json()["items"] == []
    assert today_response.json()["input_revisions"] == []
    assert today_response.json()["policy_version"] == "today-policy-v1"
    assert response.status_code == 200
    assert response.json() == []
    assert capability_response.status_code == 200
    assert capability_response.json()["graph_version"] is None
    assert paths.database.is_file()
    assert paths.artifacts.is_dir()
