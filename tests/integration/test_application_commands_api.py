from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.platform import AppPaths

TOKEN = "application-command-api-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.mark.asyncio
async def test_application_commands_use_exact_revisions_and_user_boundary(tmp_path: Path) -> None:
    app = create_runtime_app(
        Settings.for_test(token=TOKEN),
        AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")}),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        staged = await client.post("/api/v1/jobs/fixture-search", headers=AUTH, json={})
        staging_id = staged.json()[0]["staging_id"]
        admitted = await client.post(f"/api/v1/jobs/staging/{staging_id}/admit", headers=AUTH)
        opportunity = admitted.json()["admission"]["opportunity"]
        created = await client.post(
            "/api/v1/applications",
            headers=AUTH,
            json={
                "command_id": "command_application_api_1",
                "application_id": "application_api_1",
                "opportunity_id": opportunity["entity_id"],
                "opportunity_revision": opportunity["revision"],
            },
        )
        ready = await client.post(
            "/api/v1/applications/application_api_1/preparation-state",
            headers=AUTH,
            json={"command_id": "command_application_api_ready", "expected_revision": 1, "state": "ready_for_review"},
        )
        invalid_interview = await client.post(
            "/api/v1/interviews",
            headers=AUTH,
            json={
                "command_id": "command_interview_before_submit",
                "interview_id": "interview_before_submit",
                "application_id": "application_api_1",
                "application_revision": ready.json()["revision"],
                "round": "technical",
                "scheduled_at": "2026-10-01T09:00:00+08:00",
            },
        )

    assert created.status_code == 201
    assert created.json()["state"] == "preparing"
    assert ready.status_code == 200
    assert ready.json()["state"] == "ready_for_review"
    assert invalid_interview.status_code == 409
    assert "submitted" in invalid_interview.json()["detail"]
