"""Frozen input and reproducibility snapshot boundary."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Snapshot

ENTITY_KIND = EntityKind.SNAPSHOT

__all__ = ["ENTITY_KIND", "Snapshot"]
