from __future__ import annotations

from career_harness.workflows import (
    RunState,
    SequentialLocalStepRunner,
    StepDefinition,
    StepResult,
    StepState,
)


async def test_runner_stops_at_human_boundary() -> None:
    calls: list[str] = []

    async def prepare(context: dict) -> StepResult:
        calls.append("prepare")
        return StepResult(state=StepState.SUCCEEDED, output={"prepared": True})

    async def approval(context: dict) -> StepResult:
        calls.append("approval")
        assert context["prepared"] is True
        return StepResult(state=StepState.BLOCKED, reason="user approval required")

    async def submit(context: dict) -> StepResult:
        calls.append("submit")
        return StepResult(state=StepState.SUCCEEDED)

    result = await SequentialLocalStepRunner().run(
        [
            StepDefinition(name="prepare", handler=prepare),
            StepDefinition(name="approval", handler=approval),
            StepDefinition(name="submit", handler=submit),
        ],
        {},
    )

    assert result.state is RunState.WAITING_HUMAN
    assert calls == ["prepare", "approval"]

