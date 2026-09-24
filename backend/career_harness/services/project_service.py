from __future__ import annotations

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel
from career_harness.core.project import ProjectEnhancementTask, ProjectEnhancementTaskStatus
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.project_writes import (
    ProjectEnhancementTaskStatusWrite,
    ProjectEnhancementTaskWrite,
)
from career_harness.services.command_service import CommandService


class ProjectEnhancementTaskCommit(FrozenModel):
    task: ProjectEnhancementTask
    commit: CommandCommitResult


class ProjectService:
    """Write path for ProjectEnhancementTask commands.

    Creation and transitions never mutate Gaps, Match results, Capability state
    or Evidence; they only append task rows inside the command transaction.
    """

    def __init__(self, commands: CommandService, repository: ProjectRepository) -> None:
        self.commands = commands
        self.repository = repository

    def propose_enhancement_task(
        self,
        command: Command,
        *,
        task: ProjectEnhancementTask,
    ) -> ProjectEnhancementTaskCommit:
        """Persist a new enhancement task linked to a canonical Gap."""
        if command.target.kind is not EntityKind.PROJECT_ENHANCEMENT_TASK:
            raise ValueError("command requires a project_enhancement_task target")
        if command.target.entity_id != task.task_id:
            raise ValueError("command target must be the proposed task")
        if command.expected_revision != 0:
            raise ValueError("a new ProjectEnhancementTask requires expected revision zero")
        metadata = {
            "task_id": task.task_id,
            "project_id": task.project_id,
            "target_gap_id": task.target_gap_id,
            "target_capability_id": task.target_capability_id,
            "status": task.status.value,
        }
        commit = self.commands.commit(
            command,
            metadata,
            event_type="project_enhancement.proposed",
            event_payload=dict(metadata),
            transactional_write=ProjectEnhancementTaskWrite(task),
        )
        persisted = self.repository.get_enhancement_task(task.task_id)
        if persisted is None:
            raise RuntimeError("ProjectEnhancementTask commit did not persist the typed row")
        return ProjectEnhancementTaskCommit(task=persisted, commit=commit)

    def transition_enhancement_task(
        self,
        command: Command,
        *,
        task_id: str,
        to_status: ProjectEnhancementTaskStatus,
    ) -> ProjectEnhancementTaskCommit:
        """Move an existing task along the status whitelist, pinning the expected revision."""
        if command.target.kind is not EntityKind.PROJECT_ENHANCEMENT_TASK:
            raise ValueError("command requires a project_enhancement_task target")
        if command.target.entity_id != task_id:
            raise ValueError("command target must be the transitioned task")
        current = self.repository.get_enhancement_task(task_id)
        if current is None:
            raise ValueError("ProjectEnhancementTask transition requires an existing task")
        metadata = {
            "task_id": task_id,
            "status": to_status.value,
        }
        # Keep the generic projection shape stable: copy the current state and update status.
        next_state = {
            "task_id": current.task_id,
            "project_id": current.project_id,
            "target_gap_id": current.target_gap_id,
            "target_capability_id": current.target_capability_id,
            "status": to_status.value,
        }
        commit = self.commands.commit(
            command,
            next_state,
            event_type="project_enhancement.status_changed",
            event_payload=dict(metadata),
            transactional_write=ProjectEnhancementTaskStatusWrite(
                task_id=task_id,
                to_status=to_status,
                actor=command.actor,
            ),
        )
        persisted = self.repository.get_enhancement_task(task_id)
        if persisted is None or persisted.status is not to_status:
            raise RuntimeError("ProjectEnhancementTask transition did not persist the new status")
        return ProjectEnhancementTaskCommit(task=persisted, commit=commit)
