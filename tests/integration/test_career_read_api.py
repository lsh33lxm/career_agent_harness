from pathlib import Path

import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.api.career_reads import CareerReadApi
from career_harness.config import Settings
from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.common import EntityKind
from career_harness.core.outcome import OutcomeAuthority, OutcomeType
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.resume_repository import ResumeRepository
from tests.integration.test_application_service import _command, _seed_dependencies

TOKEN = "test-launch-token-value"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _app_with_history(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine, service = _seed_dependencies(tmp_path)
    service.create(
        _command("application_001", EntityKind.APPLICATION, "command_application"),
        opportunity_id="opportunity_001",
        opportunity_revision=1,
    )
    service.set_preparation_state(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_ready",
            expected_revision=1,
        ),
        state=ApplicationState.READY_FOR_REVIEW,
    )
    service.record_submission(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_submit",
            expected_revision=2,
        ),
        resume_revision_id="resume_revision_001",
        authority=SubmissionAuthority.USER_CONFIRMED,
    )
    service.advance_state(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_rejected",
            expected_revision=3,
        ),
        state=ApplicationState.REJECTED,
    )
    service.record_outcome(
        _command("outcome_001", EntityKind.OUTCOME, "command_outcome"),
        application_id="application_001",
        application_revision=4,
        result=OutcomeType.REJECTION,
        authority=OutcomeAuthority.USER_CONFIRMED,
    )
    return create_app(
        Settings.for_test(token=TOKEN),
        career_read_api=CareerReadApi(
            resumes=ResumeRepository(engine),
            applications=ApplicationRepository(engine),
        ),
    )


@pytest.mark.asyncio
async def test_career_reads_require_auth_and_return_exact_history(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app_with_history(tmp_path))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/api/v1/applications")
        applications = await client.get("/api/v1/applications", headers=AUTH)
        prepared = await client.get("/api/v1/applications/application_001?revision=2", headers=AUTH)
        outcomes = await client.get("/api/v1/applications/application_001/outcomes", headers=AUTH)
        base = await client.get("/api/v1/resumes/resume_001/base?revision=1", headers=AUTH)
        resume_revision = await client.get(
            "/api/v1/resume-revisions/resume_revision_001", headers=AUTH
        )

    assert unauthorized.status_code == 401
    assert applications.status_code == 200
    assert applications.json()[0]["state"] == "rejected"
    assert prepared.json()["state"] == "ready_for_review"
    assert outcomes.json()[0]["result"] == "rejection"
    assert base.json()["resume_id"] == "resume_001"
    assert resume_revision.json()["revision_id"] == "resume_revision_001"


@pytest.mark.asyncio
async def test_career_reads_fail_closed_and_expose_no_write_route(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app_with_history(tmp_path))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing_application = await client.get(
            "/api/v1/applications/application_missing", headers=AUTH
        )
        missing_outcomes = await client.get(
            "/api/v1/applications/application_missing/outcomes", headers=AUTH
        )
        missing_resume = await client.get(
            "/api/v1/resume-revisions/resume_revision_missing", headers=AUTH
        )
        write_attempt = await client.post("/api/v1/applications", headers=AUTH, json={})

    assert missing_application.status_code == 404
    assert missing_outcomes.status_code == 404
    assert missing_resume.status_code == 404
    assert write_attempt.status_code == 405
