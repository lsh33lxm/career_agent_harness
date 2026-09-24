from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")


class ToolPermission(StrEnum):
    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    FILESYSTEM = "filesystem"


class ToolScopeKind(StrEnum):
    USER = "user"
    WORKSPACE = "workspace"
    KNOWLEDGE_BASE = "knowledge_base"
    CAPABILITY = "capability"


class ToolFailureCategory(StrEnum):
    NOT_FOUND = "not_found"
    VALIDATION = "validation"
    PERMISSION = "permission"
    APPROVAL = "approval"
    EXECUTION = "execution"
    OUTPUT_LIMIT = "output_limit"


class ToolCallError(RuntimeError):
    def __init__(self, category: ToolFailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True, slots=True)
class ToolScope:
    kind: ToolScopeKind
    scope_id: str


@dataclass(frozen=True, slots=True)
class ToolCallContext:
    principal_id: str
    scope: ToolScope
    allowed_scopes: frozenset[ToolScope]
    permissions: frozenset[ToolPermission]
    approval_id: str | None = None


ToolHandler = Callable[[dict[str, Any]], Any]
DeferredToolLoader = Callable[[], ToolHandler]
ApprovalChecker = Callable[[str, str, str], bool]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    source: str
    version: str
    input_schema: dict[str, Any]
    permissions: frozenset[ToolPermission]
    scope_kinds: frozenset[ToolScopeKind]
    output_limit_bytes: int = 64_000
    handler: ToolHandler | None = None
    deferred_loader: DeferredToolLoader | None = None

    def __post_init__(self) -> None:
        if not _TOOL_NAME.fullmatch(self.name):
            raise ValueError("tool name must use a stable namespaced identifier")
        if self.input_schema.get("type") != "object":
            raise ValueError("tool input schema must describe an object")
        if (self.handler is None) == (self.deferred_loader is None):
            raise ValueError("tool must define exactly one handler or deferred loader")
        if not 1 <= self.output_limit_bytes <= 1_000_000:
            raise ValueError("tool output limit must be between 1 and 1000000 bytes")


class ToolAuditSink(Protocol):
    def record(
        self,
        *,
        definition: ToolDefinition,
        context: ToolCallContext,
        status: str,
        failure_category: ToolFailureCategory | None,
    ) -> None: ...


class NullToolAuditSink:
    def record(
        self,
        *,
        definition: ToolDefinition,
        context: ToolCallContext,
        status: str,
        failure_category: ToolFailureCategory | None,
    ) -> None:
        return None


class ToolRegistry:
    def __init__(
        self,
        *,
        approval_checker: ApprovalChecker | None = None,
        audit_sink: ToolAuditSink | None = None,
    ) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._loaded: dict[str, ToolHandler] = {}
        self._approval_checker = approval_checker or (lambda _principal, _approval, _tool: False)
        self._audit = audit_sink or NullToolAuditSink()

    def register(self, definition: ToolDefinition) -> bool:
        """Register once. A later name collision cannot replace the first definition."""
        if definition.name in self._tools:
            return False
        self._tools[definition.name] = definition
        return True

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools[name] for name in sorted(self._tools))

    def execute(
        self, name: str, arguments: dict[str, Any], context: ToolCallContext
    ) -> Any:
        definition = self._tools.get(name)
        if definition is None:
            raise ToolCallError(ToolFailureCategory.NOT_FOUND, "tool is not registered")
        try:
            normalized = self._authorize_and_validate(definition, arguments, context)
            handler = self._handler(definition)
            output = handler(normalized)
            encoded = json.dumps(
                output, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
            if len(encoded) > definition.output_limit_bytes:
                raise ToolCallError(
                    ToolFailureCategory.OUTPUT_LIMIT, "tool output exceeds the configured limit"
                )
        except ToolCallError as error:
            self._audit.record(
                definition=definition,
                context=context,
                status="failed",
                failure_category=error.category,
            )
            raise
        except Exception as error:
            self._audit.record(
                definition=definition,
                context=context,
                status="failed",
                failure_category=ToolFailureCategory.EXECUTION,
            )
            raise ToolCallError(ToolFailureCategory.EXECUTION, "tool execution failed") from error
        self._audit.record(
            definition=definition,
            context=context,
            status="completed",
            failure_category=None,
        )
        return output

    def _authorize_and_validate(
        self,
        definition: ToolDefinition,
        arguments: dict[str, Any],
        context: ToolCallContext,
    ) -> dict[str, Any]:
        if context.scope not in context.allowed_scopes:
            raise ToolCallError(
                ToolFailureCategory.PERMISSION, "principal lacks the requested scope"
            )
        if context.scope.kind not in definition.scope_kinds:
            raise ToolCallError(ToolFailureCategory.PERMISSION, "tool is unavailable in this scope")
        if not definition.permissions <= context.permissions:
            raise ToolCallError(ToolFailureCategory.PERMISSION, "principal lacks tool permissions")
        if ToolPermission.WRITE in definition.permissions:
            approval = context.approval_id
            if approval is None or not self._approval_checker(
                context.principal_id, approval, definition.name
            ):
                raise ToolCallError(
                    ToolFailureCategory.APPROVAL, "write tool requires a valid approval"
                )
        return _validate_object(arguments, definition.input_schema)

    def _handler(self, definition: ToolDefinition) -> ToolHandler:
        if definition.handler is not None:
            return definition.handler
        existing = self._loaded.get(definition.name)
        if existing is not None:
            return existing
        assert definition.deferred_loader is not None
        loaded = definition.deferred_loader()
        self._loaded[definition.name] = loaded
        return loaded


def _validate_object(arguments: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    required = set(schema.get("required", ()))
    unknown = set(arguments) - set(properties)
    if unknown and schema.get("additionalProperties", True) is False:
        raise ToolCallError(ToolFailureCategory.VALIDATION, "tool arguments contain unknown fields")
    missing = required - set(arguments)
    if missing:
        raise ToolCallError(ToolFailureCategory.VALIDATION, "tool arguments are missing fields")
    normalized = dict(arguments)
    for name, value in arguments.items():
        expected = properties.get(name, {}).get("type")
        try:
            normalized[name] = _coerce(value, expected)
        except (TypeError, ValueError) as error:
            raise ToolCallError(
                ToolFailureCategory.VALIDATION, f"tool argument {name} has an invalid type"
            ) from error
    return normalized


def _coerce(value: Any, expected: str | None) -> Any:
    if expected == "string":
        if not isinstance(value, str):
            raise TypeError
    elif expected == "integer":
        if isinstance(value, bool):
            raise TypeError
        if isinstance(value, str) and re.fullmatch(r"-?\d+", value):
            return int(value)
        if not isinstance(value, int):
            raise TypeError
    elif expected == "number":
        if isinstance(value, bool):
            raise TypeError
        if isinstance(value, str):
            return float(value)
        if not isinstance(value, int | float):
            raise TypeError
    elif expected == "boolean":
        if isinstance(value, str) and value.casefold() in {"true", "false"}:
            return value.casefold() == "true"
        if not isinstance(value, bool):
            raise TypeError
    elif (expected == "array" and not isinstance(value, list)) or (
        expected == "object" and not isinstance(value, dict)
    ):
        raise TypeError
    return value
