"""Human approval boundary; agents cannot self-approve."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import ActorKind, Approval, ApprovalPurpose, ApprovalStatus

ENTITY_KIND = EntityKind.APPROVAL

__all__ = ["ActorKind", "Approval", "ApprovalPurpose", "ApprovalStatus", "ENTITY_KIND"]
