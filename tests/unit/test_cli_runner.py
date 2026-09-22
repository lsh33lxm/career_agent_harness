from decimal import Decimal

from career_harness.adapters.cli_runner import SandboxedCliRunner
from career_harness.core.project.l2 import (
    AnalysisProvider,
    ExactRef,
    PreparedInvocation,
)


def _invocation() -> PreparedInvocation:
    return PreparedInvocation(
        task=ExactRef(entity_id="task_001", revision=1),
        project=ExactRef(entity_id="project_001", revision=1),
        scope=ExactRef(entity_id="scope_001", revision=1),
        manifest_id="manifest_001",
        provider=AnalysisProvider.CLAUDE,
        model="sonnet",
        max_budget_usd=Decimal("1.25"),
        timeout_seconds=30,
        max_output_bytes=1024,
        argv=("claude", "--print"),
        stdin="proposal only",
        context_digest="a" * 64,
        request_digest="b" * 64,
    )


def test_cli_runner_fails_closed_without_approval_or_sandbox() -> None:
    invocation = _invocation()
    assert SandboxedCliRunner().run(invocation, approval_id=None).status == "blocked"
    assert SandboxedCliRunner().run(invocation, approval_id="approval_001").status == "blocked"


def test_cli_runner_uses_only_injected_sandbox_executor() -> None:
    calls: list[tuple[tuple[str, ...], str, int, int]] = []

    def executor(argv: tuple[str, ...], stdin: str, timeout: int, limit: int) -> dict[str, str]:
        calls.append((argv, stdin, timeout, limit))
        return {"kind": "proposal"}

    result = SandboxedCliRunner(executor).run(_invocation(), approval_id="approval_001")
    assert result.status == "completed"
    assert result.output == {"kind": "proposal"}
    assert calls == [(('claude', '--print'), "proposal only", 30, 1024)]
