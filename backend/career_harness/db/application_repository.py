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
            return self._to_application(identity, row)

    def list(self) -> tuple[Application, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ApplicationRevisionRow).order_by(
                    ApplicationRevisionRow.application_id,
                    ApplicationRevisionRow.revision.desc(),
                )
            ).all()
            latest: dict[str, ApplicationRevisionRow] = {}
            for row in rows:
                latest.setdefault(row.application_id, row)
            applications = []
            for application_id, row in latest.items():
                identity = session.get(ApplicationIdentityRow, application_id)
                if identity is None:
                    raise RuntimeError("persisted Application identity is missing")
                applications.append(self._to_application(identity, row))
            return tuple(applications)

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        with Session(self.engine) as session:
            row = session.get(OutcomeRecordRow, outcome_id)
            if row is None:
                return None
            return self._to_outcome(session, row)

    def list_outcomes(self, application_id: str) -> tuple[Outcome, ...]:
        with Session(self.engine) as session:
            if session.get(ApplicationIdentityRow, application_id) is None:
                return ()
            rows = session.scalars(
                select(OutcomeRecordRow)
                .where(OutcomeRecordRow.application_id == application_id)
                .order_by(OutcomeRecordRow.occurred_at.desc(), OutcomeRecordRow.outcome_id)
            ).all()
            return tuple(self._to_outcome(session, row) for row in rows)

    @staticmethod
    def _to_application(
        identity: ApplicationIdentityRow, row: ApplicationRevisionRow
    ) -> Application:
        return Application(
            entity_id=identity.application_id,
            revision=row.revision,
            schema_version=row.schema_version,
            opportunity_id=identity.opportunity_id,
            opportunity_revision=identity.opportunity_revision,
            state=ApplicationState(row.state),
            resume_revision_id=row.resume_revision_id,
            submission_authority=(
                SubmissionAuthority(row.submission_authority) if row.submission_authority else None
            ),
            submission_evidence_ref_id=row.submission_evidence_ref_id,
            submitted_at=row.submitted_at,
        )

    @staticmethod
    def _to_outcome(session: Session, row: OutcomeRecordRow) -> Outcome:
        refs = session.scalars(
            select(OutcomeEvidenceRefRow)
            .where(OutcomeEvidenceRefRow.outcome_id == row.outcome_id)
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
