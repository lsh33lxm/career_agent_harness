from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Path, Query

from career_harness.db.evidence_repository import (
    EvidencePage,
    EvidenceProvenanceRead,
    EvidenceRepository,
)


@dataclass(frozen=True, slots=True)
class EvidenceApi:
    repository: EvidenceRepository


def create_evidence_router(api: EvidenceApi) -> APIRouter:
    router = APIRouter(prefix="/api/v1/evidence", tags=["evidence-reads"])

    @router.get("", response_model=EvidencePage)
    def list_evidence(
        after: str | None = Query(default=None, min_length=1, max_length=128),
        limit: int = Query(default=25, ge=1, le=100),
    ) -> EvidencePage:
        try:
            return api.repository.page(after=after, limit=limit)
        except RuntimeError as exc:
            raise HTTPException(409, "evidence provenance is incomplete or inconsistent") from exc

    @router.get("/{evidence_ref_id}", response_model=EvidenceProvenanceRead)
    def get_evidence(
        evidence_ref_id: str = Path(min_length=1, max_length=128),
    ) -> EvidenceProvenanceRead:
        try:
            item = api.repository.get(evidence_ref_id)
        except RuntimeError as exc:
            raise HTTPException(409, "evidence provenance is incomplete or inconsistent") from exc
        if item is None:
            raise HTTPException(404, "evidence reference not found")
        return item

    return router
