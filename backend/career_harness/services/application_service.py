from __future__ import annotations

from career_harness.core.application import Application, ApplicationState, SubmissionAuthority
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, OpaqueId
from career_harness.core.outcome import Outcome, OutcomeAuthority, OutcomeType
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.application_writes import ApplicationWrite, OutcomeWrite
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.opportunity_repository import OpportunityRepository
from career_harness.db.resume_repository import ResumeRepository
from career_harness.services.command_service import CommandService

_SUBMISSION_RECEIPT_SOURCE_TYPE = "ats_submission_receipt"

_POST_SUBMISSION_TRANSITIONS = {
    ApplicationState.SUBMITTED_BY_USER: {
        ApplicationState.SCREEN,
        ApplicationState.OA,
        ApplicationState.INTERVIEW,
        ApplicationState.OFFER,
        ApplicationState.REJECTED,
        ApplicationState.WITHDRAWN,
        ApplicationState.CLOSED,
    },
    ApplicationState.SCREEN: {
        ApplicationState.OA,
        ApplicationState.INTERVIEW,
        ApplicationState.OFFER,
        ApplicationState.REJECTED,
        ApplicationState.WITHDRAWN,
        ApplicationState.CLOSED,
    },
    ApplicationState.OA: {
        ApplicationState.INTERVIEW,
        ApplicationState.OFFER,
        ApplicationState.REJECTED,
        ApplicationState.WITHDRAWN,
        ApplicationState.CLOSED,
    },
    ApplicationState.INTERVIEW: {
        ApplicationState.OFFER,
        ApplicationState.REJECTED,
        ApplicationState.WITHDRAWN,
        ApplicationState.CLOSED,
    },
}


