from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import Field

from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef, FrozenModel
from career_harness.core.interview import InterviewRound
from career_harness.services.application_service import ApplicationService
from career_harness.services.interview_service import InterviewService


class CreateApplicationRequest(FrozenModel):
    command_id: str = Field(min_length=3, max_length=128)
    application_id: str = Field(min_length=3, max_length=128)
    opportunity_id: str = Field(min_length=3, max_length=128)
    opportunity_revision: int = Field(ge=1)


class ApplicationTransitionRequest(FrozenModel):
    command_id: str = Field(min_length=3, max_length=128)
    expected_revision: int = Field(ge=1)
    state: ApplicationState


class AttachResumeRequest(FrozenModel):
    command_id: str = Field(min_length=3, max_length=128)
    expected_revision: int = Field(ge=1)
    resume_revision_id: str = Field(min_length=3, max_length=128)


class SubmitApplicationRequest(FrozenModel):
    command_id: str = Field(min_length=3, max_length=128)
    expected_revision: int = Field(ge=1)
    resume_revision_id: str = Field(min_length=3, max_length=128)
    authority: SubmissionAuthority = SubmissionAuthority.USER_CONFIRMED
    evidence_ref_id: str | None = Field(default=None, min_length=3, max_length=128)


class ScheduleInterviewRequest(FrozenModel):
    command_id: str = Field(min_length=3, max_length=128)
    interview_id: str = Field(min_length=3, max_length=128)
    application_id: str = Field(min_length=3, max_length=128)
    application_revision: int = Field(ge=1)
    round: InterviewRound
    scheduled_at: datetime
    evidence_refs: tuple[str, ...] = ()


class InterviewTransitionRequest(FrozenModel):
    command_id: str = Field(min_length=3, max_length=128)
    expected_revision: int = Field(ge=1)
    evidence_refs: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class ApplicationCommandApi:
    applications: ApplicationService
    interviews: InterviewService


def _command(command_id: str, kind: EntityKind, entity_id: str, expected: int, command_type: str) -> Command:
    return Command(command_id=command_id, command_type=command_type, target=EntityRef(entity_id=entity_id, kind=kind), expected_revision=expected, idempotency_key=f"api-{command_id}", actor="user")


def _error(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(409, str(error))
    return HTTPException(422, "申请或面试操作失败")


def create_application_command_router(api: ApplicationCommandApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["application-commands"])

    @router.post("/applications", status_code=status.HTTP_201_CREATED)
    def create_application(request: CreateApplicationRequest):
        try:
            return api.applications.create(_command(request.command_id, EntityKind.APPLICATION, request.application_id, 0, "application.create"), opportunity_id=request.opportunity_id, opportunity_revision=request.opportunity_revision)
        except Exception as error:
            raise _error(error) from error

    @router.post("/applications/{application_id}/preparation-state")
    def preparation_state(request: ApplicationTransitionRequest, application_id: str = Path(min_length=3, max_length=128)):
        try:
            return api.applications.set_preparation_state(_command(request.command_id, EntityKind.APPLICATION, application_id, request.expected_revision, "application.preparation_state"), state=request.state)
        except Exception as error:
            raise _error(error) from error

    @router.post("/applications/{application_id}/resume")
    def attach_resume(request: AttachResumeRequest, application_id: str = Path(min_length=3, max_length=128)):
        try:
            return api.applications.attach_prepared_resume(_command(request.command_id, EntityKind.APPLICATION, application_id, request.expected_revision, "application.resume_attach"), resume_revision_id=request.resume_revision_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/applications/{application_id}/submit")
    def submit(request: SubmitApplicationRequest, application_id: str = Path(min_length=3, max_length=128)):
        try:
            return api.applications.record_submission(_command(request.command_id, EntityKind.APPLICATION, application_id, request.expected_revision, "application.submit"), resume_revision_id=request.resume_revision_id, authority=request.authority, evidence_ref_id=request.evidence_ref_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/applications/{application_id}/state")
    def advance_state(request: ApplicationTransitionRequest, application_id: str = Path(min_length=3, max_length=128)):
        try:
            return api.applications.advance_state(_command(request.command_id, EntityKind.APPLICATION, application_id, request.expected_revision, "application.state_advance"), state=request.state)
        except Exception as error:
            raise _error(error) from error

    @router.post("/interviews", status_code=status.HTTP_201_CREATED)
    def schedule_interview(request: ScheduleInterviewRequest):
        try:
            return api.interviews.schedule_interview(_command(request.command_id, EntityKind.INTERVIEW, request.interview_id, 0, "interview.schedule"), application_id=request.application_id, application_revision=request.application_revision, round=request.round, scheduled_at=request.scheduled_at, evidence_refs=request.evidence_refs)
        except Exception as error:
            raise _error(error) from error

    @router.post("/interviews/{interview_id}/complete")
    def complete_interview(request: InterviewTransitionRequest, interview_id: str = Path(min_length=3, max_length=128)):
        try:
            return api.interviews.complete_interview(_command(request.command_id, EntityKind.INTERVIEW, interview_id, request.expected_revision, "interview.complete"), evidence_refs=request.evidence_refs)
        except Exception as error:
            raise _error(error) from error

    @router.post("/interviews/{interview_id}/cancel")
    def cancel_interview(request: InterviewTransitionRequest, interview_id: str = Path(min_length=3, max_length=128)):
        try:
            return api.interviews.cancel_interview(_command(request.command_id, EntityKind.INTERVIEW, interview_id, request.expected_revision, "interview.cancel"))
        except Exception as error:
            raise _error(error) from error

    return router
