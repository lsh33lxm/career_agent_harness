from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi import Path as ApiPath

from career_harness.core.common import FrozenModel
from career_harness.core.connectors.models import SyncMode
from career_harness.services.legacy_import_service import (
    LegacyImportReport,
    LegacyImportService,
    LegacyImportStatus,
    LegacyJobDetail,
    LegacyJobSummary,
    LegacyKnowledgeOverview,
)
from career_harness.services.source_connector_service import (
    LegacyAgentRadarConnectorService,
)


class LegacyImportRunRequest(FrozenModel):
    source_root: Path | None = None


@dataclass(frozen=True, slots=True)
class LegacyImportApi:
    service: LegacyImportService
    connector_service: LegacyAgentRadarConnectorService | None = None


def _error(error: Exception) -> HTTPException:
    if isinstance(error, FileNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    if isinstance(error, (OSError, ValueError)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    return HTTPException(status.HTTP_409_CONFLICT, str(error))


def create_legacy_import_router(api: LegacyImportApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/legacy", tags=["legacy-import"])

    @router.get("/status", response_model=LegacyImportStatus)
    def import_status() -> LegacyImportStatus:
        return api.service.status()

    @router.get("/knowledge-overview", response_model=LegacyKnowledgeOverview)
    def knowledge_overview() -> LegacyKnowledgeOverview:
        return api.service.knowledge_overview()

    @router.post(
        "/import",
        response_model=LegacyImportReport,
        status_code=status.HTTP_201_CREATED,
    )
    def run_import(request: LegacyImportRunRequest) -> LegacyImportReport:
        try:
            if api.connector_service is not None:
                root = api.service.resolve_source_root(request.source_root)
                connector = api.connector_service.get_or_create(
                    display_name="Legacy Agent Radar 历史数据",
                    root_path=str(root),
                )
                api.connector_service.sync(connector.connector_id, SyncMode.INCREMENTAL)
                report = api.service.latest_report()
                if report is None:
                    raise RuntimeError("Legacy import completed without an audit report")
                return report
            return api.service.run(request.source_root)
        except Exception as error:
            raise _error(error) from error

    @router.get("/jobs", response_model=list[LegacyJobSummary])
    def list_jobs(
        query: Annotated[str, Query(max_length=512)] = "",
        company: Annotated[str, Query(max_length=512)] = "",
        location: Annotated[str, Query(max_length=512)] = "",
        staging_status: Annotated[str, Query(alias="status", max_length=32)] = "",
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> tuple[LegacyJobSummary, ...]:
        return api.service.list_jobs(
            query=query.strip(),
            company=company.strip(),
            location=location.strip(),
            status=staging_status.strip(),
            limit=limit,
            offset=offset,
        )

    @router.get("/jobs/{staging_id}", response_model=LegacyJobDetail)
    def get_job(staging_id: str = ApiPath(min_length=3, max_length=128)) -> LegacyJobDetail:
        result = api.service.get_job(staging_id)
        if result is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "未找到历史岗位")
        return result

    return router
