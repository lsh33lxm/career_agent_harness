from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from career_harness.core.capability import (
    CandidateCapabilityStatus,
    CapabilityLayer,
)
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.lifecycle import ActorKind
from career_harness.db.capability_repository import CapabilityRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CandidateCapabilityNodeRow,
    CapabilityEvidenceBindingRow,
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityInvestmentStateRow,
    CapabilityNodeRow,
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    IdempotencyRecordRow,
    MatchAssessmentRow,
    PersonalCapabilityStateRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.capability_review_service import (
    CandidateProposalCommit,
    CapabilityReviewService,
)
from career_harness.services.command_service import CommandService, IdempotencyConflict

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


def _seed_released_graph(connection) -> None:  # type: ignore[no-untyped-def]
    """Seed released graph_version_001 holding capability_a, in D-007 release order."""
    now = datetime.now(UTC)
    connection.exec_driver_sql(
        "INSERT INTO capability_identity (capability_id) VALUES (?)", ("capability_a",)
    )
    connection.exec_driver_sql(
        "INSERT INTO capability_node "
        "(capability_id, graph_version_id, canonical_name, description, layer, "
        "lifecycle_status) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "capability_a",
            "graph_version_001",
            "Alpha",
            "First released graph.",
            "common_core",
            "active",
        ),
    )
    connection.execute(
        CapabilityGraphVersionRow.__table__.insert(),
        {
            "graph_version_id": "graph_version_001",
            "version_label": "1.0",
            "parent_graph_version_id": None,
            "change_note": "Initial graph.",
            "released_at": now,
            "released_by": "user",
            "released_by_kind": "user",
        },
    )


def _engine(tmp_path: Path, *, with_graph: bool = False) -> Engine:
    database_url = sqlite_url(tmp_path / "capability-review.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        _seed_evidence_ref(connection, EVIDENCE_REF_ID)
        _seed_evidence_ref(connection, OTHER_EVIDENCE_REF_ID)
        if with_graph:
            _seed_released_graph(connection)
    return engine


def _services(engine: Engine) -> tuple[CapabilityRepository, CapabilityReviewService]:
    repository = CapabilityRepository(engine)
    return repository, CapabilityReviewService(CommandService(engine), repository)


def _command(
    entity_id: str,
    command_id: str,
    *,
    actor: str,
    expected_revision: int = 0,
    key: str | None = None,
    kind: EntityKind = EntityKind.CAPABILITY_CANDIDATE,
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
    service: CapabilityReviewService,
    candidate_node_id: str,
    *,
    actor: str = "agent:scout",
    command_id: str | None = None,
    evidence_refs: tuple[str, ...] = (EVIDENCE_REF_ID,),
) -> CandidateProposalCommit:
    return service.propose_candidate(
        _command(
            candidate_node_id,
            command_id or f"command_propose_{candidate_node_id}",
            actor=actor,
        ),
        proposed_canonical_name="Agent Engineering",
        proposed_description="Designing reliable agent workflows.",
        proposed_layer=CapabilityLayer.TRACK,
        source_evidence_refs=evidence_refs,
    )


def _review(
    service: CapabilityReviewService,
    candidate_node_id: str,
    *,
    actor: str = "user",
    decision: str = "accept",
    merge_target: str | None = None,
    command_id: str | None = None,
):
    return service.review_candidate(
        _command(
            candidate_node_id,
            command_id or f"command_review_{candidate_node_id}",
            actor=actor,
            expected_revision=1,
        ),
        candidate_node_id=candidate_node_id,
        decision=decision,  # type: ignore[arg-type]
        reason="Reviewed against the source evidence.",
        merge_target=merge_target,
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
                CandidateCapabilityNodeRow,
                CapabilityIdentityRow,
                CapabilityNodeRow,
                CapabilityGraphVersionRow,
            )
        )


