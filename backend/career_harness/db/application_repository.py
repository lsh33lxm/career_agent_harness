from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.application import Application, ApplicationState, SubmissionAuthority
from career_harness.core.outcome import Outcome, OutcomeAuthority, OutcomeType
from career_harness.db.models import (
    ApplicationIdentityRow,
    ApplicationRevisionRow,
    OutcomeEvidenceRefRow,
    OutcomeRecordRow,
)


class ApplicationRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, application_id: str, revision: int | None = None) -> Application | None:
        with Session(self.engine) as session:
            identity = session.get(ApplicationIdentityRow, application_id)
            if identity is None:
                return None
            if revision is None:
                row = session.scalars(
                    select(ApplicationRevisionRow)
                    .where(ApplicationRevisionRow.application_id == application_id)
                    .order_by(ApplicationRevisionRow.revision.desc())
                    .limit(1)
                ).first()
            else:
                row = session.get(ApplicationRevisionRow, (application_id, revision))
            if row is None:
                return None
            return Application(
                entity_id=application_id,
                revision=row.revision,
                schema_version=row.schema_version,
                opportunity_id=identity.opportunity_id,
                opportunity_revision=identity.opportunity_revision,
                state=ApplicationState(row.state),
                resume_revision_id=row.resume_revision_id,
                submission_authority=(
                    SubmissionAuthority(row.submission_authority)
                    if row.submission_authority
                    else None
                ),
                submission_evidence_ref_id=row.submission_evidence_ref_id,
                submitted_at=row.submitted_at,
            )

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        with Session(self.engine) as session:
            row = session.get(OutcomeRecordRow, outcome_id)
            if row is None:
                return None
            refs = session.scalars(
                select(OutcomeEvidenceRefRow)
                .where(OutcomeEvidenceRefRow.outcome_id == outcome_id)
                .order_by(OutcomeEvidenceRefRow.ordinal)
            ).all()
            if len(refs) != row.evidence_count or [item.ordinal for item in refs] != list(
                range(row.evidence_count)
            ):
                raise RuntimeError("persisted Outcome evidence aggregate is incomplete")
            return Outcome(
                entity_id=row.outcome_id,
                application_id=row.application_id,
                application_revision=row.application_revision,
                result=OutcomeType(row.result),
                occurred_at=row.occurred_at,
                authority=OutcomeAuthority(row.authority),
                evidence_refs=tuple(item.evidence_ref_id for item in refs),
                recorded_by=row.recorded_by,
            )
