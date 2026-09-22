import base64
from pathlib import Path

import httpx
import pytest

from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform import AppPaths
from career_harness.services.command_service import CommandService
from career_harness.services.resume_service import ResumeService

TOKEN = "resume-studio-api-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _command(entity_id: str, kind: EntityKind, command_id: str) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=0,
        idempotency_key=f"idempotency-{command_id}",
        actor="user",
    )


def _app(tmp_path: Path):  # type: ignore[no-untyped-def]
    paths = AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "data")})
    paths.ensure_directories()
    upgrade_to_head(sqlite_url(paths.database))
    service = ResumeService(CommandService(create_sqlite_engine(sqlite_url(paths.database))))
    service.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_base"),
        candidate_id="candidate_001",
        sections={
            "name": "Minnn",
            "contact": "minnn@example.com",
            "summary": "Verified platform engineer",
        },
    )
    service.create_revision(
        _command("resume_revision_001", EntityKind.RESUME_REVISION, "command_revision"),
        resume_id="resume_001",
        base_revision=1,
        accepted_patch_refs=(),
    )
    return create_runtime_app(Settings.for_test(token=TOKEN), paths)


@pytest.mark.asyncio
async def test_resume_studio_api_target_render_report_and_artifact(tmp_path: Path) -> None:
    transport = httpx.ASGITransport(app=_app(tmp_path))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/api/v1/resume/templates")
        templates = await client.get("/api/v1/resume/templates", headers=AUTH)
        valid_resume = await client.post(
            "/api/v1/resume/validate",
            headers=AUTH,
            json={
                "content": {
                    "name": "Minnn",
                    "skills": ["Python"],
                    "experience": [{"role": "工程师"}],
                }
            },
        )
        invalid_resume = await client.post(
            "/api/v1/resume/validate",
            headers=AUTH,
            json={"content": {"education": ["invalid-item"]}},
        )
        imported_text = await client.post(
            "/api/v1/resume/import-file",
            headers=AUTH,
            json={
                "media_type": "text/markdown",
                "content_base64": base64.b64encode(
                    "# Minnn\n\n## 技能\nPython\nSQLite\n\n## 项目\n本地求职工作台".encode()
                ).decode(),
            },
        )
        imported_image = await client.post(
            "/api/v1/resume/import-file",
            headers=AUTH,
            json={
                "media_type": "image/png",
                "content_base64": base64.b64encode(b"png-fixture").decode(),
            },
        )
        target = await client.post(
            "/api/v1/resume/target-profiles",
            headers=AUTH,
            json={
                "target_profile_id": "target_profile_api",
                "resume_id": "resume_001",
                "title": "Platform Engineer",
                "keyword_gaps": ["Kubernetes"],
            },
        )
        rendered = await client.post(
            "/api/v1/resume/render",
            headers=AUTH,
            json={
                "resume_revision_id": "resume_revision_001",
                "target_profile_id": "target_profile_api",
            },
        )
        render_id = rendered.json()["render_run_id"]
        report = await client.get(
            f"/api/v1/resume/render-runs/{render_id}/ats-report", headers=AUTH
        )
        artifact = await client.get(
            f"/api/v1/resume/render-runs/{render_id}/artifact", headers=AUTH
        )
        review = await client.post(
            f"/api/v1/resume/render-runs/{render_id}/review",
            headers=AUTH,
            json={"decision": "approved", "reason": "User reviewed the immutable output."},
        )
        loaded_review = await client.get(
            f"/api/v1/resume/render-runs/{render_id}/review", headers=AUTH
        )
        diff = await client.get("/api/v1/resume/diff/resume_revision_001", headers=AUTH)
        exported = await client.get(
            "/api/v1/resume/revisions/resume_revision_001/export?format=markdown",
            headers=AUTH,
        )

    assert unauthorized.status_code == 401
    assert templates.status_code == 200
    assert valid_resume.json()["valid"] is True
    assert valid_resume.json()["data"]["skills"] == ["Python"]
    assert invalid_resume.json()["valid"] is False
    assert imported_text.json()["valid"] is True
    assert imported_text.json()["data"]["skills"] == ["Python", "SQLite"]
    assert imported_image.json()["valid"] is False
    assert {item["template_id"] for item in templates.json()} == {
        "resume-render-html",
        "resume-render-typst",
    }
    typst = next(item for item in templates.json() if item["template_id"].endswith("typst"))
    assert typst["status"] in {"active", "disabled"}
    assert target.status_code == 201
    assert rendered.status_code == 201
    assert report.json()["keyword_gaps"] == ["Kubernetes"]
    assert artifact.headers["content-type"] == "application/pdf"
    assert artifact.content.startswith(b"%PDF-1.4")
    assert rendered.json()["renderer_plugin_id"] == "resume-render-html-builtin"
    assert review.status_code == 200
    assert loaded_review.json() == review.json()
    assert diff.json()["resume_revision_id"] == "resume_revision_001"
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "Minnn" in exported.text
