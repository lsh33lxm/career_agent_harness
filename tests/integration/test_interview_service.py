from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.commands import Command, RevisionConflict
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.interview import Interview, InterviewRound, InterviewStatus
from career_harness.db.interview_writes import InterviewWrite
from career_harness.db.models import (
    ApplicationRevisionRow,
    DomainEventRow,
    IdempotencyRecordRow,
    InterviewEvidenceRefRow,
    InterviewIdentityRow,
    InterviewRevisionRow,
    OutcomeRecordRow,
)
from career_harness.services.command_service import CommandService
from career_harness.services.interview_service import InterviewService
from tests.integration.test_application_service import _command, _seed_dependencies
from tests.integration.test_fact_service import EVIDENCE_REF_ID

SCHEDULED_AT = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)


def _submitted_application(service) -> None:  # type: ignore[no-untyped-def]
    service.create(
        _command("application_001", EntityKind.APPLICATION, "command_application"),
        opportunity_id="opportunity_001",
        opportunity_revision=1,
    )
    service.set_preparation_state(
        _command("application_001", EntityKind.APPLICATION, "command_ready", expected_revision=1),
        state=ApplicationState.READY_FOR_REVIEW,
    )
    service.record_submission(
        _command("application_001", EntityKind.APPLICATION, "command_submit", expected_revision=2),
        resume_revision_id="resume_revision_001",
        authority=SubmissionAuthority.USER_CONFIRMED,
    )


def _schedule_command(command_id: str = "command_schedule") -> Command:
    return _command("interview_001", EntityKind.INTERVIEW, command_id)


def _services(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine, applications = _seed_dependencies(tmp_path)
    _submitted_application(applications)
    return engine, applications, InterviewService(CommandService(engine))


def test_interview_schedule_complete_cancel_is_exact_and_idempotent(tmp_path: Path) -> None:
    engine, applications, interviews = _services(tmp_path)

    command = _schedule_command()
    scheduled = interviews.schedule_interview(
        command,
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.TECHNICAL,
        scheduled_at=SCHEDULED_AT,
    )
    assert scheduled.revision == 1
    assert scheduled.status is InterviewStatus.SCHEDULED
    assert scheduled.application_revision == 3
    assert scheduled.created_by == "user"

    replay = interviews.schedule_interview(
        command,
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.TECHNICAL,
        scheduled_at=SCHEDULED_AT,
    )
    assert replay == scheduled

    completed = interviews.complete_interview(
        _command("interview_001", EntityKind.INTERVIEW, "command_complete", expected_revision=1),
        evidence_refs=(EVIDENCE_REF_ID,),
    )
    assert completed.revision == 2
    assert completed.status is InterviewStatus.COMPLETED
    assert completed.evidence_refs == (EVIDENCE_REF_ID,)
    assert interviews.repository.get("interview_001") == completed
    assert interviews.repository.get("interview_001", 1) == scheduled

    cancelled = interviews.schedule_interview(
        _command("interview_002", EntityKind.INTERVIEW, "command_schedule_2", actor="agent:ops"),
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.SCREEN,
        scheduled_at=datetime(2026, 1, 8, 9, 0, tzinfo=UTC),
    )
    assert cancelled.created_by == "agent:ops"
    cancelled = interviews.cancel_interview(
        _command("interview_002", EntityKind.INTERVIEW, "command_cancel", expected_revision=1)
    )
    assert cancelled.status is InterviewStatus.CANCELLED

    listed = interviews.repository.list_for_application("application_001")
    assert [item.entity_id for item in listed] == ["interview_002", "interview_001"]

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(InterviewRevisionRow)) == 4
        assert session.scalar(select(func.count()).select_from(InterviewEvidenceRefRow)) == 1
        events = session.scalars(
            select(DomainEventRow)
            .where(DomainEventRow.entity_id.in_(["interview_001", "interview_002"]))
            .order_by(DomainEventRow.occurred_at, DomainEventRow.event_id)
        ).all()
        assert [event.event_type for event in events] == [
            "interview.scheduled",
            "interview.completed",
            "interview.scheduled",
            "interview.cancelled",
        ]
        for event in events:
            assert set(event.payload) <= {
                "revision_id",
                "interview_id",
                "application_id",
                "application_revision",
                "round",
                "scheduled_at",
                "status",
                "evidence_count",
            }


