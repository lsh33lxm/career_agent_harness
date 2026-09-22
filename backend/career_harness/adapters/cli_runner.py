"""Approval-gated CLI runner boundary; the application never launches a shell itself."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import Field

from career_harness.core.common import FrozenModel
from career_harness.core.project.l2 import PreparedInvocation


class CliRunnerBlocked(RuntimeError):
    """The configured sandbox or user approval is unavailable."""


class CliRunResult(FrozenModel):
    status: str = Field(pattern=r"^(blocked|completed)$")
    request_digest: str
    output: dict[str, Any] | None = None
    reason: str | None = None


SandboxExecutor = Callable[[tuple[str, ...], str, int, int], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class SandboxedCliRunner:
    executor: SandboxExecutor | None = None

    def run(
        self,
        invocation: PreparedInvocation,
        *,
        approval_id: str | None,
    ) -> CliRunResult:
        if not approval_id:
            return CliRunResult(
                status="blocked",
                request_digest=invocation.request_digest,
                reason="CLI 运行需要用户 approval",
            )
        if self.executor is None:
            return CliRunResult(
                status="blocked",
                request_digest=invocation.request_digest,
                reason="sandbox executor 未配置",
            )
        if not invocation.argv or invocation.argv[0].startswith(("-", "/")):
            raise CliRunnerBlocked("prepared CLI argv is invalid")
        if invocation.permissions.model_shell_tools or invocation.permissions.model_network_tools:
            raise CliRunnerBlocked("prepared invocation requests forbidden model permissions")
        result = self.executor(
            invocation.argv,
            invocation.stdin,
            invocation.timeout_seconds,
            invocation.max_output_bytes,
        )
        return CliRunResult(
            status="completed",
            request_digest=invocation.request_digest,
            output=result,
        )
