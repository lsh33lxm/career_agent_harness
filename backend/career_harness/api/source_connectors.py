from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Path
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.connectors.models import ConnectorStatus, SyncMode
from career_harness.db.source_connector_repository import SourceConnectorRepository
from career_harness.services.source_connector_service import (
    LegacyAgentRadarConnectorService,
    LocalFolderConnectorService,
)
from career_harness.services.task_service import TaskService


class LocalFolderConnectorRequest(FrozenModel):
    display_name: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=3, max_length=4096)


class LegacyAgentRadarConnectorRequest(FrozenModel):
    display_name: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=3, max_length=4096)


class SyncRequest(FrozenModel):
    mode: SyncMode = SyncMode.INCREMENTAL


@dataclass(frozen=True, slots=True)
class SourceConnectorApi:
    service: LocalFolderConnectorService
    repository: SourceConnectorRepository
    tasks: TaskService
    legacy_service: LegacyAgentRadarConnectorService | None = None

    def service_for(self, connector_type: str) -> Any:
        if connector_type == "local_folder":
            return self.service
        if connector_type == "legacy_agent_radar" and self.legacy_service is not None:
            return self.legacy_service
        raise ValueError(f"unsupported source connector type: {connector_type}")


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

    @router.post("/legacy-agent-radar")
    def create_legacy(request: LegacyAgentRadarConnectorRequest) -> Any:
        if api.legacy_service is None:
            raise HTTPException(409, "Legacy Agent Radar connector is unavailable")
        try:
            return api.legacy_service.create(**request.model_dump())
        except Exception as error:
            raise _error(error) from error

    @router.get("")
    def list_connectors() -> Any:
        return api.repository.list()

    @router.post("/{connector_id}/test")
    def test_connection(connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            connector = api.repository.get(connector_id)
            return api.service_for(connector.connector_type).test_connection(connector_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{connector_id}/sync")
    def sync(request: SyncRequest, connector_id: str = Path(min_length=3, max_length=128)) -> Any:
        try:
            connector = api.repository.get(connector_id)
            api.service_for(connector.connector_type)
            queued = api.tasks.enqueue(
                f"source.{connector.connector_type}_sync",
                {"connector_id": connector_id, "mode": request.mode.value},
            )
            completed = api.tasks.run_one("source_sync")
            return completed or queued
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
