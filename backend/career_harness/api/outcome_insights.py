from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException

from career_harness.services.outcome_insight_service import OutcomeInsightService


@dataclass(frozen=True, slots=True)
class OutcomeInsightApi:
    service: OutcomeInsightService


def create_outcome_insight_router(api: OutcomeInsightApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/outcome-insights", tags=["outcome-insights"])

    @router.post("/applications/{application_id}/offer-preparation", status_code=201)
    def offer_preparation(application_id: str) -> Any:
        try:
            return api.service.propose_offer_preparation(application_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/rejection-pattern", status_code=201)
    def rejection_pattern() -> Any:
        try:
            return api.service.propose_rejection_pattern()
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    return router
