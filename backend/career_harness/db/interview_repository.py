from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.interview import Interview, InterviewRound, InterviewStatus
from career_harness.db.models import (
    InterviewEvidenceRefRow,
    InterviewIdentityRow,
    InterviewRevisionRow,
)


class InterviewRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, interview_id: str, revision: int | None = None) -> Interview | None:
        with Session(self.engine) as session:
            identity = session.get(InterviewIdentityRow, interview_id)
            if identity is None:
                return None
            if revision is None:
                row = session.scalars(
                    select(InterviewRevisionRow)
                    .where(InterviewRevisionRow.interview_id == interview_id)
                    .order_by(InterviewRevisionRow.revision.desc())
                    .limit(1)
                ).first()
            else:
                row = session.get(InterviewRevisionRow, (interview_id, revision))
            if row is None:
                return None
            return self._to_interview(session, identity, row)

    def list_for_application(self, application_id: str) -> tuple[Interview, ...]:
        with Session(self.engine) as session:
            identities = session.scalars(
                select(InterviewIdentityRow)
                .where(InterviewIdentityRow.application_id == application_id)
                .order_by(InterviewIdentityRow.interview_id)
            ).all()
            interviews = []
            for identity in identities:
                row = session.scalars(
                    select(InterviewRevisionRow)
                    .where(InterviewRevisionRow.interview_id == identity.interview_id)
                    .order_by(InterviewRevisionRow.revision.desc())
                    .limit(1)
                ).first()
                if row is None:
                    raise RuntimeError("persisted Interview identity has no revision")
                interviews.append((row.scheduled_at, self._to_interview(session, identity, row)))
            interviews.sort(key=lambda item: (item[0], item[1].entity_id))
            return tuple(interview for _, interview in interviews)

    @staticmethod
    def _to_interview(
        session: Session, identity: InterviewIdentityRow, row: InterviewRevisionRow
    ) -> Interview:
        refs = session.scalars(
            select(InterviewEvidenceRefRow)
            .where(
                InterviewEvidenceRefRow.interview_id == row.interview_id,
                InterviewEvidenceRefRow.revision == row.revision,
            )
            .order_by(InterviewEvidenceRefRow.ordinal)
        ).all()
        if len(refs) != row.evidence_count or [item.ordinal for item in refs] != list(
            range(row.evidence_count)
        ):
            raise RuntimeError("persisted Interview evidence aggregate is incomplete")
        return Interview(
            entity_id=identity.interview_id,
            revision=row.revision,
            schema_version=row.schema_version,
            application_id=identity.application_id,
            application_revision=identity.application_revision,
            round=InterviewRound(row.round),
            scheduled_at=row.scheduled_at,
            status=InterviewStatus(row.status),
            evidence_refs=tuple(item.evidence_ref_id for item in refs),
            created_at=row.created_at,
            created_by=row.created_by,
        )
