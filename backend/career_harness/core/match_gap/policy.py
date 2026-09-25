from __future__ import annotations

from collections.abc import Iterable

from career_harness.core.capability import (
    CapabilityEvidenceAuthority,
    CapabilityEvidenceScope,
    EvidenceBinding,
    PersonalCapabilityState,
)
from career_harness.core.job import JobRequirement, JobRequirementStatus
from career_harness.core.match_gap.models import (
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
from career_harness.core.project import (
    ProjectCapabilityState,
    ProjectEvidence,
    ProjectEvidenceFreshness,
    ProjectEvidenceReviewStatus,
)


class MatchInputError(ValueError):
    pass


_SCOPE_ORDER = {scope: ordinal for ordinal, scope in enumerate(CapabilityEvidenceScope)}


def assess_match(inputs: MatchPolicyInput) -> MatchAssessment:
    indexed = _validate_and_index(inputs)
    requirements = tuple(
        sorted(inputs.requirements, key=lambda item: (item.requirement_id, item.revision))
    )
    manifest = _build_manifest(inputs, requirements)
    results = tuple(
        _assess_requirement(
            requirement,
            indexed.personal_states.get(requirement.capability_id),
            indexed.bindings.get(requirement.capability_id, ()),
            indexed.project_evidence,
            indexed.project_states.get(requirement.capability_id, ()),
        )
        for requirement in requirements
    )
    return MatchAssessment(inputs=manifest, requirements=results)


class _IndexedInputs:
    def __init__(
        self,
        *,
        personal_states: dict[str, PersonalCapabilityState],
        bindings: dict[str, tuple[EvidenceBinding, ...]],
        project_evidence: dict[tuple[str, int], ProjectEvidence],
        project_states: dict[str, tuple[ProjectCapabilityState, ...]],
    ) -> None:
        self.personal_states = personal_states
        self.bindings = bindings
        self.project_evidence = project_evidence
        self.project_states = project_states


def _validate_and_index(inputs: MatchPolicyInput) -> _IndexedInputs:
    opportunity_job = inputs.opportunity.job
    if (opportunity_job.job_id, opportunity_job.revision) != (
        inputs.job.job_id,
        inputs.job.revision,
    ):
        raise MatchInputError("opportunity and Job revision must match exactly")

    requirements_by_id: dict[str, JobRequirement] = {}
    required_capabilities: set[tuple[str, str]] = set()
    for requirement in inputs.requirements:
        if requirement.requirement_id in requirements_by_id:
            raise MatchInputError("assessment cannot contain multiple revisions of one requirement")
        requirements_by_id[requirement.requirement_id] = requirement
        if requirement.status is not JobRequirementStatus.ACCEPTED:
            raise MatchInputError("only accepted JobRequirements can enter Match")
        if requirement.job != opportunity_job:
            raise MatchInputError("JobRequirement must reference the frozen Opportunity Job")
        if requirement.capability_id is None or requirement.graph_version_id is None:
            raise MatchInputError("accepted JobRequirement requires an official capability mapping")
        required_capabilities.add((requirement.capability_id, requirement.graph_version_id))

    node_keys = [
        (node.capability_id, node.graph_version_id) for node in inputs.official_capabilities
    ]
    if len(node_keys) != len(set(node_keys)):
        raise MatchInputError("official capability inputs must be unique")
    if set(node_keys) != required_capabilities:
        raise MatchInputError("official capability inputs must exactly match requirement mappings")

    required_capability_ids = {item[0] for item in required_capabilities}
    personal_states: dict[str, PersonalCapabilityState] = {}
    personal_state_refs: set[tuple[str, int]] = set()
    for state in inputs.personal_states:
        if state.candidate_id != inputs.candidate_id:
            raise MatchInputError("personal capability state belongs to another candidate")
        if state.capability_id not in required_capability_ids:
            raise MatchInputError("personal capability state is unrelated to this Match input")
        if state.capability_id in personal_states:
            raise MatchInputError("personal capability identity is ambiguous for this capability")
        ref = (state.personal_state_id, state.revision)
        if ref in personal_state_refs:
            raise MatchInputError("personal capability state inputs must be unique")
        personal_state_refs.add(ref)
        personal_states[state.capability_id] = state

    evidence_ref_ids = [item.evidence_ref_id for item in inputs.evidence_refs]
    if len(evidence_ref_ids) != len(set(evidence_ref_ids)):
        raise MatchInputError("EvidenceRef inputs must be unique")
    project_evidence_refs = [(item.evidence_id, item.revision) for item in inputs.project_evidence]
    if len(project_evidence_refs) != len(set(project_evidence_refs)):
        raise MatchInputError("Project Evidence inputs must be unique")
    evidence_ref_set = set(evidence_ref_ids)
    project_evidence = {(item.evidence_id, item.revision): item for item in inputs.project_evidence}

    bindings_by_capability: dict[str, list[EvidenceBinding]] = {}
    binding_ids: set[str] = set()
    used_evidence_refs: set[str] = set()
    used_project_evidence_refs: set[tuple[str, int]] = set()
    for binding in inputs.evidence_bindings:
        if binding.binding_id in binding_ids:
            raise MatchInputError("EvidenceBinding inputs must be unique")
        binding_ids.add(binding.binding_id)
        state = personal_states.get(binding.capability_id)
        if state is None or (
            binding.personal_state_id,
            binding.personal_state_revision,
        ) != (state.personal_state_id, state.revision):
            raise MatchInputError("EvidenceBinding must reference the exact personal state input")
        if binding.evidence_ref_id is not None:
            if binding.evidence_ref_id not in evidence_ref_set:
                raise MatchInputError("EvidenceBinding source EvidenceRef is missing")
            used_evidence_refs.add(binding.evidence_ref_id)
        else:
            project_ref = (binding.project_evidence_id, binding.project_evidence_revision)
            if project_ref not in project_evidence:
                raise MatchInputError("EvidenceBinding source Project Evidence is missing")
            source = project_evidence[project_ref]
            if source.authority.value != binding.authority.value:
                raise MatchInputError("EvidenceBinding authority does not match Project Evidence")
            used_project_evidence_refs.add(project_ref)
        bindings_by_capability.setdefault(binding.capability_id, []).append(binding)

    if evidence_ref_set != used_evidence_refs:
        raise MatchInputError("EvidenceRef inputs must be exactly the referenced sources")
    if set(project_evidence) != used_project_evidence_refs:
        raise MatchInputError("Project Evidence inputs must be exactly the referenced sources")

    project_states_by_capability: dict[str, list[ProjectCapabilityState]] = {}
    project_state_ids: set[str] = set()
    for state in inputs.project_capability_states:
        if state.capability_state_id in project_state_ids:
            raise MatchInputError(
                "assessment cannot contain multiple revisions of one project state"
            )
        project_state_ids.add(state.capability_state_id)
        if state.capability_id not in required_capability_ids:
            raise MatchInputError("Project Capability State is unrelated to this Match input")
        project_states_by_capability.setdefault(state.capability_id, []).append(state)

    return _IndexedInputs(
        personal_states=personal_states,
        bindings={
            capability_id: tuple(sorted(items, key=lambda item: item.binding_id))
            for capability_id, items in bindings_by_capability.items()
        },
        project_evidence=project_evidence,
        project_states={
            capability_id: tuple(
                sorted(items, key=lambda item: (item.capability_state_id, item.revision))
            )
            for capability_id, items in project_states_by_capability.items()
        },
    )


def _assess_requirement(
    requirement: JobRequirement,
    personal_state: PersonalCapabilityState | None,
    bindings: tuple[EvidenceBinding, ...],
    project_evidence: dict[tuple[str, int], ProjectEvidence],
    project_states: tuple[ProjectCapabilityState, ...],
) -> RequirementMatchResult:
    required = set(requirement.required_scopes)
    personal_scopes = _personal_scopes(personal_state) & required
    qualified_bindings = tuple(
        binding for binding in bindings if _binding_is_qualified(binding, project_evidence)
    )
    unqualified_bindings = tuple(
        binding for binding in bindings if binding not in qualified_bindings
    )
    qualified_scopes = {
        scope for binding in qualified_bindings for scope in binding.scopes if scope in required
    }
    covered = personal_scopes & qualified_scopes
    missing = required - covered

    reasons: list[MatchReason] = []
    if personal_scopes == required:
        reasons.append(
            MatchReason(
                code=MatchReasonCode.PERSONAL_SCOPES_SATISFIED,
                scopes=_ordered_scopes(personal_scopes),
            )
        )
    elif personal_scopes:
        reasons.append(
            MatchReason(
                code=MatchReasonCode.PERSONAL_SCOPE_PROGRESS,
                scopes=_ordered_scopes(personal_scopes),
            )
        )

    if qualified_scopes:
        reasons.append(
            MatchReason(
                code=MatchReasonCode.QUALIFIED_EVIDENCE_SUPPORT,
                scopes=_ordered_scopes(qualified_scopes),
                binding_ids=tuple(
                    binding.binding_id
                    for binding in qualified_bindings
                    if required & set(binding.scopes)
                ),
            )
        )
    if unqualified_bindings:
        relevant = tuple(
            binding.binding_id for binding in unqualified_bindings if required & set(binding.scopes)
        )
        if relevant:
            reasons.append(
                MatchReason(
                    code=MatchReasonCode.UNQUALIFIED_EVIDENCE_EXCLUDED,
                    binding_ids=relevant,
                )
            )

    if not missing:
        classification = MatchClassification.COVERED
    elif personal_scopes or qualified_scopes or project_states:
        # Any canonical ProjectCapabilityState is qualified by construction: the model
        # enforces a state-appropriate basis. It contributes proximity only, never coverage.
        classification = MatchClassification.QUICK_TO_STRENGTHEN
        if required - qualified_scopes:
            reasons.append(
                MatchReason(
                    code=MatchReasonCode.EVIDENCE_PROVENANCE_INCOMPLETE,
                    scopes=_ordered_scopes(required - qualified_scopes),
                )
            )
        if project_states:
            reasons.append(
                MatchReason(
                    code=MatchReasonCode.PROJECT_CAPABILITY_PROXIMITY,
                    project_capability_states=tuple(
                        ExactRevisionRef(
                            entity_id=state.capability_state_id,
                            revision=state.revision,
                        )
                        for state in project_states
                    ),
                )
            )
    else:
        classification = MatchClassification.CLEAR_GAP
        reasons.append(MatchReason(code=MatchReasonCode.NO_QUALIFIED_RECORDED_SUPPORT))

    return RequirementMatchResult(
        requirement=ExactRevisionRef(
            entity_id=requirement.requirement_id,
            revision=requirement.revision,
        ),
        classification=classification,
        covered_scopes=_ordered_scopes(covered),
        missing_scopes=_ordered_scopes(missing),
        reasons=tuple(reasons),
    )


def _binding_is_qualified(
    binding: EvidenceBinding,
    project_evidence: dict[tuple[str, int], ProjectEvidence],
) -> bool:
    if binding.authority is CapabilityEvidenceAuthority.AI_INFERRED:
        return False
    if binding.evidence_ref_id is not None:
        return True
    source = project_evidence[(binding.project_evidence_id, binding.project_evidence_revision)]
    return (
        source.review_status is ProjectEvidenceReviewStatus.ACCEPTED
        and source.freshness is ProjectEvidenceFreshness.CURRENT
    )


def _personal_scopes(
    state: PersonalCapabilityState | None,
) -> set[CapabilityEvidenceScope]:
    if state is None:
        return set()
    # CapabilityEvidenceScope values must stay name-identical to PersonalCapabilityState fields.
    return {scope for scope in CapabilityEvidenceScope if bool(getattr(state, scope.value))}


def _ordered_scopes(
    scopes: Iterable[CapabilityEvidenceScope],
) -> tuple[CapabilityEvidenceScope, ...]:
    return tuple(sorted(set(scopes), key=_SCOPE_ORDER.__getitem__))


def _build_manifest(
    inputs: MatchPolicyInput,
    requirements: tuple[JobRequirement, ...],
) -> MatchInputManifest:
    return MatchInputManifest(
        opportunity=ExactRevisionRef(
            entity_id=inputs.opportunity.opportunity.entity_id,
            revision=inputs.opportunity.opportunity.revision,
        ),
        job=ExactRevisionRef(entity_id=inputs.job.job_id, revision=inputs.job.revision),
        requirements=tuple(
            RequirementInputRef(
                requirement_id=item.requirement_id,
                revision=item.revision,
                capability_id=item.capability_id,
                graph_version_id=item.graph_version_id,
                required_scopes=_ordered_scopes(item.required_scopes),
            )
            for item in requirements
        ),
        official_capabilities=tuple(
            OfficialCapabilityInputRef(
                capability_id=item.capability_id,
                graph_version_id=item.graph_version_id,
            )
            for item in sorted(
                inputs.official_capabilities,
                key=lambda item: (item.capability_id, item.graph_version_id),
            )
        ),
        personal_states=tuple(
            PersonalCapabilityInputRef(
                personal_state_id=item.personal_state_id,
                revision=item.revision,
                candidate_id=item.candidate_id,
                capability_id=item.capability_id,
            )
            for item in sorted(
                inputs.personal_states,
                key=lambda item: (item.capability_id, item.personal_state_id, item.revision),
            )
        ),
        evidence_bindings=tuple(
            EvidenceBindingInputRef(
                binding_id=item.binding_id,
                personal_state_id=item.personal_state_id,
                personal_state_revision=item.personal_state_revision,
                capability_id=item.capability_id,
                evidence_ref_id=item.evidence_ref_id,
                project_evidence_id=item.project_evidence_id,
                project_evidence_revision=item.project_evidence_revision,
                authority=item.authority,
                scopes=_ordered_scopes(item.scopes),
            )
            for item in sorted(inputs.evidence_bindings, key=lambda item: item.binding_id)
        ),
        project_capability_states=tuple(
            ProjectCapabilityInputRef(
                capability_state_id=item.capability_state_id,
                revision=item.revision,
                project_id=item.project_id,
                capability_id=item.capability_id,
                state=item.state,
                basis=tuple(
                    sorted(
                        item.basis,
                        key=lambda basis: (
                            basis.kind.value,
                            basis.reference_id,
                            basis.reference_revision,
                        ),
                    )
                ),
            )
            for item in sorted(
                inputs.project_capability_states,
                key=lambda item: (item.capability_id, item.capability_state_id, item.revision),
            )
        ),
        policy_version=inputs.policy_version,
    )
