from __future__ import annotations

import hmac

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from career_harness import __version__
from career_harness.api.capabilities import CapabilityApi, create_capability_router
from career_harness.api.capability_inbox import CapabilityInboxApi, create_capability_inbox_router
from career_harness.api.career_reads import CareerReadApi, create_career_read_router
from career_harness.api.evidence import EvidenceApi, create_evidence_router
from career_harness.api.github_projects import GitHubProjectApi, create_github_project_router
from career_harness.api.job_radar import JobRadarApi, create_job_radar_router
from career_harness.api.knowledge import KnowledgeApi, create_knowledge_router
from career_harness.api.legacy_import import LegacyImportApi, create_legacy_import_router
from career_harness.api.memory import MemoryApi, create_memory_router
from career_harness.api.model_providers import ModelProviderApi, create_model_provider_router
from career_harness.api.opportunities import OpportunityApi, create_opportunity_router
from career_harness.api.plugins import PluginApi, create_plugin_router
from career_harness.api.project_reads import ProjectReadApi, create_project_read_router
from career_harness.api.resume_studio import ResumeStudioApi, create_resume_studio_router
from career_harness.api.source_connectors import (
    SourceConnectorApi,
    create_source_connector_router,
)
from career_harness.api.tasks import TaskApi, create_task_router
from career_harness.api.today import TodayApi, create_today_router
from career_harness.api.tools import ToolApi, create_tool_router
from career_harness.config import Settings


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str
    environment: str


def create_app(
    settings: Settings | None = None,
    *,
    opportunity_api: OpportunityApi | None = None,
    evidence_api: EvidenceApi | None = None,
    project_read_api: ProjectReadApi | None = None,
    career_read_api: CareerReadApi | None = None,
    today_api: TodayApi | None = None,
    capability_api: CapabilityApi | None = None,
    capability_inbox_api: CapabilityInboxApi | None = None,
    plugin_api: PluginApi | None = None,
    knowledge_api: KnowledgeApi | None = None,
    resume_studio_api: ResumeStudioApi | None = None,
    job_radar_api: JobRadarApi | None = None,
    legacy_import_api: LegacyImportApi | None = None,
    model_provider_api: ModelProviderApi | None = None,
    github_project_api: GitHubProjectApi | None = None,
    memory_api: MemoryApi | None = None,
    task_api: TaskApi | None = None,
    source_connector_api: SourceConnectorApi | None = None,
    tool_api: ToolApi | None = None,
) -> FastAPI:
    active_settings = settings or Settings()
    app = FastAPI(title="Agent Career Harness Local API", version=__version__)
    app.state.settings = active_settings

    if active_settings.allowed_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[active_settings.allowed_origin],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
        )

    @app.middleware("http")
    async def require_launch_token(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "OPTIONS":
            return await call_next(request)
        expected = active_settings.launch_token
        provided = request.headers.get("authorization", "")
        if expected and not hmac.compare_digest(provided, f"Bearer {expected}"):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "invalid launch token"},
            )
        return await call_next(request)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="agent-career-harness",
            version=__version__,
            environment=active_settings.environment,
        )

    if opportunity_api is not None:
        app.include_router(create_opportunity_router(opportunity_api))
    if career_read_api is not None:
        app.include_router(create_career_read_router(career_read_api))
    if today_api is not None:
        app.include_router(create_today_router(today_api))
    if capability_api is not None:
        app.include_router(create_capability_router(capability_api))
    if capability_inbox_api is not None:
        app.include_router(create_capability_inbox_router(capability_inbox_api))

    if evidence_api is not None:
        app.include_router(create_evidence_router(evidence_api))

    if project_read_api is not None:
        app.include_router(create_project_read_router(project_read_api))

    if plugin_api is not None:
        app.include_router(create_plugin_router(plugin_api))
    if knowledge_api is not None:
        app.include_router(create_knowledge_router(knowledge_api))
    if resume_studio_api is not None:
        app.include_router(create_resume_studio_router(resume_studio_api))
    if job_radar_api is not None:
        app.include_router(create_job_radar_router(job_radar_api))
    if legacy_import_api is not None:
        app.include_router(create_legacy_import_router(legacy_import_api))
    if model_provider_api is not None:
        app.include_router(create_model_provider_router(model_provider_api))
    if github_project_api is not None:
        app.include_router(create_github_project_router(github_project_api))
    if memory_api is not None:
        app.include_router(create_memory_router(memory_api))
    if task_api is not None:
        app.include_router(create_task_router(task_api))
    if source_connector_api is not None:
        app.include_router(create_source_connector_router(source_connector_api))
    if tool_api is not None:
        app.include_router(create_tool_router(tool_api))

    return app
