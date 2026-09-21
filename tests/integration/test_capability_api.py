from pathlib import Path

import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.api.capabilities import CapabilityApi
from career_harness.config import Settings
from career_harness.services.capability_workspace_service import CapabilityWorkspaceService
from tests.integration.test_capability_repository import _repository, _seed_capability_data

TOKEN = "test-launch-token-value"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _app(tmp_path: Path, *, seed: bool):  # type: ignore[no-untyped-def]
    repository, connection = _repository(tmp_path)
    if seed:
        with connection.begin():
            _seed_capability_data(connection)
    connection.close()
    return create_app(
        Settings.for_test(token=TOKEN),
        capability_api=CapabilityApi(CapabilityWorkspaceService(repository)),
    )


@pytest.mark.asyncio
async def test_capability_workspace_requires_auth_and_returns_empty_graph(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app(tmp_path, seed=False))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/api/v1/capabilities/candidate_001")
        response = await client.get("/api/v1/capabilities/candidate_001", headers=AUTH)

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json() == {
        "candidate_id": "candidate_001",
        "graph_version": None,
        "nodes": [],
        "relations": [],
        "projections": [],
        "input_revisions": [],
        "workspace_version": "capability-workspace-v1",
    }


@pytest.mark.asyncio
async def test_capability_workspace_supports_exact_graph_and_unknown_is_404(
    tmp_path: Path,
) -> None:
    transport = httpx.ASGITransport(app=_app(tmp_path, seed=True))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        identities = await client.get("/api/v1/capabilities/identities", headers=AUTH)
        response = await client.get(
            "/api/v1/capabilities/candidate_001",
            params={"graph_version_id": "graph_version_001"},
            headers=AUTH,
        )
        missing = await client.get(
            "/api/v1/capabilities/candidate_001",
            params={"graph_version_id": "graph_missing"},
            headers=AUTH,
        )

    assert response.status_code == 200
    assert identities.status_code == 200
    assert identities.json() == ["candidate_001"]
    payload = response.json()
    assert payload["candidate_id"] == "candidate_001"
    assert payload["graph_version"]["graph_version_id"] == "graph_version_001"
    assert [node["capability_id"] for node in payload["nodes"]] == ["capability_a"]
    assert payload["projections"][0]["target_market_bindings"][0]["market_scope"] == "target"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "capability graph version not found: graph_missing"
