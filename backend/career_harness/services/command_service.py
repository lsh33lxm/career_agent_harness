from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from career_harness.core.commands import Command, require_expected_revision
from career_harness.core.common import EntityRef
from career_harness.core.revisions import CommandCommitResult, CurrentState
from career_harness.db.models import (
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    IdempotencyRecordRow,
    OutboxMessageRow,
)


class IdempotencyConflict(RuntimeError):
    pass


class TransactionalWrite(Protocol):
    def idempotency_payload(self) -> dict[str, Any]: ...

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None: ...


def _request_hash(
    command: Command,
    next_state: dict[str, Any],
    event_type: str,
    event_payload: dict[str, Any],
    outbox_destination: str | None,
    transactional_write: TransactionalWrite | None,
) -> str:
    value = {
        "command": command.model_dump(mode="json", exclude={"issued_at"}),
        "next_state": next_state,
        "event_type": event_type,
        "event_payload": event_payload,
        "outbox_destination": outbox_destination,
        "transactional_write": (
            transactional_write.idempotency_payload() if transactional_write else None
        ),
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class CommandService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, entity: EntityRef) -> CurrentState | None:
        with Session(self.engine) as session:
            current = session.get(EntityStateRow, entity.entity_id)
            if current is None:
                return None
            if current.entity_kind != entity.kind.value:
                raise ValueError("entity id exists with a different kind")
            return CurrentState(
                entity=entity,
                revision=current.revision,
                schema_version=current.schema_version,
                state=dict(current.state),
                updated_at=current.updated_at,
            )

    def commit(
        self,
        command: Command,
        next_state: dict[str, Any],
        *,
        event_type: str,
        event_payload: dict[str, Any] | None = None,
        outbox_destination: str | None = None,
        transactional_write: TransactionalWrite | None = None,
        session: Session | None = None,
    ) -> CommandCommitResult:
        if session is None:
            with Session(self.engine) as owned_session, owned_session.begin():
                return self._commit_in_session(
                    owned_session,
                    command,
                    next_state,
                    event_type=event_type,
                    event_payload=event_payload,
                    outbox_destination=outbox_destination,
                    transactional_write=transactional_write,
                )
        return self._commit_in_session(
            session,
            command,
            next_state,
            event_type=event_type,
            event_payload=event_payload,
            outbox_destination=outbox_destination,
            transactional_write=transactional_write,
        )

    def _commit_in_session(
        self,
        session: Session,
        command: Command,
        next_state: dict[str, Any],
        *,
        event_type: str,
        event_payload: dict[str, Any] | None,
        outbox_destination: str | None,
        transactional_write: TransactionalWrite | None,
    ) -> CommandCommitResult:
        domain_event_payload = event_payload or {}
        if "revision_id" in domain_event_payload:
            raise ValueError("event payload cannot override revision_id")
        request_hash = _request_hash(
            command,
            next_state,
            event_type,
            domain_event_payload,
            outbox_destination,
            transactional_write,
        )
        now = datetime.now(UTC)

        existing = session.get(IdempotencyRecordRow, command.idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise IdempotencyConflict("idempotency key was reused with different input")
            return CommandCommitResult.model_validate(existing.response)

        current = session.get(EntityStateRow, command.target.entity_id)
        actual_revision = current.revision if current is not None else 0
        require_expected_revision(expected=command.expected_revision, actual=actual_revision)
        new_revision = actual_revision + 1
        revision_id = f"revision_{uuid.uuid4().hex}"
        event_id = f"event_{uuid.uuid4().hex}"

        if current is None:
            current = EntityStateRow(
                entity_id=command.target.entity_id,
                entity_kind=command.target.kind.value,
                revision=new_revision,
                schema_version=1,
                state=next_state,
                updated_at=now,
            )
            session.add(current)
        else:
            current.revision = new_revision
            current.state = next_state
            current.updated_at = now

        # Explicit flushes preserve foreign-key order without coupling rows via
        # ORM relationships; every write still commits in this one transaction.
        session.flush()

        session.add(
            EntityRevisionRow(
                revision_id=revision_id,
                entity_id=command.target.entity_id,
                revision=new_revision,
                schema_version=1,
                state=next_state,
                created_at=now,
                created_by=command.actor,
            )
        )
        session.add(
            DomainEventRow(
                event_id=event_id,
                event_type=event_type,
                entity_id=command.target.entity_id,
                entity_revision=new_revision,
                command_id=command.command_id,
                payload={"revision_id": revision_id, **domain_event_payload},
                occurred_at=now,
            )
        )
        if transactional_write is not None:
            transactional_write.stage(
                session,
                entity_revision=new_revision,
                occurred_at=now,
            )
        if outbox_destination:
            session.flush()
            session.add(
                OutboxMessageRow(
                    message_id=f"outbox_{uuid.uuid4().hex}",
                    event_id=event_id,
                    destination=outbox_destination,
                    payload={"entity_id": command.target.entity_id, "revision": new_revision},
                    status="pending",
                    attempt_count=0,
                    created_at=now,
                )
            )

        result = CommandCommitResult(
            entity_id=command.target.entity_id,
            revision=new_revision,
            revision_id=revision_id,
            event_id=event_id,
        )
        session.add(
            IdempotencyRecordRow(
                idempotency_key=command.idempotency_key,
                command_id=command.command_id,
                request_hash=request_hash,
                response=result.model_dump(mode="json"),
                created_at=now,
            )
        )
        return result
