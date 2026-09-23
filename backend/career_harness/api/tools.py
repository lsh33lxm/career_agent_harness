from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Path
from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.tools.registry import (
    ToolCallContext,
    ToolCallError,
    ToolPermission,
    ToolRegistry,
    ToolScope,
    ToolScopeKind,
)


class ToolCallRequest(FrozenModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    scope_kind: ToolScopeKind = ToolScopeKind.WORKSPACE
    scope_id: str = Field(default="workspace-local", min_length=1, max_length=128)
    approval_id: str | None = Field(default=None, min_length=3, max_length=128)


@dataclass(frozen=True, slots=True)
class ToolApi:
    registry: ToolRegistry
    principal_id: str
    allowed_scopes: frozenset[ToolScope]
    permissions: frozenset[ToolPermission]


def create_tool_router(api: ToolApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/tools", tags=["tools"])

    @router.get("")
    def definitions() -> Any:
        return [
            {
                "name": item.name,
                "source": item.source,
                "version": item.version,
                "permissions": sorted(permission.value for permission in item.permissions),
                "scope_kinds": sorted(scope.value for scope in item.scope_kinds),
                "deferred": item.deferred_loader is not None,
            }
            for item in api.registry.definitions()
        ]

    @router.get("/{tool_name}/schema")
    def schema(tool_name: str = Path(min_length=3, max_length=128)) -> Any:
        definition = next(
            (item for item in api.registry.definitions() if item.name == tool_name), None
        )
        if definition is None:
            raise HTTPException(404, "tool is not registered")
        return definition.input_schema

    @router.post("/{tool_name}/calls")
    def call(request: ToolCallRequest, tool_name: str = Path(min_length=3, max_length=128)) -> Any:
        context = ToolCallContext(
            principal_id=api.principal_id,
            scope=ToolScope(request.scope_kind, request.scope_id),
            allowed_scopes=api.allowed_scopes,
            permissions=api.permissions,
            approval_id=request.approval_id,
        )
        try:
            return api.registry.execute(tool_name, request.arguments, context)
        except ToolCallError as error:
            status = 404 if error.category.value == "not_found" else 403
            if error.category.value == "validation":
                status = 422
            raise HTTPException(status, str(error)) from error

    return router
