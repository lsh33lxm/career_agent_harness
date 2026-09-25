from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, HTTPException, Path
from pydantic import Field, field_validator

from career_harness.core.common import FrozenModel
from career_harness.services.model_provider_service import PROVIDER_DEFAULTS, ModelProviderService

ProviderKind = Literal["openai", "anthropic", "deepseek", "openai_compatible"]


class ModelProviderConfigRequest(FrozenModel):
    provider_id: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]+$")
    provider_kind: ProviderKind
    base_url: str = Field(min_length=8, max_length=512)
    default_model: str = Field(min_length=1, max_length=128)
    timeout_seconds: int = Field(default=30, ge=1, le=120)
    api_key: str | None = Field(default=None, min_length=8, max_length=4096, repr=False)

    @field_validator("base_url", "default_model", "api_key")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ModelProviderTestRequest(FrozenModel):
    confirm_external_request: bool


@dataclass(frozen=True, slots=True)
class ModelProviderApi:
    service: ModelProviderService


def _error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(404, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    return HTTPException(500, "model provider operation failed")


def create_model_provider_router(api: ModelProviderApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/model-providers", tags=["model-providers"])

    @router.get("")
    def list_providers() -> list[dict[str, object]]:
        return api.service.list()

    @router.get("/defaults")
    def defaults() -> dict[str, dict[str, str]]:
        return {
            key: {"base_url": value[0], "default_model": value[1]}
            for key, value in PROVIDER_DEFAULTS.items()
        }

    @router.post("/configure")
    def configure(request: ModelProviderConfigRequest) -> dict[str, object]:
        try:
            values = request.model_dump(exclude={"api_key"})
            return api.service.configure(values, request.api_key)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{provider_id}/test")
    def test_connection(
        request: ModelProviderTestRequest,
        provider_id: str = Path(min_length=2, max_length=64),
    ) -> dict[str, object]:
        try:
            return api.service.test_connection(provider_id, request.confirm_external_request)
        except Exception as error:
            raise _error(error) from error

    return router
