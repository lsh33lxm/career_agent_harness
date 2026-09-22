from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text

from career_harness.api.app import create_app
from career_harness.api.tasks import TaskApi
from career_harness.config import Settings
from career_harness.core.tasks.models import TaskStatus
from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.db.task_repository import StaleTaskLease, TaskRepository
from career_harness.services.task_service import RegisteredTaskHandler, TaskService


def _queue(tmp_path: Path) -> tuple[TaskRepository, TaskService, object]:
    database_url = sqlite_url(tmp_path / "tasks.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    repository = TaskRepository(engine)
    service = TaskService(
        repository,
        handlers=(
            RegisteredTaskHandler(
                task_type="test.echo",
                stage="evaluation",
                handler=lambda payload: {"echo": payload["value"]},
            ),
        ),
        stage_limits={"evaluation": 2},
    )
    return repository, service, engine


def test_task_queue_executes_records_attempt_and_audit(tmp_path: Path) -> None:
    repository, service, engine = _queue(tmp_path)
    task = service.enqueue("test.echo", {"value": "真实任务"})

    completed = service.run_one("evaluation")

    assert completed is not None
    assert completed.task_id == task.task_id
    assert completed.status is TaskStatus.COMPLETED
    assert completed.progress == 1
    assert completed.result == {"echo": "真实任务"}
    assert repository.attempts(task.task_id)[0].status == "completed"
    with engine.connect() as connection:
        events = connection.execute(
            text(
                "SELECT event_type FROM domain_event WHERE entity_id=:id "
                "ORDER BY occurred_at,event_id"
            ),
            {"id": task.task_id},
        ).scalars()
    assert set(events) == {"task.enqueued", "task.started", "task.finalizing", "task.completed"}


def test_task_service_drain_ready_runs_multiple_bounded_batches(tmp_path: Path) -> None:
    repository, service, _engine = _queue(tmp_path)
    first = service.enqueue("test.echo", {"value": "一"})
    second = service.enqueue("test.echo", {"value": "二"})

    completed = service.drain_ready("evaluation", max_batches=2)

    assert {item.task_id for item in completed} == {first.task_id, second.task_id}
    assert all(item.status is TaskStatus.COMPLETED for item in completed)
    assert service.drain_ready("evaluation", max_batches=2) == ()
    with pytest.raises(ValueError, match="between 1 and 100"):
        service.drain_ready("evaluation", max_batches=0)


def test_retry_backoff_dead_letter_manual_retry_and_version_guard(tmp_path: Path) -> None:
    repository, _service, _engine = _queue(tmp_path)
    task = repository.enqueue(
        task_type="test.echo", stage="evaluation", payload={"value": 1}, max_attempts=2
    )
    first = repository.claim_next("evaluation")
    assert first is not None
    retrying = repository.fail(first, RuntimeError("temporary"), base_delay_seconds=2)
    assert retrying.status is TaskStatus.RETRYING
    assert repository.claim_next("evaluation", now=datetime.now(UTC)) is None

    second = repository.claim_next("evaluation", now=datetime.now(UTC) + timedelta(seconds=3))
    assert second is not None
    dead = repository.fail(second, RuntimeError("permanent"))
    assert dead.status is TaskStatus.DEAD_LETTER
    assert len(repository.attempts(task.task_id)) == 2

    retried = repository.manual_retry(task.task_id)
    assert retried.status is TaskStatus.PENDING
    assert retried.version == task.version + 1
    assert retried.max_attempts == 3
    third = repository.claim_next("evaluation")
    assert third is not None
    assert repository.complete(third, {"ok": True}).status is TaskStatus.COMPLETED

    stale_task = repository.enqueue(
        task_type="test.echo", stage="evaluation", payload={"value": 2}
    )
    stale_lease = repository.claim_next("evaluation")
    assert stale_lease is not None and stale_lease.task.task_id == stale_task.task_id
    cancelled = repository.cancel(stale_task.task_id)
    assert cancelled.version == stale_task.version + 1
    with pytest.raises(StaleTaskLease):
        repository.complete(stale_lease, {"must_not": "overwrite cancellation"})
    assert repository.get(stale_task.task_id).status is TaskStatus.CANCELLED


def test_task_queue_rejects_secret_payloads_and_redacts_failure_details(tmp_path: Path) -> None:
    repository, _service, _engine = _queue(tmp_path)
    with pytest.raises(ValueError, match="credential references"):
        repository.enqueue(
            task_type="test.echo",
            stage="evaluation",
            payload={"api_key": "must-not-persist"},
        )
    repository.enqueue(task_type="test.echo", stage="evaluation", payload={"value": 1})
    lease = repository.claim_next("evaluation")
    assert lease is not None
    failed = repository.fail(lease, RuntimeError("token=must-not-persist"))
    assert failed.last_error == "token=[REDACTED]"


@pytest.mark.asyncio
async def test_task_api_allows_controlled_registered_work_without_shell(tmp_path: Path) -> None:
    repository, service, _engine = _queue(tmp_path)
    app = create_app(
        Settings.for_test("task-api-token-0001"), task_api=TaskApi(service, repository)
    )
    headers = {"Authorization": "Bearer task-api-token-0001"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rejected = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"task_type": "shell.exec", "payload": {"command": "whoami"}},
        )
        assert rejected.status_code == 422

        created = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"task_type": "test.echo", "payload": {"value": "受控"}},
        )
        assert created.status_code == 200
        task_id = created.json()["task_id"]
        ran = await client.post(
            "/api/v1/tasks/stages/evaluation/run?max_batches=2", headers=headers
        )
        assert ran.status_code == 200
        detail = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert detail.json()["task"]["status"] == "completed"
        assert detail.json()["attempts"][0]["status"] == "completed"


def test_task_migration_is_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    assert {"task_queue", "task_attempt"} <= set(inspect(engine).get_table_names())
    command.downgrade(config, "0026_memory_governance")
    assert "task_queue" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "task_queue" in inspect(engine).get_table_names()
