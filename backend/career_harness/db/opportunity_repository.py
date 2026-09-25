from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.approval import ActorKind
from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Opportunity, OpportunityState
from career_harness.core.opportunity import (
    JobRef,
    OpportunityDetail,
    PriorityInputRevision,
    PriorityLevel,
    SuggestedPriority,
    UserPriority,
)
from career_harness.db.models import (
    EntityRevisionRow,
    EntityStateRow,
    OpportunityRecordRow,
    SuggestedPriorityRow,
    UserPriorityRow,
)


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

    def get_revision(self, opportunity_id: str, revision: int) -> OpportunityDetail | None:
        """Read an exact historical Opportunity revision from the immutable revision log.

        The typed priority rows only keep their latest values. A priority is included
        only when its last write happened at or before the requested revision, which
        is exact because every priority write bumps the Opportunity revision. A
        priority whose last write is newer than the requested revision cannot be
        reconstructed and is reported as absent.
        """
        with Session(self.engine) as session:
            state_row = session.get(EntityStateRow, opportunity_id)
            if state_row is None:
                return None
            if state_row.entity_kind != EntityKind.OPPORTUNITY.value:
                raise ValueError("entity id exists with a different kind")
            revision_row = session.scalars(
                select(EntityRevisionRow).where(
                    EntityRevisionRow.entity_id == opportunity_id,
                    EntityRevisionRow.revision == revision,
                )
            ).first()
            if revision_row is None:
                return None
            record_row = session.get(OpportunityRecordRow, opportunity_id)
            if record_row is None:
                raise RuntimeError("persisted Opportunity revision is missing its typed record")
            try:
                opportunity = Opportunity.model_validate(revision_row.state)
            except ValidationError as err:
                raise RuntimeError("persisted Opportunity revision state is malformed") from err
            if opportunity.entity_id != opportunity_id or opportunity.revision != revision:
                raise RuntimeError("persisted Opportunity revision state is inconsistent")
            suggested_row = session.get(SuggestedPriorityRow, opportunity_id)
            user_row = session.get(UserPriorityRow, opportunity_id)
            suggested = (
                self._to_suggested(suggested_row)
                if suggested_row is not None and suggested_row.revision <= revision
                else None
            )
            user = (
                self._to_user(user_row)
                if user_row is not None and user_row.revision <= revision
                else None
            )
            return OpportunityDetail(
                opportunity=opportunity,
                job=JobRef(job_id=record_row.job_id, revision=record_row.job_revision),
                suggested_priority=suggested,
                user_priority=user,
            )

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
            OpportunityRepository._to_suggested(suggested_row)
            if suggested_row is not None
            else None
        )
        user = OpportunityRepository._to_user(user_row) if user_row is not None else None
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

    @staticmethod
    def _to_suggested(suggested_row: SuggestedPriorityRow) -> SuggestedPriority:
        return SuggestedPriority(
            opportunity_id=suggested_row.opportunity_id,
            level=PriorityLevel(suggested_row.level),
            reasons=tuple(suggested_row.reasons),
            input_revisions=tuple(
                PriorityInputRevision.model_validate(item) for item in suggested_row.input_revisions
            ),
            calculated_at=suggested_row.calculated_at,
            score=suggested_row.score,
            rank=suggested_row.rank,
        )

    @staticmethod
    def _to_user(user_row: UserPriorityRow) -> UserPriority:
        return UserPriority(
            opportunity_id=user_row.opportunity_id,
            level=PriorityLevel(user_row.level),
            actor=ActorKind(user_row.actor),
            set_at=user_row.set_at,
            reason=user_row.reason,
        )
