from __future__ import annotations

from typing import Protocol

from pydantic import Field, field_validator

from career_harness.core.common import FrozenModel, OpaqueId
from career_harness.core.project.models import (
    PlanItem,
    ProjectEnhancementTask,
    ProjectEnhancementTaskStatus,
    _normalize_paths,
)


class ManualPlanRequest(FrozenModel):
    task_id: OpaqueId
    project_id: OpaqueId
    target_gap_id: OpaqueId
    target_capability_id: OpaqueId
    learning_plan: tuple[PlanItem, ...] = Field(min_length=1)
    files_to_review: tuple[str, ...] = Field(min_length=1)
    change_plan: tuple[PlanItem, ...] = Field(min_length=1)
    experiment_plan: tuple[PlanItem, ...] = Field(min_length=1)
    validation_plan: tuple[PlanItem, ...] = Field(min_length=1)
    expected_evidence: tuple[PlanItem, ...] = Field(min_length=1)
    requested_by: str = Field(min_length=1, max_length=255)

    @field_validator("files_to_review", mode="before")
    @classmethod
    def validate_files_to_review(cls, value: object) -> tuple[str, ...]:
        return _normalize_paths(value)


class ManualExecutor(Protocol):
    def generate_plan(self, request: ManualPlanRequest) -> ProjectEnhancementTask: ...


class L1ManualExecutor:
    """Builds a reviewable plan without reading or changing the target project."""

    def generate_plan(self, request: ManualPlanRequest) -> ProjectEnhancementTask:
        return ProjectEnhancementTask(
            task_id=request.task_id,
            project_id=request.project_id,
            target_gap_id=request.target_gap_id,
            target_capability_id=request.target_capability_id,
            learning_plan=request.learning_plan,
            files_to_review=request.files_to_review,
            change_plan=request.change_plan,
            experiment_plan=request.experiment_plan,
            validation_plan=request.validation_plan,
            expected_evidence=request.expected_evidence,
            status=ProjectEnhancementTaskStatus.PROPOSED,
            created_by=request.requested_by,
        )
