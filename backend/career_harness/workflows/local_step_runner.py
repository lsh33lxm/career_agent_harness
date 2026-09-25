from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from enum import StrEnum
from typing import Any, Protocol

from pydantic import Field

from career_harness.core.common import FrozenModel


class RunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepResult(FrozenModel):
    state: StepState
    output: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


StepHandler = Callable[[dict[str, Any]], Awaitable[StepResult]]


class StepDefinition(FrozenModel):
    name: str = Field(min_length=1, max_length=128)
    handler: StepHandler


class RunResult(FrozenModel):
    state: RunState
    steps: tuple[StepResult, ...]


class LocalStepRunner(Protocol):
    async def run(
        self, steps: Sequence[StepDefinition], context: dict[str, Any]
    ) -> RunResult: ...


class SequentialLocalStepRunner:
    async def run(
        self, steps: Sequence[StepDefinition], context: dict[str, Any]
    ) -> RunResult:
        results: list[StepResult] = []
        for step in steps:
            result = await step.handler(context)
            results.append(result)
            if result.state is StepState.BLOCKED:
                return RunResult(state=RunState.WAITING_HUMAN, steps=tuple(results))
            if result.state is StepState.FAILED:
                return RunResult(state=RunState.FAILED, steps=tuple(results))
            if result.state is not StepState.SUCCEEDED:
                raise ValueError(f"step {step.name} returned invalid terminal state {result.state}")
            context.update(result.output)
        return RunResult(state=RunState.SUCCEEDED, steps=tuple(results))

