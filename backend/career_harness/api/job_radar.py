from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import Field

from career_harness.adapters.job_sources import ManualJobSource, OfflineFixtureJobSource
from career_harness.core.common import FrozenModel
from career_harness.core.job_source import (
    JobResumeProposalSeed,
    JobStagingRecord,
    JobStagingStatus,
    RawJobRecord,
)
from career_harness.services.opportunity_radar_service import OpportunityRadarService
from career_harness.services.opportunity_service import OpportunityAdmissionCommit


class ManualJobImportRequest(FrozenModel):
    source_ref: str = Field(min_length=1, max_length=4096)
    raw_text: str = Field(min_length=1, max_length=1_000_000)
    query: str = Field(default="", max_length=2048)
    desired_terms: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()


class FixtureSearchRequest(FrozenModel):
    query: str = Field(default="", max_length=2048)
    desired_terms: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JobRadarApi:
    service: OpportunityRadarService


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    return HTTPException(409, "job radar operation failed")


def create_job_radar_router(api: JobRadarApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/jobs", tags=["job-radar"])

    @router.get("/search", response_model=list[JobStagingRecord])
    def search(
        staging_status: Annotated[JobStagingStatus | None, Query(alias="status")] = None,
    ) -> tuple[JobStagingRecord, ...]:
        return api.service.repository.list(status=staging_status)

    @router.post(
        "/import", response_model=list[JobStagingRecord], status_code=status.HTTP_201_CREATED
    )
    def import_manual(request: ManualJobImportRequest) -> tuple[JobStagingRecord, ...]:
        source = ManualJobSource(
            (RawJobRecord(source_ref=request.source_ref, raw_text=request.raw_text),)
        )
        try:
            return api.service.collect(
                source,
                query=request.query,
                desired_terms=request.desired_terms,
                excluded_terms=request.excluded_terms,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post(
        "/fixture-search",
        response_model=list[JobStagingRecord],
        status_code=status.HTTP_201_CREATED,
    )
    def fixture_search(request: FixtureSearchRequest) -> tuple[JobStagingRecord, ...]:
        try:
            return api.service.collect(
                OfflineFixtureJobSource(),
                query=request.query,
                desired_terms=request.desired_terms,
                excluded_terms=request.excluded_terms,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post(
        "/staging/{staging_id}/admit",
        response_model=OpportunityAdmissionCommit,
        status_code=status.HTTP_201_CREATED,
    )
    def admit(
        staging_id: str = Path(min_length=3, max_length=128),
    ) -> OpportunityAdmissionCommit:
        try:
            return api.service.admit(staging_id, actor="user")
        except Exception as error:
            raise _error(error) from error

    @router.get(
        "/staging/{staging_id}/resume-proposal-seed",
        response_model=JobResumeProposalSeed,
    )
    def resume_proposal_seed(
        staging_id: str = Path(min_length=3, max_length=128),
    ) -> JobResumeProposalSeed:
        try:
            return api.service.resume_proposal_seed(staging_id)
        except Exception as error:
            raise _error(error) from error

    return router
