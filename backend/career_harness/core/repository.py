from __future__ import annotations

from typing import Any, Protocol

from career_harness.core.commands import Command
from career_harness.core.common import EntityRef
from career_harness.core.revisions import CommandCommitResult, CurrentState


class RevisionRepository(Protocol):
    def get(self, entity: EntityRef) -> CurrentState | None: ...

    def commit(
        self,
        command: Command,
        next_state: dict[str, Any],
        *,
        event_type: str,
        event_payload: dict[str, Any] | None = None,
        outbox_destination: str | None = None,
    ) -> CommandCommitResult: ...

