from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import Field

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef, FrozenModel
from career_harness.core.job import JobRef, JobRequirementImportance, JobRequirementStatus
from career_harness.db.job_repository import JobRepository
from career_harness.services.command_service import CommandService
from career_harness.services.job_service import JobService


class RequirementProposalRequest(FrozenModel):
    requirement_id: str = Field(min_length=3, max_length=128, pattern=r"^[a-z][a-z0-9_-]+$")
    requirement_text: str = Field(min_length=1, max_length=4096)
    importance: JobRequirementImportance = JobRequirementImportance.REQUIRED
    required_scopes: tuple[CapabilityEvidenceScope, ...] = (CapabilityEvidenceScope.UNDERSTAND,)
    source_evidence_refs: tuple[str, ...] = Field(min_length=1)
    actor: str = Field(default="user", min_length=1, max_length=255)


class RequirementReviewRequest(FrozenModel):
    decision: JobRequirementStatus
    review_reason: str = Field(min_length=1, max_length=2048)
    capability_id: str | None = Field(default=None, min_length=3, max_length=128)
    graph_version_id: str | None = Field(default=None, min_length=3, max_length=128)


@dataclass(frozen=True, slots=True)
class JobRequirementApi:
    repository: JobRepository
    service: JobService
    commands: CommandService


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(409, str(error))
    return HTTPException(422, "岗位要求操作失败")


def create_job_requirement_router(api: JobRequirementApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/jobs", tags=["job-requirements"])

    @router.get("/{job_id}/revisions/{job_revision}/requirements")
    def list_requirements(
        job_id: str = Path(min_length=3, max_length=128),
        job_revision: int = Path(ge=1),
        status_filter: Annotated[JobRequirementStatus | None, Query(alias="status")] = None,
    ) -> list[object]:
        return list(
            api.repository.list_requirements_for_job(
                job_id, job_revision, latest_only=True, status=status_filter
            )
        )

    @router.post(
        "/{job_id}/revisions/{job_revision}/requirements",
        status_code=status.HTTP_201_CREATED,
    )
    def propose_requirement(
        request: RequirementProposalRequest,
        job_id: str = Path(min_length=3, max_length=128),
        job_revision: int = Path(ge=1),
    ) -> object:
        if api.repository.get_job(job_id, job_revision) is None:
            raise HTTPException(404, "岗位版本不存在")
        command = Command(
            command_id=f"command_{request.requirement_id}_proposal",
            command_type="job_requirement.propose",
            target=EntityRef(entity_id=request.requirement_id, kind=EntityKind.JOB_REQUIREMENT),
            expected_revision=0,
            idempotency_key=f"job-requirement-proposal-{request.requirement_id}",
            actor=request.actor,
        )
        try:
            return api.service.propose_requirement(
                command,
                job=JobRef(job_id=job_id, revision=job_revision),
                requirement_text=request.requirement_text,
                importance=request.importance,
                required_scopes=request.required_scopes,
                source_evidence_refs=request.source_evidence_refs,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post("/requirements/{requirement_id}/revisions/{revision}/review")
    def review_requirement(
        request: RequirementReviewRequest,
        requirement_id: str = Path(min_length=3, max_length=128),
        revision: int = Path(ge=1),
    ) -> object:
        command = Command(
            command_id=f"command_{requirement_id}_review_{revision}",
            command_type="job_requirement.review",
            target=EntityRef(entity_id=requirement_id, kind=EntityKind.JOB_REQUIREMENT),
            expected_revision=revision,
            idempotency_key=f"job-requirement-review-{requirement_id}-{revision}",
            actor="user",
        )
        try:
            return api.service.review_requirement(
                command,
                decision=request.decision,
                review_reason=request.review_reason,
                capability_id=request.capability_id,
                graph_version_id=request.graph_version_id,
            )
        except Exception as error:
            raise _error(error) from error

    return router
