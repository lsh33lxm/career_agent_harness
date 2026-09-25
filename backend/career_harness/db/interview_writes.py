from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from career_harness.core.interview import Interview
from career_harness.db.models import (
    EvidenceRefRow,
    InterviewEvidenceRefRow,
    InterviewIdentityRow,
    InterviewRevisionRow,
)


class InterviewWrite:
    def __init__(self, interview: Interview) -> None:
        self.interview = interview

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "interview-write-v1",
            "interview": self.interview.model_dump(mode="json"),
        }

    def stage(self, session: Session, *, entity_revision: int, occurred_at: datetime) -> None:
        interview = self.interview
        if interview.revision != entity_revision:
            raise ValueError("typed and generic Interview revisions must match")
        identity = session.get(InterviewIdentityRow, interview.entity_id)
        if identity is None:
            if interview.revision != 1:
                raise ValueError("the first Interview revision must be revision one")
            session.add(
                InterviewIdentityRow(
                    interview_id=interview.entity_id,
                    application_id=interview.application_id,
                    application_revision=interview.application_revision,
                )
            )
            session.flush()
        elif (identity.application_id, identity.application_revision) != (
            interview.application_id,
            interview.application_revision,
        ):
            raise ValueError("Interview Application identity cannot change")
        for ordinal, evidence_ref_id in enumerate(interview.evidence_refs):
            if session.get(EvidenceRefRow, evidence_ref_id) is None:
                raise ValueError("Interview requires exact canonical EvidenceRefs")
            session.add(
                InterviewEvidenceRefRow(
                    interview_id=interview.entity_id,
                    revision=interview.revision,
                    ordinal=ordinal,
                    evidence_ref_id=evidence_ref_id,
                )
            )
        session.flush()
        session.add(
            InterviewRevisionRow(
                interview_id=interview.entity_id,
                revision=interview.revision,
                schema_version=interview.schema_version,
                round=interview.round.value,
                scheduled_at=interview.scheduled_at,
                status=interview.status.value,
                evidence_count=len(interview.evidence_refs),
                created_at=interview.created_at,
                created_by=interview.created_by,
            )
        )
