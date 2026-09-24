from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import Field

from career_harness.adapters.job_sources import (
    ManualJobSource,
    OfflineFixtureJobSource,
    PackagedJobSeedSource,
)
from career_harness.adapters.official_job_sources import official_source
from career_harness.core.common import FrozenModel
from career_harness.core.job_lifecycle import JobListingObservation
from career_harness.core.job_source import (
    JobResumeProposalSeed,
    JobSourcePolicy,
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
    preferred_locations: tuple[str, ...] = ()
    minimum_salary: float | None = Field(default=None, gt=0)


class FixtureSearchRequest(FrozenModel):
    query: str = Field(default="", max_length=2048)
    desired_terms: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()
    preferred_locations: tuple[str, ...] = ()
    minimum_salary: float | None = Field(default=None, gt=0)


class OfficialSourceSearchRequest(FixtureSearchRequest):
    source_id: str = Field(min_length=3, max_length=128)


class OfficialDetailRequest(FrozenModel):
    source_id: str = Field(min_length=3, max_length=128)
    source_ref: str = Field(min_length=1, max_length=4096)


class SourcePolicyUpdateRequest(FrozenModel):
    rate_limit_ms: int | None = Field(default=None, ge=0, le=300_000)
    max_retries: int | None = Field(default=None, ge=0, le=5)
    failure_threshold: int | None = Field(default=None, ge=1, le=20)
    enabled: bool | None = None
    reset_failures: bool = False


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
                preferred_locations=request.preferred_locations,
                minimum_salary=request.minimum_salary,
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
                preferred_locations=request.preferred_locations,
                minimum_salary=request.minimum_salary,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post(
        "/packaged-seed-search",
        response_model=list[JobStagingRecord],
        status_code=status.HTTP_201_CREATED,
    )
    def packaged_seed_search(
        request: FixtureSearchRequest,
    ) -> tuple[JobStagingRecord, ...]:
        """Search approved installer data through the normal staging pipeline."""
        try:
            return api.service.collect(
                PackagedJobSeedSource(),
                query=request.query,
                desired_terms=request.desired_terms,
                excluded_terms=request.excluded_terms,
                preferred_locations=request.preferred_locations,
                minimum_salary=request.minimum_salary,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post(
        "/official-search",
        response_model=list[JobStagingRecord],
        status_code=status.HTTP_201_CREATED,
    )
    def official_search(request: OfficialSourceSearchRequest) -> tuple[JobStagingRecord, ...]:
        try:
            return api.service.collect(
                official_source(request.source_id),
                query=request.query,
                desired_terms=request.desired_terms,
                excluded_terms=request.excluded_terms,
                preferred_locations=request.preferred_locations,
                minimum_salary=request.minimum_salary,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post("/official-detail")
    def official_detail(request: OfficialDetailRequest) -> dict[str, object]:
        try:
            source = official_source(request.source_id)
            raw = source.fetch_detail(request.source_ref)
            normalized = source.normalize(raw)
            return {
                "source_id": source.source_id,
                "source_ref": raw.source_ref,
                "captured_at": raw.captured_at,
                "raw_text": raw.raw_text,
                "normalized": normalized,
                "health": source.health(),
            }
        except Exception as error:
            raise _error(error) from error

    @router.get("/source-policies", response_model=list[JobSourcePolicy])
    def source_policies() -> tuple[JobSourcePolicy, ...]:
        return api.service.source_policies()

    @router.get("/listing-lifecycle", response_model=list[JobListingObservation])
    def listing_lifecycle(
        source_id: str | None = Query(default=None, min_length=3, max_length=128),
    ) -> tuple[JobListingObservation, ...]:
        return api.service.lifecycle_observations(source_id=source_id)

    @router.post("/source-policies/{source_id}", response_model=JobSourcePolicy)
    def update_source_policy(
        request: SourcePolicyUpdateRequest,
        source_id: str = Path(min_length=3, max_length=128),
    ) -> JobSourcePolicy:
        try:
            return api.service.update_source_policy(
                source_id,
                rate_limit_ms=request.rate_limit_ms,
                max_retries=request.max_retries,
                failure_threshold=request.failure_threshold,
                enabled=request.enabled,
                reset_failures=request.reset_failures,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post("/source-policies/{source_id}/enable", response_model=JobSourcePolicy)
    def enable_source_policy(
        source_id: str = Path(min_length=3, max_length=128),
    ) -> JobSourcePolicy:
        try:
            return api.service.update_source_policy(
                source_id,
                enabled=True,
                reset_failures=True,
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

    @router.get("/staging/{staging_id}/source-document")
    def source_document(
        staging_id: str = Path(min_length=3, max_length=128),
    ) -> dict[str, object]:
        try:
            return api.service.source_document(staging_id)
        except Exception as error:
            raise _error(error) from error

    return router
