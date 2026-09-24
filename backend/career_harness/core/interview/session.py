from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId, utc_now


class InterviewSessionRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InterviewSessionEvent(FrozenModel):
    event_id: OpaqueId
    interview_id: OpaqueId
    session_id: OpaqueId
    sequence: int = Field(ge=1)
    role: InterviewSessionRole
    content: str = Field(min_length=1, max_length=20_000)
    source_refs: tuple[OpaqueId, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
