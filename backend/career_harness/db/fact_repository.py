from __future__ import annotations

from datetime import datetime

from pydantic import Field
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.common import EntityKind, EntityRef, FrozenModel, OpaqueId
from career_harness.core.evidence import ExtractedClaim, Fact
from career_harness.core.evidence.models import ClaimStatus, FactAuthority
from career_harness.core.lifecycle import ActorKind
from career_harness.db.models import (
    ExtractedClaimEvidenceRefRow,
    ExtractedClaimIdentityRow,
    ExtractedClaimRevisionRow,
    FactEvidenceRefRow,
    FactIdentityRow,
    FactRevisionRow,
)


class ClaimRecord(FrozenModel):
    """A persisted ExtractedClaim revision with its actor and review metadata."""

    claim: ExtractedClaim
    revision: int = Field(ge=1)
    schema_version: int = Field(default=1, ge=1)
    proposed_by: str = Field(min_length=1, max_length=255)
    proposed_by_kind: ActorKind
    proposed_at: datetime
    reviewed_by: str | None = Field(default=None, min_length=1, max_length=255)
    reviewed_by_kind: ActorKind | None = None
    reviewed_at: datetime | None = None


class FactRecord(FrozenModel):
    """A persisted Fact revision with its source claim provenance."""

    fact: Fact
    source_claim_id: OpaqueId
    source_claim_revision: int = Field(ge=1)
    candidate_id: OpaqueId | None = None


class FactRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_claim(self, claim_id: str, revision: int | None = None) -> ClaimRecord | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                ExtractedClaimRevisionRow,
                ExtractedClaimRevisionRow.claim_id,
                claim_id,
                ExtractedClaimRevisionRow.revision,
                revision,
            )
            return self._to_claim_record(session, row) if row is not None else None

    def get_fact(self, fact_id: str, revision: int | None = None) -> FactRecord | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                FactRevisionRow,
                FactRevisionRow.fact_id,
                fact_id,
                FactRevisionRow.revision,
                revision,
            )
            return self._to_fact_record(session, row) if row is not None else None

    def list_facts_for_subject(self, entity_id: str) -> tuple[FactRecord, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(FactRevisionRow)
                .where(FactRevisionRow.subject_entity_id == entity_id)
                .order_by(FactRevisionRow.fact_id, FactRevisionRow.revision.desc())
            ).all()
            latest_rows: dict[str, FactRevisionRow] = {}
            for row in rows:
                latest_rows.setdefault(row.fact_id, row)
            return tuple(self._to_fact_record(session, row) for row in latest_rows.values())

    @staticmethod
    def _get_revisioned_row(
        session: Session,
        row_type: type[ExtractedClaimRevisionRow] | type[FactRevisionRow],
        identity_column: object,
        identity: str,
        revision_column: object,
        revision: int | None,
    ) -> ExtractedClaimRevisionRow | FactRevisionRow | None:
        if revision is not None:
            return session.get(row_type, (identity, revision))
        return session.scalars(
            select(row_type)
            .where(identity_column == identity)
            .order_by(revision_column.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _to_claim_record(session: Session, row: ExtractedClaimRevisionRow) -> ClaimRecord:
        if session.get(ExtractedClaimIdentityRow, row.claim_id) is None:
            raise RuntimeError("persisted ExtractedClaim identity is missing")
        refs = session.scalars(
            select(ExtractedClaimEvidenceRefRow)
            .where(
                ExtractedClaimEvidenceRefRow.claim_id == row.claim_id,
                ExtractedClaimEvidenceRefRow.claim_revision == row.revision,
            )
            .order_by(ExtractedClaimEvidenceRefRow.ordinal)
        ).all()
        FactRepository._require_contiguous(
            [item.ordinal for item in refs], row.evidence_count, "extracted claim evidence"
        )
        return ClaimRecord(
            claim=ExtractedClaim(
                claim_id=row.claim_id,
                claim_type=row.claim_type,
                subject=EntityRef(
                    entity_id=row.subject_entity_id,
                    kind=EntityKind(row.subject_entity_kind),
                ),
                proposed_value=row.proposed_value,
                evidence_refs=tuple(item.evidence_ref_id for item in refs),
                extractor=row.extractor,
                extractor_version=row.extractor_version,
                confidence=row.confidence,
                status=ClaimStatus(row.status),
                review_reason=row.review_reason,
            ),
            revision=row.revision,
            schema_version=row.schema_version,
            proposed_by=row.proposed_by,
            proposed_by_kind=ActorKind(row.proposed_by_kind),
            proposed_at=row.proposed_at,
            reviewed_by=row.reviewed_by,
            reviewed_by_kind=(
                ActorKind(row.reviewed_by_kind) if row.reviewed_by_kind is not None else None
            ),
            reviewed_at=row.reviewed_at,
        )

    @staticmethod
    def _to_fact_record(session: Session, row: FactRevisionRow) -> FactRecord:
        identity = session.get(FactIdentityRow, row.fact_id)
        if identity is None:
            raise RuntimeError("persisted Fact identity is missing")
        refs = session.scalars(
            select(FactEvidenceRefRow)
            .where(
                FactEvidenceRefRow.fact_id == row.fact_id,
                FactEvidenceRefRow.fact_revision == row.revision,
            )
            .order_by(FactEvidenceRefRow.ordinal)
        ).all()
        FactRepository._require_contiguous(
            [item.ordinal for item in refs], row.evidence_count, "fact evidence"
        )
        return FactRecord(
            fact=Fact(
                fact_id=row.fact_id,
                subject=EntityRef(
                    entity_id=row.subject_entity_id,
                    kind=EntityKind(row.subject_entity_kind),
                ),
                fact_type=row.fact_type,
                value=row.value,
                authority=FactAuthority(row.authority),
                evidence_refs=tuple(item.evidence_ref_id for item in refs),
                revision=row.revision,
                verified_at=row.verified_at,
                verified_by=row.verified_by,
            ),
            source_claim_id=row.source_claim_id,
            source_claim_revision=row.source_claim_revision,
            candidate_id=identity.candidate_id,
        )

    @staticmethod
    def _require_contiguous(ordinals: list[int], expected_count: int, label: str) -> None:
        if len(ordinals) != expected_count or ordinals != list(range(expected_count)):
            raise RuntimeError(f"persisted {label} aggregate is incomplete")
