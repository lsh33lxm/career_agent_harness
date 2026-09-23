from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from career_harness.core.common import EntityRef, FrozenModel, OpaqueId, utc_now


class Command(FrozenModel):
    command_id: OpaqueId
    command_type: str = Field(min_length=1, max_length=128)
    target: EntityRef
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=255)
    actor: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime = Field(default_factory=utc_now)

    @field_validator("payload")
    @classmethod
    def payload_must_not_contain_approval_actor(cls, value: dict[str, Any]) -> dict[str, Any]:
        if "approved_by_agent" in value:
            raise ValueError("agents cannot approve their own output")
        return value


class RevisionConflict(RuntimeError):
    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"expected revision {expected}, found {actual}")
        self.expected = expected
        self.actual = actual


def require_expected_revision(*, expected: int, actual: int) -> None:
    if expected != actual:
        raise RevisionConflict(expected, actual)
