from __future__ import annotations

import pytest

from career_harness.adapters.mcp_transport import (
    AuthenticatedMcpTransport,
    McpAuthenticationError,
    McpPrincipal,
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
