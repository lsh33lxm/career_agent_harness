from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text

from career_harness.api.app import create_app
from career_harness.api.legacy_import import LegacyImportApi
from career_harness.api.source_connectors import SourceConnectorApi
from career_harness.config import Settings
from career_harness.core.connectors.models import ConnectorStatus, SyncMode
from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.db.source_connector_repository import SourceConnectorRepository
from career_harness.db.task_repository import TaskRepository
from career_harness.services.legacy_import_service import LegacyImportService
from career_harness.services.source_connector_service import (
    LegacyAgentRadarConnectorService,
    LocalFolderConnectorService,
)
from career_harness.services.task_service import RegisteredTaskHandler, TaskService
from career_harness.storage import ArtifactStore
from tests.integration.test_legacy_structured_import import _legacy_fixture


def _service(
    tmp_path: Path,
) -> tuple[SourceConnectorRepository, LocalFolderConnectorService, TaskService, Path]:
    database_url = sqlite_url(tmp_path / "connectors.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    repository = SourceConnectorRepository(engine)
    service = LocalFolderConnectorService(repository, ArtifactStore(tmp_path / "artifacts"))
    tasks = TaskService(
        TaskRepository(engine),
        handlers=(
            RegisteredTaskHandler(
                task_type="source.local_folder_sync",
                stage="source_sync",
                handler=lambda payload: service.sync(
                    str(payload["connector_id"]), SyncMode(str(payload["mode"]))
                ).model_dump(mode="json"),
            ),
        ),
        stage_limits={"source_sync": 1},
    )
    source = tmp_path / "source"
    source.mkdir()
    return repository, service, tasks, source


def test_local_folder_sync_is_incremental_auditable_and_delete_safe(tmp_path: Path) -> None:
    repository, service, tasks, source = _service(tmp_path)
    first = source / "岗位.md"
    second = source / "notes" / "面试.txt"
    second.parent.mkdir()
    first.write_text("Python 后端工程师", encoding="utf-8")
    second.write_text("STAR 复盘", encoding="utf-8")
    metadata_before = (first.stat().st_size, first.stat().st_mtime_ns)
    connector = service.create(display_name="我的求职资料", root_path=str(source))

    task = tasks.enqueue(
        "source.local_folder_sync",
        {"connector_id": connector.connector_id, "mode": "full"},
    )
    completed = tasks.run_one("source_sync")
    assert completed is not None and completed.task_id == task.task_id
    run = repository.list_runs(connector.connector_id)[0]
    assert run.status == "completed"
    assert run.stats.model_dump() == {
        "created": 2,
        "updated": 0,
        "skipped": 0,
        "deleted": 0,
        "failed": 0,
    }
    assert metadata_before == (first.stat().st_size, first.stat().st_mtime_ns)
    resources = repository.existing_resources(connector.connector_id)
    assert set(resources) == {"notes/面试.txt", "岗位.md"}
    digest = resources["岗位.md"]["artifact_sha256"]
    assert (tmp_path / "artifacts" / digest[:2] / digest[2:4] / digest).is_file()

    unchanged = service.sync(connector.connector_id)
    assert unchanged.stats.skipped == 2
    first.write_text("Python Agent 后端工程师", encoding="utf-8")
    second.unlink()
    changed = service.sync(connector.connector_id)
    assert changed.stats.updated == 1
    assert changed.stats.deleted == 1
    resources = repository.existing_resources(connector.connector_id)
    assert resources["notes/面试.txt"]["status"] == "source_deleted"
    artifact = tmp_path / "artifacts" / resources["notes/面试.txt"]["artifact_sha256"][:2]
    assert artifact.exists(), "source deletion must not remove the preserved artifact"


def test_failed_sync_preserves_cursor_and_local_resources(tmp_path: Path) -> None:
    repository, service, _tasks, source = _service(tmp_path)
    (source / "profile.md").write_text("用户确认资料", encoding="utf-8")
    connector = service.create(display_name="资料", root_path=str(source))
    service.sync(connector.connector_id)
    cursor_before = repository.get(connector.connector_id).sync_cursor
    moved = source.with_name("source-unavailable")
    source.rename(moved)

    with pytest.raises(FileNotFoundError):
        service.sync(connector.connector_id)

    current = repository.get(connector.connector_id)
    assert current.sync_cursor == cursor_before
    assert repository.existing_resources(connector.connector_id)["profile.md"]["status"] == "active"
    failed = repository.list_runs(connector.connector_id)[0]
    assert failed.status == "failed"
    assert failed.stats.failed == 1


def test_pause_resume_and_connection_test(tmp_path: Path) -> None:
    repository, service, _tasks, source = _service(tmp_path)
    connector = service.create(display_name="本地资料", root_path=str(source))
    assert service.test_connection(connector.connector_id)["ok"] is True
    repository.set_status(connector.connector_id, ConnectorStatus.PAUSED)
    with pytest.raises(ValueError, match="paused"):
        service.sync(connector.connector_id)
    resumed = repository.set_status(connector.connector_id, ConnectorStatus.ACTIVE)
    assert resumed.status is ConnectorStatus.ACTIVE


def test_legacy_connector_sync_is_idempotent_read_only_and_audited(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "legacy-connector.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    artifacts = ArtifactStore(tmp_path / "artifacts")
    repository = SourceConnectorRepository(engine)
    legacy_root = tmp_path / "legacy"
    _legacy_fixture(legacy_root)
    legacy = LegacyImportService(engine, artifacts)
    service = LegacyAgentRadarConnectorService(repository, legacy)
    before = {
        path: (path.stat().st_size, path.stat().st_mtime_ns)
        for path in legacy_root.rglob("*")
    }

    connector = service.create(display_name="历史 Agent Radar", root_path=str(legacy_root))
    assert connector.connector_type == "legacy_agent_radar"
    assert connector.delete_policy.value == "keep"
    tested = service.test_connection(connector.connector_id)
    assert tested["ok"] is True
    assert tested["required_file_count"] > 0

    first = service.sync(connector.connector_id, SyncMode.FULL)
    second = service.sync(connector.connector_id)
    assert first.stats.created == 5
    assert first.stats.failed == 0
    assert second.stats.created == 0
    assert second.stats.skipped == 5
    assert first.cursor_after is not None and second.cursor_after is not None
    assert first.cursor_after["source_signature"] == second.cursor_after["source_signature"]
    assert repository.get(connector.connector_id).sync_cursor == second.cursor_after
    after = {
        path: (path.stat().st_size, path.stat().st_mtime_ns)
        for path in legacy_root.rglob("*")
    }
    assert after == before
    with engine.connect() as connection:
        completed_events = connection.execute(
            text(
                "SELECT COUNT(*) FROM domain_event "
                "WHERE event_type='source.sync.completed'"
            )
        ).scalar_one()
    assert completed_events == 2


def test_legacy_connector_failure_preserves_cursor(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "legacy-failure.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    repository = SourceConnectorRepository(engine)
    legacy_root = tmp_path / "legacy"
    _legacy_fixture(legacy_root)
    service = LegacyAgentRadarConnectorService(
        repository,
        LegacyImportService(engine, ArtifactStore(tmp_path / "artifacts")),
    )
    connector = service.create(display_name="历史数据", root_path=str(legacy_root))
    service.sync(connector.connector_id)
    cursor_before = repository.get(connector.connector_id).sync_cursor
    (legacy_root / "data/统一数据/岗位与JD数据.csv").unlink()

    with pytest.raises(RuntimeError, match="缺少 Legacy 文件"):
        service.sync(connector.connector_id)

    assert repository.get(connector.connector_id).sync_cursor == cursor_before
    failed = repository.list_runs(connector.connector_id)[0]
    assert failed.status == "failed"
    assert failed.stats.failed == 1


@pytest.mark.asyncio
async def test_source_connector_api_runs_manual_sync_through_task_queue(tmp_path: Path) -> None:
    repository, service, tasks, source = _service(tmp_path)
    (source / "经历.md").write_text("有来源的项目经历", encoding="utf-8")
    app = create_app(
        Settings.for_test("connector-api-token-0001"),
        source_connector_api=SourceConnectorApi(service, repository, tasks),
    )
    headers = {"Authorization": "Bearer connector-api-token-0001"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/source-connectors/local-folder",
            headers=headers,
            json={"display_name": "求职资料", "root_path": str(source)},
        )
        assert created.status_code == 200
        connector_id = created.json()["connector_id"]
        synced = await client.post(
            f"/api/v1/source-connectors/{connector_id}/sync",
            headers=headers,
            json={"mode": "full"},
        )
        assert synced.status_code == 200
        assert synced.json()["status"] == "completed"
        runs = await client.get(
            f"/api/v1/source-connectors/{connector_id}/runs", headers=headers
        )
        assert runs.json()[0]["stats"]["created"] == 1


@pytest.mark.asyncio
async def test_legacy_connector_api_runs_manual_sync_through_task_queue(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "legacy-api.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    repository = SourceConnectorRepository(engine)
    artifacts = ArtifactStore(tmp_path / "artifacts")
    local = LocalFolderConnectorService(repository, artifacts)
    legacy_import = LegacyImportService(engine, artifacts)
    legacy = LegacyAgentRadarConnectorService(repository, legacy_import)
    tasks = TaskService(
        TaskRepository(engine),
        handlers=(
            RegisteredTaskHandler(
                task_type="source.legacy_agent_radar_sync",
                stage="source_sync",
                handler=lambda payload: legacy.sync(
                    str(payload["connector_id"]), SyncMode(str(payload["mode"]))
                ).model_dump(mode="json"),
            ),
        ),
        stage_limits={"source_sync": 1},
    )
    legacy_root = tmp_path / "legacy"
    _legacy_fixture(legacy_root)
    app = create_app(
        Settings.for_test("legacy-connector-api-token"),
        legacy_import_api=LegacyImportApi(legacy_import, legacy),
        source_connector_api=SourceConnectorApi(local, repository, tasks, legacy),
    )
    headers = {"Authorization": "Bearer legacy-connector-api-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/source-connectors/legacy-agent-radar",
            headers=headers,
            json={"display_name": "历史岗位", "root_path": str(legacy_root)},
        )
        assert created.status_code == 200
        connector_id = created.json()["connector_id"]
        tested = await client.post(
            f"/api/v1/source-connectors/{connector_id}/test", headers=headers
        )
        assert tested.status_code == 200
        synced = await client.post(
            f"/api/v1/source-connectors/{connector_id}/sync",
            headers=headers,
            json={"mode": "full"},
        )
        assert synced.status_code == 200
        assert synced.json()["status"] == "completed"
        runs = await client.get(
            f"/api/v1/source-connectors/{connector_id}/runs", headers=headers
        )
        assert runs.json()[0]["stats"]["created"] == 5
        compatible_import = await client.post(
            "/api/v1/legacy/import",
            headers=headers,
            json={"source_root": str(legacy_root)},
        )
        assert compatible_import.status_code == 201
        assert compatible_import.json()["totals"]["unchanged_count"] == 5
        connectors = await client.get("/api/v1/source-connectors", headers=headers)
        assert len(connectors.json()) == 1
        runs = await client.get(
            f"/api/v1/source-connectors/{connector_id}/runs", headers=headers
        )
        assert len(runs.json()) == 2
        assert runs.json()[0]["stats"]["skipped"] == 5


def test_source_connector_migration_is_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    assert {"source_connector", "source_resource", "source_sync_run"} <= set(
        inspect(engine).get_table_names()
    )
    repository = SourceConnectorRepository(engine)
    legacy = repository.create_legacy_agent_radar(
        display_name="可逆迁移", root_path=str(tmp_path / "legacy")
    )
    repository.start_run(legacy, SyncMode.FULL)
    github = repository.create_github(
        display_name="GitHub 可逆迁移",
        repository_url="https://github.com/example/career-tool",
        use_private_token=False,
    )
    repository.start_run(github, SyncMode.INCREMENTAL)
    command.downgrade(config, "0028_source_connectors")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM source_connector")
        ).scalar_one() == 0
    command.downgrade(config, "0027_task_queue")
    assert "source_connector" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "source_connector" in inspect(engine).get_table_names()
