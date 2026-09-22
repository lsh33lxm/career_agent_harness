"""Authenticated MCP transport boundary for local adapters.

This module deliberately does not open sockets or spawn processes. A future
stdio/SSE adapter can delegate authentication and tool calls here so transport
details cannot bypass the existing ToolRegistry policy.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from career_harness.core.tools.registry import (
    ToolCallContext,
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
