from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_harness.core.project import ProjectEnhancementTask, ProjectEnhancementTaskStatus
from career_harness.db.models import MatchGapRow, ProjectEnhancementTaskRow, ProjectIdentityRow

# Status transition whitelist. Completed and cancelled are terminal states.
ALLOWED_ENHANCEMENT_TRANSITIONS: dict[
    ProjectEnhancementTaskStatus, frozenset[ProjectEnhancementTaskStatus]
] = {
    ProjectEnhancementTaskStatus.PROPOSED: frozenset(
        {
            ProjectEnhancementTaskStatus.READY,
            ProjectEnhancementTaskStatus.IN_PROGRESS,
            ProjectEnhancementTaskStatus.CANCELLED,
        }
    ),
    ProjectEnhancementTaskStatus.READY: frozenset(
        {
            ProjectEnhancementTaskStatus.IN_PROGRESS,
            ProjectEnhancementTaskStatus.CANCELLED,
        }
    ),
    ProjectEnhancementTaskStatus.IN_PROGRESS: frozenset(
        {
            ProjectEnhancementTaskStatus.AWAITING_VALIDATION,
            ProjectEnhancementTaskStatus.CANCELLED,
        }
    ),
    ProjectEnhancementTaskStatus.AWAITING_VALIDATION: frozenset(
        {
            ProjectEnhancementTaskStatus.COMPLETED,
            ProjectEnhancementTaskStatus.IN_PROGRESS,
        }
    ),
    ProjectEnhancementTaskStatus.COMPLETED: frozenset(),
    ProjectEnhancementTaskStatus.CANCELLED: frozenset(),
}


class ProjectEnhancementTaskWrite:
    """Stages a new ProjectEnhancementTask inside the caller's command transaction.

    The target_gap_id column predates the canonical Gap table and has no database
    foreign key, so the write path must fail loud on dangling references.
    """

    def __init__(self, task: ProjectEnhancementTask) -> None:
        self.task = task

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "project-enhancement-task-write-v1",
            "task": self.task.model_dump(mode="json", exclude={"created_at"}),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        task = self.task
        if task.revision != entity_revision:
            raise ValueError("typed and generic ProjectEnhancementTask revisions must match")
        if entity_revision != 1:
            raise ValueError("a new ProjectEnhancementTask must be revision one")
        if task.status is not ProjectEnhancementTaskStatus.PROPOSED:
            raise ValueError("a new ProjectEnhancementTask must start as proposed")
        if session.get(ProjectIdentityRow, task.project_id) is None:
            raise ValueError("ProjectEnhancementTask requires a canonical Project")
        gap = session.get(MatchGapRow, task.target_gap_id)
        if gap is None:
            raise ValueError("ProjectEnhancementTask target_gap_id must resolve to a canonical Gap")
        if gap.capability_id != task.target_capability_id:
            raise ValueError(
                "ProjectEnhancementTask capability must equal the target Gap capability"
            )
        session.add(
            ProjectEnhancementTaskRow(
                task_id=task.task_id,
                revision=task.revision,
                project_id=task.project_id,
                target_gap_id=task.target_gap_id,
                target_capability_id=task.target_capability_id,
                learning_plan=list(task.learning_plan),
                files_to_review=list(task.files_to_review),
                change_plan=list(task.change_plan),
                experiment_plan=list(task.experiment_plan),
                validation_plan=list(task.validation_plan),
                expected_evidence=list(task.expected_evidence),
                status=task.status.value,
                schema_version=task.schema_version,
                created_at=occurred_at,
                created_by=task.created_by,
            )
        )


class ProjectEnhancementTaskStatusWrite:
    """Stages a status-only transition as a new immutable task revision.

    Plan content and target references are copied from the latest persisted
    revision; a transition can never rewrite them.
    """

    def __init__(
        self,
        *,
        task_id: str,
        to_status: ProjectEnhancementTaskStatus,
        actor: str,
    ) -> None:
        self.task_id = task_id
        self.to_status = to_status
        self.actor = actor

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "project-enhancement-task-status-write-v1",
            "task_id": self.task_id,
            "to_status": self.to_status.value,
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        row = session.scalars(
            select(ProjectEnhancementTaskRow)
            .where(ProjectEnhancementTaskRow.task_id == self.task_id)
            .order_by(ProjectEnhancementTaskRow.revision.desc())
            .limit(1)
        ).first()
        if row is None:
            raise ValueError("ProjectEnhancementTask transition requires an existing task")
        if row.revision + 1 != entity_revision:
            raise ValueError("typed and generic ProjectEnhancementTask revisions must match")
        from_status = ProjectEnhancementTaskStatus(row.status)
        if self.to_status not in ALLOWED_ENHANCEMENT_TRANSITIONS[from_status]:
            raise ValueError(
                f"ProjectEnhancementTask cannot transition from "
                f"{from_status.value} to {self.to_status.value}"
            )
        session.add(
            ProjectEnhancementTaskRow(
                task_id=row.task_id,
                revision=entity_revision,
                project_id=row.project_id,
                target_gap_id=row.target_gap_id,
                target_capability_id=row.target_capability_id,
                learning_plan=list(row.learning_plan),
                files_to_review=list(row.files_to_review),
                change_plan=list(row.change_plan),
                experiment_plan=list(row.experiment_plan),
                validation_plan=list(row.validation_plan),
                expected_evidence=list(row.expected_evidence),
                status=self.to_status.value,
                schema_version=row.schema_version,
                created_at=occurred_at,
                created_by=self.actor,
            )
        )
