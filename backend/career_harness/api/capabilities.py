from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from career_harness.core.capability_workspace import CapabilityWorkspace
from career_harness.core.common import OpaqueId
from career_harness.services.capability_workspace_service import (
    CapabilityGraphNotFoundError,
    CapabilityWorkspaceService,
)


class CapabilityApi:
    def __init__(self, service: CapabilityWorkspaceService) -> None:
        self.service = service

    def get_workspace(
        self, *, candidate_id: str, graph_version_id: str | None
    ) -> CapabilityWorkspace:
        return self.service.get_workspace(
            candidate_id=candidate_id, graph_version_id=graph_version_id
        )


def create_capability_router(api: CapabilityApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])

    @router.get("/identities", response_model=list[str])
    def list_capability_identities() -> tuple[str, ...]:
        return api.service.list_candidate_ids()

    @router.get("/{candidate_id}", response_model=CapabilityWorkspace)
    def get_capability_workspace(
        candidate_id: OpaqueId,
        graph_version_id: Annotated[OpaqueId | None, Query()] = None,
    ) -> CapabilityWorkspace:
        try:
            return api.get_workspace(candidate_id=candidate_id, graph_version_id=graph_version_id)
        except CapabilityGraphNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"capability graph version not found: {error.graph_version_id}",
            ) from error

    return router
