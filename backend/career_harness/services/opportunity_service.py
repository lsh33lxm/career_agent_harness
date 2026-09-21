from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from career_harness.core.approval import ActorKind
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.opportunity import (
    AdmissionDecision,
    JobRef,
    OpportunityAdmissionProposal,
    OpportunityAdmissionResult,
    PriorityInputRevision,
    PriorityLevel,
    SuggestedPriority,
    UserPriority,
    admit_opportunity_manually,
    review_admission_proposal,
)
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.opportunity_writes import (
    OpportunityAdmissionWrite,
    SuggestedPriorityWrite,
    UserPriorityWrite,
)
from career_harness.services.command_service import CommandService


class OpportunityAdmissionCommit(FrozenModel):
    admission: OpportunityAdmissionResult
    commit: CommandCommitResult


class OpportunityService:
    def __init__(self, commands: CommandService) -> None:
        self.commands = commands

    @staticmethod
    def admission_ids(
        command_id: OpaqueId,
        *,
        opportunity_id: OpaqueId | None = None,
        decision_id: OpaqueId | None = None,
    ) -> tuple[OpaqueId, OpaqueId]:
        def derive(prefix: str) -> str:
            seed = f"agent-career-harness:{prefix}:{command_id}"
            return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, seed).hex}"

        return opportunity_id or derive("opportunity"), decision_id or derive("decision")

    def admit_manually(
        self,
        command: Command,
        job: JobRef,
        *,
        opportunity_id: OpaqueId,
        decision_id: OpaqueId,
        reason: str | None = None,
        session: Session | None = None,
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
        return self._commit_admission(command, admission, session=session)

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

    def set_suggested_priority(
        self,
        command: Command,
        *,
        level: PriorityLevel,
        reasons: tuple[str, ...],
        input_revisions: tuple[PriorityInputRevision, ...],
        score: float | None = None,
        rank: int | None = None,
    ) -> CommandCommitResult:
        current = self._require_existing_opportunity(command)
        priority = SuggestedPriority(
            opportunity_id=command.target.entity_id,
            level=level,
            reasons=reasons,
            input_revisions=input_revisions,
            calculated_at=command.issued_at,
            score=score,
            rank=rank,
        )
        return self.commands.commit(
            command,
            self._next_opportunity_state(current.state, current.revision),
            event_type="opportunity.suggested_priority_updated",
            event_payload={"level": level.value},
            transactional_write=SuggestedPriorityWrite(priority),
        )

    def set_user_priority(
        self,
        command: Command,
        *,
        level: PriorityLevel,
        reason: str | None = None,
    ) -> CommandCommitResult:
        current = self._require_existing_opportunity(command, require_user=True)
        priority = UserPriority(
            opportunity_id=command.target.entity_id,
            level=level,
            actor=ActorKind.USER,
            set_at=command.issued_at,
            reason=reason,
        )
        return self.commands.commit(
            command,
            self._next_opportunity_state(current.state, current.revision),
            event_type="opportunity.user_priority_set",
            event_payload={"level": level.value},
            transactional_write=UserPriorityWrite(priority),
        )

    def _commit_admission(
        self,
        command: Command,
        admission: OpportunityAdmissionResult,
        *,
        proposal: OpportunityAdmissionProposal | None = None,
        session: Session | None = None,
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
            session=session,
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

    def _require_existing_opportunity(
        self,
        command: Command,
        *,
        require_user: bool = False,
    ):
        if command.target.kind is not EntityKind.OPPORTUNITY:
            raise ValueError("priority command requires an opportunity target")
        if command.expected_revision < 1:
            raise ValueError("priority command requires an existing opportunity revision")
        if require_user and command.actor != ActorKind.USER.value:
            raise ValueError("only a user command may set user priority")
        current = self.commands.get(command.target)
        if current is None:
            raise ValueError("opportunity does not exist")
        return current

    @staticmethod
    def _next_opportunity_state(current_state: dict, current_revision: int) -> dict:
        next_state = dict(current_state)
        next_state["revision"] = current_revision + 1
        return next_state
