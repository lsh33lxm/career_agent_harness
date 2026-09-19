from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter

from career_harness.core.today import TodayQueue
from career_harness.services.today_service import TodayService


@dataclass(frozen=True, slots=True)
class TodayApi:
    service: TodayService


def create_today_router(api: TodayApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["today"])

    @router.get("/today", response_model=TodayQueue)
    def get_today() -> TodayQueue:
        return api.service.build_queue()

    return router
