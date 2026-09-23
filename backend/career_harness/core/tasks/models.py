from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    FINALIZING = "finalizing"
    DEAD_LETTER = "dead_letter"


class TaskRecord(FrozenModel):
    task_id: OpaqueId
    task_type: str = Field(min_length=1, max_length=128)
    stage: str = Field(min_length=1, max_length=64)
    status: TaskStatus
    progress: float = Field(ge=0, le=1)
    payload: dict[str, Any]
    result: dict[str, Any] | None
    last_error: str | None
    current_attempt: int = Field(ge=0)
    max_attempts: int = Field(ge=1, le=20)
    version: int = Field(ge=1)
    available_at: datetime
    claimed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskLease(FrozenModel):
    task: TaskRecord
    version: int = Field(ge=1)
    attempt: int = Field(ge=1)


class TaskAttempt(FrozenModel):
    task_id: OpaqueId
    attempt: int = Field(ge=1)
    task_version: int = Field(ge=1)
    status: str = Field(pattern=r"^(completed|failed|cancelled|stale)$")
    error_type: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime
