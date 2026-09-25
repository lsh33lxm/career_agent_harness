from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from career_harness.core.common import FrozenModel, OpaqueId


class ConnectorStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class SyncMode(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"


class ConflictPolicy(StrEnum):
    SOURCE_WINS = "source_wins"
    LOCAL_WINS = "local_wins"
    DEFER = "defer"


class DeletePolicy(StrEnum):
    KEEP = "keep"
    MARK_DELETED = "mark_deleted"


class SourceConnector(FrozenModel):
    connector_id: OpaqueId
    connector_type: str
    display_name: str
    status: ConnectorStatus
    config: dict[str, Any]
    auth_schema: dict[str, Any]
    sync_cursor: dict[str, Any] | None
    conflict_policy: ConflictPolicy
    delete_policy: DeletePolicy
    created_at: datetime
    updated_at: datetime


class SyncStats(FrozenModel):
    created: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    deleted: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)


class SyncRun(FrozenModel):
    sync_run_id: OpaqueId
    connector_id: OpaqueId
    mode: SyncMode
    status: str = Field(pattern=r"^(processing|completed|failed)$")
    cursor_before: dict[str, Any] | None
    cursor_after: dict[str, Any] | None
    stats: SyncStats
    error: str | None
    started_at: datetime
    finished_at: datetime | None
