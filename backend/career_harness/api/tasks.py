from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.tasks.models import TaskStatus
from career_harness.db.task_repository import TaskRepository
from career_harness.services.task_service import TaskService


class TaskCreateRequest(FrozenModel):
    task_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=20)


@dataclass(frozen=True, slots=True)
class TaskApi:
    service: TaskService
    repository: TaskRepository


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    return HTTPException(409, str(error))


def create_task_router(api: TaskApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

    @router.post("")
    def create(request: TaskCreateRequest) -> Any:
        try:
            return api.service.enqueue(**request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.get("")
    def list_tasks(
        status: TaskStatus | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> Any:
        return api.repository.list(status=status, limit=limit)

    @router.get("/{task_id}")
    def get(task_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return {
                "task": api.repository.get(task_id),
                "attempts": api.repository.attempts(task_id),
            }
        except Exception as error:
            raise _error(error) from error

    @router.post("/{task_id}/cancel")
    def cancel(task_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.cancel(task_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{task_id}/resume")
    def resume(task_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.resume(task_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{task_id}/retry")
    def retry(task_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.manual_retry(task_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/stages/{stage}/run")
    def run(
        stage: str = Path(min_length=1, max_length=64),
        max_batches: int = Query(default=1, ge=1, le=100),
    ) -> Any:
        """Run a bounded local dispatch cycle; no background process or shell is spawned."""
        return api.service.drain_ready(stage, max_batches=max_batches)

    return router
