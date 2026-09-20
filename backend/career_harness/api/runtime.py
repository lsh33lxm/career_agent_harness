from __future__ import annotations

from fastapi import FastAPI

from career_harness.api.app import create_app
from career_harness.api.capabilities import CapabilityApi
from career_harness.api.capability_inbox import CapabilityInboxApi
from career_harness.api.career_reads import CareerReadApi
from career_harness.api.opportunities import OpportunityApi
from career_harness.config import Settings
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.resume_repository import ResumeRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform import AppPaths
from career_harness.services.capability_review_service import CapabilityReviewService
from career_harness.services.capability_workspace_service import CapabilityWorkspaceService
from career_harness.services.command_service import CommandService
from career_harness.services.opportunity_service import OpportunityService


def create_runtime_app(settings: Settings, paths: AppPaths | None = None) -> FastAPI:
    active_paths = paths or AppPaths.resolve()
    active_paths.ensure_directories()
    database_url = sqlite_url(active_paths.database)
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    return create_app(
        settings,
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
    )
