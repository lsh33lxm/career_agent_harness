from datetime import UTC, datetime, timedelta

import pytest

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import ApplicationState, OpportunityState
from career_harness.core.opportunity import PriorityLevel
from career_harness.core.project import ProjectEnhancementTaskStatus
from career_harness.core.today import (
    TODAY_POLICY_VERSION,
    ApplicationInput,
    EnhancementTaskInput,
    OpportunityInput,
    ReviewRequestInput,
    ReviewRequestStatus,
    TodayInputs,
    TodayItem,
    TodayItemKind,
    TodayQueue,
    TodayReason,
    TodayReasonCode,
    TodaySourceRef,
    build_today_queue,
)

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(days=2)


def _source(entity_id: str, kind: EntityKind, revision: int = 1) -> TodaySourceRef:
    return TodaySourceRef(entity_id=entity_id, kind=kind, revision=revision)


def _opportunity(
    entity_id: str,
    *,
    state: OpportunityState = OpportunityState.QUALIFIED,
    user: PriorityLevel | None = None,
    suggested: PriorityLevel | None = None,
    deadline: datetime | None = None,
) -> OpportunityInput:
    return OpportunityInput(
        source=_source(entity_id, EntityKind.OPPORTUNITY),
        state=state,
        user_priority=user,
        suggested_priority=suggested,
        deadline_at=deadline,
    )


def _application(
    entity_id: str,
    *,
    state: ApplicationState = ApplicationState.PREPARING,
    opportunity: TodaySourceRef | None = None,
    user: PriorityLevel | None = None,
    suggested: PriorityLevel | None = None,
    interview_at: datetime | None = None,
) -> ApplicationInput:
    return ApplicationInput(
        source=_source(entity_id, EntityKind.APPLICATION),
        opportunity=opportunity,
        state=state,
        user_priority=user,
        suggested_priority=suggested,
        interview_at=interview_at,
    )


def _task(
    entity_id: str,
    *,
    status: ProjectEnhancementTaskStatus = ProjectEnhancementTaskStatus.READY,
) -> EnhancementTaskInput:
    return EnhancementTaskInput(
        source=_source(entity_id, EntityKind.PROJECT_ENHANCEMENT_TASK),
        status=status,
    )


def _review(
    entity_id: str,
    kind: EntityKind,
    *,
    status: ReviewRequestStatus = ReviewRequestStatus.PROPOSED,
) -> ReviewRequestInput:
    return ReviewRequestInput(source=_source(entity_id, kind), status=status)


def test_empty_inputs_yield_empty_queue() -> None:
    queue = build_today_queue(TodayInputs(), generated_at=NOW)
    assert queue.items == ()
    assert queue.input_revisions == ()
    assert queue.generated_at == NOW
    assert queue.policy_version == TODAY_POLICY_VERSION


