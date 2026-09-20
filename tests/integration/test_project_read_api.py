from pathlib import Path

import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.api.project_reads import ProjectReadApi
from career_harness.config import Settings
from career_harness.db.project_repository import ProjectRepository
from tests.integration.test_project_repository import _database

AUTH = {"Authorization": "Bearer test-project-token"}


@pytest.mark.asyncio
async def test_project_read_auth_exact_revision_and_root_privacy(tmp_path: Path):
    engine, _ = _database(tmp_path)
    app = create_app(
        Settings.for_test(token="test-project-token"),
        project_read_api=ProjectReadApi(ProjectRepository(engine)),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/v1/projects/project_001")).status_code == 401
        first = await client.get("/api/v1/projects/project_001?revision=1", headers=AUTH)
        latest = await client.get("/api/v1/projects/project_001", headers=AUTH)
        assert first.json()["project"]["revision"] == 1
        assert latest.json()["project"]["revision"] == 2
        assert "root_locator" not in first.text
        assert "D:/projects" not in first.text
        assert all(e["project_id"] == "project_001" for e in first.json()["evidence"])
        assert (
            await client.get("/api/v1/projects/project_001?revision=999", headers=AUTH)
        ).status_code == 404
        assert (await client.get("/api/v1/projects/absent", headers=AUTH)).status_code == 404
        assert (
            await client.get("/api/v1/projects/project_001?revision=0", headers=AUTH)
        ).status_code == 422
        assert (await client.post("/api/v1/projects/project_001", headers=AUTH)).status_code == 405
    engine.dispose()


@pytest.mark.asyncio
async def test_cross_project_evidence_fails_loud(tmp_path: Path, monkeypatch):
    engine, _ = _database(tmp_path)
    repository = ProjectRepository(engine)
    original = repository.list_evidence_for_project("project_001")
    monkeypatch.setattr(
        repository,
        "list_evidence_for_project",
        lambda _: (original[0].model_copy(update={"project_id": "wrong"}),),
    )
    app = create_app(
        Settings.for_test(token="test-project-token"), project_read_api=ProjectReadApi(repository)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/projects/project_001", headers=AUTH)
        assert response.status_code == 409
    engine.dispose()
