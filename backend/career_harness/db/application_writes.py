from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from career_harness.core.application import Application
from career_harness.core.outcome import Outcome
from career_harness.db.models import (
    ApplicationIdentityRow,
    ApplicationRevisionRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    OutcomeEvidenceRefRow,
    OutcomeRecordRow,
    SourceSnapshotRow,
)

_SUBMISSION_RECEIPT_SOURCE_TYPE = "ats_submission_receipt"


def _is_submission_receipt(session: Session, evidence_ref_id: str | None) -> bool:
    if evidence_ref_id is None:
        return False
    evidence = session.get(EvidenceRefRow, evidence_ref_id)
    if evidence is None:
        return False
    snapshot = session.get(SourceSnapshotRow, evidence.snapshot_id)
    if snapshot is None or snapshot.artifact_id != evidence.artifact_id:
        return False
    source = session.get(EvidenceSourceRow, snapshot.source_id)
    return source is not None and source.source_type == _SUBMISSION_RECEIPT_SOURCE_TYPE


class ApplicationWrite:
    def __init__(self, application: Application, *, created_by: str) -> None:
        self.application = application
        self.created_by = created_by

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "application-write-v1",
            "application": self.application.model_dump(mode="json"),
            "created_by": self.created_by,
        }

    def stage(self, session: Session, *, entity_revision: int, occurred_at: datetime) -> None:
        application = self.application
        if application.revision != entity_revision:
            raise ValueError("typed and generic Application revisions must match")
        identity = session.get(ApplicationIdentityRow, application.entity_id)
        if identity is None:
            if application.revision != 1:
                raise ValueError("the first Application revision must be revision one")
            session.add(
                ApplicationIdentityRow(
                    application_id=application.entity_id,
                    opportunity_id=application.opportunity_id,
                    opportunity_revision=application.opportunity_revision,
                )
            )
            session.flush()
        elif (identity.opportunity_id, identity.opportunity_revision) != (
            application.opportunity_id,
            application.opportunity_revision,
        ):
            raise ValueError("Application Opportunity identity cannot change")
        if (
            application.submission_authority is not None
            and application.submission_authority.value == "portal_receipt"
            and not _is_submission_receipt(session, application.submission_evidence_ref_id)
        ):
            raise ValueError("portal receipt Application requires validated receipt Evidence")
        session.add(
            ApplicationRevisionRow(
                application_id=application.entity_id,
                revision=application.revision,
                schema_version=application.schema_version,
                state=application.state.value,
                resume_revision_id=application.resume_revision_id,
                submission_authority=(
                    application.submission_authority.value
                    if application.submission_authority
                    else None
                ),
                submission_evidence_ref_id=application.submission_evidence_ref_id,
                submitted_at=application.submitted_at,
                created_at=occurred_at,
                created_by=self.created_by,
            )
        )


class OutcomeWrite:
    def __init__(self, outcome: Outcome) -> None:
        self.outcome = outcome

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "outcome-write-v1",
            "outcome": self.outcome.model_dump(mode="json"),
        }

    def stage(self, session: Session, *, entity_revision: int, occurred_at: datetime) -> None:
        outcome = self.outcome
        if entity_revision != 1 or outcome.revision != 1:
            raise ValueError("Outcome is immutable and has one revision")
        has_receipt = False
        for ordinal, evidence_ref_id in enumerate(outcome.evidence_refs):
            if session.get(EvidenceRefRow, evidence_ref_id) is None:
                raise ValueError("Outcome requires exact canonical EvidenceRefs")
            has_receipt = has_receipt or _is_submission_receipt(session, evidence_ref_id)
            session.add(
                OutcomeEvidenceRefRow(
                    outcome_id=outcome.entity_id,
                    ordinal=ordinal,
                    evidence_ref_id=evidence_ref_id,
                )
            )
        if outcome.authority.value == "portal_receipt" and not has_receipt:
            raise ValueError("portal receipt Outcome requires validated receipt Evidence")
        session.flush()
        session.add(
            OutcomeRecordRow(
                outcome_id=outcome.entity_id,
                application_id=outcome.application_id,
                application_revision=outcome.application_revision,
                result=outcome.result.value,
                occurred_at=outcome.occurred_at,
                authority=outcome.authority.value,
                evidence_count=len(outcome.evidence_refs),
                recorded_by=outcome.recorded_by,
            )
        )
