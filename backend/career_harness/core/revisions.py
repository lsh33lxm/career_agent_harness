from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from career_harness.core.common import EntityRef, FrozenModel, OpaqueId, utc_now


class CurrentState(FrozenModel):
    entity: EntityRef
    revision: int = Field(ge=1)
    schema_version: int = Field(ge=1)
    state: dict[str, Any]
    updated_at: datetime = Field(default_factory=utc_now)


class ImmutableRevision(FrozenModel):
    revision_id: OpaqueId
    entity: EntityRef
    revision: int = Field(ge=1)
    schema_version: int = Field(ge=1)
    state: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(min_length=1, max_length=255)


class DomainEvent(FrozenModel):
    event_id: OpaqueId
    event_type: str = Field(min_length=1, max_length=128)
    entity: EntityRef
    entity_revision: int = Field(ge=1)
    command_id: OpaqueId
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utc_now)

