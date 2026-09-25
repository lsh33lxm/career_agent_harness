import sqlite3
from pathlib import Path

import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.api.evidence import EvidenceApi
from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform.paths import AppPaths
from tests.integration.test_evidence_repository import _insert_provenance

AUTH = {"Authorization": "Bearer evidence-test-token"}


def seeded(tmp_path):
    db = tmp_path / "evidence.db"
    upgrade_to_head(sqlite_url(db))
    engine = create_sqlite_engine(sqlite_url(db))
    _insert_provenance(engine)
    return (
        db,
        engine,
        create_app(
            Settings.for_test(token="evidence-test-token"),
            evidence_api=EvidenceApi(EvidenceRepository(engine)),
        ),
    )


@pytest.mark.asyncio
async def test_auth_paging_detail_and_no_writes(tmp_path: Path):
    db, engine, app = seeded(tmp_path)
    with sqlite3.connect(db) as connection:
        before = tuple(connection.iterdump())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/v1/evidence")).status_code == 401
        first = (await client.get("/api/v1/evidence?limit=1", headers=AUTH)).json()
        assert first["next_cursor"] == "evidence_job_requirements"
        assert len(first["items"]) == 1
        second = (
            await client.get("/api/v1/evidence?limit=1&after=" + first["next_cursor"], headers=AUTH)
        ).json()
        assert second["next_cursor"] is None
        assert second["items"][0]["evidence_ref"]["evidence_ref_id"] == "evidence_job_title"
        detail = (await client.get("/api/v1/evidence/evidence_job_title", headers=AUTH)).json()
        assert detail == second["items"][0]
        assert set(detail) == {"evidence_ref", "source", "snapshot", "artifact"}
        assert (await client.get("/api/v1/evidence/missing", headers=AUTH)).status_code == 404
        assert (await client.get("/api/v1/evidence?limit=101", headers=AUTH)).status_code == 422
        assert (await client.get("/api/v1/evidence?after=", headers=AUTH)).status_code == 422
        assert (await client.post("/api/v1/evidence", headers=AUTH)).status_code == 405
        assert (
            await client.delete("/api/v1/evidence/evidence_job_title", headers=AUTH)
        ).status_code == 405
    with sqlite3.connect(db) as connection:
        assert tuple(connection.iterdump()) == before
    engine.dispose()


@pytest.mark.asyncio
async def test_dangling_provenance_fails_loud_on_list_and_detail(tmp_path: Path):
    db, engine, app = seeded(tmp_path)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO evidence_ref(evidence_ref_id,snapshot_id,artifact_id) "
            "VALUES ('broken','missing','missing')"
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for path in ("/api/v1/evidence", "/api/v1/evidence/broken"):
            response = await client.get(path, headers=AUTH)
            assert response.status_code == 409
            assert response.json()["detail"] == "evidence provenance is incomplete or inconsistent"
    engine.dispose()


@pytest.mark.asyncio
async def test_runtime_uses_injected_database_only(tmp_path: Path):
    paths = AppPaths.resolve({"ACH_DATA_DIR": str(tmp_path / "rehearsal")})
    app = create_runtime_app(Settings.for_test(token="evidence-test-token"), paths)
    engine = create_sqlite_engine(sqlite_url(paths.database))
    _insert_provenance(engine)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/evidence", headers=AUTH)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2
    engine.dispose()