def test_interview_writes_never_touch_other_domains(tmp_path: Path) -> None:
    engine, applications, interviews = _services(tmp_path)
    before = applications.repository.get("application_001")

    interviews.schedule_interview(
        _schedule_command(),
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.LOOP,
        scheduled_at=SCHEDULED_AT,
    )
    interviews.complete_interview(
        _command("interview_001", EntityKind.INTERVIEW, "command_complete", expected_revision=1)
    )

    after = applications.repository.get("application_001")
    assert after == before
    assert after is not None and after.revision == 3
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ApplicationRevisionRow)) == 3
        assert session.scalar(select(func.count()).select_from(OutcomeRecordRow)) == 0
        application_events = session.scalar(
            select(func.count())
            .select_from(DomainEventRow)
            .where(DomainEventRow.entity_id == "application_001")
        )
        assert application_events == 3


def test_interview_schedule_requires_submitted_application(tmp_path: Path) -> None:
    engine, applications = _seed_dependencies(tmp_path)
    interviews = InterviewService(CommandService(engine))
    applications.create(
        _command("application_001", EntityKind.APPLICATION, "command_application"),
        opportunity_id="opportunity_001",
        opportunity_revision=1,
    )
    with pytest.raises(ValueError, match="submitted, non-terminal"):
        interviews.schedule_interview(
            _schedule_command(),
            application_id="application_001",
            application_revision=1,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
        )
    with pytest.raises(ValueError, match="exact Application revision"):
        interviews.schedule_interview(
            _schedule_command("command_dangling_app"),
            application_id="application_404",
            application_revision=1,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
        )
    with pytest.raises(ValueError, match="exact Application revision"):
        interviews.schedule_interview(
            _schedule_command("command_dangling_rev"),
            application_id="application_001",
            application_revision=9,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
        )
    _submitted_application(applications)
    with pytest.raises(ValueError, match="exact canonical EvidenceRefs"):
        interviews.schedule_interview(
            _schedule_command("command_dangling_evidence"),
            application_id="application_001",
            application_revision=3,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
            evidence_refs=("evidence_404",),
        )
    rejected = applications.advance_state(
        _command("application_001", EntityKind.APPLICATION, "command_reject", expected_revision=3),
        state=ApplicationState.REJECTED,
    )
    assert rejected.state is ApplicationState.REJECTED
    with pytest.raises(ValueError, match="submitted, non-terminal"):
        interviews.schedule_interview(
            _schedule_command("command_terminal"),
            application_id="application_001",
            application_revision=4,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
        )
    with pytest.raises(ValueError, match="expected revision zero"):
        interviews.schedule_interview(
            _command("interview_009", EntityKind.INTERVIEW, "command_bad_rev", expected_revision=1),
            application_id="application_001",
            application_revision=4,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
        )
    with pytest.raises(ValueError, match="interview target"):
        interviews.schedule_interview(
            _command("application_001", EntityKind.APPLICATION, "command_bad_kind"),
            application_id="application_001",
            application_revision=4,
            round=InterviewRound.SCREEN,
            scheduled_at=SCHEDULED_AT,
        )
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(InterviewIdentityRow)) == 0


def test_interview_invalid_transitions_fail_loud(tmp_path: Path) -> None:
    _, _, interviews = _services(tmp_path)
    interviews.schedule_interview(
        _schedule_command(),
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.OFFER_TALK,
        scheduled_at=SCHEDULED_AT,
    )
    interviews.complete_interview(
        _command("interview_001", EntityKind.INTERVIEW, "command_complete", expected_revision=1)
    )
    with pytest.raises(ValueError, match="only a scheduled Interview"):
        interviews.complete_interview(
            _command(
                "interview_001", EntityKind.INTERVIEW, "command_complete_2", expected_revision=2
            )
        )
    with pytest.raises(ValueError, match="only a scheduled Interview"):
        interviews.cancel_interview(
            _command("interview_001", EntityKind.INTERVIEW, "command_cancel", expected_revision=2)
        )
    with pytest.raises(RevisionConflict):
        interviews.cancel_interview(
            _command("interview_001", EntityKind.INTERVIEW, "command_stale", expected_revision=1)
        )
    with pytest.raises(ValueError, match="exact current revision"):
        interviews.cancel_interview(
            _command("interview_404", EntityKind.INTERVIEW, "command_missing", expected_revision=1)
        )
    with pytest.raises(ValueError, match="existing revision"):
        interviews.cancel_interview(_command("interview_001", EntityKind.INTERVIEW, "command_zero"))
    assert interviews.repository.get("interview_001").status is InterviewStatus.COMPLETED  # type: ignore[union-attr]


