from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.common import utc_now
from career_harness.core.communication import (
    CommunicationChannel,
    CommunicationDraft,
    CommunicationStatus,
)


class CommunicationRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, draft: CommunicationDraft, *, daily_limit: int = 10) -> CommunicationDraft:
        if daily_limit < 1:
            raise ValueError("每日沟通上限必须为正数")
        with self.engine.begin() as connection:
            existing = (
                connection.execute(
                    text("SELECT * FROM communication_draft WHERE draft_id=:id"),
                    {"id": draft.draft_id},
                )
                .mappings()
                .first()
            )
            if existing is not None:
                current = self._read(existing)
                if current.model_dump(exclude={"created_at", "reviewed_at"}) != draft.model_dump(
                    exclude={"created_at", "reviewed_at"}
                ):
                    raise ValueError("沟通草稿 ID 已存在且内容不同")
                return current
            created_today = int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM communication_draft "
                        "WHERE date(created_at)=date('now')"
                    )
                ).scalar_one()
            )
            persisted = draft
            if created_today >= daily_limit and draft.status in {
                CommunicationStatus.PENDING_REVIEW,
                CommunicationStatus.APPROVED,
            }:
                persisted = draft.model_copy(
                    update={
                        "status": CommunicationStatus.BLOCKED,
                        "provenance": {
                            **draft.provenance,
                            "blocked_reason": "daily_communication_limit",
                            "daily_limit": str(daily_limit),
                        },
                    }
                )
            connection.execute(
                text(
                    "INSERT INTO communication_draft "
                    "(draft_id, opportunity_id, source_staging_id, channel, recipient, body, "
                    "status, "
                    "provenance, created_by, created_at) VALUES "
                    "(:id,:opportunity,:staging,:channel,:recipient,:body,:status,:provenance,:created_by,:created_at)"
                ),
                {
                    "id": persisted.draft_id,
                    "opportunity": persisted.opportunity_id,
                    "staging": persisted.source_staging_id,
                    "channel": persisted.channel.value,
                    "recipient": persisted.recipient,
                    "body": persisted.body,
                    "status": persisted.status.value,
                    "provenance": json.dumps(
                        persisted.provenance, ensure_ascii=False, sort_keys=True
                    ),
                    "created_by": persisted.created_by,
                    "created_at": persisted.created_at,
                },
            )
        return persisted

    def get(self, draft_id: str) -> CommunicationDraft | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM communication_draft WHERE draft_id=:id"), {"id": draft_id}
                )
                .mappings()
                .first()
            )
        return self._read(row) if row else None

    def list(self, status: CommunicationStatus | None = None) -> tuple[CommunicationDraft, ...]:
        query = "SELECT * FROM communication_draft"
        params: dict[str, Any] = {}
        if status is not None:
            query += " WHERE status=:status"
            params["status"] = status.value
        query += " ORDER BY created_at DESC, draft_id"
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), params).mappings().all()
        return tuple(self._read(row) for row in rows)

    def summary(self, *, daily_limit: int = 10) -> dict[str, Any]:
        if daily_limit < 1:
            raise ValueError("每日沟通上限必须为正数")
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT status, COUNT(*) AS count FROM communication_draft GROUP BY status"
                    )
                )
                .mappings()
                .all()
            )
            today = connection.execute(
                text("SELECT COUNT(*) FROM communication_draft WHERE date(created_at)=date('now')")
            ).scalar_one()
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        return {
            "daily_limit": daily_limit,
            "created_today": int(today),
            "remaining_today": max(0, daily_limit - int(today)),
            "counts": counts,
            "reply_count": counts.get(CommunicationStatus.REPLIED.value, 0),
            "follow_up_count": counts.get(CommunicationStatus.FOLLOW_UP.value, 0),
        }

    def review(
        self, draft_id: str, *, decision: CommunicationStatus, reason: str
    ) -> CommunicationDraft:
        if decision not in {CommunicationStatus.APPROVED, CommunicationStatus.REJECTED}:
            raise ValueError("沟通草稿只能批准或拒绝")
        current = self.get(draft_id)
        if current is None:
            raise KeyError("沟通草稿不存在")
        if current.status is not CommunicationStatus.PENDING_REVIEW:
            if current.status is decision and current.review_reason == reason:
                return current
            raise ValueError("沟通草稿已经审核，不能覆盖原决定")
        reviewed = current.model_copy(
            update={
                "status": decision,
                "reviewed_by": "user",
                "review_reason": reason,
                "reviewed_at": utc_now(),
            }
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE communication_draft SET status=:status, reviewed_by='user', "
                    "review_reason=:reason, reviewed_at=:reviewed_at "
                    "WHERE draft_id=:id AND status='pending_review'"
                ),
                {
                    "id": draft_id,
                    "status": decision.value,
                    "reason": reason,
                    "reviewed_at": reviewed.reviewed_at,
                },
            )
        return self.get(draft_id) or reviewed

    def transition(self, draft_id: str, *, status: CommunicationStatus) -> CommunicationDraft:
        """Record a user-observed communication state; never sends anything externally."""
        allowed = {
            CommunicationStatus.APPROVED: {
                CommunicationStatus.SENT,
                CommunicationStatus.BLOCKED,
                CommunicationStatus.CLOSED,
            },
            CommunicationStatus.SENT: {
                CommunicationStatus.REPLIED,
                CommunicationStatus.FOLLOW_UP,
                CommunicationStatus.CLOSED,
            },
            CommunicationStatus.REPLIED: {
                CommunicationStatus.FOLLOW_UP,
                CommunicationStatus.CLOSED,
            },
            CommunicationStatus.FOLLOW_UP: {
                CommunicationStatus.REPLIED,
                CommunicationStatus.CLOSED,
            },
            CommunicationStatus.BLOCKED: {CommunicationStatus.CLOSED},
        }
        current = self.get(draft_id)
        if current is None:
            raise KeyError("沟通草稿不存在")
        if status not in allowed.get(current.status, set()):
            raise ValueError(f"不允许从 {current.status.value} 转为 {status.value}")
        with self.engine.begin() as connection:
            connection.execute(
                text("UPDATE communication_draft SET status=:status WHERE draft_id=:id"),
                {"id": draft_id, "status": status.value},
            )
        return self.get(draft_id) or current.model_copy(update={"status": status})

    @staticmethod
    def _read(row: Any) -> CommunicationDraft:
        provenance = row["provenance"]
        return CommunicationDraft(
            draft_id=row["draft_id"],
            opportunity_id=row["opportunity_id"],
            source_staging_id=row["source_staging_id"],
            channel=CommunicationChannel(row["channel"]),
            recipient=row["recipient"],
            body=row["body"],
            status=CommunicationStatus(row["status"]),
            provenance=(json.loads(provenance) if isinstance(provenance, str) else provenance),
            created_by=row["created_by"],
            reviewed_by=row["reviewed_by"],
            review_reason=row["review_reason"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
        )
