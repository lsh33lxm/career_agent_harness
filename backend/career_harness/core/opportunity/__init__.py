"""User-qualified opportunity boundary; not an application."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Opportunity, OpportunityState

ENTITY_KIND = EntityKind.OPPORTUNITY

__all__ = ["ENTITY_KIND", "Opportunity", "OpportunityState"]
