"""Application preparation and user-confirmed submission boundary."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import (
    Application,
    ApplicationState,
    FormPreparation,
    SubmissionAuthority,
)

ENTITY_KIND = EntityKind.APPLICATION

__all__ = [
    "Application",
    "ApplicationState",
    "ENTITY_KIND",
    "FormPreparation",
    "SubmissionAuthority",
]
