from pathlib import Path

import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.api.today import TodayApi
from career_harness.config import Settings
from career_harness.core.common import EntityKind
from career_harness.core.job import JobRef
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService
from career_harness.services.opportunity_service import OpportunityService
from career_harness.services.today_service import TodayService
from tests.integration.test_application_service import _command
from tests.integration.test_today_service import NOW, _interview_stage_services, _schedule
from tests.support.job_data import seed_job_revision

TOKEN = "test-launch-token-value"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _app(tmp_path: Path, *, seed: bool):  # type: ignore[no-untyped-def]
    database_url = sqlite_url(tmp_path / "today-api.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    if seed:
        seed_job_revision(engine, "job_001", 1)
        OpportunityService(CommandService(engine)).admit_manually(
            _command("opportunity_001", EntityKind.OPPORTUNITY, "command_opportunity_001"),
            JobRef(job_id="job_001", revision=1),
            opportunity_id="opportunity_001",
            decision_id="decision_001",
        )
    return create_app(
        Settings.for_test(token=TOKEN),
        today_api=TodayApi(service=TodayService(engine)),
    )


@pytest.mark.asyncio
async def test_today_requires_auth(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app(tmp_path, seed=False))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/api/v1/today")
        wrong_token = await client.get(
            "/api/v1/today", headers={"Authorization": "Bearer wrong-token-value"}
        )
    assert unauthorized.status_code == 401
    assert wrong_token.status_code == 401


@pytest.mark.asyncio
async def test_today_returns_empty_queue_for_empty_database(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app(tmp_path, seed=False))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/today", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["input_revisions"] == []
    assert payload["policy_version"] == "today-policy-v1"
    assert payload["generated_at"]


@pytest.mark.asyncio
async def test_today_returns_queue_items(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app(tmp_path, seed=True))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/today", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    assert [item["item_id"] for item in payload["items"]] == [
        "today:opportunity_action:opportunity_001"
    ]
    item = payload["items"][0]
    assert item["kind"] == "opportunity_action"
    assert item["source_refs"] == [
        {"entity_id": "opportunity_001", "kind": "opportunity", "revision": 1}
    ]
    codes = {reason["code"] for reason in item["reasons"]}
    assert "missing_user_priority" in codes
    assert "missing_suggested_priority" in codes
    assert payload["input_revisions"] == item["source_refs"]


@pytest.mark.asyncio
async def test_today_api_exposes_exact_selected_interview_and_historical_application(
    tmp_path: Path,
) -> None:
    engine, _, interviews = _interview_stage_services(tmp_path)
    _schedule(interviews, "interview_001")
    app = create_app(
        Settings.for_test(token=TOKEN), today_api=TodayApi(service=TodayService(engine))
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/today", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    item = next(item for item in payload["items"] if item["kind"] == "interview_prep")
    assert item["item_id"] == "today:interview_prep:application_001"
    assert item["interview_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert item["source_refs"] == [
        {"entity_id": "application_001", "kind": "application", "revision": 4},
        {"entity_id": "opportunity_001", "kind": "opportunity", "revision": 1},
        {"entity_id": "interview_001", "kind": "interview", "revision": 1},
        {"entity_id": "application_001", "kind": "application", "revision": 3},
    ]
    assert all(ref in payload["input_revisions"] for ref in item["source_refs"])
    assert payload["policy_version"] == "today-policy-v1"
