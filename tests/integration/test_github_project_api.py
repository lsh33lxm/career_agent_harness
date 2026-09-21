from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from career_harness.api.app import create_app
from career_harness.api.github_projects import GitHubProjectApi
from career_harness.api.project_reads import ProjectReadApi
from career_harness.config import Settings
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform.secure_store import MemorySecretStore
from career_harness.services.github_project_service import FetchedRepository, GitHubProjectService


class _Fetcher:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tokens: list[str | None] = []

    def fetch(self, url: str, cache_root: Path, token: str | None) -> FetchedRepository:
        assert url == "https://github.com/example/career-tool"
        self.tokens.append(token)
        files = [item for item in self.root.rglob("*") if item.is_file()]
        return FetchedRepository(
            self.root,
            "a" * 40,
            len(files),
            sum(item.stat().st_size for item in files),
        )


@pytest.mark.asyncio
async def test_read_only_github_analysis_creates_traceable_project_profile(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    (repository_root / "src").mkdir(parents=True)
    (repository_root / "tests").mkdir()
    (repository_root / "README.md").write_text("# Career Tool\n性能提升 30%", encoding="utf-8")
    (repository_root / "pyproject.toml").write_text(
        "[project]\nname='career-tool'", encoding="utf-8"
    )
    (repository_root / "src" / "app.py").write_text("print('hello')", encoding="utf-8")
    (repository_root / "tests" / "test_app.py").write_text(
        "def test_ok(): assert True", encoding="utf-8"
    )

    database_url = sqlite_url(tmp_path / "core.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    secrets = MemorySecretStore()
    fetcher = _Fetcher(repository_root)
    service = GitHubProjectService(engine, tmp_path / "cache", secrets, fetcher)
    app = create_app(
        Settings.for_test("github-project-test-token"),
        project_read_api=ProjectReadApi(ProjectRepository(engine)),
        github_project_api=GitHubProjectApi(service),
    )
    headers = {"Authorization": "Bearer github-project-test-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post(
            "/api/v1/github/analyze",
            headers=headers,
            json={
                "repository_url": "https://github.com/example/career-tool",
                "confirm_read_only_network": False,
            },
        )
        assert denied.status_code == 422
        assert fetcher.tokens == []

        result = await client.post(
            "/api/v1/github/analyze",
            headers=headers,
            json={
                "repository_url": "https://github.com/example/career-tool.git",
                "confirm_read_only_network": True,
            },
        )
        assert result.status_code == 200
        payload = result.json()
        assert payload["commit_sha"] == "a" * 40
        assert payload["profile"]["technology_stack"] == ["Python"]
        assert payload["profile"]["outcome_clues"] == ["性能提升 30%"]
        assert payload["provenance"]["readme"] == "README.md"
        assert fetcher.tokens == [None]

        projects = await client.get("/api/v1/projects", headers=headers)
        assert projects.json()[0]["display_name"] == "example/career-tool"
        assert "root_locator" not in projects.text

        analyses = await client.get(
            f"/api/v1/github/projects/{payload['project_id']}/analyses", headers=headers
        )
        assert analyses.json()[0]["analysis_id"] == payload["analysis_id"]


@pytest.mark.asyncio
async def test_private_token_is_stored_outside_database_and_never_returned(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    (repository_root / "README.md").write_text("private", encoding="utf-8")
    database_url = sqlite_url(tmp_path / "core.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    secrets = MemorySecretStore()
    fetcher = _Fetcher(repository_root)
    app = create_app(
        Settings.for_test("github-project-test-token"),
        github_project_api=GitHubProjectApi(
            GitHubProjectService(engine, tmp_path / "cache", secrets, fetcher)
        ),
    )
    headers = {"Authorization": "Bearer github-project-test-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        saved = await client.post(
            "/api/v1/github/token",
            headers=headers,
            json={"token": "synthetic-github-token-value"},
        )
        assert saved.json() == {"configured": True}
        assert "synthetic-github-token-value" not in saved.text
        result = await client.post(
            "/api/v1/github/analyze",
            headers=headers,
            json={
                "repository_url": "https://github.com/example/career-tool",
                "use_private_token": True,
                "confirm_read_only_network": True,
            },
        )
        assert result.status_code == 200
        assert fetcher.tokens == ["synthetic-github-token-value"]
        assert "synthetic-github-token-value" not in result.text
