from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_harness.core.evidence.models import ClaimStatus, FactAuthority
from career_harness.core.lifecycle import ActorKind
from career_harness.db.fact_repository import ClaimRecord, FactRecord
from career_harness.db.models import (
    EvidenceRefRow,
    ExtractedClaimEvidenceRefRow,
    ExtractedClaimIdentityRow,
    ExtractedClaimRevisionRow,
    FactEvidenceRefRow,
    FactIdentityRow,
    FactRevisionRow,
)


def _require_evidence_refs(session: Session, evidence_ref_ids: tuple[str, ...]) -> None:
    for evidence_ref_id in evidence_ref_ids:
        if session.get(EvidenceRefRow, evidence_ref_id) is None:
            raise ValueError("canonical EvidenceRef is required for every evidence ref id")


def _stage_claim_revision(session: Session, record: ClaimRecord, occurred_at: datetime) -> None:
    claim = record.claim
    for ordinal, evidence_ref_id in enumerate(claim.evidence_refs):
        session.add(
            ExtractedClaimEvidenceRefRow(
                claim_id=claim.claim_id,
                claim_revision=record.revision,
                ordinal=ordinal,
                evidence_ref_id=evidence_ref_id,
            )
        )
    session.flush()
    session.add(
        ExtractedClaimRevisionRow(
            claim_id=claim.claim_id,
            revision=record.revision,
            schema_version=record.schema_version,
            claim_type=claim.claim_type,
            subject_entity_id=claim.subject.entity_id,
            subject_entity_kind=claim.subject.kind.value,
            proposed_value=claim.proposed_value,
            extractor=claim.extractor,
            extractor_version=claim.extractor_version,
            confidence=claim.confidence,
            status=claim.status.value,
            evidence_count=len(claim.evidence_refs),
            proposed_by=record.proposed_by,
            proposed_by_kind=record.proposed_by_kind.value,
            proposed_at=(
                record.proposed_at if claim.status is not ClaimStatus.PROPOSED else occurred_at
            ),
            reviewed_by=record.reviewed_by,
            reviewed_by_kind=(
                record.reviewed_by_kind.value if record.reviewed_by_kind is not None else None
            ),
            review_reason=claim.review_reason,
            reviewed_at=(occurred_at if claim.status is not ClaimStatus.PROPOSED else None),
        )
    )


class ExtractedClaimWrite:
    """Stage the initial proposed revision of an ExtractedClaim."""

    def __init__(self, record: ClaimRecord) -> None:
        self.record = record

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "extracted-claim-write-v1",
            "claim": self.record.model_dump(mode="json", exclude={"proposed_at", "reviewed_at"}),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        record = self.record
        if record.revision != entity_revision:
            raise ValueError("typed and generic ExtractedClaim revisions must match")
        if record.claim.status is not ClaimStatus.PROPOSED:
            raise ValueError("a new ExtractedClaim starts as a proposed revision")
        _require_evidence_refs(session, record.claim.evidence_refs)

        if session.get(ExtractedClaimIdentityRow, record.claim.claim_id) is not None:
            raise ValueError("ExtractedClaim identity already exists")
        if record.revision != 1:
            raise ValueError("the first ExtractedClaim revision must be revision one")
        session.add(ExtractedClaimIdentityRow(claim_id=record.claim.claim_id))
        session.flush()
        _stage_claim_revision(session, record, occurred_at)


class ClaimReviewWrite:
    """Stage a review revision appended to an existing proposed ExtractedClaim."""

    def __init__(self, record: ClaimRecord) -> None:
        self.record = record

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "claim-review-write-v1",
            "claim": self.record.model_dump(mode="json", exclude={"proposed_at", "reviewed_at"}),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        record = self.record
        if record.revision != entity_revision:
            raise ValueError("typed and generic ExtractedClaim revisions must match")
        if record.claim.status is ClaimStatus.PROPOSED:
            raise ValueError("a Claim review revision must carry a review decision")
        if record.reviewed_by_kind not in {ActorKind.USER, ActorKind.RULE}:
            raise ValueError("only a user or an explicit deterministic rule may review a claim")
        _require_evidence_refs(session, record.claim.evidence_refs)

        if session.get(ExtractedClaimIdentityRow, record.claim.claim_id) is None:
            raise ValueError("Claim review requires an existing ExtractedClaim identity")
        proposal = session.get(
            ExtractedClaimRevisionRow, (record.claim.claim_id, record.revision - 1)
        )
        if proposal is None or proposal.status != ClaimStatus.PROPOSED.value:
            raise ValueError("Claim review requires the exact proposed claim revision")
        if record.reviewed_by == proposal.proposed_by:
            raise ValueError("the proposing agent can never review its own claim")
        _stage_claim_revision(session, record, occurred_at)


class FactPromotionWrite:
    """Stage a Fact revision promoted from an exact accepted claim revision."""

    def __init__(self, record: FactRecord) -> None:
        self.record = record

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "fact-promotion-write-v1",
            "fact": self.record.model_dump(mode="json", exclude={"fact": {"verified_at"}}),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        record = self.record
        fact = record.fact
        if fact.revision != entity_revision:
            raise ValueError("typed and generic Fact revisions must match")
        if fact.authority not in set(FactAuthority):
            raise ValueError("Fact promotion requires a non-AI authority")
        claim = session.get(
            ExtractedClaimRevisionRow,
            (record.source_claim_id, record.source_claim_revision),
        )
        if claim is None or claim.status != ClaimStatus.ACCEPTED.value:
            raise ValueError("Fact promotion requires an exact accepted claim revision")
        if fact.revision == 1:
            claim_refs = session.scalars(
                select(ExtractedClaimEvidenceRefRow)
                .where(
                    ExtractedClaimEvidenceRefRow.claim_id == claim.claim_id,
                    ExtractedClaimEvidenceRefRow.claim_revision == claim.revision,
                )
                .order_by(ExtractedClaimEvidenceRefRow.ordinal)
            ).all()
            if (
                claim.claim_type != fact.fact_type
                or claim.proposed_value != fact.value
                or tuple(item.evidence_ref_id for item in claim_refs) != fact.evidence_refs
            ):
                raise ValueError(
                    "the initial Fact promotion must carry the accepted claim's "
                    "fact_type, value and evidence refs"
                )
        _require_evidence_refs(session, fact.evidence_refs)

        identity = session.get(FactIdentityRow, fact.fact_id)
        if identity is None:
            if fact.revision != 1:
                raise ValueError("the first Fact revision must be revision one")
            session.add(FactIdentityRow(fact_id=fact.fact_id, candidate_id=record.candidate_id))
            session.flush()
        elif identity.candidate_id != record.candidate_id:
            raise ValueError("Fact identity cannot change its candidate ownership")

        for ordinal, evidence_ref_id in enumerate(fact.evidence_refs):
            session.add(
                FactEvidenceRefRow(
                    fact_id=fact.fact_id,
                    fact_revision=fact.revision,
                    ordinal=ordinal,
                    evidence_ref_id=evidence_ref_id,
                )
            )
        session.flush()
        session.add(
            FactRevisionRow(
                fact_id=fact.fact_id,
                revision=fact.revision,
                schema_version=1,
                subject_entity_id=fact.subject.entity_id,
                subject_entity_kind=fact.subject.kind.value,
                fact_type=fact.fact_type,
                value=fact.value,
                authority=fact.authority.value,
                source_claim_id=record.source_claim_id,
                source_claim_revision=record.source_claim_revision,
                evidence_count=len(fact.evidence_refs),
                verified_at=occurred_at,
                verified_by=fact.verified_by,
            )
        )