def test_propose_and_accept_releases_a_new_graph_version(tmp_path: Path) -> None:
    engine = _engine(tmp_path, with_graph=True)
    repository, service = _services(engine)

    proposed = _propose(service, "candidate_node_001")
    assert proposed.candidate.status is CandidateCapabilityStatus.PENDING
    assert proposed.candidate.discovered_by == "agent:scout"
    assert repository.list_candidate_inbox() == (proposed.candidate,)

    with Session(engine) as session:
        state = session.get(EntityStateRow, "candidate_node_001")
        assert state is not None
        assert state.entity_kind == "capability_candidate"
        assert state.revision == 1
        event = session.scalars(
            select(DomainEventRow).where(DomainEventRow.entity_id == "candidate_node_001")
        ).one()
        assert event.event_type == "capability_candidate.proposed"
        assert event.payload == {
            "revision_id": proposed.commit.revision_id,
            "candidate_node_id": "candidate_node_001",
            "proposed_layer": "track",
            "discovered_by_kind": "agent",
            "evidence_count": 1,
            "status": "pending",
        }

    reviewed = _review(service, "candidate_node_001")
    assert reviewed.candidate.status is CandidateCapabilityStatus.ACCEPTED
    assert reviewed.candidate.reviewed_by == "user"
    assert reviewed.candidate.reviewed_by_kind is ActorKind.USER
    assert reviewed.candidate.merge_target_capability_id is None
    assert reviewed.capability_id == "capability_candidate_node_001"
    assert reviewed.graph_version is not None

    version = reviewed.graph_version
    assert version.graph_version_id == "graph_version_candidate_node_001"
    assert version.parent_graph_version_id == "graph_version_001"
    assert version.released_by == "user"
    assert version.released_by_kind is ActorKind.USER
    assert repository.get_latest_graph_version() == version

    latest = repository.get_latest_official_graph()
    assert latest is not None
    assert [node.capability_id for node in latest.nodes] == [
        "capability_a",
        "capability_candidate_node_001",
    ]
    new_node = latest.nodes[1]
    assert new_node.canonical_name == "Agent Engineering"
    assert new_node.layer is CapabilityLayer.TRACK

    # The previously released version stays untouched.
    previous = repository.get_official_graph("graph_version_001")
    assert previous is not None
    assert [node.capability_id for node in previous.nodes] == ["capability_a"]
    assert repository.list_candidate_inbox() == ()

    with Session(engine) as session:
        state = session.get(EntityStateRow, "candidate_node_001")
        assert state is not None
        assert state.revision == 2
        revisions = session.scalars(
            select(EntityRevisionRow)
            .where(EntityRevisionRow.entity_id == "candidate_node_001")
            .order_by(EntityRevisionRow.revision)
        ).all()
        assert [row.revision for row in revisions] == [1, 2]
        assert revisions[0].state["status"] == "pending"
        assert revisions[1].state["status"] == "accepted"
        event = session.scalars(
            select(DomainEventRow)
            .where(DomainEventRow.entity_id == "candidate_node_001")
            .order_by(DomainEventRow.occurred_at, DomainEventRow.event_id)
        ).all()[-1]
        assert event.event_type == "capability_candidate.reviewed"
        assert event.payload == {
            "revision_id": reviewed.commit.revision_id,
            "candidate_node_id": "candidate_node_001",
            "status": "accepted",
            "reviewed_by_kind": "user",
            "merge_target_capability_id": None,
            "capability_id": "capability_candidate_node_001",
            "graph_version_id": "graph_version_candidate_node_001",
            "parent_graph_version_id": "graph_version_001",
        }


