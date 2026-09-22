from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from career_harness.api.app import create_app
from career_harness.api.capabilities import CapabilityApi
from career_harness.api.capability_inbox import CapabilityInboxApi
from career_harness.api.career_reads import CareerReadApi
from career_harness.api.evidence import EvidenceApi
from career_harness.api.github_projects import GitHubProjectApi
from career_harness.api.job_radar import JobRadarApi
from career_harness.api.knowledge import KnowledgeApi
from career_harness.api.legacy_import import LegacyImportApi
from career_harness.api.memory import MemoryApi
from career_harness.api.model_providers import ModelProviderApi
from career_harness.api.offline_career_loop import OfflineCareerLoopApi
from career_harness.api.opportunities import OpportunityApi
from career_harness.api.plugins import PluginApi
from career_harness.api.project_reads import ProjectReadApi
from career_harness.api.resume_studio import ResumeStudioApi
from career_harness.api.source_connectors import SourceConnectorApi
from career_harness.api.tasks import TaskApi
from career_harness.api.today import TodayApi
from career_harness.api.tools import ToolApi
from career_harness.config import Settings
from career_harness.core.connectors.models import SyncMode
from career_harness.core.tools.registry import (
    ToolDefinition,
    ToolPermission,
    ToolRegistry,
    ToolScope,
    ToolScopeKind,
)
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.knowledge_repository import KnowledgeRepository
from career_harness.db.memory_repository import MemoryRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.model_provider_repository import ModelProviderRepository
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.resume_repository import ResumeRepository
from career_harness.db.resume_studio_repository import ResumeStudioRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.db.source_connector_repository import SourceConnectorRepository
from career_harness.db.task_repository import TaskRepository
from career_harness.db.tool_audit import DatabaseToolAuditSink
from career_harness.platform import AppPaths
from career_harness.platform.secure_store import WindowsCredentialSecretStore
from career_harness.services.capability_review_service import CapabilityReviewService
from career_harness.services.capability_workspace_service import CapabilityWorkspaceService
from career_harness.services.command_service import CommandService
from career_harness.services.github_project_service import GitHubProjectService
from career_harness.services.legacy_import_service import LegacyImportService
from career_harness.services.model_provider_service import ModelProviderService
from career_harness.services.offline_career_loop_service import OfflineCareerLoopService
from career_harness.services.opportunity_radar_service import OpportunityRadarService
from career_harness.services.opportunity_service import OpportunityService
from career_harness.services.plugin_service import PluginLifecycleManager
from career_harness.services.resume_studio_service import ResumeStudioService
from career_harness.services.source_connector_service import (
    GitHubConnectorService,
    LegacyAgentRadarConnectorService,
    LocalFolderConnectorService,
)
from career_harness.services.task_service import RegisteredTaskHandler, TaskService
from career_harness.services.today_service import TodayService
from career_harness.storage import ArtifactStore


