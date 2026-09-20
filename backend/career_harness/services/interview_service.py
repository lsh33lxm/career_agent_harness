from __future__ import annotations

from datetime import datetime

from career_harness.core.application import ApplicationState
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, OpaqueId
from career_harness.core.interview import Interview, InterviewRound, InterviewStatus
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.interview_repository import InterviewRepository
from career_harness.db.interview_writes import InterviewWrite
from career_harness.services.command_service import CommandService

_SCHEDULABLE_STATES = {
    ApplicationState.SUBMITTED_BY_USER,
    ApplicationState.SCREEN,
    ApplicationState.OA,
    ApplicationState.INTERVIEW,
    ApplicationState.OFFER,
}


class InterviewService:
    """Explicit Interview lifecycle commands. Never creates or implies an Outcome."""

    def __init__(self, commands: CommandService) -> None:
        self.commands = commands
        engine = commands.engine
        self.repository = InterviewRepository(engine)
        self.applications = ApplicationRepository(engine)
        self.evidence = EvidenceRepository(engine)

    def schedule_interview(
        self,
        command: Command,
        *,
        application_id: OpaqueId,
        application_revision: int,
        round: InterviewRound,
        scheduled_at: datetime,
        evidence_refs: tuple[OpaqueId, ...] = (),
    ) -> Interview:
        self._require_interview_target(command)
        if command.expected_revision != 0:
            raise ValueError("Interview scheduling requires expected revision zero")
        application = self.applications.get(application_id, application_revision)
        if application is None:
            raise ValueError("Interview requires an exact Application revision")
        if application.state not in _SCHEDULABLE_STATES:
            raise ValueError(
                "Interview scheduling requires a submitted, non-terminal Application revision"
            )
        self._require_exact_evidence(evidence_refs)
        interview = Interview(
            entity_id=command.target.entity_id,
            revision=1,
            application_id=application_id,
            application_revision=application_revision,
            round=round,
            scheduled_at=scheduled_at,
            status=InterviewStatus.SCHEDULED,
            evidence_refs=evidence_refs,
            created_at=command.issued_at,
            created_by=command.actor,
        )
        return self._commit(command, interview, "interview.scheduled")

    def complete_interview(
        self,
        command: Command,
        *,
        evidence_refs: tuple[OpaqueId, ...] | None = None,
    ) -> Interview:
        return self._transition(
            command,
            status=InterviewStatus.COMPLETED,
            event_type="interview.completed",
            evidence_refs=evidence_refs,
        )

    def cancel_interview(self, command: Command) -> Interview:
        return self._transition(
            command, status=InterviewStatus.CANCELLED, event_type="interview.cancelled"
        )

    def _transition(
        self,
        command: Command,
        *,
        status: InterviewStatus,
        event_type: str,
        evidence_refs: tuple[OpaqueId, ...] | None = None,
    ) -> Interview:
        self._require_interview_target(command)
        if command.expected_revision < 1:
            raise ValueError("Interview transition requires an existing revision")
        current = self.repository.get(command.target.entity_id, command.expected_revision)
        if current is None:
            raise ValueError("Interview transition requires the exact current revision")
        if current.status is not InterviewStatus.SCHEDULED:
            raise ValueError("only a scheduled Interview can transition")
        if evidence_refs is None:
            evidence_refs = current.evidence_refs
        self._require_exact_evidence(evidence_refs)
        next_interview = current.model_copy(
            update={
                "revision": current.revision + 1,
                "status": status,
                "evidence_refs": evidence_refs,
                "created_at": command.issued_at,
                "created_by": command.actor,
            }
        )
        return self._commit(command, next_interview, event_type)

    def _commit(self, command: Command, interview: Interview, event_type: str) -> Interview:
        result = self.commands.commit(
            command,
            interview.model_dump(mode="json"),
            event_type=event_type,
            event_payload={
                "interview_id": interview.entity_id,
                "application_id": interview.application_id,
                "application_revision": interview.application_revision,
                "round": interview.round.value,
                "scheduled_at": interview.scheduled_at.isoformat(),
                "status": interview.status.value,
                "evidence_count": len(interview.evidence_refs),
            },
            transactional_write=InterviewWrite(interview),
        )
        persisted = self.repository.get(interview.entity_id, result.revision)
        if persisted is None:
            raise RuntimeError("Interview commit did not persist the typed aggregate")
        return persisted

    def _require_exact_evidence(self, evidence_refs: tuple[OpaqueId, ...]) -> None:
        for evidence_ref_id in evidence_refs:
            if self.evidence.get(evidence_ref_id) is None:
                raise ValueError("Interview requires exact canonical EvidenceRefs")

    @staticmethod
    def _require_interview_target(command: Command) -> None:
        if command.target.kind is not EntityKind.INTERVIEW:
            raise ValueError("command requires an interview target")
