from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event
from typing import Any, Protocol


class ScopedCoreClient(Protocol):
    """The intentionally narrow Core surface exposed to a plugin.

    Implementations must not expose SQLAlchemy objects, file paths or arbitrary
    query methods. This protocol is the plugin boundary, not a database API.
    """

    def get_read_model(self, name: str, identifier: str) -> dict[str, Any] | None: ...


class ScopedArtifactClient(Protocol):
    def get_metadata(self, artifact_id: str) -> dict[str, Any] | None: ...


class CancellationToken:
    def __init__(self, event: Event | None = None) -> None:
        self._event = event or Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise PluginCancelled("plugin invocation cancelled")


class PluginCancelled(RuntimeError):
    pass


class SecretHandle(Protocol):
    def resolve(self, name: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class PluginContext:
    core: ScopedCoreClient | None = None
    artifacts: ScopedArtifactClient | None = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("career_harness.plugin")
    )
    clock: type[datetime] = datetime
    secrets: SecretHandle | None = None
    cancellation: CancellationToken = field(default_factory=CancellationToken)

    def now(self) -> datetime:
        return self.clock.now(UTC)


class PluginHandler(Protocol):
    def __call__(self, payload: dict[str, Any], context: PluginContext) -> dict[str, Any]: ...
