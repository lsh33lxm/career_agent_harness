"""Pure invocation preview. This module never discovers or launches a CLI."""

import hashlib
import json

from career_harness.core.project.l2 import (
    MAX_PROMPT_BYTES,
    AnalysisProvider,
    AnalysisRequest,
    PreparationError,
    PreparedInvocation,
    UnsupportedProviderError,
)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def prepare_claude_invocation(
    request: AnalysisRequest, *, prompt: str, context_digest: str
) -> PreparedInvocation:
    if request.provider is not AnalysisProvider.CLAUDE:
        raise UnsupportedProviderError("provider does not support tools-disabled L2 analysis")
    if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise PreparationError("prepared prompt exceeds the byte limit")
    budget = format(request.max_budget_usd.normalize(), "f")
    argv = (
        "--print",
        "--safe-mode",
        "--tools",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--no-chrome",
        "--input-format",
        "text",
        "--output-format",
        "json",
        "--model",
        request.model,
        "--max-budget-usd",
        budget,
    )
    refs_and_limits = request.model_dump(mode="json", exclude={"files"})
    refs_and_limits["max_budget_usd"] = budget
    request_digest = digest(
        {
            "contract": "0.15.0",
            "request": refs_and_limits,
            "stdin": prompt,
            "context_digest": context_digest,
            "argv": argv,
        }
    )
    return PreparedInvocation(
        **refs_and_limits,
        argv=argv,
        stdin=prompt,
        context_digest=context_digest,
        request_digest=request_digest,
    )
