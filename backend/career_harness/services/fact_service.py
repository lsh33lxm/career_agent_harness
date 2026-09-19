from __future__ import annotations

from typing import Any

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef, FrozenModel, OpaqueId
from career_harness.core.evidence import ExtractedClaim, Fact
from career_harness.core.evidence.models import ClaimStatus, FactAuthority
from career_harness.core.lifecycle import ActorKind
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.fact_repository import ClaimRecord, FactRecord, FactRepository
from career_harness.db.fact_writes import (
    ClaimReviewWrite,
    ExtractedClaimWrite,
    FactPromotionWrite,
)
from career_harness.services.command_service import CommandService

_UNSET: Any = object()


class ClaimCommit(FrozenModel):
    claim: ClaimRecord
    commit: CommandCommitResult


class FactCommit(FrozenModel):
    fact: FactRecord
    commit: CommandCommitResult


def _actor_kind(actor: str) -> ActorKind:
    if actor == ActorKind.USER.value:
        return ActorKind.USER
    if actor.startswith(f"{ActorKind.RULE.value}:"):
        return ActorKind.RULE
    return ActorKind.AGENT


class FactService:
    def __init__(self, commands: CommandService, repository: FactRepository) -> None:
        self.commands = commands
        self.repository = repository

    def propose_claim(
        self,
        command: Command,
        *,
        claim_type: str,
        subject: EntityRef,
        proposed_value: Any,
        evidence_refs: tuple[OpaqueId, ...],
        extractor: str,
        extractor_version: str,
        confidence: float,
    ) -> ClaimCommit:
        self._require_target(command, EntityKind.EXTRACTED_CLAIM)
        if command.expected_revision != 0:
            raise ValueError("a new ExtractedClaim proposal requires expected revision zero")
        record = ClaimRecord(
            claim=ExtractedClaim(
                claim_id=command.target.entity_id,
                claim_type=claim_type,
                subject=subject,
                proposed_value=proposed_value,
                evidence_refs=evidence_refs,
                extractor=extractor,
                extractor_version=extractor_version,
                confidence=confidence,
            ),
            revision=1,
            proposed_by=command.actor,
            proposed_by_kind=_actor_kind(command.actor),
            proposed_at=command.issued_at,
        )
        return self._commit_claim(command, record, "claim.proposed")

    def review_claim(
        self,
        command: Command,
        *,
        decision: ClaimStatus,
        review_reason: str,
    ) -> ClaimCommit:
        self._require_target(command, EntityKind.EXTRACTED_CLAIM)
        if decision not in {
            ClaimStatus.ACCEPTED,
            ClaimStatus.REJECTED,
            ClaimStatus.SUPERSEDED,
        }:
            raise ValueError("review decision must be accepted, rejected or superseded")
        reviewer_kind = _actor_kind(command.actor)
        if reviewer_kind not in {ActorKind.USER, ActorKind.RULE}:
            raise ValueError("only a user or an explicit deterministic rule may review a claim")
        proposal = self.repository.get_claim(command.target.entity_id, command.expected_revision)
        if proposal is None or proposal.claim.status is not ClaimStatus.PROPOSED:
            raise ValueError("review requires the exact proposed ExtractedClaim revision")
        if command.actor == proposal.proposed_by:
            raise ValueError("the proposing agent can never review its own claim")
        record = ClaimRecord(
            claim=proposal.claim.model_copy(
                update={"status": decision, "review_reason": review_reason}
            ),
            revision=command.expected_revision + 1,
            schema_version=proposal.schema_version,
            proposed_by=proposal.proposed_by,
            proposed_by_kind=proposal.proposed_by_kind,
            proposed_at=proposal.proposed_at,
            reviewed_by=command.actor,
            reviewed_by_kind=reviewer_kind,
            reviewed_at=command.issued_at,
        )
        return self._commit_claim(command, record, "claim.reviewed")

    def promote_fact(
        self,
        command: Command,
        *,
        source_claim_id: OpaqueId,
        source_claim_revision: int,
        authority: FactAuthority,
        fact_type: str | None = None,
        value: Any = _UNSET,
        evidence_refs: tuple[OpaqueId, ...] | None = None,
        candidate_id: OpaqueId | None = None,
    ) -> FactCommit:
        self._require_target(command, EntityKind.FACT)
        if _actor_kind(command.actor) is ActorKind.AGENT:
            raise ValueError("an agent can never promote its own claim to a Fact")
        authority = FactAuthority(authority)
        claim = self.repository.get_claim(source_claim_id, source_claim_revision)
        if claim is None or claim.claim.status is not ClaimStatus.ACCEPTED:
            raise ValueError("Fact promotion requires an exact accepted claim revision")
        record = FactRecord(
            fact=Fact(
                fact_id=command.target.entity_id,
                subject=claim.claim.subject,
                fact_type=fact_type if fact_type is not None else claim.claim.claim_type,
                value=claim.claim.proposed_value if value is _UNSET else value,
                authority=authority,
                evidence_refs=(
                    claim.claim.evidence_refs if evidence_refs is None else evidence_refs
                ),
                revision=command.expected_revision + 1,
                verified_at=command.issued_at,
                verified_by=command.actor,
            ),
            source_claim_id=source_claim_id,
            source_claim_revision=source_claim_revision,
            candidate_id=candidate_id,
        )
        fact = record.fact
        state = record.model_dump(mode="json", exclude={"fact": {"verified_at"}})
        commit = self.commands.commit(
            command,
            state,
            event_type="fact.promoted",
            event_payload={
                "fact_id": fact.fact_id,
                "fact_type": fact.fact_type,
                "authority": fact.authority.value,
                "source_claim_id": record.source_claim_id,
                "source_claim_revision": record.source_claim_revision,
                "evidence_count": len(fact.evidence_refs),
            },
            transactional_write=FactPromotionWrite(record),
        )
        persisted = self.repository.get_fact(fact.fact_id, commit.revision)
        if persisted is None:
            raise RuntimeError("Fact commit did not persist the typed aggregate")
        return FactCommit(fact=persisted, commit=commit)

    def _commit_claim(
        self,
        command: Command,
        record: ClaimRecord,
        event_type: str,
    ) -> ClaimCommit:
        claim = record.claim
        state = record.model_dump(mode="json", exclude={"proposed_at", "reviewed_at"})
        commit = self.commands.commit(
            command,
            state,
            event_type=event_type,
            event_payload={
                "claim_id": claim.claim_id,
                "claim_type": claim.claim_type,
                "subject_entity_id": claim.subject.entity_id,
                "subject_entity_kind": claim.subject.kind.value,
                "status": claim.status.value,
                "evidence_count": len(claim.evidence_refs),
            },
            transactional_write=(
                ExtractedClaimWrite(record)
                if claim.status is ClaimStatus.PROPOSED
                else ClaimReviewWrite(record)
            ),
        )
        persisted = self.repository.get_claim(claim.claim_id, commit.revision)
        if persisted is None:
            raise RuntimeError("ExtractedClaim commit did not persist the typed aggregate")
        return ClaimCommit(claim=persisted, commit=commit)

    @staticmethod
    def _require_target(command: Command, kind: EntityKind) -> None:
        if command.target.kind is not kind:
            raise ValueError(f"command requires a {kind.value} target")
