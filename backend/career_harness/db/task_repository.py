from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.tasks.models import TaskAttempt, TaskLease, TaskRecord, TaskStatus

_MAX_TASK_JSON_BYTES = 1_000_000
_SECRET_KEY = re.compile(r"(^|_)(api_?key|token|password|secret|authorization)$", re.IGNORECASE)
_SECRET_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*\S+"
)


class StaleTaskLease(RuntimeError):
    """Raised when an old worker tries to mutate a newer task version."""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _validate_task_json(value: dict[str, Any], label: str) -> str:
    def has_secret_key(item: Any) -> bool:
        if isinstance(item, dict):
            return any(
                _SECRET_KEY.search(str(key)) or has_secret_key(child)
                for key, child in item.items()
            )
        if isinstance(item, list | tuple):
            return any(has_secret_key(child) for child in item)
        return False

    if has_secret_key(value):
        raise ValueError(f"{label} must use credential references instead of secret values")
    encoded = _json(value)
    if len(encoded.encode("utf-8")) > _MAX_TASK_JSON_BYTES:
        raise ValueError(f"{label} exceeds the 1000000 byte limit")
    return encoded


def _safe_error(error: Exception) -> str:
    return _SECRET_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", str(error))[:4000]


class TaskRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _event(
        connection: Any,
        event_type: str,
        task_id: str,
        version: int,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        connection.execute(
            text(
                "INSERT INTO domain_event "
                "(event_id,event_type,entity_id,entity_revision,command_id,payload,occurred_at) "
                "VALUES (:event_id,:event_type,:task_id,:version,:command_id,:payload,:now)"
            ),
            {
                "event_id": f"event_task_{uuid.uuid4().hex}",
                "event_type": event_type,
                "task_id": task_id,
                "version": version,
                "command_id": f"task_{uuid.uuid4().hex}",
                "payload": _json(payload),
                "now": now,
            },
        )

    def enqueue(
        self,
        *,
        task_type: str,
        stage: str,
        payload: dict[str, Any],
        max_attempts: int = 3,
        task_id: str | None = None,
        available_at: datetime | None = None,
    ) -> TaskRecord:
        if not task_type.strip() or not stage.strip():
            raise ValueError("task type and stage are required")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max attempts must be between 1 and 20")
        task_id = task_id or f"task_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        ready_at = available_at or now
        encoded_payload = _validate_task_json(payload, "task payload")
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO task_queue "
                    "(task_id,task_type,stage,status,progress,payload,current_attempt,max_attempts,"
                    "version,available_at,created_at,updated_at) VALUES "
                    "(:id,:type,:stage,'pending',0,:payload,0,:max_attempts,1,:available,:now,:now)"
                ),
                {
                    "id": task_id,
                    "type": task_type,
                    "stage": stage,
                    "payload": encoded_payload,
                    "max_attempts": max_attempts,
                    "available": ready_at,
                    "now": now,
                },
            )
            self._event(connection, "task.enqueued", task_id, 1, {"stage": stage}, now)
        return self.get(task_id)

    def get(self, task_id: str) -> TaskRecord:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM task_queue WHERE task_id=:id"), {"id": task_id}
                )
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError("task not found")
        return self._task(row)

    def list(self, *, status: TaskStatus | None = None, limit: int = 100) -> tuple[TaskRecord, ...]:
        clause = "WHERE status=:status" if status is not None else ""
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status.value
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        f"SELECT * FROM task_queue {clause} "  # noqa: S608 - fixed clause
                        "ORDER BY created_at DESC LIMIT :limit"
                    ),
                    params,
                )
                .mappings()
                .all()
            )
        return tuple(self._task(row) for row in rows)

    def claim_next(self, stage: str, *, now: datetime | None = None) -> TaskLease | None:
        current = now or datetime.now(UTC)
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT * FROM task_queue WHERE stage=:stage "
                        "AND status IN ('pending','retrying') AND available_at<=:now "
                        "ORDER BY available_at,created_at LIMIT 1"
                    ),
                    {"stage": stage, "now": current},
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            attempt = int(row["current_attempt"]) + 1
            updated = connection.execute(
                text(
                    "UPDATE task_queue SET status='processing',progress=0.01,"
                    "current_attempt=:attempt,claimed_at=:now,updated_at=:now "
                    "WHERE task_id=:id AND version=:version "
                    "AND status IN ('pending','retrying')"
                ),
                {
                    "attempt": attempt,
                    "now": current,
                    "id": row["task_id"],
                    "version": row["version"],
                },
            )
            if updated.rowcount != 1:
                return None
            self._event(
                connection,
                "task.started",
                row["task_id"],
                row["version"],
                {"attempt": attempt},
                current,
            )
        task = self.get(row["task_id"])
        return TaskLease(task=task, version=task.version, attempt=attempt)

    def set_progress(self, lease: TaskLease, progress: float) -> TaskRecord:
        if not 0 <= progress < 1:
            raise ValueError("processing progress must be between 0 and 1")
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    "UPDATE task_queue SET progress=:progress,updated_at=:now "
                    "WHERE task_id=:id AND version=:version AND current_attempt=:attempt "
                    "AND status='processing'"
                ),
                {
                    "progress": progress,
                    "now": now,
                    "id": lease.task.task_id,
                    "version": lease.version,
                    "attempt": lease.attempt,
                },
            )
            if result.rowcount != 1:
                raise StaleTaskLease("task lease is no longer current")
        return self.get(lease.task.task_id)

    def complete(self, lease: TaskLease, result: dict[str, Any]) -> TaskRecord:
        now = datetime.now(UTC)
        encoded_result = _validate_task_json(result, "task result")
        with self.engine.begin() as connection:
            finishing = connection.execute(
                text(
                    "UPDATE task_queue SET status='finalizing',progress=0.95,updated_at=:now "
                    "WHERE task_id=:id AND version=:version AND current_attempt=:attempt "
                    "AND status='processing'"
                ),
                self._lease_params(lease, now),
            )
            if finishing.rowcount != 1:
                raise StaleTaskLease("task lease is no longer current")
            self._event(
                connection,
                "task.finalizing",
                lease.task.task_id,
                lease.version,
                {"attempt": lease.attempt},
                now,
            )
            connection.execute(
                text(
                    "INSERT INTO task_attempt "
                    "(task_id,attempt,task_version,status,started_at,finished_at) VALUES "
                    "(:id,:attempt,:version,'completed',:started,:now)"
                ),
                {
                    **self._lease_params(lease, now),
                    "started": lease.task.claimed_at or now,
                },
            )
            connection.execute(
                text(
                    "UPDATE task_queue SET status='completed',progress=1,result=:result,"
                    "last_error=NULL,updated_at=:now WHERE task_id=:id AND version=:version "
                    "AND current_attempt=:attempt AND status='finalizing'"
                ),
                {**self._lease_params(lease, now), "result": encoded_result},
            )
            self._event(
                connection,
                "task.completed",
                lease.task.task_id,
                lease.version,
                {"attempt": lease.attempt},
                now,
            )
        return self.get(lease.task.task_id)

    def fail(
        self,
        lease: TaskLease,
        error: Exception,
        *,
        base_delay_seconds: int = 1,
    ) -> TaskRecord:
        now = datetime.now(UTC)
        message = _safe_error(error)
        retry = lease.attempt < lease.task.max_attempts
        status = TaskStatus.RETRYING if retry else TaskStatus.DEAD_LETTER
        delay = base_delay_seconds * (2 ** (lease.attempt - 1))
        available = now + timedelta(seconds=delay) if retry else now
        with self.engine.begin() as connection:
            updated = connection.execute(
                text(
                    "UPDATE task_queue SET status=:status,last_error=:error,"
                    "available_at=:available,"
                    "updated_at=:now WHERE task_id=:id AND version=:version "
                    "AND current_attempt=:attempt AND status='processing'"
                ),
                {
                    **self._lease_params(lease, now),
                    "status": status.value,
                    "error": message,
                    "available": available,
                },
            )
            if updated.rowcount != 1:
                raise StaleTaskLease("task lease is no longer current")
            connection.execute(
                text(
                    "INSERT INTO task_attempt "
                    "(task_id,attempt,task_version,status,error_type,error_message,started_at,"
                    "finished_at) VALUES "
                    "(:id,:attempt,:version,'failed',:error_type,:error,:started,:now)"
                ),
                {
                    **self._lease_params(lease, now),
                    "error_type": type(error).__name__[:128],
                    "error": message,
                    "started": lease.task.claimed_at or now,
                },
            )
            self._event(
                connection,
                "task.retry_scheduled" if retry else "task.dead_lettered",
                lease.task.task_id,
                lease.version,
                {"attempt": lease.attempt, "delay_seconds": delay if retry else None},
                now,
            )
        return self.get(lease.task.task_id)

    def cancel(self, task_id: str) -> TaskRecord:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            row = self._locked_row(connection, task_id)
            if row["status"] in {"completed", "cancelled", "dead_letter"}:
                raise ValueError("task cannot be cancelled from its current state")
            old_version = int(row["version"])
            if row["status"] in {"processing", "finalizing"}:
                connection.execute(
                    text(
                        "INSERT INTO task_attempt "
                        "(task_id,attempt,task_version,status,started_at,finished_at) VALUES "
                        "(:id,:attempt,:version,'cancelled',:started,:now)"
                    ),
                    {
                        "id": task_id,
                        "attempt": row["current_attempt"],
                        "version": old_version,
                        "started": row["claimed_at"] or now,
                        "now": now,
                    },
                )
            connection.execute(
                text(
                    "UPDATE task_queue SET status='cancelled',version=version+1,updated_at=:now "
                    "WHERE task_id=:id"
                ),
                {"id": task_id, "now": now},
            )
            self._event(connection, "task.cancelled", task_id, old_version + 1, {}, now)
        return self.get(task_id)

    def resume(self, task_id: str) -> TaskRecord:
        return self._requeue(task_id, allowed={"cancelled", "failed"}, event="task.resumed")

    def manual_retry(self, task_id: str) -> TaskRecord:
        return self._requeue(
            task_id,
            allowed={"dead_letter", "failed"},
            event="task.manual_retry",
            extend_attempts=True,
        )

    def attempts(self, task_id: str) -> tuple[TaskAttempt, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text("SELECT * FROM task_attempt WHERE task_id=:id ORDER BY attempt"),
                    {"id": task_id},
                )
                .mappings()
                .all()
            )
        return tuple(TaskAttempt(**row) for row in rows)

    def _requeue(
        self,
        task_id: str,
        *,
        allowed: set[str],
        event: str,
        extend_attempts: bool = False,
    ) -> TaskRecord:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            row = self._locked_row(connection, task_id)
            if row["status"] not in allowed:
                raise ValueError("task cannot be requeued from its current state")
            max_attempts = max(int(row["max_attempts"]), int(row["current_attempt"]) + 1)
            if not extend_attempts:
                max_attempts = int(row["max_attempts"])
            connection.execute(
                text(
                    "UPDATE task_queue SET status='pending',progress=0,result=NULL,last_error=NULL,"
                    "version=version+1,max_attempts=:max_attempts,available_at=:now,claimed_at=NULL,"
                    "updated_at=:now WHERE task_id=:id"
                ),
                {"id": task_id, "max_attempts": max_attempts, "now": now},
            )
            self._event(connection, event, task_id, int(row["version"]) + 1, {}, now)
        return self.get(task_id)

    @staticmethod
    def _lease_params(lease: TaskLease, now: datetime) -> dict[str, Any]:
        return {
            "id": lease.task.task_id,
            "version": lease.version,
            "attempt": lease.attempt,
            "now": now,
        }

    @staticmethod
    def _locked_row(connection: Any, task_id: str) -> Any:
        row = (
            connection.execute(text("SELECT * FROM task_queue WHERE task_id=:id"), {"id": task_id})
            .mappings()
            .first()
        )
        if row is None:
            raise KeyError("task not found")
        return row

    @staticmethod
    def _task(row: Any) -> TaskRecord:
        values = dict(row)
        values["payload"] = _loads(values["payload"])
        values["result"] = _loads(values["result"]) if values["result"] is not None else None
        values["status"] = TaskStatus(values["status"])
        return TaskRecord(**values)
