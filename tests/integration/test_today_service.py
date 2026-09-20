from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import Engine, event, func, select
from sqlalchemy.orm import Session

from career_harness.core.common import EntityKind
from career_harness.core.interview import Interview, InterviewRound, InterviewStatus
from career_harness.core.job import JobRef
from career_harness.core.lifecycle import ApplicationState
from career_harness.core.opportunity import PriorityInputRevision, PriorityLevel
from career_harness.core.today import TodayReasonCode
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    Base,
    CapabilityIdentityRow,
    ExtractedClaimEvidenceRefRow,
    ExtractedClaimIdentityRow,
    ExtractedClaimRevisionRow,
    JobRequirementEvidenceRefRow,
    JobRequirementIdentityRow,
    JobRequirementRevisionRow,
    JobRequirementScopeRow,
    ProjectEnhancementTaskRow,
    ProjectIdentityRow,
    ResumeBaseRevisionRow,
    ResumeIdentityRow,
    ResumePatchIdentityRow,
    ResumePatchRevisionRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.application_service import ApplicationService
from career_harness.services.command_service import CommandService
from career_harness.services.interview_service import InterviewService
from career_harness.services.opportunity_service import OpportunityService
from career_harness.services.today_service import TodayService
from tests.integration.test_application_service import _command
from tests.integration.test_fact_service import EVIDENCE_REF_ID, _seed_evidence_ref
from tests.integration.test_interview_service import _services
from tests.support.job_data import seed_job_revision

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _engine(tmp_path: Path) -> Engine:
    database_url = sqlite_url(tmp_path / "today-service.db")
    upgrade_to_head(database_url)
    return create_sqlite_engine(database_url)


def _table_counts(engine: Engine) -> dict[str, int]:
    with Session(engine) as session:
        return {
            table.name: session.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }


