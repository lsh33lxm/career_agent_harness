from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.platform import AppPaths


@pytest.mark.asyncio
async def test_knowledge_api_import_search_and_review(tmp_path: Path) -> None:
    token = "knowledge-api-test-token"
    app = create_runtime_app(
        Settings.for_test(token=token),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        imported = await client.post(
            "/api/v1/knowledge/import",
            headers=headers,
            json={
                "content": "A verified platform project with exact evidence.",
                "media_type": "text/plain",
                "source_type": "manual_note",
                "source_locator": "fixture://api-knowledge",
                "category": "project_evidence",
                "title": "API project",
                "authority": "document_supported",
            },
        )
        assert imported.status_code == 200
        evidence_ref = imported.json()["evidence_refs"][0]
        search = await client.post(
            "/api/v1/knowledge/search",
            headers=headers,
            json={"query": "verified platform", "limit": 10},
        )
        assert search.status_code == 200
        assert search.json()["evidence_sufficient"] is True
        assert search.json()["items"][0]["citation"]["evidence_refs"] == [evidence_ref]
        proposal = await client.post(
            "/api/v1/knowledge/proposals",
            headers=headers,
            json={
                "category": "skill",
                "title": "Python",
                "content": "Python is proposed from the project note.",
                "evidence_refs": [evidence_ref],
            },
        )
        assert proposal.status_code == 200
        proposal_id = proposal.json()["proposal_id"]
        review = await client.post(
            f"/api/v1/knowledge/proposals/{proposal_id}/review",
            headers=headers,
            json={
                "decision": "approved",
                "reviewer": "user",
                "reason": "confirmed",
            },
        )
        assert review.status_code == 200
        assert review.json()["status"] == "approved"
        revisions = await client.get(
            f"/api/v1/wiki/pages/knowledge_{proposal_id[9:]}/revisions",
            headers=headers,
        )
        assert revisions.status_code == 200
        assert len(revisions.json()) == 1
