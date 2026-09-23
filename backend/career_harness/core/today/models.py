"""Core-owned Today read model (contract 0.8.0, D-017).

Today is a deterministic projection, not a canonical entity: computing it never
writes anything, never mutates source state and never changes UserPriority.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.opportunity import PriorityLevel

TODAY_POLICY_VERSION = "today-policy-v1"

TodayItemId = Annotated[
    str,
    Field(min_length=1, max_length=192, pattern=r"^today:[a-z_]+:[a-z][a-z0-9_-]+$"),
]


class TodayItemKind(StrEnum):
    """Closed item-kind set for v1; new kinds require a contract change."""

    OPPORTUNITY_ACTION = "opportunity_action"
    APPLICATION_STEP = "application_step"
    INTERVIEW_PREP = "interview_prep"
    ENHANCEMENT_TASK = "enhancement_task"
    REVIEW_REQUEST = "review_request"


class TodayReasonCode(StrEnum):
    USER_PRIORITY_URGENT = "user_priority_urgent"
    USER_PRIORITY_HIGH = "user_priority_high"
    USER_PRIORITY_MEDIUM = "user_priority_medium"
    USER_PRIORITY_LOW = "user_priority_low"
    SUGGESTED_PRIORITY_URGENT = "suggested_priority_urgent"
    SUGGESTED_PRIORITY_HIGH = "suggested_priority_high"
    SUGGESTED_PRIORITY_MEDIUM = "suggested_priority_medium"
    SUGGESTED_PRIORITY_LOW = "suggested_priority_low"
    MISSING_USER_PRIORITY = "missing_user_priority"
    MISSING_SUGGESTED_PRIORITY = "missing_suggested_priority"
    DEADLINE_APPROACHING = "deadline_approaching"
    INTERVIEW_UPCOMING = "interview_upcoming"
    OPPORTUNITY_ACTIVE = "opportunity_active"
    APPLICATION_STEP_PENDING = "application_step_pending"
    INTERVIEW_PREP_DUE = "interview_prep_due"
    GAP_LINKED_TASK = "gap_linked_task"
    PENDING_USER_REVIEW = "pending_user_review"


class TodaySourceRef(FrozenModel):
    """An exact source entity plus revision used to compute the queue."""

    entity_id: OpaqueId
    kind: EntityKind
    revision: int = Field(ge=1)


class TodayReason(FrozenModel):
    code: TodayReasonCode
    explanation: str = Field(min_length=1, max_length=512)


def today_item_id(kind: TodayItemKind, entity_id: str) -> str:
    """Stable deterministic item ID derived from the kind and source entity ID."""

    return f"today:{kind.value}:{entity_id}"


def _aware(value: datetime | None) -> datetime | None:
    # SQLite returns naive datetimes; Today compares them, so normalize to UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class TodayItem(FrozenModel):
    item_id: TodayItemId
    kind: TodayItemKind
    source_refs: tuple[TodaySourceRef, ...] = Field(min_length=1)
    reasons: tuple[TodayReason, ...] = Field(min_length=1)
    user_priority: PriorityLevel | None = None
    suggested_priority: PriorityLevel | None = None
    deadline_at: datetime | None = None
    interview_at: datetime | None = None

    @field_validator("deadline_at", "interview_at")
    @classmethod
    def times_are_utc_aware(cls, value: datetime | None) -> datetime | None:
        return _aware(value)

    @model_validator(mode="after")
    def item_id_matches_kind_and_source(self) -> TodayItem:
        if self.item_id != today_item_id(self.kind, self.source_refs[0].entity_id):
            raise ValueError("today item id must derive from its kind and primary source entity")
        return self


_PRIORITY_ORDER: dict[PriorityLevel, int] = {
    PriorityLevel.URGENT: 0,
    PriorityLevel.HIGH: 1,
    PriorityLevel.MEDIUM: 2,
    PriorityLevel.LOW: 3,
}
MISSING_PRIORITY_RANK = len(_PRIORITY_ORDER)
_FAR_FUTURE = datetime.max.replace(tzinfo=UTC)


def _priority_rank(level: PriorityLevel | None) -> int:
    if level is None:
        return MISSING_PRIORITY_RANK
    return _PRIORITY_ORDER[level]


def today_item_sort_key(item: TodayItem) -> tuple[int, int, bool, datetime, str]:
    """Contract 0.8.0 total order.

    User priority rank first, then suggested priority rank, then earliest
    deadline/interview time (missing times sort last within their bucket),
    then the stable item ID as the final tiebreaker.
    """

    timed = [value for value in (item.deadline_at, item.interview_at) if value is not None]
    earliest = min(timed) if timed else None
    return (
        _priority_rank(item.user_priority),
        _priority_rank(item.suggested_priority),
        earliest is None,
        earliest if earliest is not None else _FAR_FUTURE,
        item.item_id,
    )


class TodayQueue(FrozenModel):
    items: tuple[TodayItem, ...] = ()
    input_revisions: tuple[TodaySourceRef, ...] = ()
    generated_at: datetime
    policy_version: str = TODAY_POLICY_VERSION

    @field_validator("generated_at")
    @classmethod
    def generated_at_is_utc_aware(cls, value: datetime) -> datetime:
        aware = _aware(value)
        if aware is None:  # generated_at is required.
            raise ValueError("generated_at is required")
        return aware

    @model_validator(mode="after")
    def queue_is_canonical(self) -> TodayQueue:
        item_ids = [item.item_id for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("today items must have unique item ids")
        keys = [today_item_sort_key(item) for item in self.items]
        if keys != sorted(keys):
            raise ValueError("today items must follow the contract total order")
        refs = [(ref.entity_id, ref.kind, ref.revision) for ref in self.input_revisions]
        if len(set(refs)) != len(refs):
            raise ValueError("today input revisions must be unique")
        return self
