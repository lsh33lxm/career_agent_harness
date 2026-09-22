from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Query, status

from career_harness.core.application import Application
from career_harness.core.outcome import Outcome
from career_harness.core.resume import ResumeBase, ResumeRevision
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.interview_repository import InterviewRepository
from career_harness.db.resume_repository import ResumeRepository


@dataclass(frozen=True, slots=True)
class CareerReadApi:
    resumes: ResumeRepository
    applications: ApplicationRepository
    interviews: InterviewRepository | None = None


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def create_career_read_router(api: CareerReadApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["career-reads"])

    @router.get("/resumes", response_model=list[ResumeBase])
    def list_resume_bases() -> tuple[ResumeBase, ...]:
        return api.resumes.list_bases()

    @router.get("/resumes/{resume_id}/base", response_model=ResumeBase)
    def get_resume_base(
        resume_id: str,
        revision: int | None = Query(default=None, ge=1),
    ) -> ResumeBase:
        result = api.resumes.get_base(resume_id, revision)
        if result is None:
            raise _not_found("resume base not found")
        return result

    @router.get("/resumes/{resume_id}/bases", response_model=list[ResumeBase])
    def list_resume_base_revisions(resume_id: str) -> tuple[ResumeBase, ...]:
        if api.resumes.get_base(resume_id) is None:
            raise _not_found("resume not found")
        return api.resumes.list_base_revisions(resume_id)

    @router.get("/resume-revisions/{revision_id}", response_model=ResumeRevision)
    def get_resume_revision(revision_id: str) -> ResumeRevision:
        result = api.resumes.get_revision(revision_id)
        if result is None:
            raise _not_found("resume revision not found")
        return result

    @router.get("/resumes/{resume_id}/revisions", response_model=list[ResumeRevision])
    def list_resume_revisions(resume_id: str) -> tuple[ResumeRevision, ...]:
        if api.resumes.get_base(resume_id) is None:
            raise _not_found("resume not found")
        return api.resumes.list_revisions(resume_id)

    @router.get("/applications", response_model=list[Application])
    def list_applications() -> tuple[Application, ...]:
        return api.applications.list()

    @router.get("/applications/{application_id}", response_model=Application)
    def get_application(
        application_id: str,
        revision: int | None = Query(default=None, ge=1),
    ) -> Application:
        result = api.applications.get(application_id, revision)
        if result is None:
            raise _not_found("application not found")
        return result

    @router.get("/applications/{application_id}/outcomes", response_model=list[Outcome])
    def list_outcomes(application_id: str) -> tuple[Outcome, ...]:
        if api.applications.get(application_id) is None:
            raise _not_found("application not found")
        return api.applications.list_outcomes(application_id)

    @router.get("/applications/{application_id}/interviews")
    def list_interviews(application_id: str):
        if api.interviews is None:
            raise _not_found("interview read model unavailable")
        if api.applications.get(application_id) is None:
            raise _not_found("application not found")
        return api.interviews.list_for_application(application_id)

    @router.get("/interviews/{interview_id}")
    def get_interview(interview_id: str, revision: int | None = Query(default=None, ge=1)):
        if api.interviews is None:
            raise _not_found("interview read model unavailable")
        result = api.interviews.get(interview_id, revision)
        if result is None:
            raise _not_found("interview not found")
        return result

    return router
