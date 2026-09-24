import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from career_harness.core.application import ApplicationState, SubmissionAuthority
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.opportunity import JobRef
from career_harness.core.outcome import OutcomeAuthority, OutcomeType
from career_harness.db.models import (
    ApplicationRevisionRow,
    EvidenceArtifactRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    IdempotencyRecordRow,
    OutcomeRecordRow,
    SourceSnapshotRow,
)
from career_harness.services.application_service import ApplicationService
from career_harness.services.command_service import CommandService
from career_harness.services.opportunity_service import OpportunityService
from career_harness.services.resume_service import ResumeService
from tests.integration.test_fact_service import EVIDENCE_REF_ID, _engine
from tests.support.job_data import seed_job_revision


def _command(
    entity_id: str,
    kind: EntityKind,
    command_id: str,
    *,
    expected_revision: int = 0,
    actor: str = "user",
) -> Command:
    return Command(
        command_id=command_id,
        command_type=f"{kind.value}.command",
        target=EntityRef(entity_id=entity_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=f"idempotency-{command_id}",
        actor=actor,
    )


def _seed_dependencies(tmp_path: Path):
    engine = _engine(tmp_path)
    seed_job_revision(engine, "job_001", 1)
    _seed_receipt(engine)
    commands = CommandService(engine)
    OpportunityService(commands).admit_manually(
        _command("opportunity_001", EntityKind.OPPORTUNITY, "command_opportunity"),
        JobRef(job_id="job_001", revision=1),
        opportunity_id="opportunity_001",
        decision_id="decision_001",
    )
    resumes = ResumeService(commands)
    resumes.save_base_revision(
        _command("resume_001", EntityKind.RESUME, "command_resume_base"),
        candidate_id="candidate_001",
        sections={"summary": "Verified summary"},
    )
    resumes.create_revision(
        _command("resume_revision_001", EntityKind.RESUME_REVISION, "command_resume_revision"),
        resume_id="resume_001",
        base_revision=1,
        accepted_patch_refs=(),
    )
    return engine, ApplicationService(commands)


def test_application_submission_and_outcome_flow_is_exact_and_idempotent(tmp_path: Path) -> None:
    engine, service = _seed_dependencies(tmp_path)
    application = service.create(
        _command("application_001", EntityKind.APPLICATION, "command_application"),
        opportunity_id="opportunity_001",
        opportunity_revision=1,
    )
    assert application.state is ApplicationState.PREPARING
    ready = service.set_preparation_state(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_ready",
            expected_revision=1,
        ),
        state=ApplicationState.READY_FOR_REVIEW,
    )
    assert ready.revision == 2
    submitted = service.record_submission(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_submit",
            expected_revision=2,
        ),
        resume_revision_id="resume_revision_001",
        authority=SubmissionAuthority.PORTAL_RECEIPT,
        evidence_ref_id=RECEIPT_EVIDENCE_ID,
    )
    assert submitted.state is ApplicationState.SUBMITTED_BY_USER
    screened = service.advance_state(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_screen",
            expected_revision=3,
        ),
        state=ApplicationState.SCREEN,
    )
    assert screened.resume_revision_id == "resume_revision_001"
    with (
        pytest.raises(IntegrityError, match="submission identity cannot change"),
        engine.begin() as connection,
    ):
        connection.execute(
            ApplicationRevisionRow.__table__.insert(),
            {
                "application_id": "application_001",
                "revision": 5,
                "schema_version": 1,
                "state": "screen",
                "resume_revision_id": "resume_revision_001",
                "submission_authority": "user_confirmed",
                "submission_evidence_ref_id": None,
                "submitted_at": screened.submitted_at,
                "created_at": datetime.now(UTC),
                "created_by": "user",
            },
        )

    outcome_command = _command("outcome_001", EntityKind.OUTCOME, "command_outcome")
    outcome = service.record_outcome(
        outcome_command,
        application_id="application_001",
        application_revision=4,
        result=OutcomeType.REJECTION,
        authority=OutcomeAuthority.PORTAL_RECEIPT,
        evidence_refs=(RECEIPT_EVIDENCE_ID,),
    )
    replay = service.record_outcome(
        outcome_command,
        application_id="application_001",
        application_revision=4,
        result=OutcomeType.REJECTION,
        authority=OutcomeAuthority.PORTAL_RECEIPT,
        evidence_refs=(RECEIPT_EVIDENCE_ID,),
    )
    assert replay == outcome
    assert service.repository.get_outcome("outcome_001") == outcome
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ApplicationRevisionRow)) == 4
        assert session.scalar(select(func.count()).select_from(OutcomeRecordRow)) == 1
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 8


def test_application_and_outcome_authority_fail_closed(tmp_path: Path) -> None:
    engine, service = _seed_dependencies(tmp_path)
    with pytest.raises(ValueError, match="only the user"):
        service.create(
            _command(
                "application_agent",
                EntityKind.APPLICATION,
                "command_agent",
                actor="agent:application",
            ),
            opportunity_id="opportunity_001",
            opportunity_revision=1,
        )
    service.create(
        _command("application_001", EntityKind.APPLICATION, "command_application"),
        opportunity_id="opportunity_001",
        opportunity_revision=1,
    )
    service.set_preparation_state(
        _command(
            "application_001",
            EntityKind.APPLICATION,
            "command_ready",
            expected_revision=1,
        ),
        state=ApplicationState.READY_FOR_REVIEW,
    )
    with pytest.raises(ValueError, match="exact EvidenceRef"):
        service.record_submission(
            _command(
                "application_001",
                EntityKind.APPLICATION,
                "command_bad_receipt",
                expected_revision=2,
            ),
            resume_revision_id="resume_revision_001",
            authority=SubmissionAuthority.PORTAL_RECEIPT,
            evidence_ref_id=EVIDENCE_REF_ID,
        )
    with pytest.raises(ValueError, match="submitted Application"):
        service.record_outcome(
            _command("outcome_001", EntityKind.OUTCOME, "command_outcome"),
            application_id="application_001",
            application_revision=2,
            result=OutcomeType.CLOSED,
            authority=OutcomeAuthority.USER_CONFIRMED,
        )
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ApplicationRevisionRow)) == 2
        assert session.scalar(select(func.count()).select_from(OutcomeRecordRow)) == 0


RECEIPT_EVIDENCE_ID = "evidence_submission_receipt"


def _seed_receipt(engine) -> None:  # type: ignore[no-untyped-def]
    digest = hashlib.sha256(b"submission receipt").hexdigest()
    with engine.begin() as connection:
        connection.execute(
            EvidenceArtifactRow.__table__.insert(),
            {
                "artifact_id": "artifact_submission_receipt",
                "sha256": digest,
                "media_type": "application/json",
                "artifact_class": "personal",
                "byte_length": 18,
            },
        )
        connection.execute(
            EvidenceSourceRow.__table__.insert(),
            {
                "source_id": "source_submission_receipt",
                "source_type": "ats_submission_receipt",
                "locator": "test://submission-receipt",
            },
        )
        connection.execute(
            SourceSnapshotRow.__table__.insert(),
            {
                "snapshot_id": "snapshot_submission_receipt",
                "source_id": "source_submission_receipt",
                "captured_at": datetime.now(UTC),
                "artifact_id": "artifact_submission_receipt",
            },
        )
        connection.execute(
            EvidenceRefRow.__table__.insert(),
            {
                "evidence_ref_id": RECEIPT_EVIDENCE_ID,
                "snapshot_id": "snapshot_submission_receipt",
                "artifact_id": "artifact_submission_receipt",
                "selector": None,
            },
        )
