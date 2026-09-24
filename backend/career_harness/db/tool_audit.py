from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from career_harness.core.tools.registry import (
    ToolCallContext,
    ToolDefinition,
    ToolFailureCategory,
)


class DatabaseToolAuditSink:
    """Persist bounded metadata only; arguments, outputs and credentials are excluded."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def record(
        self,
        *,
        definition: ToolDefinition,
        context: ToolCallContext,
        status: str,
        failure_category: ToolFailureCategory | None,
    ) -> None:
        now = datetime.now(UTC)
        call_id = f"tool_call_{uuid.uuid4().hex}"
        payload = {
            "tool_name": definition.name,
            "tool_source": definition.source,
            "tool_version": definition.version,
            "principal_id": context.principal_id,
            "scope_kind": context.scope.kind.value,
            "scope_id": context.scope.scope_id,
            "status": status,
            "failure_category": failure_category.value if failure_category else None,
            "approval_present": context.approval_id is not None,
        }
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO domain_event "
                    "(event_id,event_type,entity_id,entity_revision,command_id,payload,"
                    "occurred_at) "
                    "VALUES (:event,:type,:entity,1,:command,:payload,:now)"
                ),
                {
                    "event": f"event_{call_id}",
                    "type": f"tool.call.{status}",
                    "entity": call_id,
                    "command": call_id,
                    "payload": json.dumps(
                        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ),
                    "now": now,
                },
            )
