from __future__ import annotations

import io
import json

import pytest

from career_harness.adapters.mcp_transport import (
    AuthenticatedMcpTransport,
    McpAuthenticationError,
    McpPrincipal,
    McpSseAdapter,
    McpStdioServer,
)
from career_harness.core.tools.registry import (
    ToolCallError,
    ToolDefinition,
    ToolPermission,
    ToolRegistry,
    ToolScope,
    ToolScopeKind,
)


def _transport() -> AuthenticatedMcpTransport:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="knowledge.search",
            source="builtin://knowledge",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
            permissions=frozenset({ToolPermission.READ}),
            scope_kinds=frozenset({ToolScopeKind.WORKSPACE}),
            handler=lambda args: {"query": args["query"]},
        )
    )
    scope = ToolScope(ToolScopeKind.WORKSPACE, "workspace-local")
    return AuthenticatedMcpTransport(
        registry=registry,
        authenticator=lambda token: (
            McpPrincipal("local-user", frozenset({scope}), frozenset({ToolPermission.READ}))
            if token == "valid-token"
            else None
        ),
    )


def test_mcp_transport_requires_authentication_and_preserves_scope() -> None:
    transport = _transport()
    with pytest.raises(McpAuthenticationError):
        transport.list_tools(bearer_token=None)
    with pytest.raises(McpAuthenticationError):
        transport.list_tools(bearer_token="invalid")
    assert transport.call(
        bearer_token="valid-token",
        tool_name="knowledge.search",
        arguments={"query": "resume"},
        scope_kind=ToolScopeKind.WORKSPACE,
        scope_id="workspace-local",
    ) == {"query": "resume"}


def test_mcp_transport_cannot_expand_scope_or_permissions() -> None:
    transport = _transport()
    with pytest.raises(ToolCallError):
        transport.call(
            bearer_token="valid-token",
            tool_name="knowledge.search",
            arguments={"query": "resume"},
            scope_kind=ToolScopeKind.WORKSPACE,
            scope_id="other-workspace",
        )


def test_stdio_adapter_handles_tools_and_redacts_auth_from_protocol_output() -> None:
    server = McpStdioServer(_transport())
    listed = json.loads(
        server.handle(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/list",
            "params": {"auth_token": "valid-token"},
        }))
    )
    assert listed["result"]["tools"][0]["name"] == "knowledge.search"
    called = json.loads(
        server.handle(json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "auth_token": "valid-token", "name": "knowledge.search",
                "arguments": {"query": "resume"},
            },
        }))
    )
    assert called["result"] == {"query": "resume"}
    output = io.StringIO()
    server.serve(
        io.StringIO(
            '{"jsonrpc":"2.0","id":3,"method":"tools/list",'
            '"params":{"auth_token":"valid-token"}}\n'
        ),
        output,
    )
    assert "valid-token" not in output.getvalue()


def test_sse_adapter_reuses_authenticated_handler_and_bounds_output() -> None:
    server = McpStdioServer(_transport())
    adapter = McpSseAdapter(server, max_event_bytes=1000)
    event = adapter.event(json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "tools/list",
        "params": {"auth_token": "valid-token"},
    }))
    assert event.startswith("event: message\ndata: ")
    assert "knowledge.search" in event
    assert "valid-token" not in event

    bounded = McpSseAdapter(server, max_event_bytes=1).event(json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "tools/list",
        "params": {"auth_token": "valid-token"},
    }))
    assert "SSE response exceeds limit" in bounded


def test_stdio_adapter_bounds_incoming_messages() -> None:
    server = McpStdioServer(_transport(), max_message_bytes=16)
    response = json.loads(server.handle('{"method":"tools/list"}'))
    assert response["error"]["code"] == -32001
    assert "message limit" in response["error"]["message"]
