from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Path
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.connectors.models import ConnectorStatus, SyncMode
from career_harness.db.source_connector_repository import SourceConnectorRepository
from career_harness.services.source_connector_service import LocalFolderConnectorService
from career_harness.services.task_service import TaskService


class LocalFolderConnectorRequest(FrozenModel):
    display_name: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=3, max_length=4096)


class SyncRequest(FrozenModel):
    mode: SyncMode = SyncMode.INCREMENTAL


@dataclass(frozen=True, slots=True)
class SourceConnectorApi:
    service: LocalFolderConnectorService
    repository: SourceConnectorRepository
    tasks: TaskService


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError | FileNotFoundError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    return HTTPException(409, str(error))


def create_source_connector_router(api: SourceConnectorApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/source-connectors", tags=["source-connectors"])

    @router.post("/local-folder")
    def create(request: LocalFolderConnectorRequest) -> Any:
        try:
            return api.service.create(**request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.get("")
    def list_connectors() -> Any:
        return api.repository.list()

    @router.post("/{connector_id}/test")
    def test_connection(connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.service.test_connection(connector_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{connector_id}/sync")
    def sync(request: SyncRequest, connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            api.repository.get(connector_id)
            return api.tasks.enqueue(
                "source.local_folder_sync",
                {"connector_id": connector_id, "mode": request.mode.value},
            )
        except Exception as error:
            raise _error(error) from error

    @router.get("/{connector_id}/runs")
    def runs(connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            api.repository.get(connector_id)
            return api.repository.list_runs(connector_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{connector_id}/pause")
    def pause(connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.set_status(connector_id, ConnectorStatus.PAUSED)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{connector_id}/resume")
    def resume(connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            return api.repository.set_status(connector_id, ConnectorStatus.ACTIVE)
        except Exception as error:
            raise _error(error) from error

    return router
