"""Pure deterministic policy computing a TodayQueue from typed inputs.

No I/O, no clock access beyond the caller-supplied ``generated_at`` and no
mutation: equal inputs always produce equal output regardless of input order.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from career_harness.core.common import EntityKind, FrozenModel
from career_harness.core.interview import InterviewStatus
from career_harness.core.lifecycle import ApplicationState, OpportunityState
from career_harness.core.opportunity import PriorityLevel
from career_harness.core.project import ProjectEnhancementTaskStatus
from career_harness.core.today.models import (
    TodayItem,
    TodayItemKind,
    TodayQueue,
    TodayReason,
    TodayReasonCode,
    TodaySourceRef,
    today_item_id,
    today_item_sort_key,
)

ACTIVE_OPPORTUNITY_STATES = frozenset(
    {
        OpportunityState.DISCOVERED,
        OpportunityState.WATCHING,
        OpportunityState.QUALIFIED,
        OpportunityState.PREPARING,
    }
)
APPLICATION_STEP_STATES = frozenset(
    {
        ApplicationState.PREPARING,
        ApplicationState.READY_FOR_REVIEW,
        ApplicationState.SCREEN,
        ApplicationState.OA,
    }
)
OPEN_ENHANCEMENT_STATUSES = frozenset(
    {
        ProjectEnhancementTaskStatus.PROPOSED,
        ProjectEnhancementTaskStatus.READY,
        ProjectEnhancementTaskStatus.IN_PROGRESS,
        ProjectEnhancementTaskStatus.AWAITING_VALIDATION,
    }
)
REVIEW_REQUEST_KINDS = frozenset(
    {
        EntityKind.JOB_REQUIREMENT,
        EntityKind.EXTRACTED_CLAIM,
        EntityKind.RESUME_PATCH,
    }
)

_USER_REASON_CODES: dict[PriorityLevel, TodayReasonCode] = {
    PriorityLevel.URGENT: TodayReasonCode.USER_PRIORITY_URGENT,
    PriorityLevel.HIGH: TodayReasonCode.USER_PRIORITY_HIGH,
    PriorityLevel.MEDIUM: TodayReasonCode.USER_PRIORITY_MEDIUM,
    PriorityLevel.LOW: TodayReasonCode.USER_PRIORITY_LOW,
}
_SUGGESTED_REASON_CODES: dict[PriorityLevel, TodayReasonCode] = {
    PriorityLevel.URGENT: TodayReasonCode.SUGGESTED_PRIORITY_URGENT,
    PriorityLevel.HIGH: TodayReasonCode.SUGGESTED_PRIORITY_HIGH,
    PriorityLevel.MEDIUM: TodayReasonCode.SUGGESTED_PRIORITY_MEDIUM,
    PriorityLevel.LOW: TodayReasonCode.SUGGESTED_PRIORITY_LOW,
}


class OpportunityInput(FrozenModel):
    source: TodaySourceRef
    state: OpportunityState
    user_priority: PriorityLevel | None = None
    suggested_priority: PriorityLevel | None = None
    deadline_at: datetime | None = None

    @model_validator(mode="after")
    def source_is_opportunity(self) -> OpportunityInput:
        if self.source.kind is not EntityKind.OPPORTUNITY:
            raise ValueError("opportunity input source must be an opportunity")
        return self


class InterviewInput(FrozenModel):
    """Latest canonical Interview revision with its exact Application pin."""

    source: TodaySourceRef
    application: TodaySourceRef
    status: InterviewStatus
    scheduled_at: datetime

    @field_validator("scheduled_at")
    @classmethod
    def schedule_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @model_validator(mode="after")
    def sources_are_typed(self) -> InterviewInput:
        if self.source.kind is not EntityKind.INTERVIEW:
            raise ValueError("interview input source must be an interview")
        if self.application.kind is not EntityKind.APPLICATION:
            raise ValueError("interview application source must be an application")
        return self


class ApplicationInput(FrozenModel):
    source: TodaySourceRef
    opportunity: TodaySourceRef | None = None
    state: ApplicationState
    user_priority: PriorityLevel | None = None
    suggested_priority: PriorityLevel | None = None
    interview_at: datetime | None = None
    # None preserves direct policy callers; runtime always supplies canonical inputs,
    # including an empty tuple, and cannot use the legacy bare timestamp path.
    interviews: tuple[InterviewInput, ...] | None = None

    @model_validator(mode="after")
    def sources_are_typed(self) -> ApplicationInput:
        if self.source.kind is not EntityKind.APPLICATION:
            raise ValueError("application input source must be an application")
        if self.opportunity is not None and self.opportunity.kind is not EntityKind.OPPORTUNITY:
            raise ValueError("application opportunity source must be an opportunity")
        if self.interviews is not None:
            if self.interview_at is not None:
                raise ValueError(
                    "canonical interview inputs cannot carry a bare interview timestamp"
                )
            if self.interviews and self.state is not ApplicationState.INTERVIEW:
                raise ValueError("interview inputs require an interview-stage application")
            interview_ids: set[str] = set()
            for interview in self.interviews:
                if interview.application.entity_id != self.source.entity_id:
                    raise ValueError("interview must belong to the same application")
                if interview.source.entity_id in interview_ids:
                    raise ValueError("duplicate or conflicting interview revisions")
                interview_ids.add(interview.source.entity_id)
        return self


class EnhancementTaskInput(FrozenModel):
    source: TodaySourceRef
    status: ProjectEnhancementTaskStatus

    @model_validator(mode="after")
    def source_is_enhancement_task(self) -> EnhancementTaskInput:
        if self.source.kind is not EntityKind.PROJECT_ENHANCEMENT_TASK:
            raise ValueError("enhancement task input source must be a project enhancement task")
        return self


class ReviewRequestStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ReviewRequestInput(FrozenModel):
    source: TodaySourceRef
    status: ReviewRequestStatus

    @model_validator(mode="after")
    def source_is_reviewable(self) -> ReviewRequestInput:
        if self.source.kind not in REVIEW_REQUEST_KINDS:
            raise ValueError("review request source must be a requirement, claim or resume patch")
        return self


class TodayInputs(FrozenModel):
    opportunities: tuple[OpportunityInput, ...] = ()
    applications: tuple[ApplicationInput, ...] = ()
    enhancement_tasks: tuple[EnhancementTaskInput, ...] = ()
    review_requests: tuple[ReviewRequestInput, ...] = ()


def _priority_reasons(
    user_priority: PriorityLevel | None,
    suggested_priority: PriorityLevel | None,
) -> tuple[TodayReason, ...]:
    reasons: list[TodayReason] = []
    if user_priority is None:
        reasons.append(
            TodayReason(
                code=TodayReasonCode.MISSING_USER_PRIORITY,
                explanation=(
                    "no user priority is recorded; "
                    "the item ranks in the lowest user-priority bucket"
                ),
            )
        )
    else:
        reasons.append(
            TodayReason(
                code=_USER_REASON_CODES[user_priority],
                explanation=f"user priority is {user_priority.value}",
            )
        )
    if suggested_priority is None:
        reasons.append(
            TodayReason(
                code=TodayReasonCode.MISSING_SUGGESTED_PRIORITY,
                explanation=(
                    "no suggested priority is recorded; "
                    "the item ranks in the lowest suggested-priority bucket"
                ),
            )
        )
    else:
        reasons.append(
            TodayReason(
                code=_SUGGESTED_REASON_CODES[suggested_priority],
                explanation=f"suggested priority is {suggested_priority.value}",
            )
        )
    return tuple(reasons)


def _opportunity_item(input_: OpportunityInput) -> TodayItem | None:
    if input_.state not in ACTIVE_OPPORTUNITY_STATES:
        return None
    reasons = [
        TodayReason(
            code=TodayReasonCode.OPPORTUNITY_ACTIVE,
            explanation=f"opportunity is in the active state '{input_.state.value}'",
        )
    ]
    if input_.deadline_at is not None:
        reasons.append(
            TodayReason(
                code=TodayReasonCode.DEADLINE_APPROACHING,
                explanation=f"deadline is {input_.deadline_at.isoformat()}",
            )
        )
    reasons.extend(_priority_reasons(input_.user_priority, input_.suggested_priority))
    return TodayItem(
        item_id=today_item_id(TodayItemKind.OPPORTUNITY_ACTION, input_.source.entity_id),
        kind=TodayItemKind.OPPORTUNITY_ACTION,
        source_refs=(input_.source,),
        reasons=tuple(reasons),
        user_priority=input_.user_priority,
        suggested_priority=input_.suggested_priority,
        deadline_at=input_.deadline_at,
    )


def _application_item(input_: ApplicationInput) -> TodayItem | None:
    selected: InterviewInput | None = None
    if input_.state in APPLICATION_STEP_STATES:
        kind = TodayItemKind.APPLICATION_STEP
        reasons = [
            TodayReason(
                code=TodayReasonCode.APPLICATION_STEP_PENDING,
                explanation=f"application is in state '{input_.state.value}' and needs a next step",
            )
        ]
        interview_at = None
    elif input_.state is ApplicationState.INTERVIEW:
        kind = TodayItemKind.INTERVIEW_PREP
        reasons = [
            TodayReason(
                code=TodayReasonCode.INTERVIEW_PREP_DUE,
                explanation="application is in the interview stage",
            )
        ]
        if input_.interviews is None:
            interview_at = input_.interview_at
        else:
            selected = min(
                (i for i in input_.interviews if i.status is InterviewStatus.SCHEDULED),
                key=lambda i: (i.scheduled_at, i.source.entity_id),
                default=None,
            )
            interview_at = selected.scheduled_at if selected is not None else None
        if interview_at is not None:
            reasons.append(
                TodayReason(
                    code=TodayReasonCode.INTERVIEW_UPCOMING,
                    explanation=f"interview is scheduled at {interview_at.isoformat()}",
                )
            )
    else:
        return None
    reasons.extend(_priority_reasons(input_.user_priority, input_.suggested_priority))
    source_refs = (
        (input_.source,)
        if input_.opportunity is None
        else (
            input_.source,
            input_.opportunity,
        )
    )
    if selected is not None:
        source_refs = tuple(dict.fromkeys((*source_refs, selected.source, selected.application)))
    return TodayItem(
        item_id=today_item_id(kind, input_.source.entity_id),
        kind=kind,
        source_refs=source_refs,
        reasons=tuple(reasons),
        user_priority=input_.user_priority,
        suggested_priority=input_.suggested_priority,
        interview_at=interview_at,
    )


def _enhancement_task_item(input_: EnhancementTaskInput) -> TodayItem | None:
    if input_.status not in OPEN_ENHANCEMENT_STATUSES:
        return None
    reasons = [
        TodayReason(
            code=TodayReasonCode.GAP_LINKED_TASK,
            explanation=(f"enhancement task targeting a canonical gap is '{input_.status.value}'"),
        )
    ]
    reasons.extend(_priority_reasons(None, None))
    return TodayItem(
        item_id=today_item_id(TodayItemKind.ENHANCEMENT_TASK, input_.source.entity_id),
        kind=TodayItemKind.ENHANCEMENT_TASK,
        source_refs=(input_.source,),
        reasons=tuple(reasons),
    )


def _review_request_item(input_: ReviewRequestInput) -> TodayItem | None:
    if input_.status is not ReviewRequestStatus.PROPOSED:
        return None
    reasons = [
        TodayReason(
            code=TodayReasonCode.PENDING_USER_REVIEW,
            explanation=f"{input_.source.kind.value} proposal is pending user review",
        )
    ]
    reasons.extend(_priority_reasons(None, None))
    return TodayItem(
        item_id=today_item_id(TodayItemKind.REVIEW_REQUEST, input_.source.entity_id),
        kind=TodayItemKind.REVIEW_REQUEST,
        source_refs=(input_.source,),
        reasons=tuple(reasons),
    )


def build_today_queue(inputs: TodayInputs, *, generated_at: datetime) -> TodayQueue:
    """Compute the deterministic Today queue; empty inputs yield an empty queue."""

    items: list[TodayItem] = []
    for opportunity in inputs.opportunities:
        item = _opportunity_item(opportunity)
        if item is not None:
            items.append(item)
    for application in inputs.applications:
        item = _application_item(application)
        if item is not None:
            items.append(item)
    for task in inputs.enhancement_tasks:
        item = _enhancement_task_item(task)
        if item is not None:
            items.append(item)
    for review_request in inputs.review_requests:
        item = _review_request_item(review_request)
        if item is not None:
            items.append(item)

    used_refs = {
        (ref.entity_id, ref.kind, ref.revision): ref
        for input_ in (
            *inputs.opportunities,
            *inputs.applications,
            *inputs.enhancement_tasks,
            *inputs.review_requests,
        )
        for ref in (
            (input_.source, input_.opportunity)
            if isinstance(input_, ApplicationInput)
            else (input_.source, None)
        )
        if ref is not None
    }
    for application in inputs.applications:
        for interview in application.interviews or ():
            for ref in (interview.source, interview.application):
                used_refs[(ref.entity_id, ref.kind, ref.revision)] = ref
    input_revisions = tuple(
        sorted(used_refs.values(), key=lambda ref: (ref.entity_id, ref.kind.value, ref.revision))
    )
    return TodayQueue(
        items=tuple(sorted(items, key=today_item_sort_key)),
        input_revisions=input_revisions,
        generated_at=generated_at,
    )
