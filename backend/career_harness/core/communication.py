from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId, utc_now


class CommunicationChannel(StrEnum):
    EMAIL = "email"
    PLATFORM_MESSAGE = "platform_message"
    FOLLOW_UP_NOTE = "follow_up_note"


class CommunicationStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    REPLIED = "replied"
    FOLLOW_UP = "follow_up"
    CLOSED = "closed"
    BLOCKED = "blocked"


class CommunicationDraft(FrozenModel):
    draft_id: OpaqueId
    opportunity_id: OpaqueId
    source_staging_id: OpaqueId | None = None
    channel: CommunicationChannel
    recipient: str | None = Field(default=None, max_length=512)
    body: str = Field(min_length=1, max_length=10000)
    status: CommunicationStatus = CommunicationStatus.PENDING_REVIEW
    provenance: dict[str, str] = Field(default_factory=dict)
    created_by: str = Field(min_length=1, max_length=255)
    reviewed_by: str | None = None
    review_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    reviewed_at: datetime | None = None