def _seed_pending_proposals(engine: Engine) -> None:
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _seed_evidence_ref(connection, EVIDENCE_REF_ID)
        connection.execute(ProjectIdentityRow.__table__.insert(), {"project_id": "project_001"})
        connection.execute(
            CapabilityIdentityRow.__table__.insert(), {"capability_id": "capability_001"}
        )
        for task_id, status in (("task_001", "ready"), ("task_002", "completed")):
            connection.execute(
                ProjectEnhancementTaskRow.__table__.insert(),
                {
                    "task_id": task_id,
                    "revision": 1,
                    "project_id": "project_001",
                    "target_gap_id": "gap_001",
                    "target_capability_id": "capability_001",
                    "learning_plan": ["learn the gap"],
                    "files_to_review": ["src/module.py"],
                    "change_plan": ["change the module"],
                    "experiment_plan": ["run the experiment"],
                    "validation_plan": ["validate the change"],
                    "expected_evidence": ["test output"],
                    "status": status,
                    "schema_version": 1,
                    "created_at": now,
                    "created_by": "agent:planner",
                },
            )
        for claim_id, status, reviewed in (
            ("claim_001", "proposed", False),
            ("claim_002", "accepted", True),
        ):
            connection.execute(ExtractedClaimIdentityRow.__table__.insert(), {"claim_id": claim_id})
            connection.execute(
                ExtractedClaimEvidenceRefRow.__table__.insert(),
                {
                    "claim_id": claim_id,
                    "claim_revision": 1,
                    "ordinal": 0,
                    "evidence_ref_id": EVIDENCE_REF_ID,
                },
            )
            connection.execute(
                ExtractedClaimRevisionRow.__table__.insert(),
                {
                    "claim_id": claim_id,
                    "revision": 1,
                    "schema_version": 1,
                    "claim_type": "work_history",
                    "subject_entity_id": "candidate_001",
                    "subject_entity_kind": "candidate",
                    "proposed_value": {"detail": f"{claim_id} value"},
                    "extractor": "test-extractor",
                    "extractor_version": "1.0",
                    "confidence": 0.5,
                    "status": status,
                    "evidence_count": 1,
                    "proposed_by": "agent:extractor",
                    "proposed_by_kind": "agent",
                    "proposed_at": now,
                    "reviewed_by": "user" if reviewed else None,
                    "reviewed_by_kind": "user" if reviewed else None,
                    "review_reason": "reviewed" if reviewed else None,
                    "reviewed_at": now if reviewed else None,
                },
            )
        connection.execute(
            ResumeIdentityRow.__table__.insert(),
            {"resume_id": "resume_001", "candidate_id": "candidate_001"},
        )
        connection.execute(
            ResumeBaseRevisionRow.__table__.insert(),
            {
                "resume_id": "resume_001",
                "revision": 1,
                "schema_version": 1,
                "sections": {"summary": "Verified summary"},
                "created_at": now,
                "created_by": "user",
            },
        )
        for patch_id, status, reviewed in (
            ("patch_001", "proposed", False),
            ("patch_002", "accepted", True),
        ):
            connection.execute(
                ResumePatchIdentityRow.__table__.insert(),
                {"patch_id": patch_id, "resume_id": "resume_001", "base_revision": 1},
            )
            connection.execute(
                ResumePatchRevisionRow.__table__.insert(),
                {
                    "patch_id": patch_id,
                    "revision": 1,
                    "operations": [{"operation": "replace", "target_path": "/summary"}],
                    "generator_run_id": None,
                    "status": status,
                    "proposed_by": "agent:resume",
                    "proposed_by_kind": "agent",
                    "proposed_at": now,
                    "reviewed_by": "user" if reviewed else None,
                    "reviewed_by_kind": "user" if reviewed else None,
                    "review_reason": "reviewed" if reviewed else None,
                    "reviewed_at": now if reviewed else None,
                },
            )
        for requirement_id, status, reviewed in (
            ("requirement_001", "proposed", False),
            ("requirement_002", "rejected", True),
        ):
            connection.execute(
                JobRequirementIdentityRow.__table__.insert(),
                {"requirement_id": requirement_id, "job_id": "job_001"},
            )
            connection.execute(
                JobRequirementScopeRow.__table__.insert(),
                {
                    "requirement_id": requirement_id,
                    "requirement_revision": 1,
                    "ordinal": 0,
                    "scope": "apply",
                },
            )
            connection.execute(
                JobRequirementEvidenceRefRow.__table__.insert(),
                {
                    "requirement_id": requirement_id,
                    "requirement_revision": 1,
                    "ordinal": 0,
                    "evidence_ref_id": EVIDENCE_REF_ID,
                },
            )
            connection.execute(
                JobRequirementRevisionRow.__table__.insert(),
                {
                    "requirement_id": requirement_id,
                    "revision": 1,
                    "schema_version": 1,
                    "job_id": "job_001",
                    "job_revision": 1,
                    "requirement_text": f"{requirement_id} text",
                    "importance": "required",
                    "capability_id": None,
                    "graph_version_id": None,
                    "required_scope_count": 1,
                    "source_evidence_count": 1,
                    "status": status,
                    "proposed_by": "agent:parser",
                    "proposed_by_kind": "agent",
                    "proposed_at": now,
                    "reviewed_by": "user" if reviewed else None,
                    "reviewed_by_kind": "user" if reviewed else None,
                    "review_reason": "reviewed" if reviewed else None,
                    "reviewed_at": now if reviewed else None,
                },
            )


def _seed_career_data(engine: Engine) -> None:
    seed_job_revision(engine, "job_001", 1)
    seed_job_revision(engine, "job_002", 1)
    commands = CommandService(engine)
    opportunities = OpportunityService(commands)
    opportunities.admit_manually(
        _command("opportunity_001", EntityKind.OPPORTUNITY, "command_opportunity_001"),
        JobRef(job_id="job_001", revision=1),
        opportunity_id="opportunity_001",
        decision_id="decision_001",
    )
    opportunities.set_user_priority(
        _command(
            "opportunity_001",
            EntityKind.OPPORTUNITY,
            "command_user_priority",
            expected_revision=1,
        ),
        level=PriorityLevel.HIGH,
    )
    opportunities.set_suggested_priority(
        _command(
            "opportunity_001",
            EntityKind.OPPORTUNITY,
            "command_suggested_priority",
            expected_revision=2,
        ),
        level=PriorityLevel.MEDIUM,
        reasons=("strong match",),
        input_revisions=(PriorityInputRevision(entity_id="job_001", revision=1),),
    )
    opportunities.admit_manually(
        _command("opportunity_002", EntityKind.OPPORTUNITY, "command_opportunity_002"),
        JobRef(job_id="job_002", revision=1),
        opportunity_id="opportunity_002",
        decision_id="decision_002",
    )
    ApplicationService(commands).create(
        _command("application_001", EntityKind.APPLICATION, "command_application_001"),
        opportunity_id="opportunity_002",
        opportunity_revision=1,
    )
    _seed_pending_proposals(engine)


