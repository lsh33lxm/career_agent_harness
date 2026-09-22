"""Authenticated MCP transport boundary for local adapters.

This module deliberately does not open sockets or spawn processes. A future
stdio/SSE adapter can delegate authentication and tool calls here so transport
details cannot bypass the existing ToolRegistry policy.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from career_harness.core.tools.registry import (
    ToolCallContext,
    ToolCallError,
    ToolPermission,
    ToolRegistry,
    ToolScope,
    ToolScopeKind,
)


class McpAuthenticationError(PermissionError):
    """The transport token is missing or rejected."""


@dataclass(frozen=True, slots=True)
class McpPrincipal:
    principal_id: str
    allowed_scopes: frozenset[ToolScope]
    permissions: frozenset[ToolPermission]


Authenticator = Callable[[str], McpPrincipal | None]


@dataclass(frozen=True, slots=True)
class AuthenticatedMcpTransport:
    registry: ToolRegistry
    authenticator: Authenticator

    def _principal(self, bearer_token: str | None) -> McpPrincipal:
        if not bearer_token:
            raise McpAuthenticationError("MCP authentication is required")
        principal = self.authenticator(bearer_token)
        if principal is None:
            raise McpAuthenticationError("MCP authentication failed")
        return principal

    def list_tools(self, *, bearer_token: str | None) -> tuple[dict[str, Any], ...]:
        """Return metadata only; handlers and credentials never leave the process."""
        self._principal(bearer_token)
        return tuple(
            {
                "name": definition.name,
                "source": definition.source,
                "version": definition.version,
                "permissions": tuple(sorted(item.value for item in definition.permissions)),
                "scope_kinds": tuple(sorted(item.value for item in definition.scope_kinds)),
            }
            for definition in self.registry.definitions()
        )

    def call(
        self,
        *,
        bearer_token: str | None,
        tool_name: str,
        arguments: dict[str, Any],
        scope_kind: ToolScopeKind,
        scope_id: str,
        approval_id: str | None = None,
    ) -> Any:
        principal = self._principal(bearer_token)
        scope = ToolScope(scope_kind, scope_id)
        return self.registry.execute(
            tool_name,
            arguments,
            ToolCallContext(
                principal_id=principal.principal_id,
                scope=scope,
                allowed_scopes=principal.allowed_scopes,
                permissions=principal.permissions,
                approval_id=approval_id,
            ),
        )


@dataclass(frozen=True, slots=True)
class McpStdioServer:
    """Line-delimited JSON-RPC adapter; the caller owns stdin/stdout."""

    transport: AuthenticatedMcpTransport

    def handle(self, message: str) -> str:
        request: Any = {}
        try:
            request = json.loads(message)
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}
            token = params.get("auth_token")
            if method == "initialize":
                result: Any = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}}
            elif method == "tools/list":
                result = {"tools": list(self.transport.list_tools(bearer_token=token))}
            elif method == "tools/call":
                result = self.transport.call(
                    bearer_token=token,
                    tool_name=str(params["name"]),
                    arguments=dict(params.get("arguments") or {}),
                    scope_kind=ToolScopeKind(str(params.get("scope_kind", "workspace"))),
                    scope_id=str(params.get("scope_id", "workspace-local")),
                    approval_id=params.get("approval_id"),
                )
            else:
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "method not found"},
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "result": result},
                ensure_ascii=False,
                default=str,
            )
        except (KeyError, TypeError, ValueError, McpAuthenticationError, ToolCallError) as error:
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32001, "message": str(error)},
                },
                ensure_ascii=False,
            )

    def serve(self, input_stream: Any, output_stream: Any) -> None:
        for line in input_stream:
            if line.strip():
                output_stream.write(self.handle(line))
                output_stream.write("\n")
                output_stream.flush()


@dataclass(frozen=True, slots=True)
class McpSseAdapter:
    """Encode authenticated JSON-RPC responses as bounded SSE message events."""

    server: McpStdioServer
    max_event_bytes: int = 256_000

    def __post_init__(self) -> None:
        if not 1 <= self.max_event_bytes <= 1_000_000:
            raise ValueError("SSE event limit must be between 1 and 1000000 bytes")

    def event(self, message: str) -> str:
        response = self.server.handle(message)
        if len(response.encode("utf-8")) > self.max_event_bytes:
            response = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32002, "message": "SSE response exceeds limit"},
                },
                ensure_ascii=False,
            )
        lines = response.splitlines() or [""]
        return "event: message\n" + "".join(f"data: {line}\n" for line in lines) + "\n"
