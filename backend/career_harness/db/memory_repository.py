from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.memory.models import (
    MemoryCreator,
    MemoryProposal,
    MemoryProposalStatus,
    MemoryRevision,
    MemoryScope,
    MemorySearchResult,
    MemoryType,
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class MemoryRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _event(
        connection: Any,
        event_type: str,
        entity_id: str,
        revision: int,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        connection.execute(
            text(
                "INSERT INTO domain_event "
                "(event_id,event_type,entity_id,entity_revision,command_id,payload,occurred_at) "
                "VALUES (:event_id,:event_type,:entity_id,:revision,:command_id,:payload,:now)"
            ),
            {
                "event_id": f"event_memory_{uuid.uuid4().hex}",
                "event_type": event_type,
                "entity_id": entity_id,
                "revision": revision,
                "command_id": f"memory_{uuid.uuid4().hex}",
                "payload": _json(payload),
                "now": now,
            },
        )

    def create_proposal(
        self,
        *,
        memory_type: MemoryType,
        scope_kind: MemoryScope,
        scope_id: str,
        content: str,
        source_type: str,
        source_locator: str,
        source_refs: tuple[str, ...] = (),
        confidence: float = 0.5,
        created_by: MemoryCreator = MemoryCreator.LLM,
        target_memory_id: str | None = None,
        base_revision: int | None = None,
        proposal_id: str | None = None,
    ) -> MemoryProposal:
        cleaned = content.strip()
        if not cleaned:
            raise ValueError("memory proposal content is required")
        if len(cleaned) > 10_000:
            raise ValueError("memory proposal content exceeds limit")
        if not scope_id.strip() or not source_locator.strip():
            raise ValueError("memory scope and source locator are required")
        proposal_id = proposal_id or f"memory_proposal_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            existing = connection.execute(
                text("SELECT * FROM memory_proposal WHERE proposal_id=:id"),
                {"id": proposal_id},
            ).mappings().first()
            if existing is not None:
                if (
                    existing["memory_type"] != memory_type.value
                    or existing["scope_kind"] != scope_kind.value
                    or existing["scope_id"] != scope_id
                    or existing["content"] != cleaned
                    or existing["source_type"] != source_type
                    or existing["source_locator"] != source_locator
                ):
                    raise ValueError("memory proposal id already exists with different content")
                return self._proposal(existing)
            if target_memory_id is not None:
                target = (
                    connection.execute(
                        text("SELECT * FROM memory_item WHERE memory_id=:id"),
                        {"id": target_memory_id},
                    )
                    .mappings()
                    .first()
                )
                if target is None or target["status"] == "tombstoned":
                    raise KeyError("memory proposal target is unavailable")
                if (
                    target["memory_type"] != memory_type.value
                    or target["scope_kind"] != scope_kind.value
                    or target["scope_id"] != scope_id
                ):
                    raise ValueError("memory proposal cannot change type or scope")
                if base_revision is None:
                    base_revision = int(target["current_revision"])
            connection.execute(
                text(
                    "INSERT INTO memory_proposal "
                    "(proposal_id,target_memory_id,base_revision,memory_type,scope_kind,scope_id,"
                    "content,content_sha256,source_type,source_locator,source_refs,confidence,"
                    "created_by,status,created_at) VALUES "
                    "(:proposal_id,:target,:base,:memory_type,:scope_kind,:scope_id,:content,"
                    ":hash,:source_type,:source_locator,:refs,:confidence,:created_by,'pending',:now)"
                ),
                {
                    "proposal_id": proposal_id,
                    "target": target_memory_id,
                    "base": base_revision,
                    "memory_type": memory_type.value,
                    "scope_kind": scope_kind.value,
                    "scope_id": scope_id,
                    "content": cleaned,
                    "hash": _hash(cleaned),
                    "source_type": source_type,
                    "source_locator": source_locator,
                    "refs": _json(list(source_refs)),
                    "confidence": confidence,
                    "created_by": created_by.value,
                    "now": now,
                },
            )
            self._event(
                connection,
                "memory.proposal.created",
                proposal_id,
                1,
                {"scope_kind": scope_kind.value, "scope_id": scope_id},
                now,
            )
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: str) -> MemoryProposal:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM memory_proposal WHERE proposal_id=:id"),
                    {"id": proposal_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError("memory proposal not found")
        return self._proposal(row)

    def list_proposals(
        self, *, scope_kind: MemoryScope, scope_id: str, status: MemoryProposalStatus
    ) -> tuple[MemoryProposal, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT * FROM memory_proposal WHERE scope_kind=:scope_kind "
                        "AND scope_id=:scope_id AND status=:status ORDER BY created_at DESC"
                    ),
                    {
                        "scope_kind": scope_kind.value,
                        "scope_id": scope_id,
                        "status": status.value,
                    },
                )
                .mappings()
                .all()
            )
        return tuple(self._proposal(row) for row in rows)

    def review_proposal(
        self,
        proposal_id: str,
        *,
        decision: MemoryProposalStatus,
        reason: str,
        edited_content: str | None = None,
        reviewer: str = "user",
    ) -> MemoryProposal:
        if reviewer != "user":
            raise ValueError("only the user may review memory proposals")
        if decision not in {MemoryProposalStatus.APPROVED, MemoryProposalStatus.REJECTED}:
            raise ValueError("memory review decision must approve or reject")
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM memory_proposal WHERE proposal_id=:id"),
                    {"id": proposal_id},
                )
                .mappings()
                .first()
            )
            if row is None:
                raise KeyError("memory proposal not found")
            if row["status"] != MemoryProposalStatus.PENDING.value:
                raise ValueError("memory proposal has already been reviewed")
            approved_content = (edited_content or row["content"]).strip()
            if not approved_content:
                raise ValueError("approved memory content is required")
            memory_id = row["target_memory_id"] or f"memory_{uuid.uuid4().hex}"
            revision = 1
            if decision is MemoryProposalStatus.APPROVED:
                target = (
                    connection.execute(
                        text("SELECT * FROM memory_item WHERE memory_id=:id"),
                        {"id": memory_id},
                    )
                    .mappings()
                    .first()
                )
                if target is not None:
                    if int(row["base_revision"] or 0) != int(target["current_revision"]):
                        raise RuntimeError("memory proposal base revision is stale")
                    revision = int(target["current_revision"]) + 1
                else:
                    connection.execute(
                        text(
                            "INSERT INTO memory_item "
                            "(memory_id,memory_type,scope_kind,scope_id,status,current_revision,"
                            "created_at,updated_at) VALUES "
                            "(:id,:memory_type,:scope_kind,:scope_id,'confirmed',1,:now,:now)"
                        ),
                        {
                            "id": memory_id,
                            "memory_type": row["memory_type"],
                            "scope_kind": row["scope_kind"],
                            "scope_id": row["scope_id"],
                            "now": now,
                        },
                    )
                connection.execute(
                    text(
                        "INSERT INTO memory_revision "
                        "(memory_id,revision,content,content_sha256,source_type,source_locator,"
                        "source_refs,confidence,created_by,confirmed_by,created_at) VALUES "
                        "(:id,:revision,:content,:hash,:source_type,:source_locator,:refs,"
                        ":confidence,:created_by,'user',:now)"
                    ),
                    {
                        "id": memory_id,
                        "revision": revision,
                        "content": approved_content,
                        "hash": _hash(approved_content),
                        "source_type": row["source_type"],
                        "source_locator": row["source_locator"],
                        "refs": row["source_refs"],
                        "confidence": row["confidence"],
                        "created_by": row["created_by"],
                        "now": now,
                    },
                )
                connection.execute(
                    text(
                        "UPDATE memory_item SET current_revision=:revision,status='confirmed',"
                        "updated_at=:now WHERE memory_id=:id"
                    ),
                    {"id": memory_id, "revision": revision, "now": now},
                )
                self._event(
                    connection,
                    "memory.confirmed",
                    memory_id,
                    revision,
                    {"proposal_id": proposal_id},
                    now,
                )
            connection.execute(
                text(
                    "UPDATE memory_proposal SET status=:status,reviewed_by=:reviewer,"
                    "review_reason=:reason,approved_content=:content,"
                    "approved_content_sha256=:hash,reviewed_at=:now WHERE proposal_id=:id"
                ),
                {
                    "status": decision.value,
                    "reviewer": reviewer,
                    "reason": reason,
                    "content": approved_content
                    if decision is MemoryProposalStatus.APPROVED
                    else None,
                    "hash": _hash(approved_content)
                    if decision is MemoryProposalStatus.APPROVED
                    else None,
                    "now": now,
                    "id": proposal_id,
                },
            )
            if decision is MemoryProposalStatus.REJECTED:
                self._event(
                    connection,
                    "memory.proposal.rejected",
                    proposal_id,
                    1,
                    {"reason": reason},
                    now,
                )
        return self.get_proposal(proposal_id)

    def search(
        self,
        *,
        scope_kind: MemoryScope,
        scope_id: str,
        query: str = "",
        limit: int = 50,
    ) -> tuple[MemorySearchResult, ...]:
        terms = tuple(term.casefold() for term in query.split() if term.strip())
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT i.*,r.revision,r.content,r.source_type,r.source_locator,"
                        "r.source_refs,"
                        "r.confidence,r.created_by,r.confirmed_by,"
                        "r.created_at AS revision_created_at "
                        "FROM memory_item i JOIN memory_revision r ON r.memory_id=i.memory_id "
                        "AND r.revision=i.current_revision WHERE i.scope_kind=:scope_kind "
                        "AND i.scope_id=:scope_id AND i.status='confirmed' "
                        "ORDER BY i.updated_at DESC"
                    ),
                    {"scope_kind": scope_kind.value, "scope_id": scope_id},
                )
                .mappings()
                .all()
            )
        results: list[MemorySearchResult] = []
        for row in rows:
            content = row["content"].casefold()
            if terms and not all(term in content for term in terms):
                continue
            relevance = (
                1.0
                if not terms
                else sum(content.count(term) for term in terms)
                / (len(terms) + sum(content.count(term) for term in terms))
            )
            results.append(MemorySearchResult(memory=self._revision(row), relevance=relevance))
        results.sort(key=lambda item: (-item.relevance, item.memory.memory_id))
        return tuple(results[:limit])

    def affinity(
        self,
        *,
        scope_kind: MemoryScope,
        scope_id: str,
        source_ref: str,
        limit: int = 50,
    ) -> tuple[MemorySearchResult, ...]:
        """Return confirmed memories explicitly citing one document/evidence ref."""
        if not source_ref.strip():
            raise ValueError("source_ref 不能为空")
        results = self.search(scope_kind=scope_kind, scope_id=scope_id, limit=limit)
        return tuple(item for item in results if source_ref in item.memory.source_refs)

    def propose_consolidation(
        self,
        *,
        scope_kind: MemoryScope,
        scope_id: str,
        memory_ids: tuple[str, ...],
        source_locator: str,
    ) -> MemoryProposal:
        """Create a review-gated consolidation proposal from confirmed memories."""
        if not memory_ids:
            raise ValueError("consolidation 至少需要一条记忆")
        indexed = {
            item.memory.memory_id: item.memory
            for item in self.search(scope_kind=scope_kind, scope_id=scope_id, limit=1000)
        }
        try:
            memories = tuple(indexed[memory_id] for memory_id in dict.fromkeys(memory_ids))
        except KeyError as error:
            raise KeyError("consolidation 只能引用已确认且未删除的记忆") from error
        if any(
            item.scope_kind is not scope_kind or item.scope_id != scope_id
            for item in memories
        ):
            raise ValueError("只能合并同一作用域内的记忆")
        content = "\n".join(f"- {item.content}" for item in memories)
        refs = tuple(dict.fromkeys(ref for item in memories for ref in item.source_refs))
        return self.create_proposal(
            memory_type=memories[0].memory_type,
            scope_kind=scope_kind,
            scope_id=scope_id,
            content=content,
            source_type="memory_consolidation",
            source_locator=source_locator,
            source_refs=refs,
            confidence=min(item.confidence for item in memories),
            created_by=MemoryCreator.RULE,
        )

    def tombstone(self, memory_id: str, *, reason: str, actor: str = "user") -> MemoryRevision:
        if actor != "user":
            raise ValueError("only the user may delete memory")
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            item = (
                connection.execute(
                    text("SELECT * FROM memory_item WHERE memory_id=:id"), {"id": memory_id}
                )
                .mappings()
                .first()
            )
            if item is None:
                raise KeyError("memory not found")
            if item["status"] == "tombstoned":
                raise ValueError("memory is already deleted")
            revision = int(item["current_revision"]) + 1
            connection.execute(
                text(
                    "INSERT INTO memory_revision "
                    "(memory_id,revision,content,content_sha256,source_type,source_locator,"
                    "source_refs,confidence,created_by,confirmed_by,created_at) VALUES "
                    "(:id,:revision,'[deleted]',:hash,'tombstone',:locator,'[]',"
                    "1,'USER','user',:now)"
                ),
                {
                    "id": memory_id,
                    "revision": revision,
                    "hash": _hash("[deleted]"),
                    "locator": f"reason:{reason[:256]}",
                    "now": now,
                },
            )
            connection.execute(
                text(
                    "UPDATE memory_item SET status='tombstoned',current_revision=:revision,"
                    "updated_at=:now WHERE memory_id=:id"
                ),
                {"id": memory_id, "revision": revision, "now": now},
            )
            self._event(
                connection,
                "memory.tombstoned",
                memory_id,
                revision,
                {"reason": reason},
                now,
            )
        return self.get_revision(memory_id, revision)

    def get_revision(self, memory_id: str, revision: int) -> MemoryRevision:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT i.*,r.revision,r.content,r.source_type,r.source_locator,"
                        "r.source_refs,"
                        "r.confidence,r.created_by,r.confirmed_by,"
                        "r.created_at AS revision_created_at "
                        "FROM memory_item i JOIN memory_revision r ON r.memory_id=i.memory_id "
                        "WHERE i.memory_id=:id AND r.revision=:revision"
                    ),
                    {"id": memory_id, "revision": revision},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError("memory revision not found")
        return self._revision(
            row, status_override="tombstoned" if row["source_type"] == "tombstone" else "confirmed"
        )

    @staticmethod
    def _proposal(row: Any) -> MemoryProposal:
        return MemoryProposal(
            proposal_id=row["proposal_id"],
            target_memory_id=row["target_memory_id"],
            base_revision=row["base_revision"],
            memory_type=MemoryType(row["memory_type"]),
            scope_kind=MemoryScope(row["scope_kind"]),
            scope_id=row["scope_id"],
            content=row["content"],
            source_type=row["source_type"],
            source_locator=row["source_locator"],
            source_refs=tuple(_loads(row["source_refs"])),
            confidence=row["confidence"],
            created_by=MemoryCreator(row["created_by"]),
            status=MemoryProposalStatus(row["status"]),
            reviewed_by=row["reviewed_by"],
            review_reason=row["review_reason"],
            approved_content=row["approved_content"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
        )

    @staticmethod
    def _revision(row: Any, status_override: str | None = None) -> MemoryRevision:
        return MemoryRevision(
            memory_id=row["memory_id"],
            revision=row["current_revision"] if "revision" not in row else row["revision"],
            memory_type=MemoryType(row["memory_type"]),
            scope_kind=MemoryScope(row["scope_kind"]),
            scope_id=row["scope_id"],
            status=status_override or row["status"],
            content=row["content"],
            source_type=row["source_type"],
            source_locator=row["source_locator"],
            source_refs=tuple(_loads(row["source_refs"])),
            confidence=row["confidence"],
            created_by=MemoryCreator(row["created_by"]),
            confirmed_by=row["confirmed_by"],
            created_at=row["revision_created_at"],
        )