def test_today_service_assembles_multi_source_queue_without_writes(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    _seed_career_data(engine)
    before = _table_counts(engine)

    queue = TodayService(engine).build_queue(generated_at=NOW)

    assert _table_counts(engine) == before
    assert [item.item_id for item in queue.items] == [
        "today:opportunity_action:opportunity_001",
        "today:application_step:application_001",
        "today:enhancement_task:task_001",
        "today:opportunity_action:opportunity_002",
        "today:review_request:claim_001",
        "today:review_request:patch_001",
        "today:review_request:requirement_001",
    ]
    first = queue.items[0]
    assert first.user_priority is PriorityLevel.HIGH
    assert first.suggested_priority is PriorityLevel.MEDIUM
    first_codes = {reason.code for reason in first.reasons}
    assert TodayReasonCode.USER_PRIORITY_HIGH in first_codes
    assert TodayReasonCode.SUGGESTED_PRIORITY_MEDIUM in first_codes
    application_item = queue.items[1]
    application_codes = {reason.code for reason in application_item.reasons}
    assert TodayReasonCode.MISSING_USER_PRIORITY in application_codes
    assert TodayReasonCode.APPLICATION_STEP_PENDING in application_codes
    refs = {(ref.entity_id, ref.kind, ref.revision) for ref in queue.input_revisions}
    assert ("opportunity_001", EntityKind.OPPORTUNITY, 3) in refs
    assert ("opportunity_002", EntityKind.OPPORTUNITY, 1) in refs
    assert ("application_001", EntityKind.APPLICATION, 1) in refs
    assert ("task_001", EntityKind.PROJECT_ENHANCEMENT_TASK, 1) in refs
    # Excluded sources (completed task, decided proposals) were still read exactly.
    assert ("task_002", EntityKind.PROJECT_ENHANCEMENT_TASK, 1) in refs
    assert ("claim_002", EntityKind.EXTRACTED_CLAIM, 1) in refs
    assert ("patch_002", EntityKind.RESUME_PATCH, 1) in refs
    assert ("requirement_002", EntityKind.JOB_REQUIREMENT, 1) in refs
    assert queue.policy_version == "today-policy-v1"
    assert queue.generated_at == NOW


def test_today_service_returns_empty_queue_for_empty_database(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    before = _table_counts(engine)

    queue = TodayService(engine).build_queue(generated_at=NOW)

    assert _table_counts(engine) == before
    assert queue.items == ()
    assert queue.input_revisions == ()


def _interview_stage_services(
    tmp_path: Path,
) -> tuple[Engine, ApplicationService, InterviewService]:
    engine, applications, interviews = _services(tmp_path)
    applications.advance_state(
        _command(
            "application_001", EntityKind.APPLICATION, "command_interview", expected_revision=3
        ),
        state=ApplicationState.INTERVIEW,
    )
    return engine, applications, interviews


def _schedule(
    interviews: InterviewService,
    interview_id: str,
    *,
    scheduled_at: datetime = NOW,
    application_revision: int = 3,
) -> Interview:
    return interviews.schedule_interview(
        _command(interview_id, EntityKind.INTERVIEW, f"command_schedule_{interview_id}"),
        application_id="application_001",
        application_revision=application_revision,
        round=InterviewRound.TECHNICAL,
        scheduled_at=scheduled_at,
    )


def test_today_interviews_use_latest_status_and_exact_historical_pins_without_writes(
    tmp_path: Path,
) -> None:
    engine, _, interviews = _interview_stage_services(tmp_path)
    _schedule(interviews, "interview_later", scheduled_at=NOW + timedelta(days=1))
    _schedule(interviews, "interview_b", application_revision=4)
    selected = _schedule(interviews, "interview_a")
    for interview_id, terminal in (
        ("interview_cancelled", interviews.cancel_interview),
        ("interview_completed", interviews.complete_interview),
    ):
        _schedule(interviews, interview_id, scheduled_at=NOW - timedelta(days=1))
        terminal(
            _command(
                interview_id, EntityKind.INTERVIEW, f"command_{interview_id}", expected_revision=1
            )
        )
    today = TodayService(engine)
    before = _table_counts(engine)
    statements = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        queue = today.build_queue(generated_at=NOW + timedelta(days=2))
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)
    assert statements and all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )
    assert _table_counts(engine) == before
    item = next(item for item in queue.items if item.kind.value == "interview_prep")
    assert item.interview_at == selected.scheduled_at.replace(tzinfo=UTC) == NOW
    assert [(ref.entity_id, ref.revision) for ref in item.source_refs] == [
        ("application_001", 4),
        ("opportunity_001", 1),
        ("interview_a", 1),
        ("application_001", 3),
    ]
    assert {(ref.entity_id, ref.revision) for ref in queue.input_revisions} == {
        ("application_001", 3),
        ("application_001", 4),
        ("opportunity_001", 1),
        ("interview_a", 1),
        ("interview_b", 1),
        ("interview_later", 1),
        ("interview_cancelled", 2),
        ("interview_completed", 2),
    }
    latest = today.interviews.list_for_application("application_001")
    today.interviews.list_for_application = Mock(return_value=tuple(reversed(latest)))
    assert today.build_queue(generated_at=queue.generated_at) == queue


