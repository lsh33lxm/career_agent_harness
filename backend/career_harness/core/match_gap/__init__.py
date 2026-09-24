"""Evidence-aware Match/Gap policy over frozen canonical inputs."""

from career_harness.core.match_gap.models import (
    MATCH_POLICY_VERSION,
    EvidenceBindingInputRef,
    ExactRevisionRef,
    MatchAssessment,
    MatchClassification,
    MatchInputManifest,
    MatchPolicyInput,
    MatchReason,
    MatchReasonCode,
    OfficialCapabilityInputRef,
    PersonalCapabilityInputRef,
    ProjectCapabilityInputRef,
    RequirementInputRef,
    RequirementMatchResult,
)
from career_harness.core.match_gap.policy import MatchInputError, assess_match

__all__ = [
    "MATCH_POLICY_VERSION",
    "EvidenceBindingInputRef",
    "ExactRevisionRef",
    "MatchAssessment",
    "MatchClassification",
    "MatchInputError",
    "MatchInputManifest",
    "MatchPolicyInput",
    "MatchReason",
    "MatchReasonCode",
    "OfficialCapabilityInputRef",
    "PersonalCapabilityInputRef",
    "ProjectCapabilityInputRef",
    "RequirementInputRef",
    "RequirementMatchResult",
    "assess_match",
]
