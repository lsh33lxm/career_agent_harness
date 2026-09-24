import hashlib
from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.platform import AppPaths

TOKEN = "requirements-api-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.mark.asyncio
async def test_requirement_propose_list_and_user_review_keep_exact_job_revision(
    tmp_path: Path,
) -> None:
    app = create_runtime_app(
        Settings.for_test(token=TOKEN),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await client.post(
            "/api/v1/jobs/fixture-search",
            headers=AUTH,
            json={"query": "platform"},
        )
        staging_id = seeded.json()[0]["staging_id"]
        raw_sha = seeded.json()[0]["raw_sha256"]
        digest = hashlib.sha256((staging_id + raw_sha).encode()).hexdigest()[:32]
        evidence_ref = f"evidence_job_staging_{digest}"
        admitted = await client.post(
            f"/api/v1/jobs/staging/{staging_id}/admit", headers=AUTH
        )
        job_id = admitted.json()["admission"]["decision"]["job"]["job_id"]
        proposed = await client.post(
            f"/api/v1/jobs/{job_id}/revisions/1/requirements",
            headers=AUTH,
            json={
                "requirement_id": "requirement_python_fixture",
                "requirement_text": "熟悉 Python",
                "source_evidence_refs": [
                    evidence_ref
                ],
            },
        )
        listed = await client.get(
            f"/api/v1/jobs/{job_id}/revisions/1/requirements", headers=AUTH
        )
        rejected = await client.post(
            "/api/v1/jobs/requirements/requirement_python_fixture/revisions/1/review",
            headers=AUTH,
            json={"decision": "rejected", "review_reason": "这是候选要求，暂不纳入匹配"},
        )

    assert proposed.status_code == 201
    assert proposed.json()["requirement"]["job"] == {"job_id": job_id, "revision": 1}
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "proposed"
    assert rejected.status_code == 200
    assert rejected.json()["requirement"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_acceptance_without_official_capability_mapping_is_rejected(tmp_path: Path) -> None:
    app = create_runtime_app(
        Settings.for_test(token=TOKEN),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await client.post("/api/v1/jobs/fixture-search", headers=AUTH, json={})
        staging_id = seeded.json()[0]["staging_id"]
        raw_sha = seeded.json()[0]["raw_sha256"]
        digest = hashlib.sha256((staging_id + raw_sha).encode()).hexdigest()[:32]
        evidence_ref = f"evidence_job_staging_{digest}"
        admitted = await client.post(
            f"/api/v1/jobs/staging/{staging_id}/admit", headers=AUTH
        )
        job_id = admitted.json()["admission"]["decision"]["job"]["job_id"]
        await client.post(
            f"/api/v1/jobs/{job_id}/revisions/1/requirements",
            headers=AUTH,
            json={
                "requirement_id": "requirement_accept_fixture",
                "requirement_text": "熟悉 Python",
                "source_evidence_refs": [
                    evidence_ref
                ],
            },
        )
        response = await client.post(
            "/api/v1/jobs/requirements/requirement_accept_fixture/revisions/1/review",
            headers=AUTH,
            json={"decision": "accepted", "review_reason": "确认"},
        )

    assert response.status_code == 409
    assert "official capability" in response.json()["detail"]