def test_accept_without_a_released_graph_releases_a_root_version(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")

    reviewed = _review(service, "candidate_node_001")

    assert reviewed.graph_version is not None
    assert reviewed.graph_version.parent_graph_version_id is None
    latest = repository.get_latest_official_graph()
    assert latest is not None
    assert [node.capability_id for node in latest.nodes] == ["capability_candidate_node_001"]


def test_accept_requires_a_user_actor(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")
    before = _write_counts(engine)

    with pytest.raises(ValueError, match="requires a user actor"):
        _review(service, "candidate_node_001", actor="rule:inbox-gate")
    with pytest.raises(ValueError, match="agent cannot decide"):
        _review(service, "candidate_node_001", actor="agent:reviewer")

    assert _write_counts(engine) == before
    assert repository.list_candidate_inbox()[0].status is CandidateCapabilityStatus.PENDING
    assert repository.get_latest_graph_version() is None


def test_reject_allows_user_or_rule_and_keeps_history(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")
    _propose(service, "candidate_node_002")

    rejected_by_user = _review(service, "candidate_node_001", decision="reject")
    rejected_by_rule = _review(
        service, "candidate_node_002", actor="rule:inbox-dedup", decision="reject"
    )

    assert rejected_by_user.candidate.status is CandidateCapabilityStatus.IGNORED
    assert rejected_by_user.candidate.reviewed_by_kind is ActorKind.USER
    assert rejected_by_rule.candidate.status is CandidateCapabilityStatus.IGNORED
    assert rejected_by_rule.candidate.reviewed_by_kind is ActorKind.RULE
    assert rejected_by_rule.candidate.reviewed_by == "rule:inbox-dedup"
    # Rejection never deletes the proposal or its evidence refs, and releases nothing.
    assert repository.list_candidate_inbox() == ()
    assert repository.get_latest_graph_version() is None
    assert rejected_by_user.candidate.source_evidence_refs == (EVIDENCE_REF_ID,)
    with Session(engine) as session:
        revisions = session.scalars(
            select(EntityRevisionRow)
            .where(EntityRevisionRow.entity_id == "candidate_node_001")
            .order_by(EntityRevisionRow.revision)
        ).all()
        assert [row.revision for row in revisions] == [1, 2]
        assert revisions[0].state["status"] == "pending"
        assert revisions[1].state["status"] == "ignored"


def test_the_discovering_actor_can_never_review_its_own_candidate(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _repository, service = _services(engine)
    _propose(service, "candidate_node_001", actor="user")
    before = _write_counts(engine)

    with pytest.raises(ValueError, match="never review its own candidate"):
        _review(service, "candidate_node_001", actor="user", decision="reject")

    assert _write_counts(engine) == before


def test_merge_acceptance_records_the_target_without_a_new_node(tmp_path: Path) -> None:
    engine = _engine(tmp_path, with_graph=True)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")

    reviewed = _review(service, "candidate_node_001", merge_target="capability_a")

    assert reviewed.candidate.status is CandidateCapabilityStatus.MERGED
    assert reviewed.candidate.merge_target_capability_id == "capability_a"
    assert reviewed.capability_id is None
    assert reviewed.graph_version is None
    latest = repository.get_latest_graph_version()
    assert latest is not None
    assert latest.graph_version_id == "graph_version_001"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(CapabilityIdentityRow)) == 1


def test_merge_target_must_exist_and_failure_rolls_back_atomically(tmp_path: Path) -> None:
    engine = _engine(tmp_path, with_graph=True)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")
    before = _write_counts(engine)

    with pytest.raises(ValueError, match="existing canonical capability identity"):
        _review(service, "candidate_node_001", merge_target="capability_missing")

    assert _write_counts(engine) == before
    candidate = repository.list_candidate_inbox()[0]
    assert candidate.status is CandidateCapabilityStatus.PENDING


def test_dangling_source_evidence_ref_fails_loud_and_rolls_back(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    before = _write_counts(engine)

    with pytest.raises(ValueError, match="canonical EvidenceRef"):
        _propose(service, "candidate_node_001", evidence_refs=("evidence_missing",))

    assert _write_counts(engine) == before
    assert repository.list_candidate_inbox() == ()


def test_propose_and_review_are_idempotent(tmp_path: Path) -> None:
    engine = _engine(tmp_path, with_graph=True)
    repository, service = _services(engine)

    propose_command = _command("candidate_node_001", "command_propose_001", actor="agent:scout")
    proposal_kwargs = {
        "proposed_canonical_name": "Agent Engineering",
        "proposed_description": "Designing reliable agent workflows.",
        "proposed_layer": CapabilityLayer.TRACK,
        "source_evidence_refs": (EVIDENCE_REF_ID,),
    }
    first = service.propose_candidate(propose_command, **proposal_kwargs)
    replay = service.propose_candidate(propose_command, **proposal_kwargs)
    assert replay.commit == first.commit
    assert replay.candidate == first.candidate

    conflicting = _command(
        "candidate_node_001",
        "command_propose_001",
        actor="agent:scout",
        key="idempotency-command_propose_001",
    )
    with pytest.raises(IdempotencyConflict):
        service.propose_candidate(
            conflicting, **{**proposal_kwargs, "proposed_canonical_name": "Other"}
        )

    review_command = _command(
        "candidate_node_001", "command_review_001", actor="user", expected_revision=1
    )
    review_kwargs = {
        "candidate_node_id": "candidate_node_001",
        "decision": "accept",
        "reason": "Reviewed against the source evidence.",
    }
    reviewed = service.review_candidate(review_command, **review_kwargs)  # type: ignore[arg-type]
    reviewed_replay = service.review_candidate(review_command, **review_kwargs)  # type: ignore[arg-type]
    assert reviewed_replay.commit == reviewed.commit
    assert reviewed_replay.candidate == reviewed.candidate
    assert reviewed_replay.graph_version == reviewed.graph_version

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(CandidateCapabilityNodeRow)) == 1
        assert session.scalar(select(func.count()).select_from(CapabilityGraphVersionRow)) == 2
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 2
    latest = repository.get_latest_official_graph()
    assert latest is not None
    assert [node.capability_id for node in latest.nodes] == [
        "capability_a",
        "capability_candidate_node_001",
    ]


def test_a_reviewed_candidate_cannot_be_reviewed_again(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")
    _review(service, "candidate_node_001", decision="reject")
    before = _write_counts(engine)

    with pytest.raises(ValueError, match="already reviewed"):
        service.review_candidate(
            _command(
                "candidate_node_001",
                "command_second_review",
                actor="user",
                expected_revision=2,
            ),
            candidate_node_id="candidate_node_001",
            decision="accept",
            reason="Second review attempt.",
        )

    assert _write_counts(engine) == before
    assert repository.get_latest_graph_version() is None


def test_released_graph_versions_stay_immutable_after_acceptance(tmp_path: Path) -> None:
    engine = _engine(tmp_path, with_graph=True)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001")
    _review(service, "candidate_node_001")

    with pytest.raises(IntegrityError, match="immutable"), engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE capability_graph_version SET change_note = 'tampered' "
            "WHERE graph_version_id = 'graph_version_001'"
        )
    with pytest.raises(IntegrityError, match="released"), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO capability_node "
            "(capability_id, graph_version_id, canonical_name, description, layer, "
            "lifecycle_status) VALUES ('capability_a', 'graph_version_001', 'X', 'Y', "
            "'track', 'active')"
        )
    previous = repository.get_official_graph("graph_version_001")
    assert previous is not None
    assert previous.graph_version.change_note == "Initial graph."
    assert [node.capability_id for node in previous.nodes] == ["capability_a"]


def test_review_never_mutates_overlay_bindings_match_or_priorities(tmp_path: Path) -> None:
    engine = _engine(tmp_path, with_graph=True)
    _repository, service = _services(engine)
    _propose(service, "candidate_node_001")

    def counts() -> tuple[int, ...]:
        with Session(engine) as session:
            return tuple(
                session.scalar(select(func.count()).select_from(row)) or 0
                for row in (
                    PersonalCapabilityStateRow,
                    CapabilityEvidenceBindingRow,
                    CapabilityInvestmentStateRow,
                    MatchAssessmentRow,
                )
            )

    before = counts()
    _review(service, "candidate_node_001")
    assert counts() == before
