from pathlib import Path

from career_harness.core.project import (
    L1ManualExecutor,
    ManualExecutor,
    ManualPlanRequest,
    ProjectEnhancementTaskStatus,
)


def test_l1_manual_executor_builds_complete_candidate_plan_without_side_effects(
    tmp_path: Path,
) -> None:
    executor: ManualExecutor = L1ManualExecutor()
    request = ManualPlanRequest(
        task_id="enhancement_001",
        project_id="project_001",
        target_gap_id="gap_observability",
        target_capability_id="capability_observability",
        learning_plan=("Learn OpenTelemetry span and context propagation basics.",),
        files_to_review=("src/router.py", "tests/test_router.py"),
        change_plan=("Propose tracing around router and provider calls.",),
        experiment_plan=("Compare traces for primary and fallback provider requests.",),
        validation_plan=("Run focused tests and inspect a recorded trace.",),
        expected_evidence=(
            "Code diff candidate showing span creation.",
            "Test result candidate covering provider fallback tracing.",
        ),
        requested_by="user",
    )

    before = tuple(tmp_path.rglob("*"))
    task = executor.generate_plan(request)
    after = tuple(tmp_path.rglob("*"))

    assert task.learning_plan
    assert task.files_to_review == ("src/router.py", "tests/test_router.py")
    assert task.change_plan
    assert task.experiment_plan
    assert task.validation_plan
    assert task.expected_evidence
    assert task.status is ProjectEnhancementTaskStatus.PROPOSED
    assert before == after == ()