def create_runtime_app(settings: Settings, paths: AppPaths | None = None) -> FastAPI:
    active_paths = paths or AppPaths.resolve()
    active_paths.ensure_directories()
    database_url = sqlite_url(active_paths.database)
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    knowledge_repository = KnowledgeRepository(engine, ArtifactStore(active_paths.artifacts))
    resume_studio_repository = ResumeStudioRepository(
        engine,
        ArtifactStore(active_paths.artifacts),
    )
    resume_studio_service = ResumeStudioService(CommandService(engine), resume_studio_repository)
    opportunity_radar_service = OpportunityRadarService(
        engine, ArtifactStore(active_paths.artifacts)
    )
    offline_career_loop_service = OfflineCareerLoopService(
        opportunity_radar_service, resume_studio_service
    )
    plugin_service = PluginLifecycleManager(
        engine,
        knowledge_search=knowledge_repository.search_for_plugin,
    )
    configured_legacy_root = os.getenv("ACH_LEGACY_AGENT_RADAR_ROOT")
    legacy_import_service = LegacyImportService(
        engine,
        ArtifactStore(active_paths.artifacts),
        default_source_root=Path(configured_legacy_root) if configured_legacy_root else None,
    )
    task_repository = TaskRepository(engine)
    source_connector_repository = SourceConnectorRepository(engine)
    source_connector_service = LocalFolderConnectorService(
        source_connector_repository, ArtifactStore(active_paths.artifacts)
    )
    legacy_connector_service = LegacyAgentRadarConnectorService(
        source_connector_repository, legacy_import_service
    )
    github_project_service = GitHubProjectService(
        engine,
        active_paths.root / "project-cache" / "github",
        WindowsCredentialSecretStore(),
    )
    github_connector_service = GitHubConnectorService(
        source_connector_repository, github_project_service
    )
    task_service = TaskService(
        task_repository,
        handlers=(
            RegisteredTaskHandler(
                task_type="local.health_check",
                stage="evaluation",
                handler=lambda payload: {"ok": True, "label": payload.get("label")},
            ),
            RegisteredTaskHandler(
                task_type="source.local_folder_sync",
                stage="source_sync",
                handler=lambda payload: source_connector_service.sync(
                    str(payload["connector_id"]),
                    SyncMode(str(payload.get("mode", "incremental"))),
                ).model_dump(mode="json"),
            ),
            RegisteredTaskHandler(
                task_type="source.legacy_agent_radar_sync",
                stage="source_sync",
                handler=lambda payload: legacy_connector_service.sync(
                    str(payload["connector_id"]),
                    SyncMode(str(payload.get("mode", "incremental"))),
                ).model_dump(mode="json"),
            ),
            RegisteredTaskHandler(
                task_type="source.github_sync",
                stage="source_sync",
                handler=lambda payload: github_connector_service.sync(
                    str(payload["connector_id"]),
                    SyncMode(str(payload.get("mode", "incremental"))),
                ).model_dump(mode="json"),
            ),
        ),
        stage_limits={"evaluation": 2, "source_sync": 1},
    )
    tool_registry = ToolRegistry(audit_sink=DatabaseToolAuditSink(engine))
    tool_registry.register(
        ToolDefinition(
            name="knowledge.search",
            source="builtin://career-knowledge",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            permissions=frozenset({ToolPermission.READ}),
            scope_kinds=frozenset({ToolScopeKind.WORKSPACE}),
            output_limit_bytes=128_000,
            handler=lambda arguments: knowledge_repository.search_for_plugin(
                str(arguments["query"]),
                {"limit": int(arguments.get("limit", 20)), "redact_sensitive": True},
            ),
        )
    )
    return create_app(
        settings,
        project_read_api=ProjectReadApi(ProjectRepository(engine)),
        evidence_api=EvidenceApi(repository=EvidenceRepository(engine)),
        today_api=TodayApi(service=TodayService(engine)),
        opportunity_api=OpportunityApi(
            repository=OpportunityRepository(engine),
            service=OpportunityService(CommandService(engine)),
        ),
        career_read_api=CareerReadApi(
            resumes=ResumeRepository(engine),
            applications=ApplicationRepository(engine),
        ),
        capability_api=CapabilityApi(
            service=CapabilityWorkspaceService(CapabilityRepository(engine))
        ),
        capability_inbox_api=CapabilityInboxApi(
            repository=CapabilityRepository(engine),
            commands=CommandService(engine),
            service=CapabilityReviewService(CommandService(engine), CapabilityRepository(engine)),
        ),
        plugin_api=PluginApi(plugin_service),
        knowledge_api=KnowledgeApi(knowledge_repository),
        resume_studio_api=ResumeStudioApi(resume_studio_service),
        job_radar_api=JobRadarApi(
            opportunity_radar_service
        ),
        offline_career_loop_api=OfflineCareerLoopApi(offline_career_loop_service),
        legacy_import_api=LegacyImportApi(
            legacy_import_service, legacy_connector_service
        ),
        model_provider_api=ModelProviderApi(
            ModelProviderService(
                ModelProviderRepository(engine),
                WindowsCredentialSecretStore(),
            )
        ),
        github_project_api=GitHubProjectApi(
            github_project_service, github_connector_service
        ),
        memory_api=MemoryApi(MemoryRepository(engine)),
        task_api=TaskApi(task_service, task_repository),
        source_connector_api=SourceConnectorApi(
            source_connector_service,
            source_connector_repository,
            task_service,
            legacy_connector_service,
            github_connector_service,
        ),
        tool_api=ToolApi(
            registry=tool_registry,
            principal_id="local-user",
            allowed_scopes=frozenset(
                {ToolScope(ToolScopeKind.WORKSPACE, "workspace-local")}
            ),
            permissions=frozenset({ToolPermission.READ}),
        ),
    )
