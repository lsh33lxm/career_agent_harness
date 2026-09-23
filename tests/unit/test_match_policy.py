import pytest

from career_harness.core.capability import (
    CapabilityEvidenceAuthority,
    CapabilityEvidenceScope,
    CapabilityLayer,
    CapabilityNode,
    EvidenceBinding,
    PersonalCapabilityState,
)
from career_harness.core.evidence import EvidenceRef
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind, Opportunity, OpportunityState
from career_harness.core.match_gap import (
    MatchClassification,
    MatchInputError,
    MatchPolicyInput,
    MatchReasonCode,
    assess_match,
)
from career_harness.core.opportunity import OpportunityDetail
from career_harness.core.project import (
    ProjectCapabilityBasis,
    ProjectCapabilityBasisKind,
    ProjectCapabilityLevel,
    ProjectCapabilityState,
    ProjectEvidence,
    ProjectEvidenceAuthority,
    ProjectEvidenceFreshness,
    ProjectEvidenceReviewStatus,
    ProjectSourceEntry,
    ProjectSourceManifest,
)


def _job() -> JobRevision:
    return JobRevision(
        job_id="job_001",
        revision=2,
        content_sha256="a" * 64,
        source_evidence_refs=("evidence_job",),
    )


def _opportunity() -> OpportunityDetail:
    return OpportunityDetail(
        opportunity=Opportunity(
            entity_id="opportunity_001",
            revision=3,
            state=OpportunityState.PREPARING,
        ),
        job=JobRef(job_id="job_001", revision=2),
    )


def _requirement(
    requirement_id: str = "requirement_001",
    *,
    status: JobRequirementStatus = JobRequirementStatus.ACCEPTED,
) -> JobRequirement:
    review = (
        {
            "reviewed_by": "user",
            "reviewed_by_kind": ActorKind.USER,
            "review_reason": "Confirmed against the captured job description.",
            "reviewed_at": "2026-09-19T00:00:00Z",
        }
        if status is not JobRequirementStatus.PROPOSED
        else {}
    )
    return JobRequirement(
        requirement_id=requirement_id,
        revision=2,
        job=JobRef(job_id="job_001", revision=2),
        requirement_text="Build and explain reliable agent workflows.",
        importance=JobRequirementImportance.REQUIRED,
        capability_id="capability_agents",
        graph_version_id="graph_001",
        required_scopes=(
            CapabilityEvidenceScope.UNDERSTAND,
            CapabilityEvidenceScope.APPLY,
        ),
        source_evidence_refs=("evidence_job",),
        status=status,
        proposed_by="agent:extractor",
        proposed_by_kind=ActorKind.AGENT,
        **review,
    )


def _node() -> CapabilityNode:
    return CapabilityNode(
        capability_id="capability_agents",
        canonical_name="Agent Engineering",
        description="Build reliable agent systems.",
        layer=CapabilityLayer.TRACK,
        graph_version_id="graph_001",
    )


def _personal_state(
    personal_state_id: str = "personal_agents",
    *,
    understand: bool = True,
    apply: bool = True,
) -> PersonalCapabilityState:
    return PersonalCapabilityState(
        personal_state_id=personal_state_id,
        candidate_id="candidate_001",
        capability_id="capability_agents",
        understand=understand,
        apply=apply,
        revision=4,
        updated_by="user",
        updated_by_kind=ActorKind.USER,
    )


def _evidence_ref(evidence_ref_id: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_ref_id=evidence_ref_id,
        snapshot_id=f"snapshot_{evidence_ref_id}",
        artifact_id=f"artifact_{evidence_ref_id}",
    )


def _binding(
    binding_id: str,
    scope: CapabilityEvidenceScope,
    *,
    authority: CapabilityEvidenceAuthority = CapabilityEvidenceAuthority.DOCUMENT_SUPPORTED,
    evidence_ref_id: str | None = None,
    project_evidence_id: str | None = None,
) -> EvidenceBinding:
    return EvidenceBinding(
        binding_id=binding_id,
        personal_state_id="personal_agents",
        personal_state_revision=4,
        capability_id="capability_agents",
        evidence_ref_id=evidence_ref_id,
        project_evidence_id=project_evidence_id,
        project_evidence_revision=1 if project_evidence_id is not None else None,
        authority=authority,
        scopes=(scope,),
        bound_by="user",
    )