def test_interview_commit_rolls_back_atomically_on_write_failure(tmp_path: Path) -> None:
    engine, _, interviews = _services(tmp_path)
    command = _schedule_command()

    # Bypass service validation with a dangling evidence ref: the transactional
    # write fails inside the commit and must roll back every row.
    interview = Interview(
        entity_id="interview_001",
        revision=1,
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.SCREEN,
        scheduled_at=SCHEDULED_AT,
        evidence_refs=("evidence_404",),
        created_by="user",
    )
    with pytest.raises(ValueError, match="exact canonical EvidenceRefs"):
        interviews.commands.commit(
            command,
            interview.model_dump(mode="json"),
            event_type="interview.scheduled",
            transactional_write=InterviewWrite(interview),
        )
    assert (
        interviews.commands.get(EntityRef(entity_id="interview_001", kind=EntityKind.INTERVIEW))
        is None
    )
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(InterviewIdentityRow)) == 0
        assert session.scalar(select(func.count()).select_from(InterviewRevisionRow)) == 0
        assert session.scalar(select(func.count()).select_from(InterviewEvidenceRefRow)) == 0
        assert (
            session.scalar(
                select(func.count())
                .select_from(DomainEventRow)
                .where(DomainEventRow.entity_id == "interview_001")
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(IdempotencyRecordRow)
                .where(IdempotencyRecordRow.idempotency_key == command.idempotency_key)
            )
            == 0
        )

    # The same command id can be retried with valid input after the rollback.
    scheduled = interviews.schedule_interview(
        command,
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.SCREEN,
        scheduled_at=SCHEDULED_AT,
    )
    assert scheduled.revision == 1


def test_interview_rows_are_immutable_and_identity_is_stable(tmp_path: Path) -> None:
    engine, _, interviews = _services(tmp_path)
    interviews.schedule_interview(
        _schedule_command(),
        application_id="application_001",
        application_revision=3,
        round=InterviewRound.TECHNICAL,
        scheduled_at=SCHEDULED_AT,
    )
    with (
        pytest.raises(IntegrityError, match="interview_identity is immutable"),
        engine.begin() as connection,
    ):
        connection.execute(
            InterviewIdentityRow.__table__.update()
            .where(InterviewIdentityRow.interview_id == "interview_001")
            .values(application_revision=2)
        )
    with (
        pytest.raises(IntegrityError, match="interview_revision_record is immutable"),
        engine.begin() as connection,
    ):
        connection.execute(
            InterviewRevisionRow.__table__.delete().where(
                InterviewRevisionRow.interview_id == "interview_001"
            )
        )
    with (
        pytest.raises(IntegrityError, match="ck_interview_round"),
        engine.begin() as connection,
    ):
        connection.execute(
            InterviewRevisionRow.__table__.insert(),
            {
                "interview_id": "interview_001",
                "revision": 2,
                "schema_version": 1,
                "round": "group_chat",
                "scheduled_at": datetime.now(UTC),
                "status": "scheduled",
                "evidence_count": 0,
                "created_at": datetime.now(UTC),
                "created_by": "user",
            },
        )
    with (
        pytest.raises(IntegrityError, match="interview evidence aggregate is incomplete"),
        engine.begin() as connection,
    ):
        connection.execute(
            InterviewRevisionRow.__table__.insert(),
            {
                "interview_id": "interview_001",
                "revision": 2,
                "schema_version": 1,
                "round": "loop",
                "scheduled_at": datetime.now(UTC),
                "status": "completed",
                "evidence_count": 1,
                "created_at": datetime.now(UTC),
                "created_by": "user",
            },
        )
    assert interviews.repository.get("interview_001").revision == 1  # type: ignore[union-attr]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(InterviewRevisionRow)) == 1
