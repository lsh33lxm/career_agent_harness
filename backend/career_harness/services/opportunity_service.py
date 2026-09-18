from __future__ import annotations

from career_harness.core.approval import ActorKind
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.opportunity import (
    AdmissionDecision,
    JobRef,
    OpportunityAdmissionProposal,
    OpportunityAdmissionResult,
    admit_opportunity_manually,
    review_admission_proposal,
)
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.opportunity_writes import OpportunityAdmissionWrite
from career_harness.services.command_service import CommandService


class OpportunityAdmissionCommit(FrozenModel):
    admission: OpportunityAdmissionResult
    commit: CommandCommitResult


class OpportunityService:
    def __init__(self, commands: CommandService) -> None:
        self.commands = commands

    def admit_manually(
        self,
        command: Command,
        job: JobRef,
        *,
        opportunity_id: OpaqueId,
        decision_id: OpaqueId,
        reason: str | None = None,
    ) -> OpportunityAdmissionCommit:
        self._require_new_user_opportunity(command, opportunity_id)
        admission = admit_opportunity_manually(
            job,
            decision_id=decision_id,
            opportunity_id=opportunity_id,
            decided_by=ActorKind.USER,
            reason=reason,
            decided_at=command.issued_at,
        )
        return self._commit_admission(command, admission)

    def review_proposal(
        self,
        command: Command,
        proposal: OpportunityAdmissionProposal,
        *,
        decision_id: OpaqueId,
        opportunity_id: OpaqueId,
        reason: str | None = None,
    ) -> OpportunityAdmissionCommit:
        self._require_new_user_opportunity(command, opportunity_id)
        admission = review_admission_proposal(
            proposal,
            decision_id=decision_id,
            decision=AdmissionDecision.ADMITTED,
            decided_by=ActorKind.USER,
            opportunity_id=opportunity_id,
            reason=reason,
            decided_at=command.issued_at,
        )
        return self._commit_admission(command, admission, proposal=proposal)

    def _commit_admission(
        self,
        command: Command,
        admission: OpportunityAdmissionResult,
        *,
        proposal: OpportunityAdmissionProposal | None = None,
    ) -> OpportunityAdmissionCommit:
        opportunity = admission.opportunity
        if opportunity is None:
            raise ValueError("admission service only persists admitted opportunities")
        decision = admission.decision
        commit = self.commands.commit(
            command,
            opportunity.model_dump(mode="json"),
            event_type="opportunity.admitted",
            event_payload={
                "decision_id": decision.decision_id,
                "job_id": decision.job.job_id,
                "job_revision": decision.job.revision,
                "path": decision.path.value,
            },
            transactional_write=OpportunityAdmissionWrite(admission, proposal=proposal),
        )
        return OpportunityAdmissionCommit(admission=admission, commit=commit)

    @staticmethod
    def _require_new_user_opportunity(command: Command, opportunity_id: OpaqueId) -> None:
        if command.target.kind is not EntityKind.OPPORTUNITY:
            raise ValueError("opportunity admission command requires an opportunity target")
        if command.target.entity_id != opportunity_id:
            raise ValueError("command target must match the admitted opportunity")
        if command.expected_revision != 0:
            raise ValueError("opportunity admission requires expected revision zero")
        if command.actor != ActorKind.USER.value:
            raise ValueError("only a user command may admit an opportunity")
