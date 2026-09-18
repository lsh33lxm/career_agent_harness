from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from career_harness.core.opportunity import (
    OpportunityAdmissionProposal,
    OpportunityAdmissionResult,
)
from career_harness.db.models import (
    OpportunityAdmissionDecisionRow,
    OpportunityAdmissionProposalRow,
    OpportunityRecordRow,
)


class OpportunityAdmissionWrite:
    """Maps a reviewed domain result into typed rows inside the caller's transaction."""

    def __init__(
        self,
        result: OpportunityAdmissionResult,
        *,
        proposal: OpportunityAdmissionProposal | None = None,
    ) -> None:
        self.result = result
        self.proposal = proposal

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "opportunity-admission-write-v1",
            "proposal": (
                self.proposal.model_dump(mode="json", exclude={"proposed_at"})
                if self.proposal
                else None
            ),
            "result": self.result.model_dump(
                mode="json",
                exclude={"decision": {"decided_at"}},
            ),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        decision = self.result.decision
        opportunity = self.result.opportunity
        if opportunity is None:
            raise ValueError("an admission write requires an admitted opportunity")
        if opportunity.revision != entity_revision:
            raise ValueError("typed and generic opportunity revisions must match")
        if decision.proposal_id is not None:
            if self.proposal is None or self.proposal.proposal_id != decision.proposal_id:
                raise ValueError("proposal admission write requires the reviewed proposal")
        elif self.proposal is not None:
            raise ValueError("manual admission write cannot persist a proposal")

        if self.proposal is not None:
            session.add(
                OpportunityAdmissionProposalRow(
                    proposal_id=self.proposal.proposal_id,
                    job_id=self.proposal.job.job_id,
                    job_revision=self.proposal.job.revision,
                    proposed_by=self.proposal.proposed_by.value,
                    reason=self.proposal.reason,
                    proposed_at=self.proposal.proposed_at,
                )
            )
        session.add(
            OpportunityRecordRow(
                opportunity_id=opportunity.entity_id,
                job_id=decision.job.job_id,
                job_revision=decision.job.revision,
                state=opportunity.state.value,
                revision=entity_revision,
                schema_version=opportunity.schema_version,
                admitted_at=occurred_at,
                admitted_by=decision.decided_by.value,
            )
        )
        session.flush()
        session.add(
            OpportunityAdmissionDecisionRow(
                decision_id=decision.decision_id,
                job_id=decision.job.job_id,
                job_revision=decision.job.revision,
                decision=decision.decision.value,
                path=decision.path.value,
                decided_by=decision.decided_by.value,
                proposal_id=decision.proposal_id,
                opportunity_id=decision.opportunity_id,
                reason=decision.reason,
                decided_at=decision.decided_at,
            )
        )
