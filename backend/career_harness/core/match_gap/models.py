from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from career_harness.core.capability import (
    CapabilityEvidenceAuthority,
    CapabilityEvidenceScope,
    CapabilityNode,
    EvidenceBinding,
    PersonalCapabilityState,
)
from career_harness.core.common import FrozenModel, OpaqueId
from career_harness.core.evidence import EvidenceRef
from career_harness.core.job import JobRequirement, JobRevision
from career_harness.core.opportunity import OpportunityDetail
from career_harness.core.project import (
    ProjectCapabilityBasis,
    ProjectCapabilityLevel,
    ProjectCapabilityState,
    ProjectEvidence,
)

MATCH_POLICY_VERSION = "match-policy-v1"


class MatchClassification(StrEnum):
    COVERED = "covered"
    QUICK_TO_STRENGTHEN = "quick_to_strengthen"
    CLEAR_GAP = "clear_gap"


class MatchReasonCode(StrEnum):
    PERSONAL_SCOPES_SATISFIED = "personal_scopes_satisfied"
    PERSONAL_SCOPE_PROGRESS = "personal_scope_progress"
    QUALIFIED_EVIDENCE_SUPPORT = "qualified_evidence_support"
    EVIDENCE_PROVENANCE_INCOMPLETE = "evidence_provenance_incomplete"
    UNQUALIFIED_EVIDENCE_EXCLUDED = "unqualified_evidence_excluded"
    PROJECT_CAPABILITY_PROXIMITY = "project_capability_proximity"
    NO_QUALIFIED_RECORDED_SUPPORT = "no_qualified_recorded_support"


class ExactRevisionRef(FrozenModel):
    entity_id: OpaqueId
    revision: int = Field(ge=1)


class RequirementInputRef(FrozenModel):
    requirement_id: OpaqueId
    revision: int = Field(ge=1)
    capability_id: OpaqueId
    graph_version_id: OpaqueId
    required_scopes: tuple[CapabilityEvidenceScope, ...] = Field(min_length=1)


class OfficialCapabilityInputRef(FrozenModel):
    capability_id: OpaqueId
    graph_version_id: OpaqueId


class PersonalCapabilityInputRef(FrozenModel):
    personal_state_id: OpaqueId
    revision: int = Field(ge=1)
    candidate_id: OpaqueId
    capability_id: OpaqueId


class EvidenceBindingInputRef(FrozenModel):
    binding_id: OpaqueId
    personal_state_id: OpaqueId
    personal_state_revision: int = Field(ge=1)
    capability_id: OpaqueId
    evidence_ref_id: OpaqueId | None = None
    project_evidence_id: OpaqueId | None = None
    project_evidence_revision: int | None = Field(default=None, ge=1)
    authority: CapabilityEvidenceAuthority
    scopes: tuple[CapabilityEvidenceScope, ...] = Field(min_length=1)


class ProjectCapabilityInputRef(FrozenModel):
    capability_state_id: OpaqueId
    revision: int = Field(ge=1)
    project_id: OpaqueId
    capability_id: OpaqueId
    state: ProjectCapabilityLevel
    basis: tuple[ProjectCapabilityBasis, ...] = Field(min_length=1)


class MatchInputManifest(FrozenModel):
    opportunity: ExactRevisionRef
    job: ExactRevisionRef
    requirements: tuple[RequirementInputRef, ...] = Field(min_length=1)
    official_capabilities: tuple[OfficialCapabilityInputRef, ...] = Field(min_length=1)
    personal_states: tuple[PersonalCapabilityInputRef, ...] = ()
    evidence_bindings: tuple[EvidenceBindingInputRef, ...] = ()
    project_capability_states: tuple[ProjectCapabilityInputRef, ...] = ()
    policy_version: Literal["match-policy-v1"] = MATCH_POLICY_VERSION


class MatchReason(FrozenModel):
    code: MatchReasonCode
    scopes: tuple[CapabilityEvidenceScope, ...] = ()
    binding_ids: tuple[OpaqueId, ...] = ()
    project_capability_states: tuple[ExactRevisionRef, ...] = ()


class RequirementMatchResult(FrozenModel):
    requirement: ExactRevisionRef
    classification: MatchClassification
    covered_scopes: tuple[CapabilityEvidenceScope, ...] = ()
    missing_scopes: tuple[CapabilityEvidenceScope, ...] = ()
    reasons: tuple[MatchReason, ...] = Field(min_length=1)


class MatchAssessment(FrozenModel):
    """Deterministic policy output; persistence adds durable identity and audit events."""

    inputs: MatchInputManifest
    requirements: tuple[RequirementMatchResult, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def every_requirement_has_one_complete_result(self) -> Self:
        expected = {
            (item.requirement_id, item.revision): set(item.required_scopes)
            for item in self.inputs.requirements
        }
        actual = [
            (item.requirement.entity_id, item.requirement.revision) for item in self.requirements
        ]
        if len(actual) != len(set(actual)) or set(actual) != set(expected):
            raise ValueError("assessment must contain exactly one result per frozen requirement")
        for item in self.requirements:
            key = (item.requirement.entity_id, item.requirement.revision)
            covered = set(item.covered_scopes)
            missing = set(item.missing_scopes)
            if covered & missing or covered | missing != expected[key]:
                raise ValueError("covered and missing scopes must partition required scopes")
        return self


class MatchPolicyInput(FrozenModel):
    opportunity: OpportunityDetail
    job: JobRevision
    requirements: tuple[JobRequirement, ...] = Field(min_length=1)
    official_capabilities: tuple[CapabilityNode, ...] = Field(min_length=1)
    candidate_id: OpaqueId
    personal_states: tuple[PersonalCapabilityState, ...] = ()
    evidence_bindings: tuple[EvidenceBinding, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    project_evidence: tuple[ProjectEvidence, ...] = ()
    project_capability_states: tuple[ProjectCapabilityState, ...] = ()
    policy_version: Literal["match-policy-v1"] = MATCH_POLICY_VERSION
