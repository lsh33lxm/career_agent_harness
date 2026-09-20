"""Read-only assembly of the Core-owned Today queue (contract 0.8.0, D-017).

The service only reads: it never writes any table, never recomputes or writes
SuggestedPriority and never mutates UserPriority. Opportunity/Application data
comes from the existing repositories; the review-proposal and task scans use
read-only SELECTs because the repositories expose no list reads for them yet
(follow-up: promote these scans into repository list methods). Selection rules
live in the policy; the service only assembles typed inputs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.common import EntityKind, utc_now
from career_harness.core.lifecycle import ApplicationState
from career_harness.core.today import (
    ApplicationInput,
    EnhancementTaskInput,
    InterviewInput,
    OpportunityInput,
    ReviewRequestInput,
    TodayInputs,
    TodayQueue,
    TodaySourceRef,
    build_today_queue,
)
from career_harness.db.application_repository import ApplicationRepository
from career_harness.db.interview_repository import InterviewRepository
from career_harness.db.models import (
    ExtractedClaimRevisionRow,
    JobRequirementRevisionRow,
    ProjectEnhancementTaskRow,
    ResumePatchRevisionRow,
)
from career_harness.db.opportunity_repository import OpportunityRepository


class TodayService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.opportunities = OpportunityRepository(engine)
        self.applications = ApplicationRepository(engine)
        self.interviews = InterviewRepository(engine)

    def build_queue(self, *, generated_at: datetime | None = None) -> TodayQueue:
        details = self.opportunities.list()
        detail_by_id = {detail.opportunity.entity_id: detail for detail in details}
        opportunity_inputs = tuple(
            OpportunityInput(
                source=TodaySourceRef(
                    entity_id=detail.opportunity.entity_id,
                    kind=EntityKind.OPPORTUNITY,
                    revision=detail.opportunity.revision,
                ),
                state=detail.opportunity.state,
                user_priority=(
                    detail.user_priority.level if detail.user_priority is not None else None
                ),
                suggested_priority=(
                    detail.suggested_priority.level
                    if detail.suggested_priority is not None
                    else None
                ),
            )
            for detail in details
        )
        application_inputs = []
        for application in self.applications.list():
            detail = detail_by_id.get(application.opportunity_id)
            application_inputs.append(
                ApplicationInput(
                    source=TodaySourceRef(
                        entity_id=application.entity_id,
                        kind=EntityKind.APPLICATION,
                        revision=application.revision,
                    ),
                    opportunity=(
                        TodaySourceRef(
                            entity_id=detail.opportunity.entity_id,
                            kind=EntityKind.OPPORTUNITY,
                            revision=detail.opportunity.revision,
                        )
                        if detail is not None
                        else None
                    ),
                    state=application.state,
                    interviews=(
                        self._interview_inputs(application.entity_id)
                        if application.state is ApplicationState.INTERVIEW
                        else ()
                    ),
                    user_priority=(
                        detail.user_priority.level
                        if detail is not None and detail.user_priority is not None
                        else None
                    ),
                    suggested_priority=(
                        detail.suggested_priority.level
                        if detail is not None and detail.suggested_priority is not None
                        else None
                    ),
                )
            )
        inputs = TodayInputs(
            opportunities=opportunity_inputs,
            applications=tuple(application_inputs),
            enhancement_tasks=self._open_enhancement_tasks(),
            review_requests=self._review_request_inputs(),
        )
        return build_today_queue(inputs, generated_at=generated_at or utc_now())

    def _interview_inputs(self, application_id: str) -> tuple[InterviewInput, ...]:
        inputs: list[InterviewInput] = []
        for interview in self.interviews.list_for_application(application_id):
            if interview.application_id != application_id:
                raise ValueError("Interview must belong to the requested Application")
            application = self.applications.get(
                interview.application_id, interview.application_revision
            )
            if (
                application is None
                or application.entity_id != interview.application_id
                or application.revision != interview.application_revision
            ):
                raise ValueError("Interview requires its exact pinned Application revision")
            inputs.append(
                InterviewInput(
                    source=TodaySourceRef(
                        entity_id=interview.entity_id,
                        kind=EntityKind.INTERVIEW,
                        revision=interview.revision,
                    ),
                    application=TodaySourceRef(
                        entity_id=application.entity_id,
                        kind=EntityKind.APPLICATION,
                        revision=application.revision,
                    ),
                    status=interview.status,
                    scheduled_at=interview.scheduled_at,
                )
            )
        return tuple(inputs)

    def _open_enhancement_tasks(self) -> tuple[EnhancementTaskInput, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ProjectEnhancementTaskRow).order_by(
                    ProjectEnhancementTaskRow.task_id,
                    ProjectEnhancementTaskRow.revision.desc(),
                )
            ).all()
        latest: dict[str, ProjectEnhancementTaskRow] = {}
        for row in rows:
            latest.setdefault(row.task_id, row)
        return tuple(
            EnhancementTaskInput(
                source=TodaySourceRef(
                    entity_id=row.task_id,
                    kind=EntityKind.PROJECT_ENHANCEMENT_TASK,
                    revision=row.revision,
                ),
                status=row.status,
            )
            for row in latest.values()
        )

    def _review_request_inputs(self) -> tuple[ReviewRequestInput, ...]:
        requests = []
        requests.extend(self._requirement_review_inputs())
        requests.extend(self._claim_review_inputs())
        requests.extend(self._patch_review_inputs())
        return tuple(requests)

    def _requirement_review_inputs(self) -> tuple[ReviewRequestInput, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(JobRequirementRevisionRow).order_by(
                    JobRequirementRevisionRow.requirement_id,
                    JobRequirementRevisionRow.revision.desc(),
                )
            ).all()
        latest: dict[str, JobRequirementRevisionRow] = {}
        for row in rows:
            latest.setdefault(row.requirement_id, row)
        return tuple(
            ReviewRequestInput(
                source=TodaySourceRef(
                    entity_id=row.requirement_id,
                    kind=EntityKind.JOB_REQUIREMENT,
                    revision=row.revision,
                ),
                status=row.status,
            )
            for row in latest.values()
        )

    def _claim_review_inputs(self) -> tuple[ReviewRequestInput, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ExtractedClaimRevisionRow).order_by(
                    ExtractedClaimRevisionRow.claim_id,
                    ExtractedClaimRevisionRow.revision.desc(),
                )
            ).all()
        latest: dict[str, ExtractedClaimRevisionRow] = {}
        for row in rows:
            latest.setdefault(row.claim_id, row)
        return tuple(
            ReviewRequestInput(
                source=TodaySourceRef(
                    entity_id=row.claim_id,
                    kind=EntityKind.EXTRACTED_CLAIM,
                    revision=row.revision,
                ),
                status=row.status,
            )
            for row in latest.values()
        )

    def _patch_review_inputs(self) -> tuple[ReviewRequestInput, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ResumePatchRevisionRow).order_by(
                    ResumePatchRevisionRow.patch_id,
                    ResumePatchRevisionRow.revision.desc(),
                )
            ).all()
        latest: dict[str, ResumePatchRevisionRow] = {}
        for row in rows:
            latest.setdefault(row.patch_id, row)
        return tuple(
            ReviewRequestInput(
                source=TodaySourceRef(
                    entity_id=row.patch_id,
                    kind=EntityKind.RESUME_PATCH,
                    revision=row.revision,
                ),
                status=row.status,
            )
            for row in latest.values()
        )
