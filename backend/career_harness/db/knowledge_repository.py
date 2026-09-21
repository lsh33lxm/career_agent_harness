from __future__ import annotations

import difflib
import hashlib
import io
import json
import re
import uuid
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile

from sqlalchemy import Engine, text

from career_harness.core.evidence.models import ArtifactClass
from career_harness.core.knowledge.models import (
    KnowledgeAuthority,
    KnowledgeCategory,
    KnowledgeCitation,
    KnowledgeCreatedBy,
    KnowledgeEntry,
    KnowledgeLink,
    KnowledgeProposal,
    KnowledgeRevision,
    KnowledgeSearchPage,
    KnowledgeSearchResult,
    KnowledgeStatus,
    ProposalStatus,
)
from career_harness.storage import ArtifactStore

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_CONTENT_CHARS = 1_000_000
MAX_CHUNK_CHARS = 800
_INJECTION_PATTERN = re.compile(
    r"(?i)\b(ignore\s+(?:all\s+)?previous|system\s+prompt|developer\s+message|"
    r"reveal\s+instructions|do\s+not\s+follow)\b"
)


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _parse_document(content: bytes, media_type: str, locator: str) -> str:
    suffix = PurePosixPath(locator.split("?", 1)[0]).suffix.lower()
    normalized = media_type.lower()
    if normalized in {"text/html", "application/xhtml+xml"} or suffix in {".html", ".htm"}:
        parser = _TextParser()
        parser.feed(content.decode("utf-8", errors="replace"))
        return "\n".join(parser.parts)
    if (
        normalized
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or suffix == ".docx"
    ):
        try:
            with ZipFile(io.BytesIO(content)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
        except (BadZipFile, KeyError) as exc:
            raise ValueError("DOCX artifact is not a readable document") from exc
        return re.sub(r"<[^>]+>", " ", xml).replace("&amp;", "&").replace("&lt;", "<")
    if normalized == "application/pdf" or suffix == ".pdf":
        decoded = content.decode("latin-1", errors="ignore")
        strings = re.findall(r"\(([^()]*)\)", decoded)
        return "\n".join(strings) or re.sub(r"[^\x09\x0a\x0d\x20-\x7e]", " ", decoded)
    return content.decode("utf-8", errors="replace")


def _clean_content(content: str) -> str:
    cleaned = content.replace("\x00", "").strip()
    if not cleaned:
        raise ValueError("knowledge document contains no readable text")
    if len(cleaned) > MAX_CONTENT_CHARS:
        raise ValueError("knowledge document exceeds text limit")
    return cleaned


def _prompt_injection_flag(content: str) -> bool:
    return bool(_INJECTION_PATTERN.search(content))


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _chunks(content: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    result: list[str] = []
    for paragraph in paragraphs:
        for offset in range(0, len(paragraph), MAX_CHUNK_CHARS):
            result.append(paragraph[offset : offset + MAX_CHUNK_CHARS])
    return result or [content[:MAX_CHUNK_CHARS]]


def _provenance_ids(content: bytes, source_type: str, source_locator: str) -> dict[str, str]:
    key = _hash_text(
        source_type + "\n" + source_locator + "\n" + hashlib.sha256(content).hexdigest()
    )
    digest = hashlib.sha256(content).hexdigest()
    return {
        "artifact_id": f"artifact_knowledge_{digest[:32]}",
        "source_id": f"source_knowledge_{_hash_text(source_locator)[:32]}",
        "snapshot_id": f"snapshot_knowledge_{key[:32]}",
        "evidence_ref_id": f"evidence_knowledge_{key[:32]}",
    }


class KnowledgeRepository:
    def __init__(self, engine: Engine, artifact_store: ArtifactStore) -> None:
        self.engine = engine
        self.artifact_store = artifact_store

    def import_document(
        self,
        *,
        content: bytes,
        media_type: str,
        source_type: str,
        source_locator: str,
        category: KnowledgeCategory,
        title: str,
        authority: KnowledgeAuthority,
        created_by: KnowledgeCreatedBy = KnowledgeCreatedBy.IMPORTER,
        labels: tuple[str, ...] = (),
        confidence: float = 1.0,
    ) -> KnowledgeRevision:
        if len(content) > MAX_IMPORT_BYTES:
            raise ValueError("knowledge artifact exceeds byte limit")
        text_content = _clean_content(_parse_document(content, media_type, source_locator))
        content_hash = _hash_text(text_content)
        ids = _provenance_ids(content, source_type, source_locator)
        knowledge_id = f"knowledge_{_hash_text(source_type + source_locator + content_hash)[:32]}"
        now = datetime.now(UTC)
        stored = self.artifact_store.put(content, ArtifactClass.PERSONAL)
        flagged = _prompt_injection_flag(text_content)
        with self.engine.begin() as connection:
            existing = connection.execute(
                text(
                    "SELECT knowledge_id, current_revision FROM knowledge_entry "
                    "WHERE knowledge_id=:knowledge_id"
                ),
                {"knowledge_id": knowledge_id},
            ).mappings().first()
            if existing is not None:
                return self.get_revision(knowledge_id, int(existing["current_revision"]))
            self._ensure_evidence(
                connection,
                content=content,
                media_type=media_type,
                source_type=source_type,
                source_locator=source_locator,
                ids=ids,
                now=now,
            )
            connection.execute(
                text(
                    "INSERT INTO knowledge_entry "
                    "(knowledge_id, category, title, status, authority, created_by, "
                    "current_revision, labels, created_at, updated_at) VALUES "
                    "(:knowledge_id, :category, :title, 'proposed', :authority, "
                    ":created_by, 1, :labels, :now, :now)"
                ),
                {
                    "knowledge_id": knowledge_id,
                    "category": category.value,
                    "title": title,
                    "authority": authority.value,
                    "created_by": created_by.value,
                    "labels": _json(list(labels)),
                    "now": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO knowledge_revision "
                    "(knowledge_id, revision, title, content, content_sha256, source_type, "
                    "source_locator, artifact_id, evidence_refs, authority, confidence, "
                    "created_by, status, prompt_injection_flag, created_at) VALUES "
                    "(:knowledge_id, 1, :title, :content, :content_sha256, :source_type, "
                    ":source_locator, :artifact_id, :evidence_refs, :authority, :confidence, "
                    ":created_by, 'proposed', :prompt_injection_flag, :now)"
                ),
                {
                    "knowledge_id": knowledge_id,
                    "title": title,
                    "content": text_content,
                    "content_sha256": content_hash,
                    "source_type": source_type,
                    "source_locator": source_locator,
                    "artifact_id": stored.sha256 and ids["artifact_id"],
                    "evidence_refs": _json([ids["evidence_ref_id"]]),
                    "authority": authority.value,
                    "confidence": confidence,
                    "created_by": created_by.value,
                    "prompt_injection_flag": flagged,
                    "now": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO knowledge_revision_evidence_ref "
                    "(knowledge_id, revision, ordinal, evidence_ref_id) "
                    "VALUES (:knowledge_id, 1, 0, :evidence_ref_id)"
                ),
                {"knowledge_id": knowledge_id, "evidence_ref_id": ids["evidence_ref_id"]},
            )
            self._replace_chunks(connection, knowledge_id, 1, text_content)
            self._event(
                connection,
                action="knowledge.import",
                entity_id=knowledge_id,
                payload={
                    "source_type": source_type,
                    "source_locator": source_locator,
                    "artifact_id": ids["artifact_id"],
                    "prompt_injection_flag": flagged,
                },
                now=now,
            )
        return self.get_revision(knowledge_id, 1)

    @staticmethod
    def _ensure_evidence(
        connection: Any,
        *,
        content: bytes,
        media_type: str,
        source_type: str,
        source_locator: str,
        ids: dict[str, str],
        now: datetime,
    ) -> None:
        digest = hashlib.sha256(content).hexdigest()
        connection.execute(
            text(
                "INSERT OR IGNORE INTO evidence_artifact "
                "(artifact_id, sha256, media_type, artifact_class, byte_length) "
                "VALUES (:artifact_id, :sha256, :media_type, 'personal', :byte_length)"
            ),
            {
                "artifact_id": ids["artifact_id"],
                "sha256": digest,
                "media_type": media_type,
                "byte_length": len(content),
            },
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO evidence_source "
                "(source_id, source_type, locator) VALUES (:source_id, :source_type, :locator)"
            ),
            {
                "source_id": ids["source_id"],
                "source_type": source_type,
                "locator": source_locator,
            },
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO source_snapshot "
                "(snapshot_id, source_id, captured_at, artifact_id) "
                "VALUES (:snapshot_id, :source_id, :captured_at, :artifact_id)"
            ),
            {
                "snapshot_id": ids["snapshot_id"],
                "source_id": ids["source_id"],
                "captured_at": now,
                "artifact_id": ids["artifact_id"],
            },
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO evidence_ref "
                "(evidence_ref_id, snapshot_id, artifact_id, selector) "
                "VALUES (:evidence_ref_id, :snapshot_id, :artifact_id, NULL)"
            ),
            {
                "evidence_ref_id": ids["evidence_ref_id"],
                "snapshot_id": ids["snapshot_id"],
                "artifact_id": ids["artifact_id"],
            },
        )

    @staticmethod
    def _replace_chunks(connection: Any, knowledge_id: str, revision: int, content: str) -> None:
        connection.execute(
            text(
                "DELETE FROM knowledge_chunk "
                "WHERE knowledge_id=:knowledge_id AND revision=:revision"
            ),
            {"knowledge_id": knowledge_id, "revision": revision},
        )
        for ordinal, chunk in enumerate(_chunks(content)):
            connection.execute(
                text(
                    "INSERT INTO knowledge_chunk "
                    "(chunk_id, knowledge_id, revision, ordinal, text, text_sha256, token_count) "
                    "VALUES (:chunk_id, :knowledge_id, :revision, :ordinal, :text, "
                    ":text_sha256, :token_count)"
                ),
                {
                    "chunk_id": f"chunk_{uuid.uuid4().hex}",
                    "knowledge_id": knowledge_id,
                    "revision": revision,
                    "ordinal": ordinal,
                    "text": chunk,
                    "text_sha256": _hash_text(chunk),
                    "token_count": len(chunk.split()),
                },
            )

    @staticmethod
    def _event(
        connection: Any,
        *,
        action: str,
        entity_id: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        connection.execute(
            text(
                "INSERT INTO domain_event "
                "(event_id, event_type, entity_id, entity_revision, command_id, "
                "payload, occurred_at) "
                "VALUES (:event_id, :event_type, :entity_id, :revision, :command_id, "
                ":payload, :occurred_at)"
            ),
            {
                "event_id": f"event_knowledge_{uuid.uuid4().hex}",
                "event_type": action,
                "entity_id": entity_id,
                "revision": int(payload.get("revision", 1)),
                "command_id": f"knowledge_{action.replace('.', '_')}_{uuid.uuid4().hex}",
                "payload": _json(payload),
                "occurred_at": now,
            },
        )

    def get_entry(self, knowledge_id: str) -> KnowledgeEntry | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM knowledge_entry WHERE knowledge_id=:knowledge_id"),
                {"knowledge_id": knowledge_id},
            ).mappings().first()
        return self._entry(row) if row else None

    def get_revision(self, knowledge_id: str, revision: int) -> KnowledgeRevision:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT * FROM knowledge_revision "
                    "WHERE knowledge_id=:knowledge_id AND revision=:revision"
                ),
                {"knowledge_id": knowledge_id, "revision": revision},
            ).mappings().first()
            if row is None:
                raise KeyError("knowledge revision not found")
            refs = connection.execute(
                text(
                    "SELECT evidence_ref_id FROM knowledge_revision_evidence_ref "
                    "WHERE knowledge_id=:knowledge_id AND revision=:revision ORDER BY ordinal"
                ),
                {"knowledge_id": knowledge_id, "revision": revision},
            ).scalars().all()
        return self._revision(row, tuple(refs))

    def list_revisions(self, knowledge_id: str) -> tuple[KnowledgeRevision, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM knowledge_revision WHERE knowledge_id=:knowledge_id "
                    "ORDER BY revision"
                ),
                {"knowledge_id": knowledge_id},
            ).mappings().all()
            result = []
            for row in rows:
                refs = tuple(
                    connection.execute(
                        text(
                            "SELECT evidence_ref_id FROM knowledge_revision_evidence_ref "
                            "WHERE knowledge_id=:knowledge_id AND revision=:revision "
                            "ORDER BY ordinal"
                        ),
                        {
                            "knowledge_id": knowledge_id,
                            "revision": row["revision"],
                        },
                    ).scalars().all()
                )
                result.append(self._revision(row, refs))
        return tuple(result)

    def search(
        self,
        *,
        query: str,
        categories: tuple[KnowledgeCategory, ...] = (),
        statuses: tuple[KnowledgeStatus, ...] = (
            KnowledgeStatus.APPROVED,
            KnowledgeStatus.PROPOSED,
        ),
        limit: int = 20,
        after: str | None = None,
    ) -> KnowledgeSearchPage:
        if not 1 <= limit <= 100:
            raise ValueError("knowledge page limit must be between 1 and 100")
        terms = tuple(term.lower() for term in re.findall(r"\w+", query.lower()))
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT e.*, r.title AS revision_title, r.content, r.content_sha256, "
                    "r.source_type, r.source_locator, r.artifact_id AS revision_artifact_id, "
                    "r.evidence_refs AS revision_evidence_refs, r.authority AS revision_authority, "
                    "r.confidence, r.created_by AS revision_created_by, "
                    "r.status AS revision_status, "
                    "r.prompt_injection_flag, r.created_at AS revision_created_at "
                    "FROM knowledge_entry e JOIN knowledge_revision r "
                    "ON r.knowledge_id=e.knowledge_id AND r.revision=e.current_revision "
                    "WHERE e.status IN ('approved', 'proposed') "
                    "ORDER BY e.knowledge_id"
                )
            ).mappings().all()
            results: list[KnowledgeSearchResult] = []
            for row in rows:
                if categories and row["category"] not in {item.value for item in categories}:
                    continue
                if statuses and row["status"] not in {item.value for item in statuses}:
                    continue
                if after is not None and row["knowledge_id"] <= after:
                    continue
                content = str(row["content"])
                haystack = f"{row['title']} {content}".lower()
                score = float(sum(haystack.count(term) for term in terms))
                if terms and score == 0:
                    continue
                refs = tuple(
                    connection.execute(
                        text(
                            "SELECT evidence_ref_id FROM knowledge_revision_evidence_ref "
                            "WHERE knowledge_id=:knowledge_id AND revision=:revision "
                            "ORDER BY ordinal"
                        ),
                        {
                            "knowledge_id": row["knowledge_id"],
                            "revision": row["current_revision"],
                        },
                    ).scalars().all()
                )
                if not refs:
                    refs = tuple(_loads(row["revision_evidence_refs"], []))
                self._assert_evidence_refs(connection, refs)
                results.append(
                    KnowledgeSearchResult(
                        knowledge_id=row["knowledge_id"],
                        revision=row["current_revision"],
                        title=row["revision_title"],
                        snippet=self._snippet(content, terms),
                        score=score,
                        category=KnowledgeCategory(row["category"]),
                        status=KnowledgeStatus(row["status"]),
                        citation=KnowledgeCitation(
                            knowledge_id=row["knowledge_id"],
                            revision=row["current_revision"],
                            evidence_refs=refs,
                            source_type=row["source_type"],
                            source_locator=row["source_locator"],
                            authority=KnowledgeAuthority(row["revision_authority"]),
                        ),
                    )
                )
        results.sort(key=lambda item: (-item.score, item.knowledge_id))
        page = results[:limit]
        return KnowledgeSearchPage(
            items=tuple(page),
            query=query,
            evidence_sufficient=bool(page),
            message=(
                None
                if page
                else "evidence insufficient: no matching approved/proposed knowledge"
            ),
            next_cursor=page[-1].knowledge_id if len(results) > limit else None,
        )

    def search_for_plugin(
        self, query: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        options = options or {}
        page = self.search(
            query=query,
            limit=int(options.get("limit", 20)),
            after=options.get("after"),
        )
        return page.model_dump(mode="json")

    @staticmethod
    def _snippet(content: str, terms: tuple[str, ...]) -> str:
        if not terms:
            return content[:240]
        lower = content.lower()
        positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
        start = max(0, min(positions, default=0) - 80)
        return content[start : start + 320]

    @staticmethod
    def _assert_evidence_refs(connection: Any, refs: tuple[str, ...]) -> None:
        for evidence_ref in refs:
            exists = connection.execute(
                text("SELECT 1 FROM evidence_ref WHERE evidence_ref_id=:evidence_ref"),
                {"evidence_ref": evidence_ref},
            ).first()
            if exists is None:
                raise RuntimeError(f"dangling knowledge evidence reference: {evidence_ref}")

    def create_proposal(
        self,
        *,
        category: KnowledgeCategory,
        title: str,
        content: str,
        authority: KnowledgeAuthority,
        created_by: KnowledgeCreatedBy,
        evidence_refs: tuple[str, ...] = (),
        target_knowledge_id: str | None = None,
        base_revision: int | None = None,
    ) -> KnowledgeProposal:
        text_content = _clean_content(content)
        proposal_id = f"proposal_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            if target_knowledge_id is not None:
                target = connection.execute(
                    text("SELECT current_revision FROM knowledge_entry WHERE knowledge_id=:id"),
                    {"id": target_knowledge_id},
                ).first()
                if target is None:
                    raise KeyError("proposal target knowledge does not exist")
                if base_revision is None:
                    base_revision = int(target[0])
            self._assert_evidence_refs(connection, evidence_refs)
            connection.execute(
                text(
                    "INSERT INTO knowledge_proposal "
                    "(proposal_id, target_knowledge_id, base_revision, category, title, "
                    "proposed_content, content_sha256, evidence_refs, authority, created_by, "
                    "status, created_at) VALUES "
                    "(:proposal_id, :target_knowledge_id, :base_revision, :category, :title, "
                    ":content, :content_sha256, :evidence_refs, :authority, :created_by, "
                    "'pending', :created_at)"
                ),
                {
                    "proposal_id": proposal_id,
                    "target_knowledge_id": target_knowledge_id,
                    "base_revision": base_revision,
                    "category": category.value,
                    "title": title,
                    "content": text_content,
                    "content_sha256": _hash_text(text_content),
                    "evidence_refs": _json(list(evidence_refs)),
                    "authority": authority.value,
                    "created_by": created_by.value,
                    "created_at": now,
                },
            )
            self._event(
                connection,
                action="knowledge.proposal.created",
                entity_id=proposal_id,
                payload={"target_knowledge_id": target_knowledge_id},
                now=now,
            )
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: str) -> KnowledgeProposal:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM knowledge_proposal WHERE proposal_id=:proposal_id"),
                {"proposal_id": proposal_id},
            ).mappings().first()
        if row is None:
            raise KeyError("knowledge proposal not found")
        return self._proposal(row)

    def review_proposal(
        self,
        proposal_id: str,
        *,
        decision: ProposalStatus,
        reviewer: str,
        reason: str,
    ) -> KnowledgeProposal:
        if decision not in {ProposalStatus.APPROVED, ProposalStatus.REJECTED}:
            raise ValueError("review decision must be approved or rejected")
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            row = connection.execute(
                text("SELECT * FROM knowledge_proposal WHERE proposal_id=:proposal_id"),
                {"proposal_id": proposal_id},
            ).mappings().first()
            if row is None:
                raise KeyError("knowledge proposal not found")
            if row["status"] != ProposalStatus.PENDING.value:
                raise ValueError("knowledge proposal has already been reviewed")
            if decision is ProposalStatus.APPROVED:
                target_id = row["target_knowledge_id"] or f"knowledge_{proposal_id[9:]}"
                target = connection.execute(
                    text("SELECT current_revision FROM knowledge_entry WHERE knowledge_id=:id"),
                    {"id": target_id},
                ).first()
                revision = int(target[0]) + 1 if target else 1
                if target is None:
                    connection.execute(
                        text(
                            "INSERT INTO knowledge_entry "
                            "(knowledge_id, category, title, status, authority, created_by, "
                            "current_revision, labels, created_at, updated_at) VALUES "
                            "(:id, :category, :title, 'approved', :authority, :created_by, "
                            ":revision, '[]', :now, :now)"
                        ),
                        {
                            "id": target_id,
                            "category": row["category"],
                            "title": row["title"],
                            "authority": row["authority"],
                            "created_by": row["created_by"],
                            "revision": revision,
                            "now": now,
                        },
                    )
                else:
                    connection.execute(
                        text(
                            "UPDATE knowledge_entry SET current_revision=:revision, "
                            "status='approved', updated_at=:now WHERE knowledge_id=:id"
                        ),
                        {"revision": revision, "now": now, "id": target_id},
                    )
                refs = tuple(_loads(row["evidence_refs"], []))
                self._assert_evidence_refs(connection, refs)
                connection.execute(
                    text(
                        "INSERT INTO knowledge_revision "
                        "(knowledge_id, revision, title, content, content_sha256, source_type, "
                        "source_locator, artifact_id, evidence_refs, authority, confidence, "
                        "created_by, status, prompt_injection_flag, created_at) VALUES "
                        "(:id, :revision, :title, :content, :hash, 'proposal', :locator, NULL, "
                        ":refs, :authority, 1, :created_by, 'approved', 0, :now)"
                    ),
                    {
                        "id": target_id,
                        "revision": revision,
                        "title": row["title"],
                        "content": row["proposed_content"],
                        "hash": row["content_sha256"],
                        "locator": f"proposal:{proposal_id}",
                        "refs": _json(list(refs)),
                        "authority": row["authority"],
                        "created_by": row["created_by"],
                        "now": now,
                    },
                )
                for ordinal, evidence_ref in enumerate(refs):
                    connection.execute(
                        text(
                            "INSERT INTO knowledge_revision_evidence_ref "
                            "(knowledge_id, revision, ordinal, evidence_ref_id) "
                            "VALUES (:id, :revision, :ordinal, :evidence_ref)"
                        ),
                        {
                            "id": target_id,
                            "revision": revision,
                            "ordinal": ordinal,
                            "evidence_ref": evidence_ref,
                        },
                    )
                self._replace_chunks(connection, target_id, revision, row["proposed_content"])
                self._event(
                    connection,
                    action="knowledge.proposal.approved",
                    entity_id=target_id,
                    payload={"proposal_id": proposal_id, "revision": revision},
                    now=now,
                )
            connection.execute(
                text(
                    "UPDATE knowledge_proposal SET status=:status, reviewed_by=:reviewed_by, "
                    "review_reason=:reason, reviewed_at=:reviewed_at WHERE proposal_id=:id"
                ),
                {
                    "status": decision.value,
                    "reviewed_by": reviewer,
                    "reason": reason,
                    "reviewed_at": now,
                    "id": proposal_id,
                },
            )
        return self.get_proposal(proposal_id)

    def diff(self, knowledge_id: str, left_revision: int, right_revision: int) -> str:
        left = self.get_revision(knowledge_id, left_revision)
        right = self.get_revision(knowledge_id, right_revision)
        return "\n".join(
            difflib.unified_diff(
                left.content.splitlines(),
                right.content.splitlines(),
                fromfile=f"{knowledge_id}#{left_revision}",
                tofile=f"{knowledge_id}#{right_revision}",
                lineterm="",
            )
        )

    def rollback(
        self,
        knowledge_id: str,
        target_revision: int,
        *,
        reviewer: str,
    ) -> KnowledgeRevision:
        target = self.get_revision(knowledge_id, target_revision)
        entry = self.get_entry(knowledge_id)
        if entry is None:
            raise KeyError("knowledge entry not found")
        revision = entry.current_revision + 1
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO knowledge_revision "
                    "(knowledge_id, revision, title, content, content_sha256, source_type, "
                    "source_locator, artifact_id, evidence_refs, authority, confidence, "
                    "created_by, status, prompt_injection_flag, created_at) VALUES "
                    "(:id, :revision, :title, :content, :hash, 'rollback', :locator, "
                    ":artifact_id, :refs, :authority, :confidence, 'USER', 'approved', "
                    ":flag, :now)"
                ),
                {
                    "id": knowledge_id,
                    "revision": revision,
                    "title": target.title,
                    "content": target.content,
                    "hash": target.content_sha256,
                    "locator": f"{knowledge_id}#{target_revision}",
                    "artifact_id": target.artifact_id,
                    "refs": _json(list(target.evidence_refs)),
                    "authority": target.authority.value,
                    "confidence": target.confidence,
                    "flag": target.prompt_injection_flag,
                    "now": now,
                },
            )
            for ordinal, evidence_ref in enumerate(target.evidence_refs):
                connection.execute(
                    text(
                        "INSERT INTO knowledge_revision_evidence_ref "
                        "(knowledge_id, revision, ordinal, evidence_ref_id) "
                        "VALUES (:id, :revision, :ordinal, :evidence_ref)"
                    ),
                    {
                        "id": knowledge_id,
                        "revision": revision,
                        "ordinal": ordinal,
                        "evidence_ref": evidence_ref,
                    },
                )
            self._replace_chunks(connection, knowledge_id, revision, target.content)
            connection.execute(
                text(
                    "UPDATE knowledge_entry SET current_revision=:revision, "
                    "status='approved', updated_at=:now WHERE knowledge_id=:id"
                ),
                {"revision": revision, "now": now, "id": knowledge_id},
            )
            self._event(
                connection,
                action="knowledge.rollback",
                entity_id=knowledge_id,
                payload={
                    "revision": revision,
                    "target_revision": target_revision,
                    "reviewer": reviewer,
                },
                now=now,
            )
        return self.get_revision(knowledge_id, revision)

    def rebuild_index(self, knowledge_id: str | None = None) -> int:
        with self.engine.begin() as connection:
            query = "SELECT knowledge_id, revision, content FROM knowledge_revision"
            params: dict[str, Any] = {}
            if knowledge_id is not None:
                query += " WHERE knowledge_id=:knowledge_id"
                params["knowledge_id"] = knowledge_id
            rows = connection.execute(text(query), params).mappings().all()
            for row in rows:
                self._replace_chunks(
                    connection, row["knowledge_id"], row["revision"], row["content"]
                )
        return len(rows)

    def create_link(
        self,
        *,
        source_knowledge_id: str,
        source_revision: int,
        target_knowledge_id: str,
        target_revision: int,
        relation: str,
        evidence_refs: tuple[str, ...],
        created_by: KnowledgeCreatedBy,
    ) -> KnowledgeLink:
        link_id = f"link_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            self.get_revision(source_knowledge_id, source_revision)
            self.get_revision(target_knowledge_id, target_revision)
            self._assert_evidence_refs(connection, evidence_refs)
            connection.execute(
                text(
                    "INSERT INTO knowledge_link "
                    "(link_id, source_knowledge_id, source_revision, target_knowledge_id, "
                    "target_revision, relation, evidence_refs, created_by, created_at) VALUES "
                    "(:link_id, :source_id, :source_revision, :target_id, :target_revision, "
                    ":relation, :evidence_refs, :created_by, :created_at)"
                ),
                {
                    "link_id": link_id,
                    "source_id": source_knowledge_id,
                    "source_revision": source_revision,
                    "target_id": target_knowledge_id,
                    "target_revision": target_revision,
                    "relation": relation,
                    "evidence_refs": _json(list(evidence_refs)),
                    "created_by": created_by.value,
                    "created_at": now,
                },
            )
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM knowledge_link WHERE link_id=:link_id"),
                {"link_id": link_id},
            ).mappings().one()
        return self._link(row)

    @staticmethod
    def _entry(row: Any) -> KnowledgeEntry:
        return KnowledgeEntry(
            knowledge_id=row["knowledge_id"],
            category=KnowledgeCategory(row["category"]),
            title=row["title"],
            status=KnowledgeStatus(row["status"]),
            authority=KnowledgeAuthority(row["authority"]),
            created_by=KnowledgeCreatedBy(row["created_by"]),
            current_revision=row["current_revision"],
            labels=tuple(_loads(row["labels"], [])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _revision(row: Any, refs: tuple[str, ...]) -> KnowledgeRevision:
        return KnowledgeRevision(
            knowledge_id=row["knowledge_id"],
            revision=row["revision"],
            title=row["title"],
            content=row["content"],
            content_sha256=row["content_sha256"],
            source_type=row["source_type"],
            source_locator=row["source_locator"],
            artifact_id=row["artifact_id"],
            evidence_refs=refs,
            authority=KnowledgeAuthority(row["authority"]),
            confidence=row["confidence"],
            created_by=KnowledgeCreatedBy(row["created_by"]),
            status=KnowledgeStatus(row["status"]),
            prompt_injection_flag=bool(row["prompt_injection_flag"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _proposal(row: Any) -> KnowledgeProposal:
        return KnowledgeProposal(
            proposal_id=row["proposal_id"],
            target_knowledge_id=row["target_knowledge_id"],
            base_revision=row["base_revision"],
            category=KnowledgeCategory(row["category"]),
            title=row["title"],
            proposed_content=row["proposed_content"],
            content_sha256=row["content_sha256"],
            evidence_refs=tuple(_loads(row["evidence_refs"], [])),
            authority=KnowledgeAuthority(row["authority"]),
            created_by=KnowledgeCreatedBy(row["created_by"]),
            status=ProposalStatus(row["status"]),
            reviewed_by=row["reviewed_by"],
            review_reason=row["review_reason"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
        )

    @staticmethod
    def _link(row: Any) -> KnowledgeLink:
        return KnowledgeLink(
            link_id=row["link_id"],
            source_knowledge_id=row["source_knowledge_id"],
            source_revision=row["source_revision"],
            target_knowledge_id=row["target_knowledge_id"],
            target_revision=row["target_revision"],
            relation=row["relation"],
            evidence_refs=tuple(_loads(row["evidence_refs"], [])),
            created_by=KnowledgeCreatedBy(row["created_by"]),
            created_at=row["created_at"],
        )
