from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from career_harness.core.tasks.models import TaskRecord
from career_harness.db.task_repository import StaleTaskLease, TaskRepository

TaskHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class RegisteredTaskHandler:
    task_type: str
    stage: str
    handler: TaskHandler


class TaskService:
    def __init__(
        self,
        repository: TaskRepository,
        handlers: tuple[RegisteredTaskHandler, ...] = (),
        stage_limits: dict[str, int] | None = None,
    ) -> None:
        self.repository = repository
        self.handlers = {item.task_type: item for item in handlers}
        if len(self.handlers) != len(handlers):
            raise ValueError("task handler names must be unique")
        self.stage_limits = dict(stage_limits or {})
        if any(limit < 1 for limit in self.stage_limits.values()):
            raise ValueError("stage concurrency limits must be positive")

    def enqueue(
        self, task_type: str, payload: dict[str, Any], *, max_attempts: int = 3
    ) -> TaskRecord:
        registration = self.handlers.get(task_type)
        if registration is None:
            raise ValueError("task type is not registered")
        return self.repository.enqueue(
            task_type=task_type,
            stage=registration.stage,
            payload=payload,
            max_attempts=max_attempts,
        )

    def run_one(self, stage: str) -> TaskRecord | None:
        lease = self.repository.claim_next(stage)
        if lease is None:
            return None
        registration = self.handlers.get(lease.task.task_type)
        if registration is None or registration.stage != stage:
            return self.repository.fail(lease, RuntimeError("task handler is unavailable"))
        try:
            result = registration.handler(dict(lease.task.payload))
            return self.repository.complete(lease, result)
        except StaleTaskLease:
            return self.repository.get(lease.task.task_id)
        except Exception as error:
            try:
                return self.repository.fail(lease, error)
            except StaleTaskLease:
                return self.repository.get(lease.task.task_id)

    def run_ready(self, stage: str) -> tuple[TaskRecord, ...]:
        limit = self.stage_limits.get(stage, 1)
        with ThreadPoolExecutor(max_workers=limit, thread_name_prefix=f"task-{stage}") as pool:
            results = tuple(pool.map(lambda _index: self.run_one(stage), range(limit)))
        return tuple(result for result in results if result is not None)

    def drain_ready(self, stage: str, *, max_batches: int = 10) -> tuple[TaskRecord, ...]:
        """Run a bounded local dispatch cycle; callers own scheduling and shutdown."""
        if max_batches < 1 or max_batches > 100:
            raise ValueError("max_batches must be between 1 and 100")
        completed: list[TaskRecord] = []
        for _ in range(max_batches):
            batch = self.run_ready(stage)
            if not batch:
                break
            completed.extend(batch)
        return tuple(completed)

    def dispatch_stages(
        self,
        stages: tuple[str, ...],
        *,
        max_batches: int = 1,
        max_tasks: int = 100,
    ) -> tuple[TaskRecord, ...]:
        """Run a bounded, deterministic local dispatcher across registered stages."""
        if not stages or len(stages) > 32 or len(set(stages)) != len(stages):
            raise ValueError("stages must contain 1 to 32 unique stage names")
        if max_batches < 1 or max_batches > 100:
            raise ValueError("max_batches must be between 1 and 100")
        if max_tasks < 1 or max_tasks > 1000:
            raise ValueError("max_tasks must be between 1 and 1000")
        results: list[TaskRecord] = []
        for _ in range(max_batches):
            progressed = False
            for stage in stages:
                remaining = max_tasks - len(results)
                if remaining <= 0:
                    return tuple(results)
                batch = tuple(
                    result
                    for _ in range(min(self.stage_limits.get(stage, 1), remaining))
                    if (result := self.run_one(stage)) is not None
                )
                if batch:
                    progressed = True
                    results.extend(batch[:remaining])
            if not progressed:
                break
        return tuple(results[:max_tasks])
