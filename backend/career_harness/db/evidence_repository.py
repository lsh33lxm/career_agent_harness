from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.common import FrozenModel
from career_harness.core.evidence import Artifact, EvidenceRef, Source, SourceSnapshot
from career_harness.core.evidence.models import ArtifactClass
from career_harness.db.models import (
    EvidenceArtifactRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    SourceSnapshotRow,
)


class EvidenceProvenanceRead(FrozenModel):
    evidence_ref: EvidenceRef
    snapshot: SourceSnapshot
    source: Source
    artifact: Artifact


class EvidencePage(FrozenModel):
    items: tuple[EvidenceProvenanceRead, ...]
    next_cursor: str | None = None


class EvidenceRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def page(self, *, after: str | None = None, limit: int = 25) -> EvidencePage:
        if not 1 <= limit <= 100:
            raise ValueError("page limit must be between 1 and 100")
        if after is not None and (not after or len(after) > 128):
            raise ValueError("invalid evidence cursor")
        query = select(EvidenceRefRow.evidence_ref_id).order_by(EvidenceRefRow.evidence_ref_id)
        if after is not None:
            query = query.where(EvidenceRefRow.evidence_ref_id > after)
        with Session(self.engine) as session:
            ids = session.scalars(query.limit(limit + 1)).all()
        items: list[EvidenceProvenanceRead] = []
        for ref_id in ids[:limit]:
            item = self.get(ref_id)
            if item is None:
                raise RuntimeError("persisted EvidenceRef disappeared during page read")
            items.append(item)
        return EvidencePage(
            items=tuple(items),
            next_cursor=ids[limit - 1] if len(ids) > limit else None,
        )

    def get(self, evidence_ref_id: str) -> EvidenceProvenanceRead | None:
        with Session(self.engine) as session:
            ref_row = session.get(EvidenceRefRow, evidence_ref_id)
            if ref_row is None:
                return None
            snapshot_row = session.get(SourceSnapshotRow, ref_row.snapshot_id)
            if snapshot_row is None:
                raise RuntimeError("persisted EvidenceRef snapshot is missing")
            if snapshot_row.artifact_id != ref_row.artifact_id:
                raise RuntimeError("persisted EvidenceRef artifact does not match its snapshot")
            source_row = session.get(EvidenceSourceRow, snapshot_row.source_id)
            artifact_row = session.get(EvidenceArtifactRow, snapshot_row.artifact_id)
            if source_row is None or artifact_row is None:
                raise RuntimeError("persisted EvidenceRef provenance is incomplete")
            return self._to_provenance(ref_row, snapshot_row, source_row, artifact_row)

    def list_for_snapshot(self, snapshot_id: str) -> tuple[EvidenceProvenanceRead, ...]:
        with Session(self.engine) as session:
            ref_rows = session.scalars(
                select(EvidenceRefRow)
                .where(EvidenceRefRow.snapshot_id == snapshot_id)
                .order_by(EvidenceRefRow.evidence_ref_id)
            ).all()
            if not ref_rows:
                return ()
            snapshot_row = session.get(SourceSnapshotRow, snapshot_id)
            if snapshot_row is None:
                raise RuntimeError("persisted EvidenceRef snapshot is missing")
            if any(ref_row.artifact_id != snapshot_row.artifact_id for ref_row in ref_rows):
                raise RuntimeError("persisted EvidenceRef artifact does not match its snapshot")
            source_row = session.get(EvidenceSourceRow, snapshot_row.source_id)
            artifact_row = session.get(EvidenceArtifactRow, snapshot_row.artifact_id)
            if source_row is None or artifact_row is None:
                raise RuntimeError("persisted EvidenceRef provenance is incomplete")
            return tuple(
                self._to_provenance(ref_row, snapshot_row, source_row, artifact_row)
                for ref_row in ref_rows
            )

    @staticmethod
    def _to_provenance(
        ref_row: EvidenceRefRow,
        snapshot_row: SourceSnapshotRow,
        source_row: EvidenceSourceRow,
        artifact_row: EvidenceArtifactRow,
    ) -> EvidenceProvenanceRead:
        return EvidenceProvenanceRead(
            evidence_ref=EvidenceRef(
                evidence_ref_id=ref_row.evidence_ref_id,
                snapshot_id=ref_row.snapshot_id,
                artifact_id=ref_row.artifact_id,
                selector=ref_row.selector,
            ),
            snapshot=SourceSnapshot(
                snapshot_id=snapshot_row.snapshot_id,
                source_id=snapshot_row.source_id,
                captured_at=snapshot_row.captured_at,
                artifact_id=snapshot_row.artifact_id,
            ),
            source=Source(
                source_id=source_row.source_id,
                source_type=source_row.source_type,
                locator=source_row.locator,
            ),
            artifact=Artifact(
                artifact_id=artifact_row.artifact_id,
                sha256=artifact_row.sha256,
                media_type=artifact_row.media_type,
                artifact_class=ArtifactClass(artifact_row.artifact_class),
                byte_length=artifact_row.byte_length,
            ),
        )
