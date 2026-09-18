from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.api.opportunities import OpportunityApi
from career_harness.config import Settings
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService
from career_harness.services.opportunity_service import OpportunityService

TOKEN = "test-launch-token-value"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def app_for_test(tmp_path: Path):  # type: ignore[no-untyped-def]
    database_url = sqlite_url(tmp_path / "api.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    return create_app(
        Settings.for_test(token=TOKEN),
        opportunity_api=OpportunityApi(
            repository=OpportunityRepository(engine),
            service=OpportunityService(CommandService(engine)),
        ),
    )


@pytest.mark.asyncio
async def test_opportunity_api_requires_token_and_supports_read_flow(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=app_for_test(tmp_path))
    admission = {
        "command_id": "command_admit_001",
        "opportunity_id": "opportunity_001",
        "decision_id": "decision_001",
        "job_id": "job_001",
        "job_revision": 2,
        "reason": "User selected this role.",
    }
    headers = {**AUTH, "X-Idempotency-Key": "manual-admission-001"}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/opportunities")).status_code == 401
        created = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers=headers,
            json=admission,
        )
        replay = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers=headers,
            json=admission,
        )
        listed = await client.get("/api/v1/opportunities", headers=AUTH)
        detail = await client.get("/api/v1/opportunities/opportunity_001", headers=AUTH)

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["commit"] == created.json()["commit"]
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert detail.json()["job"] == {"job_id": "job_001", "revision": 2}


@pytest.mark.asyncio
async def test_core_generates_stable_admission_ids_when_client_omits_them(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=app_for_test(tmp_path))
    admission = {
        "command_id": "command_generated_ids_001",
        "job_id": "job_generated_ids_001",
        "job_revision": 1,
    }
    headers = {**AUTH, "X-Idempotency-Key": "generated-admission-001"}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers=headers,
            json=admission,
        )
        replay = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers=headers,
            json=admission,
        )
        opportunity_id = created.json()["admission"]["opportunity"]["entity_id"]
        detail = await client.get(f"/api/v1/opportunities/{opportunity_id}", headers=AUTH)

    decision_id = created.json()["admission"]["decision"]["decision_id"]
    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["commit"] == created.json()["commit"]
    assert replay.json()["admission"]["opportunity"]["entity_id"] == opportunity_id
    assert replay.json()["admission"]["decision"]["decision_id"] == decision_id
    assert opportunity_id.startswith("opportunity_")
    assert decision_id.startswith("decision_")
    assert detail.status_code == 200
    assert detail.json()["job"]["job_id"] == "job_generated_ids_001"


@pytest.mark.asyncio
async def test_user_priority_api_uses_revision_and_preserves_user_authority(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=app_for_test(tmp_path))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers={**AUTH, "X-Idempotency-Key": "manual-admission-001"},
            json={
                "command_id": "command_admit_001",
                "opportunity_id": "opportunity_001",
                "decision_id": "decision_001",
                "job_id": "job_001",
                "job_revision": 1,
            },
        )
        updated = await client.patch(
            "/api/v1/opportunities/opportunity_001/user-priority",
            headers={**AUTH, "X-Idempotency-Key": "user-priority-001"},
            json={
                "command_id": "command_priority_001",
                "expected_revision": 1,
                "level": "high",
                "reason": "User-selected focus.",
            },
        )
        conflict = await client.patch(
            "/api/v1/opportunities/opportunity_001/user-priority",
            headers={**AUTH, "X-Idempotency-Key": "user-priority-002"},
            json={
                "command_id": "command_priority_002",
                "expected_revision": 1,
                "level": "low",
            },
        )
        detail = await client.get("/api/v1/opportunities/opportunity_001", headers=AUTH)

    assert updated.status_code == 200
    assert conflict.status_code == 409
    assert detail.json()["user_priority"]["level"] == "high"
    assert detail.json()["suggested_priority"] is None


@pytest.mark.asyncio
async def test_opportunity_api_rejects_missing_idempotency_header(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=app_for_test(tmp_path))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers=AUTH,
            json={
                "command_id": "command_admit_001",
                "opportunity_id": "opportunity_001",
                "decision_id": "decision_001",
                "job_id": "job_001",
                "job_revision": 1,
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ai_proposal_requires_user_confirmation_endpoint(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=app_for_test(tmp_path))
    headers = {**AUTH, "X-Idempotency-Key": "proposal-admission-001"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/opportunities/proposal-admissions",
            headers=headers,
            json={
                "command_id": "command_admit_001",
                "proposal_id": "proposal_001",
                "job_id": "job_001",
                "job_revision": 1,
                "proposal_reason": "Agent found strong target-market alignment.",
                "reason": "User confirmed the investment.",
                "proposed_by": "agent",
            },
        )
        opportunity_id = response.json()["admission"]["opportunity"]["entity_id"]
        detail = await client.get(f"/api/v1/opportunities/{opportunity_id}", headers=AUTH)

    assert response.status_code == 201
    assert opportunity_id.startswith("opportunity_")
    assert response.json()["admission"]["decision"]["proposal_id"] == "proposal_001"
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_duplicate_job_admission_returns_conflict(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=app_for_test(tmp_path))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers={**AUTH, "X-Idempotency-Key": "manual-admission-001"},
            json={
                "command_id": "command_admit_001",
                "opportunity_id": "opportunity_001",
                "decision_id": "decision_001",
                "job_id": "job_001",
                "job_revision": 1,
            },
        )
        duplicate = await client.post(
            "/api/v1/opportunities/manual-admissions",
            headers={**AUTH, "X-Idempotency-Key": "manual-admission-002"},
            json={
                "command_id": "command_admit_002",
                "opportunity_id": "opportunity_002",
                "decision_id": "decision_002",
                "job_id": "job_001",
                "job_revision": 1,
            },
        )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "opportunity conflicts with existing canonical state"}
    assert "INSERT" not in duplicate.text
