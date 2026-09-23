from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from career_harness.adapters.feishu_projection import (
    FeishuTodayPreview,
    prepare_today_projection,
)
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

    @router.post(
        "/projections/feishu/today/preview",
        response_model=FeishuTodayPreview,
    )
    def preview_feishu_today() -> FeishuTodayPreview:
        queue = api.service.build_queue()
        try:
            return prepare_today_projection(queue)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    return router