def _project_evidence(
    *,
    freshness: ProjectEvidenceFreshness = ProjectEvidenceFreshness.CURRENT,
    review_status: ProjectEvidenceReviewStatus = ProjectEvidenceReviewStatus.ACCEPTED,
) -> ProjectEvidence:
    return ProjectEvidence(
        evidence_id="project_evidence_001",
        project_id="project_001",
        summary="A validated implementation is present.",
        source_manifest=ProjectSourceManifest(
            manifest_id="manifest_001",
            scan_scope_id="scope_001",
            scan_scope_revision=1,
            entries=(
                ProjectSourceEntry(
                    relative_path="src/agent.py",
                    sha256="b" * 64,
                    byte_length=100,
                ),
            ),
        ),
        scanner="test-scanner",
        scanner_version="1",
        authority=ProjectEvidenceAuthority.DOCUMENT_SUPPORTED,
        freshness=freshness,
        review_status=review_status,
        reviewed_by="evidence-rule-v1",
        reviewed_by_kind="rule",
        review_reason="Documented and reviewed.",
        revision=1,
        created_by="scanner",
    )


def _project_state() -> ProjectCapabilityState:
    return ProjectCapabilityState(
        capability_state_id="project_state_agents",
        project_id="project_001",
        capability_id="capability_agents",
        state=ProjectCapabilityLevel.VALIDATED,
        basis=(
            ProjectCapabilityBasis(
                kind=ProjectCapabilityBasisKind.VALIDATION_EVIDENCE,
                reference_id="project_evidence_001",
                reference_revision=1,
            ),
        ),
        finalized_at="2026-09-19T00:00:00Z",
        revision=2,
        created_by="rule",
    )


def _project_state_existing() -> ProjectCapabilityState:
    return ProjectCapabilityState(
        capability_state_id="project_state_existing",
        project_id="project_001",
        capability_id="capability_agents",
        state=ProjectCapabilityLevel.EXISTING,
        basis=(
            ProjectCapabilityBasis(
                kind=ProjectCapabilityBasisKind.DOCUMENT_EVIDENCE,
                reference_id="document_001",
                reference_revision=1,
            ),
            ProjectCapabilityBasis(
                kind=ProjectCapabilityBasisKind.CODE_EVIDENCE,
                reference_id="code_001",
                reference_revision=3,
            ),
        ),
        finalized_at="2026-09-19T00:00:00Z",
        revision=1,
        created_by="rule",
    )


def _inputs(
    *,
    requirements: tuple[JobRequirement, ...] | None = None,
    personal_states: tuple[PersonalCapabilityState, ...] | None = None,
    bindings: tuple[EvidenceBinding, ...] = (),
    evidence_refs: tuple[EvidenceRef, ...] = (),
    project_evidence: tuple[ProjectEvidence, ...] = (),
    project_states: tuple[ProjectCapabilityState, ...] = (),
) -> MatchPolicyInput:
    return MatchPolicyInput(
        opportunity=_opportunity(),
        job=_job(),
        requirements=requirements or (_requirement(),),
        official_capabilities=(_node(),),
        candidate_id="candidate_001",
        personal_states=personal_states if personal_states is not None else (_personal_state(),),
        evidence_bindings=bindings,
        evidence_refs=evidence_refs,
        project_evidence=project_evidence,
        project_capability_states=project_states,
    )


def test_covered_requires_personal_dimensions_and_qualified_evidence_intersection() -> None:
    bindings = (
        _binding(
            "binding_apply",
            CapabilityEvidenceScope.APPLY,
            evidence_ref_id="evidence_apply",
        ),
        _binding(
            "binding_understand",
            CapabilityEvidenceScope.UNDERSTAND,
            evidence_ref_id="evidence_understand",
        ),
    )
    assessment = assess_match(
        _inputs(
            bindings=bindings,
            evidence_refs=(
                _evidence_ref("evidence_understand"),
                _evidence_ref("evidence_apply"),
            ),
        )
    )

    result = assessment.requirements[0]
    assert result.classification is MatchClassification.COVERED
    assert result.covered_scopes == (
        CapabilityEvidenceScope.UNDERSTAND,
        CapabilityEvidenceScope.APPLY,
    )
    assert {reason.code for reason in result.reasons} == {
        MatchReasonCode.PERSONAL_SCOPES_SATISFIED,
        MatchReasonCode.QUALIFIED_EVIDENCE_SUPPORT,
    }
    assert "score" not in assessment.model_dump()


