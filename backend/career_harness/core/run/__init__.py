"""Auditable run and step execution boundary."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Run, RunState

ENTITY_KIND = EntityKind.RUN

__all__ = ["ENTITY_KIND", "Run", "RunState"]
