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
class SandboxPolicy:
    allowed_executables: frozenset[str] = frozenset({"claude", "codex", "opencode"})
    forbidden_tokens: frozenset[str] = frozenset(
        {"&&", "||", ";", "|", ">", ">>", "<", "--network", "--write", "--shell"}
    )

    def validate(self, argv: tuple[str, ...]) -> None:
        executable = argv[0].rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
        if executable not in self.allowed_executables:
            raise CliRunnerBlocked("CLI executable is outside the sandbox allowlist")
        if any(token in self.forbidden_tokens for token in argv):
            raise CliRunnerBlocked(
                "CLI arguments request forbidden shell, network, or write behavior"
            )
        if any(
            any(marker in token for marker in ("&&", "||", ";", "|", ">", "<"))
            for token in argv
        ):
            raise CliRunnerBlocked("CLI arguments contain shell metacharacters")


@dataclass(frozen=True, slots=True)
class SandboxedCliRunner:
    executor: SandboxExecutor | None = None
    policy: SandboxPolicy = SandboxPolicy()

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
        self.policy.validate(invocation.argv)
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
