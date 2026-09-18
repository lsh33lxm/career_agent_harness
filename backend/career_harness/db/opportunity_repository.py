from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.approval import ActorKind
from career_harness.core.lifecycle import Opportunity, OpportunityState
from career_harness.core.opportunity import (
    JobRef,
    OpportunityDetail,
    PriorityInputRevision,
    PriorityLevel,
    SuggestedPriority,
    UserPriority,
)
from career_harness.db.models import OpportunityRecordRow, SuggestedPriorityRow, UserPriorityRow


class OpportunityRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, opportunity_id: str) -> OpportunityDetail | None:
        with Session(self.engine) as session:
            row = session.get(OpportunityRecordRow, opportunity_id)
            if row is None:
                return None
            suggested_row = session.get(SuggestedPriorityRow, opportunity_id)
            user_row = session.get(UserPriorityRow, opportunity_id)
            return self._to_detail(row, suggested_row, user_row)

    def list(self) -> tuple[OpportunityDetail, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(OpportunityRecordRow).order_by(OpportunityRecordRow.admitted_at.desc())
            ).all()
            return tuple(
                self._to_detail(
                    row,
                    session.get(SuggestedPriorityRow, row.opportunity_id),
                    session.get(UserPriorityRow, row.opportunity_id),
                )
                for row in rows
            )

    @staticmethod
    def _to_detail(
        row: OpportunityRecordRow,
        suggested_row: SuggestedPriorityRow | None,
        user_row: UserPriorityRow | None,
    ) -> OpportunityDetail:
        suggested = (
            SuggestedPriority(
                opportunity_id=suggested_row.opportunity_id,
                level=PriorityLevel(suggested_row.level),
                reasons=tuple(suggested_row.reasons),
                input_revisions=tuple(
                    PriorityInputRevision.model_validate(item)
                    for item in suggested_row.input_revisions
                ),
                calculated_at=suggested_row.calculated_at,
                score=suggested_row.score,
                rank=suggested_row.rank,
            )
            if suggested_row is not None
            else None
        )
        user = (
            UserPriority(
                opportunity_id=user_row.opportunity_id,
                level=PriorityLevel(user_row.level),
                actor=ActorKind(user_row.actor),
                set_at=user_row.set_at,
                reason=user_row.reason,
            )
            if user_row is not None
            else None
        )
        return OpportunityDetail(
            opportunity=Opportunity(
                entity_id=row.opportunity_id,
                revision=row.revision,
                schema_version=row.schema_version,
                state=OpportunityState(row.state),
            ),
            job=JobRef(job_id=row.job_id, revision=row.job_revision),
            suggested_priority=suggested,
            user_priority=user,
        )
