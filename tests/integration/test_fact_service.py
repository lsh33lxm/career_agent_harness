from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.evidence.models import ClaimStatus, FactAuthority
from career_harness.core.lifecycle import ActorKind
from career_harness.db.fact_repository import FactRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CapabilityEvidenceBindingRow,
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    EvidenceRefRow,
    ExtractedClaimIdentityRow,
    ExtractedClaimRevisionRow,
    FactIdentityRow,
    FactRevisionRow,
    IdempotencyRecordRow,
    MatchAssessmentRow,
    PersonalCapabilityStateRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.fact_service import ClaimCommit, FactService

SUBJECT = EntityRef(entity_id="candidate_001", kind=EntityKind.CANDIDATE)
EVIDENCE_REF_ID = "evidence_001"
OTHER_EVIDENCE_REF_ID = "evidence_002"


def _seed_evidence_ref(connection, evidence_ref_id: str) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC).isoformat()
    connection.exec_driver_sql(
        "INSERT INTO evidence_artifact "
        "(artifact_id, sha256, media_type, artifact_class, byte_length) "
        "VALUES (?, ?, ?, ?, ?)",
        (f"artifact_{evidence_ref_id}", "a" * 64, "text/plain", "public_source", 16),
    )
    connection.exec_driver_sql(
        "INSERT INTO evidence_source (source_id, source_type, locator) VALUES (?, ?, ?)",
        (f"source_{evidence_ref_id}", "test_fixture", f"test://{evidence_ref_id}"),
    )
    connection.exec_driver_sql(
        "INSERT INTO source_snapshot (snapshot_id, source_id, captured_at, artifact_id) "
        "VALUES (?, ?, ?, ?)",
        (
            f"snapshot_{evidence_ref_id}",
            f"source_{evidence_ref_id}",
            now,
            f"artifact_{evidence_ref_id}",
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO evidence_ref (evidence_ref_id, snapshot_id, artifact_id, selector) "
        "VALUES (?, ?, ?, ?)",
        (
            evidence_ref_id,
            f"snapshot_{evidence_ref_id}",
            f"artifact_{evidence_ref_id}",
            None,
        ),
    )


def _engine(tmp_path: Path) -> Engine:
    database_url = sqlite_url(tmp_path / "fact-service.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        _seed_evidence_ref(connection, EVIDENCE_REF_ID)
        _seed_evidence_ref(connection, OTHER_EVIDENCE_REF_ID)
    return engine


def _services(engine: Engine) -> tuple[FactRepository, FactService]:
    repository = FactRepository(engine)
    return repository, FactService(CommandService(engine), repository)


def _command(
    entity_id: str,
    kind: EntityKind,
    *,
    command_id: str,
    actor: str,
    expected_revision: int = 0,
    key: str | None = None,
) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=key or f"idempotency-{command_id}",
        actor=actor,
    )


def _propose(
    service: FactService,
    claim_id: str,
    *,
    actor: str = "agent:extractor",
    command_id: str | None = None,
    evidence_refs: tuple[str, ...] = (EVIDENCE_REF_ID,),
) -> ClaimCommit:
    return service.propose_claim(
        _command(
            claim_id,
            EntityKind.EXTRACTED_CLAIM,
            command_id=command_id or f"command_propose_{claim_id}",
            actor=actor,
        ),
        claim_type="skill",
        subject=SUBJECT,
        proposed_value={"name": "agent engineering", "depth": "production"},
        evidence_refs=evidence_refs,
        extractor="agent:extractor",
        extractor_version="extractor-1",
        confidence=0.9,
    )


def _review(
    service: FactService,
    claim_id: str,
    *,
    actor: str = "user",
    expected_revision: int = 1,
    decision: ClaimStatus = ClaimStatus.ACCEPTED,
) -> ClaimCommit:
    return service.review_claim(
        _command(
            claim_id,
            EntityKind.EXTRACTED_CLAIM,
            command_id=f"command_review_{claim_id}",
            actor=actor,
            expected_revision=expected_revision,
        ),
        decision=decision,
        review_reason="Confirmed against the captured source.",
    )


def _write_counts(engine: Engine) -> tuple[int, ...]:
    with Session(engine) as session:
        return tuple(
            session.scalar(select(func.count()).select_from(row)) or 0
            for row in (
                EntityStateRow,
                EntityRevisionRow,
                DomainEventRow,
                IdempotencyRecordRow,
                ExtractedClaimIdentityRow,
                ExtractedClaimRevisionRow,
                FactIdentityRow,
                FactRevisionRow,
            )
        )


def test_propose_review_and_promote_persist_typed_aggregates(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)

    proposed = _propose(service, "claim_001")
    assert proposed.claim.claim.status is ClaimStatus.PROPOSED
    assert proposed.claim.revision == 1
    assert proposed.claim.proposed_by == "agent:extractor"
    assert proposed.claim.proposed_by_kind is ActorKind.AGENT
    assert repository.get_claim("claim_001", 1) == proposed.claim
    assert repository.get_claim("claim_001") == proposed.claim
    assert repository.get_claim("claim_missing") is None

    with Session(engine) as session:
        state = session.get(EntityStateRow, "claim_001")
        assert state is not None
        assert state.entity_kind == "extracted_claim"
        event = session.scalars(
            select(DomainEventRow).where(DomainEventRow.entity_id == "claim_001")
        ).one()
        assert event.event_type == "claim.proposed"
        assert event.payload == {
            "revision_id": proposed.commit.revision_id,
            "claim_id": "claim_001",
            "claim_type": "skill",
            "subject_entity_id": "candidate_001",
            "subject_entity_kind": "candidate",
            "status": "proposed",
            "evidence_count": 1,
        }

    reviewed = _review(service, "claim_001")
    assert reviewed.claim.claim.status is ClaimStatus.ACCEPTED
    assert reviewed.claim.revision == 2
    assert reviewed.claim.reviewed_by == "user"
    assert reviewed.claim.reviewed_by_kind is ActorKind.USER
    assert repository.get_claim("claim_001", 1) == proposed.claim
    assert repository.get_claim("claim_001") == reviewed.claim

    promoted = service.promote_fact(
        _command("fact_001", EntityKind.FACT, command_id="command_promote_001", actor="user"),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
        candidate_id="candidate_001",
    )
    fact = promoted.fact.fact
    assert fact.fact_id == "fact_001"
    assert fact.revision == 1
    assert fact.subject == SUBJECT
    assert fact.fact_type == "skill"
    assert fact.value == {"name": "agent engineering", "depth": "production"}
    assert fact.authority is FactAuthority.USER_ASSERTED
    assert fact.evidence_refs == (EVIDENCE_REF_ID,)
    assert fact.verified_by == "user"
    assert promoted.fact.source_claim_id == "claim_001"
    assert promoted.fact.source_claim_revision == 2
    assert promoted.fact.candidate_id == "candidate_001"
    assert repository.get_fact("fact_001", 1) == promoted.fact
    assert repository.get_fact("fact_001") == promoted.fact
    assert repository.get_fact("fact_missing") is None
    assert repository.list_facts_for_subject("candidate_001") == (promoted.fact,)
    assert repository.list_facts_for_subject("candidate_missing") == ()

    with Session(engine) as session:
        state = session.get(EntityStateRow, "fact_001")
        assert state is not None
        assert state.entity_kind == "fact"
        event = session.scalars(
            select(DomainEventRow).where(DomainEventRow.entity_id == "fact_001")
        ).one()
        assert event.event_type == "fact.promoted"
        assert event.payload == {
            "revision_id": promoted.commit.revision_id,
            "fact_id": "fact_001",
            "fact_type": "skill",
            "authority": "user_asserted",
            "source_claim_id": "claim_001",
            "source_claim_revision": 2,
            "evidence_count": 1,
        }


def test_fact_correction_appends_a_revision_under_the_same_fact_id(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "claim_001")
    _review(service, "claim_001")
    first = service.promote_fact(
        _command("fact_001", EntityKind.FACT, command_id="command_promote_001", actor="user"),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
    )

    corrected = service.promote_fact(
        _command(
            "fact_001",
            EntityKind.FACT,
            command_id="command_promote_002",
            actor="user",
            expected_revision=1,
        ),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.DOCUMENT_SUPPORTED,
        value={"name": "agent engineering", "depth": "staff-level"},
        evidence_refs=(EVIDENCE_REF_ID, OTHER_EVIDENCE_REF_ID),
    )

    assert corrected.fact.fact.revision == 2
    assert corrected.fact.fact.authority is FactAuthority.DOCUMENT_SUPPORTED
    assert corrected.fact.fact.value == {"name": "agent engineering", "depth": "staff-level"}
    assert repository.get_fact("fact_001", 1) == first.fact
    assert repository.get_fact("fact_001") == corrected.fact


def test_agent_cannot_review_or_promote(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "claim_001")

    with pytest.raises(ValueError, match="user or an explicit deterministic rule"):
        _review(service, "claim_001", actor="agent:reviewer")

    reviewed = _review(service, "claim_001", actor="rule:claim-gate")
    assert reviewed.claim.reviewed_by_kind is ActorKind.RULE

    with pytest.raises(ValueError, match="never promote"):
        service.promote_fact(
            _command(
                "fact_001", EntityKind.FACT, command_id="command_agent_promote", actor="agent:x"
            ),
            source_claim_id="claim_001",
            source_claim_revision=2,
            authority=FactAuthority.RULE_VERIFIED,
        )
    assert repository.get_fact("fact_001") is None


def test_user_cannot_review_own_claim(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _repository, service = _services(engine)
    _propose(service, "claim_001", actor="user")

    with pytest.raises(ValueError, match="never review its own claim"):
        service.review_claim(
            _command(
                "claim_001",
                EntityKind.EXTRACTED_CLAIM,
                command_id="command_user_self_review",
                actor="user",
                expected_revision=1,
            ),
            decision=ClaimStatus.ACCEPTED,
            review_reason="Self approval attempt.",
        )


def test_review_requires_the_exact_proposed_revision(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _repository, service = _services(engine)
    _propose(service, "claim_001")
    _review(service, "claim_001")

    with pytest.raises(ValueError, match="exact proposed ExtractedClaim revision"):
        service.review_claim(
            _command(
                "claim_001",
                EntityKind.EXTRACTED_CLAIM,
                command_id="command_second_review",
                actor="user",
                expected_revision=2,
            ),
            decision=ClaimStatus.REJECTED,
            review_reason="Second review attempt.",
        )


def test_promotion_requires_an_exact_accepted_claim_revision(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "claim_001")

    with pytest.raises(ValueError, match="exact accepted claim revision"):
        service.promote_fact(
            _command("fact_001", EntityKind.FACT, command_id="command_promote_001", actor="user"),
            source_claim_id="claim_001",
            source_claim_revision=1,
            authority=FactAuthority.USER_ASSERTED,
        )
    with pytest.raises(ValueError, match="exact accepted claim revision"):
        service.promote_fact(
            _command("fact_002", EntityKind.FACT, command_id="command_promote_002", actor="user"),
            source_claim_id="claim_missing",
            source_claim_revision=1,
            authority=FactAuthority.USER_ASSERTED,
        )
    assert repository.get_fact("fact_001") is None
    assert repository.get_fact("fact_002") is None


def test_dangling_evidence_ref_fails_loud_and_rolls_back_atomically(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)

    before = _write_counts(engine)
    with pytest.raises(ValueError, match="EvidenceRef"):
        _propose(service, "claim_dangling", evidence_refs=("evidence_missing",))
    assert _write_counts(engine) == before
    assert repository.get_claim("claim_dangling") is None

    _propose(service, "claim_001")
    _review(service, "claim_001")
    before = _write_counts(engine)
    with pytest.raises(ValueError, match="EvidenceRef"):
        service.promote_fact(
            _command("fact_001", EntityKind.FACT, command_id="command_promote_001", actor="user"),
            source_claim_id="claim_001",
            source_claim_revision=2,
            authority=FactAuthority.USER_ASSERTED,
            evidence_refs=("evidence_missing",),
        )
    assert _write_counts(engine) == before
    assert repository.get_fact("fact_001") is None


def test_proposal_and_promotion_are_idempotent(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)

    command = _command(
        "claim_001",
        EntityKind.EXTRACTED_CLAIM,
        command_id="command_propose_001",
        actor="agent:extractor",
    )
    proposed_value = {"name": "agent engineering"}
    first = service.propose_claim(
        command,
        claim_type="skill",
        subject=SUBJECT,
        proposed_value=proposed_value,
        evidence_refs=(EVIDENCE_REF_ID,),
        extractor="agent:extractor",
        extractor_version="extractor-1",
        confidence=0.9,
    )
    replay = service.propose_claim(
        command,
        claim_type="skill",
        subject=SUBJECT,
        proposed_value=proposed_value,
        evidence_refs=(EVIDENCE_REF_ID,),
        extractor="agent:extractor",
        extractor_version="extractor-1",
        confidence=0.9,
    )
    assert replay.commit == first.commit
    assert replay.claim == first.claim
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ExtractedClaimRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 1

    conflicting = _command(
        "claim_001",
        EntityKind.EXTRACTED_CLAIM,
        command_id="command_propose_001",
        actor="agent:extractor",
        key="idempotency-command_propose_001",
    )
    with pytest.raises(IdempotencyConflict):
        service.propose_claim(
            conflicting,
            claim_type="other",
            subject=SUBJECT,
            proposed_value=proposed_value,
            evidence_refs=(EVIDENCE_REF_ID,),
            extractor="agent:extractor",
            extractor_version="extractor-1",
            confidence=0.9,
        )

    _review(service, "claim_001")
    promote_command = _command(
        "fact_001", EntityKind.FACT, command_id="command_promote_001", actor="user"
    )
    promoted = service.promote_fact(
        promote_command,
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
    )
    promoted_replay = service.promote_fact(
        promote_command,
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
    )
    assert promoted_replay.commit == promoted.commit
    assert promoted_replay.fact == promoted.fact
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(FactRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(FactIdentityRow)) == 1


def test_review_and_promotion_never_mutate_other_domain_tables(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _repository, service = _services(engine)
    _propose(service, "claim_001")

    def counts() -> tuple[int, ...]:
        with Session(engine) as session:
            return tuple(
                session.scalar(select(func.count()).select_from(row)) or 0
                for row in (
                    EvidenceRefRow,
                    CapabilityEvidenceBindingRow,
                    PersonalCapabilityStateRow,
                    MatchAssessmentRow,
                )
            )

    before = counts()
    _review(service, "claim_001")
    service.promote_fact(
        _command("fact_001", EntityKind.FACT, command_id="command_promote_001", actor="user"),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
    )
    assert counts() == before


def test_list_facts_for_subject_returns_latest_revisions_in_stable_order(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "claim_001")
    _review(service, "claim_001")
    service.promote_fact(
        _command("fact_b", EntityKind.FACT, command_id="command_promote_b", actor="user"),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
    )
    service.promote_fact(
        _command("fact_a", EntityKind.FACT, command_id="command_promote_a", actor="user"),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.RULE_VERIFIED,
    )
    corrected = service.promote_fact(
        _command(
            "fact_b",
            EntityKind.FACT,
            command_id="command_promote_b2",
            actor="user",
            expected_revision=1,
        ),
        source_claim_id="claim_001",
        source_claim_revision=2,
        authority=FactAuthority.USER_ASSERTED,
        value={"name": "corrected"},
    )

    facts = repository.list_facts_for_subject("candidate_001")
    assert [record.fact.fact_id for record in facts] == ["fact_a", "fact_b"]
    assert facts[1] == corrected.fact


def test_malformed_persisted_aggregate_fails_loud(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "claim_001")
    assert repository.get_claim("claim_001") is not None

    with engine.begin() as connection:
        # Simulate a bypassed write path: drop the guard so the delete lands.
        connection.exec_driver_sql("DROP TRIGGER trg_extracted_claim_evidence_ref_no_delete")
        connection.exec_driver_sql(
            "DELETE FROM extracted_claim_evidence_ref WHERE claim_id = 'claim_001'"
        )

    with pytest.raises(RuntimeError, match="incomplete"):
        repository.get_claim("claim_001")
