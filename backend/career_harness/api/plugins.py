from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Path
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.plugin.contracts import PluginEnvelope, PluginManifest
from career_harness.services.plugin_service import (
    PluginLifecycleManager,
    PluginNotFound,
    PluginPermissionDenied,
    PluginStateError,
)


class PluginManifestRequest(FrozenModel):
    manifest: PluginManifest


class PluginInvokeRequest(FrozenModel):
    request_id: str = Field(min_length=8, max_length=128)
    capability: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_permissions: tuple[str, ...] = ()
    timeout_ms: int | None = Field(default=None, ge=100, le=300_000)


class PluginSwitchRequest(FrozenModel):
    version: str | None = Field(default=None, min_length=5, max_length=128)


IdempotencyHeader = Annotated[
    str | None, Header(alias="X-Idempotency-Key", min_length=8, max_length=255)
]


@dataclass(frozen=True, slots=True)
class PluginApi:
    service: PluginLifecycleManager


def _error(error: Exception) -> HTTPException:
    if isinstance(error, PluginNotFound):
        return HTTPException(404, "plugin not found")
    if isinstance(error, PluginPermissionDenied):
        return HTTPException(403, str(error))
    if isinstance(error, PluginStateError):
        return HTTPException(409, str(error))
    if isinstance(error, ValueError):
        return HTTPException(422, str(error))
    return HTTPException(500, "plugin operation failed")


def create_plugin_router(api: PluginApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])

    @router.get("")
    def list_plugins() -> list[dict[str, Any]]:
        return api.service.catalog()

    @router.get("/catalog")
    def catalog() -> list[dict[str, Any]]:
        return api.service.catalog()

    @router.post("/install-preview")
    def install_preview(request: PluginManifestRequest) -> dict[str, Any]:
        try:
            return api.service.install_preview(request.manifest)
        except Exception as error:
            raise _error(error) from error

    @router.post("/install")
    def install(
        request: PluginManifestRequest,
        idempotency_key: IdempotencyHeader = None,
    ) -> dict[str, Any]:
        try:
            return api.service.install(
                request.manifest,
                idempotency_key=idempotency_key,
            )
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/enable")
    def enable(plugin_id: str = Path(min_length=3, max_length=64)) -> dict[str, Any]:
        try:
            return api.service.enable(plugin_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/disable")
    def disable(plugin_id: str = Path(min_length=3, max_length=64)) -> dict[str, Any]:
        try:
            return api.service.disable(plugin_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/healthcheck", response_model=PluginEnvelope)
    def healthcheck(plugin_id: str = Path(min_length=3, max_length=64)) -> PluginEnvelope:
        try:
            return api.service.healthcheck(plugin_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/update-preview")
    def update_preview(plugin_id: str = Path(min_length=3, max_length=64)) -> dict[str, Any]:
        try:
            return api.service.update_preview(plugin_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/rollback")
    def rollback(plugin_id: str = Path(min_length=3, max_length=64)) -> dict[str, Any]:
        try:
            return api.service.rollback(plugin_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/switch")
    def switch(
        request: PluginSwitchRequest,
        plugin_id: str = Path(min_length=3, max_length=64),
    ) -> dict[str, Any]:
        try:
            return api.service.switch(plugin_id, version=request.version)
        except Exception as error:
            raise _error(error) from error

    @router.get("/{plugin_id}/audit")
    def audit(plugin_id: str = Path(min_length=3, max_length=64)) -> list[dict[str, Any]]:
        try:
            return api.service.audit(plugin_id)
        except Exception as error:
            raise _error(error) from error

    @router.post("/{plugin_id}/invoke", response_model=PluginEnvelope)
    def invoke(
        request: PluginInvokeRequest,
        plugin_id: str = Path(min_length=3, max_length=64),
    ) -> PluginEnvelope:
        try:
            return api.service.invoke(
                plugin_id,
                request_id=request.request_id,
                capability=request.capability,
                payload=request.payload,
                requested_permissions=request.requested_permissions,
                timeout_ms=request.timeout_ms,
            )
        except Exception as error:
            raise _error(error) from error

    return router
