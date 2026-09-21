from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.platform import AppPaths

TOKEN = "job-radar-api-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.mark.asyncio
async def test_fixture_search_lists_staging_and_requires_user_admission(tmp_path: Path) -> None:
    app = create_runtime_app(
        Settings.for_test(token=TOKEN),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/api/v1/jobs/search")
        collected = await client.post(
            "/api/v1/jobs/fixture-search",
            headers=AUTH,
            json={"query": "platform", "desired_terms": ["Python", "Rust"]},
        )
        staging_id = collected.json()[0]["staging_id"]
        listing = await client.get("/api/v1/jobs/search?status=staged", headers=AUTH)
        admitted = await client.post(
            f"/api/v1/jobs/staging/{staging_id}/admit", headers=AUTH
        )
        seed = await client.get(
            f"/api/v1/jobs/staging/{staging_id}/resume-proposal-seed", headers=AUTH
        )
        opportunities = await client.get("/api/v1/opportunities", headers=AUTH)

    assert unauthorized.status_code == 401
    assert collected.status_code == 201
    assert collected.json()[0]["gaps"] == ["Rust"]
    assert listing.json()[0]["staging_id"] == staging_id
    assert admitted.status_code == 201
    assert seed.status_code == 200
    assert seed.json()["status"] == "proposal_only"
    assert opportunities.json()[0]["job"]["job_id"] == (
        admitted.json()["admission"]["decision"]["job"]["job_id"]
    )
