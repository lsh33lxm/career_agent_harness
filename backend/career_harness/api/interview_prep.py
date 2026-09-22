from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException

from career_harness.services.interview_prep_service import (
    InterviewFeedbackRequest,
    InterviewLearningPlanRequest,
    InterviewPrepRequest,
    InterviewPrepService,
    InterviewSessionEventRequest,
)


@dataclass(frozen=True, slots=True)
class InterviewPrepApi:
    service: InterviewPrepService


def create_interview_prep_router(api: InterviewPrepApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/interviews", tags=["interview-prep"])

    @router.post("/{interview_id}/prep-proposals", status_code=201)
    def create(interview_id: str, request: InterviewPrepRequest) -> Any:
        try:
            return api.service.propose(
                interview_id, mode=request.mode, focus=request.focus
            )
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/{interview_id}/feedback-proposals", status_code=201)
    def feedback(interview_id: str, request: InterviewFeedbackRequest) -> Any:
        try:
            return api.service.propose_feedback(
                interview_id, question=request.question, answer=request.answer
            )
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/{interview_id}/learning-plan-proposals", status_code=201)
    def learning_plan(
        interview_id: str, request: InterviewLearningPlanRequest
    ) -> Any:
        try:
            return api.service.propose_learning_plan(interview_id, gaps=request.gaps)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/{interview_id}/sessions/events", status_code=201)
    def append_event(interview_id: str, request: InterviewSessionEventRequest) -> Any:
        try:
            return api.service.append_session_event(interview_id, request)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except (RuntimeError, ValueError) as error:
            raise HTTPException(422, str(error)) from error

    @router.get("/{interview_id}/sessions/{session_id}/events")
    def list_events(interview_id: str, session_id: str) -> Any:
        try:
            return api.service.list_session_events(interview_id, session_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except (RuntimeError, ValueError) as error:
            raise HTTPException(422, str(error)) from error

    return router