def test_partial_personal_progress_is_quick_to_strengthen() -> None:
    result = assess_match(_inputs(personal_states=(_personal_state(apply=False),))).requirements[0]

    assert result.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert result.covered_scopes == ()
    assert MatchReasonCode.PERSONAL_SCOPE_PROGRESS in {reason.code for reason in result.reasons}


def test_project_capability_is_proximity_but_never_personal_coverage() -> None:
    result = assess_match(
        _inputs(personal_states=(), project_states=(_project_state(),))
    ).requirements[0]

    assert result.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert result.covered_scopes == ()
    assert result.missing_scopes == (
        CapabilityEvidenceScope.UNDERSTAND,
        CapabilityEvidenceScope.APPLY,
    )
    assert MatchReasonCode.PROJECT_CAPABILITY_PROXIMITY in {
        reason.code for reason in result.reasons
    }


def test_no_recorded_support_is_a_clear_gap_without_claiming_objective_lack() -> None:
    result = assess_match(_inputs(personal_states=())).requirements[0]

    assert result.classification is MatchClassification.CLEAR_GAP
    assert [reason.code for reason in result.reasons] == [
        MatchReasonCode.NO_QUALIFIED_RECORDED_SUPPORT
    ]


def test_ai_only_binding_is_excluded_from_coverage() -> None:
    binding = _binding(
        "binding_ai",
        CapabilityEvidenceScope.APPLY,
        authority=CapabilityEvidenceAuthority.AI_INFERRED,
        evidence_ref_id="evidence_ai",
    )
    result = assess_match(
        _inputs(bindings=(binding,), evidence_refs=(_evidence_ref("evidence_ai"),))
    ).requirements[0]

    assert result.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert result.covered_scopes == ()
    assert MatchReasonCode.UNQUALIFIED_EVIDENCE_EXCLUDED in {
        reason.code for reason in result.reasons
    }


def test_stale_project_evidence_cannot_support_covered() -> None:
    binding = _binding(
        "binding_project",
        CapabilityEvidenceScope.APPLY,
        project_evidence_id="project_evidence_001",
    )
    result = assess_match(
        _inputs(
            bindings=(binding,),
            project_evidence=(_project_evidence(freshness=ProjectEvidenceFreshness.STALE),),
        )
    ).requirements[0]

    assert result.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert result.covered_scopes == ()
    assert MatchReasonCode.UNQUALIFIED_EVIDENCE_EXCLUDED in {
        reason.code for reason in result.reasons
    }


def test_non_accepted_requirement_and_wrong_graph_fail_closed() -> None:
    with pytest.raises(MatchInputError, match="only accepted"):
        assess_match(_inputs(requirements=(_requirement(status=JobRequirementStatus.PROPOSED),)))

    with pytest.raises(MatchInputError, match="exactly match"):
        assess_match(
            _inputs().model_copy(
                update={
                    "official_capabilities": (
                        _node().model_copy(update={"graph_version_id": "graph_wrong"}),
                    )
                }
            )
        )


def test_missing_or_mismatched_evidence_sources_fail_closed() -> None:
    generic_binding = _binding(
        "binding_missing",
        CapabilityEvidenceScope.APPLY,
        evidence_ref_id="evidence_missing",
    )
    with pytest.raises(MatchInputError, match="source EvidenceRef is missing"):
        assess_match(_inputs(bindings=(generic_binding,)))

    project_binding = _binding(
        "binding_project",
        CapabilityEvidenceScope.APPLY,
        authority=CapabilityEvidenceAuthority.USER_CONFIRMED,
        project_evidence_id="project_evidence_001",
    )
    with pytest.raises(MatchInputError, match="authority does not match"):
        assess_match(
            _inputs(
                bindings=(project_binding,),
                project_evidence=(_project_evidence(),),
            )
        )


def test_ambiguous_personal_identity_fails_closed() -> None:
    with pytest.raises(MatchInputError, match="identity is ambiguous"):
        assess_match(
            _inputs(
                personal_states=(
                    _personal_state("personal_agents_a"),
                    _personal_state("personal_agents_b"),
                )
            )
        )