class ApplicationService:
    def __init__(self, commands: CommandService) -> None:
        self.commands = commands
        engine = commands.engine
        self.repository = ApplicationRepository(engine)
        self.opportunities = OpportunityRepository(engine)
        self.resumes = ResumeRepository(engine)
        self.evidence = EvidenceRepository(engine)

    def create(
        self,
        command: Command,
        *,
        opportunity_id: OpaqueId,
        opportunity_revision: int,
    ) -> Application:
        self._require_user(command, EntityKind.APPLICATION)
        if command.expected_revision != 0:
            raise ValueError("Application creation requires expected revision zero")
        if self.opportunities.get_revision(opportunity_id, opportunity_revision) is None:
            raise ValueError("Application requires an exact Opportunity revision")
        application = Application(
            entity_id=command.target.entity_id,
            revision=1,
            opportunity_id=opportunity_id,
            opportunity_revision=opportunity_revision,
            state=ApplicationState.PREPARING,
        )
        return self._commit_application(command, application, "application.created")

    def set_preparation_state(self, command: Command, *, state: ApplicationState) -> Application:
        self._require_user(command, EntityKind.APPLICATION)
        if state not in {ApplicationState.PREPARING, ApplicationState.READY_FOR_REVIEW}:
            raise ValueError("preparation state must be PREPARING or READY_FOR_REVIEW")
        current = self._exact_application(command)
        allowed = {
            ApplicationState.PREPARING: {ApplicationState.READY_FOR_REVIEW},
            ApplicationState.READY_FOR_REVIEW: {ApplicationState.PREPARING},
        }
        if state not in allowed.get(current.state, set()):
            raise ValueError("invalid Application preparation transition")
        next_application = current.model_copy(
            update={"revision": current.revision + 1, "state": state}
        )
        return self._commit_application(command, next_application, "application.state_changed")

    def record_submission(
        self,
        command: Command,
        *,
        resume_revision_id: OpaqueId,
        authority: SubmissionAuthority,
        evidence_ref_id: OpaqueId | None = None,
    ) -> Application:
        self._require_user(command, EntityKind.APPLICATION)
        current = self._exact_application(command)
        if current.state is not ApplicationState.READY_FOR_REVIEW:
            raise ValueError("submission requires READY_FOR_REVIEW Application state")
        if self.resumes.get_revision(resume_revision_id) is None:
            raise ValueError("submission requires an exact ResumeRevision")
        if authority is SubmissionAuthority.PORTAL_RECEIPT:
            receipt = self.evidence.get(evidence_ref_id) if evidence_ref_id else None
            if receipt is None or receipt.source.source_type != _SUBMISSION_RECEIPT_SOURCE_TYPE:
                raise ValueError("portal receipt submission requires an exact EvidenceRef")
        elif evidence_ref_id is not None:
            raise ValueError("USER_CONFIRMED submission cannot claim portal receipt evidence")
        submitted = current.model_copy(
            update={
                "revision": current.revision + 1,
                "state": ApplicationState.SUBMITTED_BY_USER,
                "resume_revision_id": resume_revision_id,
                "submission_authority": authority,
                "submission_evidence_ref_id": evidence_ref_id,
                "submitted_at": command.issued_at,
            }
        )
        return self._commit_application(command, submitted, "application.submission_recorded")

    def advance_state(self, command: Command, *, state: ApplicationState) -> Application:
        self._require_user(command, EntityKind.APPLICATION)
        current = self._exact_application(command)
        if state not in _POST_SUBMISSION_TRANSITIONS.get(current.state, set()):
            raise ValueError("invalid post-submission Application transition")
        advanced = current.model_copy(update={"revision": current.revision + 1, "state": state})
        return self._commit_application(command, advanced, "application.state_changed")

    def record_outcome(
        self,
        command: Command,
        *,
        application_id: OpaqueId,
        application_revision: int,
        result: OutcomeType,
        authority: OutcomeAuthority,
        evidence_refs: tuple[OpaqueId, ...] = (),
    ) -> Outcome:
        self._require_user(command, EntityKind.OUTCOME)
        if command.expected_revision != 0:
            raise ValueError("Outcome creation requires expected revision zero")
        application = self.repository.get(application_id, application_revision)
        if application is None:
            raise ValueError("Outcome requires an exact Application revision")
        if application.state in {
            ApplicationState.PREPARING,
            ApplicationState.READY_FOR_REVIEW,
        }:
            raise ValueError("Outcome requires a submitted Application revision")
        resolved_evidence = []
        for evidence_ref_id in evidence_refs:
            evidence = self.evidence.get(evidence_ref_id)
            if evidence is None:
                raise ValueError("Outcome requires exact canonical EvidenceRefs")
            resolved_evidence.append(evidence)
        if authority is OutcomeAuthority.PORTAL_RECEIPT and not any(
            item.source.source_type == _SUBMISSION_RECEIPT_SOURCE_TYPE for item in resolved_evidence
        ):
            raise ValueError("portal receipt Outcome requires validated receipt Evidence")
        outcome = Outcome(
            entity_id=command.target.entity_id,
            application_id=application_id,
            application_revision=application_revision,
            result=result,
            occurred_at=command.issued_at,
            authority=authority,
            evidence_refs=evidence_refs,
            recorded_by=command.actor,
        )
        result_commit = self.commands.commit(
            command,
            outcome.model_dump(mode="json"),
            event_type="outcome.recorded",
            event_payload={
                "application_id": application_id,
                "application_revision": application_revision,
                "result": outcome.result.value,
                "authority": outcome.authority.value,
                "evidence_count": len(outcome.evidence_refs),
            },
            transactional_write=OutcomeWrite(outcome),
        )
        persisted = self.repository.get_outcome(outcome.entity_id)
        if persisted is None or result_commit.revision != 1:
            raise RuntimeError("Outcome commit did not persist the typed aggregate")
        return persisted

    def _exact_application(self, command: Command) -> Application:
        if command.expected_revision < 1:
            raise ValueError("Application transition requires an existing revision")
        current = self.repository.get(command.target.entity_id, command.expected_revision)
        if current is None:
            raise ValueError("Application transition requires the exact current revision")
        return current

    def _commit_application(
        self, command: Command, application: Application, event_type: str
    ) -> Application:
        result = self.commands.commit(
            command,
            application.model_dump(mode="json"),
            event_type=event_type,
            event_payload={
                "application_id": application.entity_id,
                "opportunity_id": application.opportunity_id,
                "opportunity_revision": application.opportunity_revision,
                "state": application.state.value,
            },
            transactional_write=ApplicationWrite(application, created_by=command.actor),
        )
        persisted = self.repository.get(application.entity_id, result.revision)
        if persisted is None:
            raise RuntimeError("Application commit did not persist the typed aggregate")
        return persisted

    @staticmethod
    def _require_user(command: Command, kind: EntityKind) -> None:
        if command.target.kind is not kind:
            raise ValueError(f"command requires a {kind.value} target")
        if command.actor != "user":
            raise ValueError("only the user may perform this Application/Outcome command")
