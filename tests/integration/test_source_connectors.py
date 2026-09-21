from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect

from career_harness.core.connectors.models import ConnectorStatus, SyncMode
from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.db.source_connector_repository import SourceConnectorRepository
from career_harness.db.task_repository import TaskRepository
from career_harness.services.source_connector_service import LocalFolderConnectorService
from career_harness.services.task_service import RegisteredTaskHandler, TaskService
from career_harness.storage import ArtifactStore


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


def test_source_connector_migration_is_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    assert {"source_connector", "source_resource", "source_sync_run"} <= set(
        inspect(engine).get_table_names()
    )
    command.downgrade(config, "0027_task_queue")
    assert "source_connector" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "source_connector" in inspect(engine).get_table_names()