def test_total_order_user_then_suggested_then_time_then_item_id() -> None:
    inputs = TodayInputs(
        opportunities=(
            _opportunity("opportunity_plain"),
            _opportunity("opportunity_user_high", user=PriorityLevel.HIGH),
            _opportunity("opportunity_suggested", suggested=PriorityLevel.URGENT),
            _opportunity("opportunity_deadline_late", deadline=LATER),
            _opportunity("opportunity_deadline_early", deadline=NOW),
            _opportunity("opportunity_user_urgent", user=PriorityLevel.URGENT),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    assert [item.item_id for item in queue.items] == [
        "today:opportunity_action:opportunity_user_urgent",
        "today:opportunity_action:opportunity_user_high",
        "today:opportunity_action:opportunity_suggested",
        "today:opportunity_action:opportunity_deadline_early",
        "today:opportunity_action:opportunity_deadline_late",
        "today:opportunity_action:opportunity_plain",
    ]


def test_item_id_is_final_tiebreaker() -> None:
    inputs = TodayInputs(
        opportunities=(
            _opportunity("opportunity_b", user=PriorityLevel.MEDIUM),
            _opportunity("opportunity_a", user=PriorityLevel.MEDIUM),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    assert [item.item_id for item in queue.items] == [
        "today:opportunity_action:opportunity_a",
        "today:opportunity_action:opportunity_b",
    ]


def test_shuffled_input_order_produces_equal_output() -> None:
    ordered = TodayInputs(
        opportunities=(
            _opportunity("opportunity_001", user=PriorityLevel.HIGH),
            _opportunity("opportunity_002", suggested=PriorityLevel.LOW),
        ),
        applications=(
            _application("application_001"),
            _application(
                "application_002",
                state=ApplicationState.INTERVIEW,
                interview_at=NOW,
            ),
        ),
        enhancement_tasks=(
            _task("task_001"),
            _task("task_002", status=ProjectEnhancementTaskStatus.IN_PROGRESS),
        ),
        review_requests=(
            _review("claim_001", EntityKind.EXTRACTED_CLAIM),
            _review("requirement_001", EntityKind.JOB_REQUIREMENT),
            _review("patch_001", EntityKind.RESUME_PATCH),
        ),
    )
    shuffled = TodayInputs(
        opportunities=tuple(reversed(ordered.opportunities)),
        applications=tuple(reversed(ordered.applications)),
        enhancement_tasks=tuple(reversed(ordered.enhancement_tasks)),
        review_requests=tuple(reversed(ordered.review_requests)),
    )
    assert build_today_queue(shuffled, generated_at=NOW) == build_today_queue(
        ordered, generated_at=NOW
    )


def test_missing_priorities_degrade_to_lowest_bucket_with_reason_codes() -> None:
    queue = build_today_queue(
        TodayInputs(opportunities=(_opportunity("opportunity_001"),)),
        generated_at=NOW,
    )
    item = queue.items[0]
    assert item.user_priority is None
    assert item.suggested_priority is None
    codes = {reason.code for reason in item.reasons}
    assert TodayReasonCode.MISSING_USER_PRIORITY in codes
    assert TodayReasonCode.MISSING_SUGGESTED_PRIORITY in codes
    explanations = {reason.code: reason.explanation for reason in item.reasons}
    assert "lowest user-priority bucket" in explanations[TodayReasonCode.MISSING_USER_PRIORITY]


def test_missing_deadline_sorts_last_within_bucket() -> None:
    inputs = TodayInputs(
        opportunities=(
            _opportunity("opportunity_no_deadline", user=PriorityLevel.HIGH),
            _opportunity("opportunity_deadline", user=PriorityLevel.HIGH, deadline=LATER),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    assert [item.item_id for item in queue.items] == [
        "today:opportunity_action:opportunity_deadline",
        "today:opportunity_action:opportunity_no_deadline",
    ]
    codes = {reason.code for reason in queue.items[0].reasons}
    assert TodayReasonCode.DEADLINE_APPROACHING in codes


def test_stable_deterministic_item_ids() -> None:
    inputs = TodayInputs(
        opportunities=(_opportunity("opportunity_001"),),
        applications=(_application("application_001"),),
        enhancement_tasks=(_task("task_001"),),
        review_requests=(_review("claim_001", EntityKind.EXTRACTED_CLAIM),),
    )
    first = build_today_queue(inputs, generated_at=NOW)
    second = build_today_queue(inputs, generated_at=NOW)
    assert first == second
    assert {item.item_id for item in first.items} == {
        "today:opportunity_action:opportunity_001",
        "today:application_step:application_001",
        "today:enhancement_task:task_001",
        "today:review_request:claim_001",
    }


def test_terminal_and_inactive_sources_are_excluded() -> None:
    inputs = TodayInputs(
        opportunities=(
            _opportunity("opportunity_declined", state=OpportunityState.DECLINED),
            _opportunity("opportunity_expired", state=OpportunityState.EXPIRED),
            _opportunity("opportunity_archived", state=OpportunityState.ARCHIVED),
        ),
        applications=(
            _application("application_submitted", state=ApplicationState.SUBMITTED_BY_USER),
            _application("application_rejected", state=ApplicationState.REJECTED),
            _application("application_closed", state=ApplicationState.CLOSED),
        ),
        enhancement_tasks=(
            _task("task_completed", status=ProjectEnhancementTaskStatus.COMPLETED),
            _task("task_cancelled", status=ProjectEnhancementTaskStatus.CANCELLED),
        ),
        review_requests=(
            _review(
                "claim_decided",
                EntityKind.EXTRACTED_CLAIM,
                status=ReviewRequestStatus.ACCEPTED,
            ),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    assert queue.items == ()
    # Excluded inputs were still read, so their exact revisions stay auditable.
    assert len(queue.input_revisions) == 9


def test_interview_stage_produces_interview_prep_item() -> None:
    inputs = TodayInputs(
        applications=(
            _application(
                "application_001",
                state=ApplicationState.INTERVIEW,
                interview_at=NOW,
                user=PriorityLevel.HIGH,
            ),
            _application("application_002", state=ApplicationState.INTERVIEW),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    scheduled, unscheduled = queue.items
    assert scheduled.kind is TodayItemKind.INTERVIEW_PREP
    assert scheduled.interview_at == NOW
    scheduled_codes = {reason.code for reason in scheduled.reasons}
    assert TodayReasonCode.INTERVIEW_UPCOMING in scheduled_codes
    assert TodayReasonCode.INTERVIEW_PREP_DUE in scheduled_codes
    assert TodayReasonCode.USER_PRIORITY_HIGH in scheduled_codes
    assert unscheduled.interview_at is None
    assert TodayReasonCode.INTERVIEW_UPCOMING not in {reason.code for reason in unscheduled.reasons}


def test_application_item_carries_opportunity_source_ref() -> None:
    opportunity = _source("opportunity_001", EntityKind.OPPORTUNITY, revision=3)
    inputs = TodayInputs(
        applications=(
            _application(
                "application_001",
                state=ApplicationState.OA,
                opportunity=opportunity,
                suggested=PriorityLevel.MEDIUM,
            ),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    item = queue.items[0]
    assert item.kind is TodayItemKind.APPLICATION_STEP
    assert item.source_refs[1] == opportunity
    assert item.suggested_priority is PriorityLevel.MEDIUM


def test_review_request_kinds_and_reason() -> None:
    inputs = TodayInputs(
        review_requests=(
            _review("requirement_001", EntityKind.JOB_REQUIREMENT),
            _review("claim_001", EntityKind.EXTRACTED_CLAIM),
            _review("patch_001", EntityKind.RESUME_PATCH),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    assert [item.kind for item in queue.items] == [TodayItemKind.REVIEW_REQUEST] * 3
    for item in queue.items:
        codes = {reason.code for reason in item.reasons}
        assert TodayReasonCode.PENDING_USER_REVIEW in codes


def test_review_request_rejects_non_reviewable_kind() -> None:
    with pytest.raises(ValueError, match="requirement, claim or resume patch"):
        _review("opportunity_001", EntityKind.OPPORTUNITY)


def test_item_id_must_derive_from_kind_and_source() -> None:
    with pytest.raises(ValueError, match="item id must derive"):
        TodayItem(
            item_id="today:review_request:opportunity_001",
            kind=TodayItemKind.OPPORTUNITY_ACTION,
            source_refs=(_source("opportunity_001", EntityKind.OPPORTUNITY),),
            reasons=(
                TodayReason(
                    code=TodayReasonCode.OPPORTUNITY_ACTIVE,
                    explanation="opportunity is in the active state 'qualified'",
                ),
            ),
        )


def test_queue_rejects_unordered_items() -> None:
    inputs = TodayInputs(
        opportunities=(
            _opportunity("opportunity_a", user=PriorityLevel.LOW),
            _opportunity("opportunity_b", user=PriorityLevel.URGENT),
        ),
    )
    queue = build_today_queue(inputs, generated_at=NOW)
    with pytest.raises(ValueError, match="total order"):
        TodayQueue(
            items=(queue.items[1], queue.items[0]),
            input_revisions=queue.input_revisions,
            generated_at=NOW,
        )
