from __future__ import annotations

from fastapi import FastAPI

from career_harness.api.app import create_app
from career_harness.api.capabilities import CapabilityApi
from career_harness.api.capability_inbox import CapabilityInboxApi
from career_harness.api.career_reads import CareerReadApi
from career_harness.api.evidence import EvidenceApi
from career_harness.api.knowledge import KnowledgeApi
from career_harness.api.opportunities import OpportunityApi
from career_harness.api.plugins import PluginApi
from career_harness.api.project_reads import ProjectReadApi
from career_harness.api.today import TodayApi
from career_harness.config import Settings
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.knowledge_repository import KnowledgeRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.resume_repository import ResumeRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform import AppPaths
from career_harness.services.capability_review_service import CapabilityReviewService
from career_harness.services.capability_workspace_service import CapabilityWorkspaceService
from career_harness.services.command_service import CommandService
from career_harness.services.opportunity_service import OpportunityService
from career_harness.services.plugin_service import PluginLifecycleManager
from career_harness.services.today_service import TodayService
from career_harness.storage import ArtifactStore


def create_runtime_app(settings: Settings, paths: AppPaths | None = None) -> FastAPI:
    active_paths = paths or AppPaths.resolve()
    active_paths.ensure_directories()
    database_url = sqlite_url(active_paths.database)
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    knowledge_repository = KnowledgeRepository(engine, ArtifactStore(active_paths.artifacts))
    plugin_service = PluginLifecycleManager(
        engine,
        knowledge_search=knowledge_repository.search_for_plugin,
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
    )
