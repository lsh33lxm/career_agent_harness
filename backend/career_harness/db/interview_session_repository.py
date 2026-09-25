from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from career_harness.core.interview import InterviewSessionEvent, InterviewSessionRole


class InterviewSessionRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def append(
        self,
        *,
        interview_id: str,
        session_id: str,
        role: InterviewSessionRole,
        content: str,
        source_refs: tuple[str, ...] = (),
    ) -> InterviewSessionEvent:
        content = content.strip()
        if not content:
            raise ValueError("面试会话内容不能为空")
        if len(content) > 20_000:
            raise ValueError("面试会话内容超过 20000 字限制")
        with self.engine.begin() as connection:
            current = connection.execute(
                text(
                    "SELECT COALESCE(MAX(sequence), 0) FROM interview_session_event "
                    "WHERE session_id=:id"
                ),
                {"id": session_id},
            ).scalar_one()
            event = InterviewSessionEvent(
                event_id=f"interview_event_{uuid.uuid4().hex}",
                interview_id=interview_id,
                session_id=session_id,
                sequence=int(current) + 1,
                role=role,
                content=content,
                source_refs=source_refs,
                created_at=datetime.now(UTC),
            )
            connection.execute(
                text(
                    "INSERT INTO interview_session_event "
                    "(event_id,interview_id,session_id,sequence,role,content,source_refs,"
                    "created_at) "
                    "VALUES (:event,:interview,:session,:sequence,:role,:content,:refs,:created)"
                ),
                {
                    "event": event.event_id,
                    "interview": event.interview_id,
                    "session": event.session_id,
                    "sequence": event.sequence,
                    "role": event.role.value,
                    "content": event.content,
                    "refs": json.dumps(event.source_refs, ensure_ascii=False),
                    "created": event.created_at,
                },
            )
        return event

    def list(self, session_id: str) -> tuple[InterviewSessionEvent, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT event_id,interview_id,session_id,sequence,role,content,source_refs,"
                    "created_at "
                    "FROM interview_session_event WHERE session_id=:id ORDER BY sequence"
                ),
                {"id": session_id},
            ).mappings().all()
        return tuple(
            InterviewSessionEvent(
                event_id=row["event_id"],
                interview_id=row["interview_id"],
                session_id=row["session_id"],
                sequence=row["sequence"],
                role=InterviewSessionRole(row["role"]),
                content=row["content"],
                source_refs=tuple(json.loads(row["source_refs"] or "[]")),
                created_at=row["created_at"],
            )
            for row in rows
        )
