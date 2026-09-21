"""Read-only WeKnora-shaped adapter.

The adapter deliberately performs no network call in v2.0 Slice B. A configured
endpoint and verified license/terms are required before a real MCP transport can
be enabled.
"""

from __future__ import annotations

from typing import Any


class CareerKbWeknoraAdapter:
    def __init__(self, *, configured: bool = False) -> None:
        self.configured = configured

    def health(self) -> dict[str, Any]:
        if not self.configured:
            return {
                "status": "blocked",
                "code": "weknora_not_configured",
                "message": "WeKnora endpoint, credentials and terms are not configured",
            }
        return {"status": "blocked", "code": "external_action_blocked"}

    def search(self, query: str) -> dict[str, Any]:
        if not self.configured:
            return {
                "status": "blocked",
                "code": "weknora_not_configured",
                "query": query,
                "items": [],
                "evidence_refs": [],
            }
        return {
            "status": "blocked",
            "code": "external_action_blocked",
            "query": query,
            "items": [],
            "evidence_refs": [],
        }

    def read(self, passage_id: str) -> dict[str, Any]:
        result = self.search(passage_id)
        return {**result, "passage_id": passage_id}

    def ask(self, question: str) -> dict[str, Any]:
        result = self.search(question)
        return {**result, "question": question}
