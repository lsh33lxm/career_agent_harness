from pathlib import Path

import httpx
import pytest

from career_harness.adapters.official_job_sources import TENCENT_CAMPUS, OfficialCampusJobSource
from career_harness.api import job_radar
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
            json={
                "query": "platform",
                "desired_terms": ["Python", "Rust"],
                "preferred_locations": ["Remote"],
                "minimum_salary": 100000,
            },
        )
        staging_id = collected.json()[0]["staging_id"]
        listing = await client.get("/api/v1/jobs/search?status=staged", headers=AUTH)
        admitted = await client.post(
            f"/api/v1/jobs/staging/{staging_id}/admit", headers=AUTH
        )
        seed = await client.get(
            f"/api/v1/jobs/staging/{staging_id}/resume-proposal-seed", headers=AUTH
        )
        source_document = await client.get(
            f"/api/v1/jobs/staging/{staging_id}/source-document", headers=AUTH
        )
        opportunities = await client.get("/api/v1/opportunities", headers=AUTH)
        policies = await client.get("/api/v1/jobs/source-policies", headers=AUTH)
        lifecycle = await client.get("/api/v1/jobs/listing-lifecycle", headers=AUTH)

    assert unauthorized.status_code == 401
    assert collected.status_code == 201
    assert collected.json()[0]["gaps"] == ["Rust"]
    assert "capability_match" in collected.json()[0]["score_breakdown"]
    assert listing.json()[0]["staging_id"] == staging_id
    assert admitted.status_code == 201
    assert seed.status_code == 200
    assert seed.json()["status"] == "proposal_only"
    assert source_document.status_code == 200
    assert source_document.json()["staging_id"] == staging_id
    assert source_document.json()["raw_sha256"] == collected.json()[0]["raw_sha256"]
    assert "Platform Engineer" in source_document.json()["raw_text"]
    assert opportunities.json()[0]["job"]["job_id"] == (
        admitted.json()["admission"]["decision"]["job"]["job_id"]
    )
    assert policies.status_code == 200
    assert policies.json()[0]["disabled"] is False
    assert lifecycle.status_code == 200
    assert lifecycle.json()[0]["status"] == "active"


@pytest.mark.asyncio
async def test_official_source_search_uses_existing_staging_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"腾讯 AI 实习生",
     "hiringOrganization":{"name":"腾讯"},
     "description":"参与 Agent 工程\\n- 熟悉 Python",
     "url":"https://join.qq.com/job/fixture"}
    </script>
    """
    monkeypatch.setattr(
        job_radar,
        "official_source",
        lambda source_id: OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html=fixture),
    )
    app = create_runtime_app(
        Settings.for_test(token=TOKEN),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/official-search",
            headers=AUTH,
            json={"source_id": TENCENT_CAMPUS.source_id, "query": "Agent"},
        )

    assert response.status_code == 201
    payload = response.json()[0]
    assert payload["source_id"] == TENCENT_CAMPUS.source_id
    assert payload["normalized"]["title"] == "腾讯 AI 实习生"
    assert payload["normalized"]["requirements"] == ["参与 Agent 工程", "熟悉 Python"]


@pytest.mark.asyncio
async def test_official_detail_returns_full_jd_and_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"腾讯 AI 实习生",
     "hiringOrganization":{"name":"腾讯"},
     "description":"岗位职责\\n参与 Agent 工程\\n任职要求\\n熟悉 Python",
     "url":"https://join.qq.com/job/detail-fixture"}
    </script>
    """
    monkeypatch.setattr(
        job_radar,
        "official_source",
        lambda source_id: OfficialCampusJobSource(TENCENT_CAMPUS, fixture_html=fixture),
    )
    app = create_runtime_app(
        Settings.for_test(token=TOKEN),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/official-detail",
            headers=AUTH,
            json={"source_id": TENCENT_CAMPUS.source_id, "source_ref": "https://join.qq.com/job/detail-fixture"},
        )

    assert response.status_code == 200
    assert response.json()["normalized"]["title"] == "腾讯 AI 实习生"
    assert "熟悉 Python" in response.json()["raw_text"]
    assert response.json()["source_ref"].endswith("detail-fixture")
