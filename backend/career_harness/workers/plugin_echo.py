"""Deterministic offline worker fixture used by the v2.0 plugin contract tests."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TextIO

from career_harness.core.plugin.runtime import PluginContext


def echo_worker(payload: dict[str, object], context: PluginContext) -> dict[str, object]:
    context.cancellation.raise_if_cancelled()
    return {"echo": payload, "fixture": True, "canonical": False}


def run_ndjson(lines: Iterable[str], output: TextIO) -> None:
    """Run the fixture's tiny JSON/NDJSON protocol without opening a database."""

    for line in lines:
        if not line.strip():
            continue
        request = json.loads(line)
        result = {
            "request_id": request.get("request_id"),
            "status": "ok",
            "data": {"echo": request.get("payload", {}), "fixture": True},
        }
        output.write(json.dumps(result, sort_keys=True) + "\n")