def test_input_order_is_canonical_and_business_output_is_deterministic() -> None:
    requirements = (
        _requirement("requirement_z"),
        _requirement("requirement_a"),
    )
    bindings = (
        _binding(
            "binding_z",
            CapabilityEvidenceScope.APPLY,
            evidence_ref_id="evidence_z",
        ),
        _binding(
            "binding_a",
            CapabilityEvidenceScope.UNDERSTAND,
            evidence_ref_id="evidence_a",
        ),
    )
    evidence = (_evidence_ref("evidence_z"), _evidence_ref("evidence_a"))
    project_states = (_project_state(), _project_state_existing())

    first = assess_match(
        _inputs(
            requirements=requirements,
            bindings=bindings,
            evidence_refs=evidence,
            project_states=project_states,
        )
    )
    second = assess_match(
        _inputs(
            requirements=tuple(reversed(requirements)),
            bindings=tuple(reversed(bindings)),
            evidence_refs=tuple(reversed(evidence)),
            project_states=tuple(
                state.model_copy(update={"basis": tuple(reversed(state.basis))})
                for state in reversed(project_states)
            ),
        )
    )

    assert first == second
    assert [item.requirement.entity_id for item in first.requirements] == [
        "requirement_a",
        "requirement_z",
    ]


def test_qualified_evidence_without_personal_scope_is_never_covered() -> None:
    bindings = (
        _binding(
            "binding_understand",
            CapabilityEvidenceScope.UNDERSTAND,
            evidence_ref_id="evidence_understand",
        ),
        _binding(
            "binding_apply",
            CapabilityEvidenceScope.APPLY,
            evidence_ref_id="evidence_apply",
        ),
    )
    result = assess_match(
        _inputs(
            personal_states=(_personal_state(understand=False, apply=False),),
            bindings=bindings,
            evidence_refs=(
                _evidence_ref("evidence_understand"),
                _evidence_ref("evidence_apply"),
            ),
        )
    ).requirements[0]

    assert result.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert result.covered_scopes == ()
    assert result.missing_scopes == (
        CapabilityEvidenceScope.UNDERSTAND,
        CapabilityEvidenceScope.APPLY,
    )


@pytest.mark.parametrize(
    "review_status",
    [ProjectEvidenceReviewStatus.REJECTED, ProjectEvidenceReviewStatus.SUPERSEDED],
)
def test_rejected_or_superseded_project_evidence_cannot_support_covered(
    review_status: ProjectEvidenceReviewStatus,
) -> None:
    binding = _binding(
        "binding_project",
        CapabilityEvidenceScope.APPLY,
        project_evidence_id="project_evidence_001",
    )
    result = assess_match(
        _inputs(
            bindings=(binding,),
            project_evidence=(_project_evidence(review_status=review_status),),
        )
    ).requirements[0]

    assert result.classification is MatchClassification.QUICK_TO_STRENGTHEN
    assert result.covered_scopes == ()
    assert MatchReasonCode.UNQUALIFIED_EVIDENCE_EXCLUDED in {
        reason.code for reason in result.reasons
    }


def test_unreferenced_evidence_inputs_fail_closed() -> None:
    binding = _binding(
        "binding_apply",
        CapabilityEvidenceScope.APPLY,
        evidence_ref_id="evidence_apply",
    )
    with pytest.raises(MatchInputError, match="exactly the referenced sources"):
        assess_match(
            _inputs(
                bindings=(binding,),
                evidence_refs=(
                    _evidence_ref("evidence_apply"),
                    _evidence_ref("evidence_extra"),
                ),
            )
        )

    project_binding = _binding(
        "binding_project",
        CapabilityEvidenceScope.APPLY,
        project_evidence_id="project_evidence_001",
    )
    extra = _project_evidence().model_copy(update={"evidence_id": "project_evidence_extra"})
    with pytest.raises(MatchInputError, match="exactly the referenced sources"):
        assess_match(
            _inputs(
                bindings=(project_binding,),
                project_evidence=(_project_evidence(), extra),
            )
        )


def test_binding_with_mismatched_personal_state_fails_closed() -> None:
    stale_binding = _binding(
        "binding_stale",
        CapabilityEvidenceScope.APPLY,
        evidence_ref_id="evidence_apply",
    ).model_copy(update={"personal_state_revision": 99})
    with pytest.raises(MatchInputError, match="exact personal state"):
        assess_match(
            _inputs(
                bindings=(stale_binding,),
                evidence_refs=(_evidence_ref("evidence_apply"),),
            )
        )

    with pytest.raises(MatchInputError, match="belongs to another candidate"):
        assess_match(
            _inputs(
                personal_states=(
                    _personal_state().model_copy(update={"candidate_id": "candidate_other"}),
                )
            )
        )