@pytest.mark.parametrize("status", [None, InterviewStatus.CANCELLED, InterviewStatus.COMPLETED])
def test_today_interview_without_eligible_schedule_has_no_timestamp(
    tmp_path: Path, status: InterviewStatus | None
) -> None:
    engine, _, interviews = _interview_stage_services(tmp_path)
    if status is not None:
        _schedule(interviews, "interview_001")
        transition = (
            interviews.cancel_interview
            if status is InterviewStatus.CANCELLED
            else interviews.complete_interview
        )
        transition(
            _command("interview_001", EntityKind.INTERVIEW, "command_terminal", expected_revision=1)
        )
    queue = TodayService(engine).build_queue(generated_at=NOW)
    item = next(item for item in queue.items if item.kind.value == "interview_prep")
    assert item.interview_at is None
    assert all(ref.kind is not EntityKind.INTERVIEW for ref in item.source_refs)
    consulted = [ref for ref in queue.input_revisions if ref.kind is EntityKind.INTERVIEW]
    assert [(ref.entity_id, ref.revision) for ref in consulted] == (
        [] if status is None else [("interview_001", 2)]
    )


@pytest.mark.parametrize("fault", ["missing", "wrong_id", "wrong_revision"])
@pytest.mark.parametrize("terminal", [False, True])
def test_today_rejects_missing_or_mismatched_exact_application_pins(
    tmp_path: Path, fault: str, terminal: bool
) -> None:
    engine, applications, interviews = _interview_stage_services(tmp_path)
    _schedule(interviews, "interview_001")
    if terminal:
        interviews.cancel_interview(
            _command("interview_001", EntityKind.INTERVIEW, "command_cancel", expected_revision=1)
        )
    historical = applications.repository.get("application_001", 3)
    assert historical is not None
    if fault == "missing":
        resolved = None
    elif fault == "wrong_id":
        resolved = historical.model_copy(update={"entity_id": "application_002"})
    else:
        resolved = applications.repository.get("application_001", 4)
    today = TodayService(engine)
    today.applications.get = Mock(return_value=resolved)
    with pytest.raises(ValueError, match="exact pinned Application revision"):
        today.build_queue(generated_at=NOW)
    today.applications.get.assert_called_once_with("application_001", 3)


def test_today_rejects_cross_application_interview_returned_by_repository(tmp_path: Path) -> None:
    engine, _, interviews = _interview_stage_services(tmp_path)
    interview = _schedule(interviews, "interview_001")
    today = TodayService(engine)
    today.interviews.list_for_application = Mock(
        return_value=(interview.model_copy(update={"application_id": "application_other"}),)
    )
    with pytest.raises(ValueError, match="requested Application"):
        today.build_queue(generated_at=NOW)


def test_today_ignores_interviews_for_other_application_stages(tmp_path: Path) -> None:
    engine, _, interviews = _services(tmp_path)
    _schedule(interviews, "interview_001")
    today = TodayService(engine)
    today.interviews.list_for_application = Mock(side_effect=AssertionError("unexpected read"))
    queue = today.build_queue(generated_at=NOW)
    assert all(item.kind.value != "interview_prep" for item in queue.items)
    assert all(ref.kind is not EntityKind.INTERVIEW for ref in queue.input_revisions)
    today.interviews.list_for_application.assert_not_called()
