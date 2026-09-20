from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path, Query

from career_harness.core.common import FrozenModel
from career_harness.core.project import ProjectEvidence
from career_harness.db.project_repository import ProjectRepository


class ProjectMetadata(FrozenModel):
    project_id: str
    revision: int
    display_name: str
    schema_version: int
    created_at: datetime
    created_by: str


class ProjectRead(FrozenModel):
    project: ProjectMetadata
    evidence: tuple[ProjectEvidence, ...]
    evidence_basis: str = "latest_evidence_revisions_not_project_revision_snapshot"


@dataclass(frozen=True, slots=True)
class ProjectReadApi:
    repository: ProjectRepository


def create_project_read_router(api: ProjectReadApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects", tags=["project-reads"])

    @router.get("/{project_id}", response_model=ProjectRead)
    def get_project(
        project_id: str = Path(min_length=1, max_length=128),
        revision: int | None = Query(default=None, ge=1),
    ) -> ProjectRead:
        try:
            project = api.repository.get_project(project_id, revision)
            if project is None:
                raise HTTPException(404, "project revision not found")
            if project.project_id != project_id:
                raise RuntimeError("project identity mismatch")
            evidence = api.repository.list_evidence_for_project(project_id)
            for item in evidence:
                scope = api.repository.get_scan_scope(
                    item.source_manifest.scan_scope_id, item.source_manifest.scan_scope_revision
                )
                if item.project_id != project_id or scope is None or scope.project_id != project_id:
                    raise RuntimeError("project evidence identity mismatch")
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(409, "project evidence provenance is inconsistent") from exc
        return ProjectRead(
            project=ProjectMetadata.model_validate(project.model_dump(exclude={"root_locator"})),
            evidence=evidence,
        )

    return router
