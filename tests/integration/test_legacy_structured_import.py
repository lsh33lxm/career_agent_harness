from __future__ import annotations

import csv
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from career_harness.api.app import create_app
from career_harness.api.legacy_import import LegacyImportApi
from career_harness.config import Settings
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.legacy_import_service import SOURCE_SPECS, LegacyImportService
from career_harness.storage import ArtifactStore

TOKEN = "legacy-structured-test-token"


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _legacy_fixture(root: Path) -> None:
    for spec in SOURCE_SPECS:
        path = root / spec.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    _write_csv(
        root / "data/统一数据/岗位与JD数据.csv",
        [
            "unified_job_id",
            "company_canonical",
            "role_raw",
            "location",
            "requirements_raw",
            "original_url",
            "effective_date",
        ],
        [
            {
                "unified_job_id": "job-history-1",
                "company_canonical": "示例科技",
                "role_raw": "Python 开发工程师",
                "location": "上海",
                "requirements_raw": "Python；SQLite",
                "original_url": "https://example.invalid/jobs/1",
                "effective_date": "2026-09-18",
            }
        ],
    )
    _write_csv(
        root / "data/统一数据/面试事件数据.csv",
        ["unified_interview_id", "company_canonical", "role_raw", "title"],
        [
            {
                "unified_interview_id": "interview-1",
                "company_canonical": "示例科技",
                "role_raw": "Python 开发工程师",
                "title": "一面记录",
            }
        ],
    )
    _write_csv(
        root / "data/统一数据/问题明细.csv",
        ["unified_record_id", "canonical_question", "topic", "company", "role"],
        [
            {
                "unified_record_id": "question-1",
                "canonical_question": "如何设计可审计的 Agent 工作流？",
                "topic": "Agent 工程",
                "company": "示例科技",
                "role": "Python 开发工程师",
            }
        ],
    )
    _write_csv(
        root / "data/统一数据/来源总台账.csv",
        ["unified_source_id", "original_url"],
        [],
    )
    _write_csv(
        root / "data/统一数据/个人刷题记录.csv",
        ["LeetCode 题号", "题目"],
        [{"LeetCode 题号": "1", "题目": "两数之和"}],
    )
    _write_csv(
        root / "data/候选数据/9.16补采/PlatformJobObservation_candidate_platform.csv",
        ["observation_id", "company_canonical", "job_title_canonical"],
        [],
    )
    _write_csv(
        root / "data/候选数据/9.16补采/OfficialJD_candidate_official.csv",
        ["portal_id", "company_canonical", "job_title", "official_portal_url"],
        [
            {
                "portal_id": "portal-1",
                "company_canonical": "示例科技",
                "job_title": "",
                "official_portal_url": "https://example.invalid/careers",
            }
        ],
    )
    _write_csv(
        root / "data/候选数据/9.16补采/CanonicalJobPosting_candidate_platform.csv",
        ["canonical_id", "company_canonical", "job_title_canonical"],
        [],
    )


@pytest.fixture
def legacy_service(tmp_path: Path) -> tuple[LegacyImportService, Path]:
    legacy = tmp_path / "legacy"
    _legacy_fixture(legacy)
    data = tmp_path / "data"
    artifacts = data / "artifacts"
    artifacts.mkdir(parents=True)
    engine = create_sqlite_engine(sqlite_url(data / "career_harness.db"))
    upgrade_to_head(sqlite_url(data / "career_harness.db"))
    return LegacyImportService(
        engine,
        ArtifactStore(artifacts),
        default_source_root=legacy,
    ), legacy


def test_structured_import_is_read_only_idempotent_and_queryable(
    legacy_service: tuple[LegacyImportService, Path],
) -> None:
    service, legacy = legacy_service
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in legacy.rglob("*")}

    first = service.run()
    second = service.run()

    assert first.status == "completed"
    assert first.totals == {
        "read_count": 5,
        "new_count": 5,
        "updated_count": 0,
        "unchanged_count": 0,
        "duplicate_count": 0,
        "failed_count": 0,
    }
    assert second.totals["new_count"] == 0
    assert second.totals["unchanged_count"] == 5
    assert second.totals["failed_count"] == 0
    assert first.source_signature_before == first.source_signature_after
    assert second.source_signature_before == second.source_signature_after
    after = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in legacy.rglob("*")}
    assert after == before
    reopened_status = LegacyImportService(service.engine, service.artifact_store).status()
    assert reopened_status.configured_source_root == str(legacy.resolve())
    assert reopened_status.source_accessible is True

    jobs = service.list_jobs(query="Python", location="上海")
    assert len(jobs) == 1
    assert jobs[0].company == "示例科技"
    assert jobs[0].row_number == 2
    assert jobs[0].source_sha256
    detail = service.get_job(jobs[0].staging_id)
    assert detail is not None
    assert "SQLite" in detail.jd_text
    assert detail.raw_record["unified_job_id"] == "job-history-1"
    assert len(detail.related_interviews) == 1

    overview = service.knowledge_overview()
    assert overview.job_count == 1
    assert overview.interview_count == 1
    assert overview.question_count == 1
    assert overview.coding_count == 1
    assert overview.top_skills[0].label in {"Python", "SQLite"}
    assert overview.questions[0].title == "如何设计可审计的 Agent 工作流？"
    assert overview.questions[0].source_path.endswith("问题明细.csv")
    assert overview.questions[0].source_sha256

    with service.engine.connect() as connection:
        source_rows = connection.execute(
            text("SELECT COUNT(*) FROM legacy_projection_record WHERE record_kind='source'")
        ).scalar_one()
        assert source_rows == 1
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    with pytest.raises(IntegrityError), service.engine.begin() as connection:
        connection.execute(
            text("UPDATE legacy_projection_record SET review_status='needs_review'")
        )


@pytest.mark.asyncio
async def test_legacy_import_api_runs_import_and_returns_provenance(
    legacy_service: tuple[LegacyImportService, Path],
) -> None:
    service, legacy = legacy_service
    app = create_app(
        Settings.for_test(token=TOKEN),
        legacy_import_api=LegacyImportApi(service),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ) as client:
        status_response = await client.get("/api/v1/legacy/status")
        assert status_response.status_code == 200
        assert status_response.json()["source_accessible"] is True

        import_response = await client.post(
            "/api/v1/legacy/import",
            json={"source_root": str(legacy)},
        )
        assert import_response.status_code == 201
        assert import_response.json()["totals"]["failed_count"] == 0

        jobs_response = await client.get("/api/v1/legacy/jobs", params={"query": "Python"})
        assert jobs_response.status_code == 200
        job = jobs_response.json()[0]
        detail_response = await client.get(f"/api/v1/legacy/jobs/{job['staging_id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["job"]["source_path"].endswith("岗位与JD数据.csv")

        overview_response = await client.get("/api/v1/legacy/knowledge-overview")
        assert overview_response.status_code == 200
        overview = overview_response.json()
        assert overview["job_count"] == 1
        assert overview["question_count"] == 1
        assert overview["questions"][0]["title"] == "如何设计可审计的 Agent 工作流？"
