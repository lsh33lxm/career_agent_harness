import pytest
from pydantic import ValidationError

from career_harness.core.project import (
    ProjectCapabilityBasis,
    ProjectCapabilityBasisKind,
    ProjectCapabilityLevel,
    ProjectCapabilityState,
    ProjectEvidence,
    ProjectEvidenceAuthority,
    ProjectEvidenceClaimKind,
    ProjectEvidenceReviewStatus,
    ProjectSourceEntry,
    ProjectSourceManifest,
)


def make_manifest() -> ProjectSourceManifest:
    return ProjectSourceManifest(
        manifest_id="manifest_001",
        scan_scope_id="scope_001",
        scan_scope_revision=1,
        entries=(
            ProjectSourceEntry(
                relative_path="src/router.py",
                sha256="a" * 64,
                byte_length=128,
            ),
        ),
    )


def test_code_can_support_a_reviewed_technical_observation() -> None:
    evidence = ProjectEvidence(
        evidence_id="project_evidence_001",
        project_id="project_001",
        summary="Router exposes an explicit provider fallback branch.",
        source_manifest=make_manifest(),
        scanner="fixture-scanner",
        scanner_version="1",
        authority=ProjectEvidenceAuthority.CODE_VERIFIED,
        review_status=ProjectEvidenceReviewStatus.ACCEPTED,
        reviewed_by="project-evidence-policy-v1",
        reviewed_by_kind="rule",
        review_reason="Technical observation is directly supported by the manifest.",
        created_by="rule:project-scan",
    )

    assert evidence.claim_kind is ProjectEvidenceClaimKind.TECHNICAL_OBSERVATION


def test_source_code_alone_cannot_verify_performance_or_personal_claims() -> None:
    with pytest.raises(ValidationError, match="source code alone"):
        ProjectEvidence(
            evidence_id="project_evidence_001",
            project_id="project_001",
            summary="The project reduced latency by 40 percent.",
            claim_kind=ProjectEvidenceClaimKind.PERFORMANCE,
            source_manifest=make_manifest(),
            scanner="fixture-scanner",
            scanner_version="1",
            authority=ProjectEvidenceAuthority.CODE_VERIFIED,
            created_by="rule:project-scan",
        )


def test_ai_inference_cannot_be_accepted_without_promotion() -> None:
    with pytest.raises(ValidationError, match="explicit promotion"):
        ProjectEvidence(
            evidence_id="project_evidence_001",
            project_id="project_001",
            summary="The user independently designed the router.",
            claim_kind=ProjectEvidenceClaimKind.OWNERSHIP,
            source_manifest=make_manifest(),
            scanner="model-scanner",
            scanner_version="1",
            authority=ProjectEvidenceAuthority.AI_INFERRED,
            review_status=ProjectEvidenceReviewStatus.ACCEPTED,
            reviewed_by="project-evidence-policy-v1",
            reviewed_by_kind="rule",
            review_reason="Model claim was reviewed but not promoted by a user.",
            created_by="agent",
        )


def test_code_presence_cannot_make_a_capability_resume_ready() -> None:
    with pytest.raises(ValidationError, match="lacks required evidence or approval"):
        ProjectCapabilityState(
            capability_state_id="project_capability_001",
            project_id="project_001",
            capability_id="capability_observability",
            state=ProjectCapabilityLevel.RESUME_READY,
            basis=(
                ProjectCapabilityBasis(
                    kind=ProjectCapabilityBasisKind.CODE_EVIDENCE,
                    reference_id="project_evidence_001",
                    reference_revision=1,
                ),
            ),
            created_by="agent",
        )


def test_resume_ready_requires_validation_and_explicit_resume_approval() -> None:
    state = ProjectCapabilityState(
        capability_state_id="project_capability_001",
        project_id="project_001",
        capability_id="capability_observability",
        state=ProjectCapabilityLevel.RESUME_READY,
        basis=(
            ProjectCapabilityBasis(
                kind=ProjectCapabilityBasisKind.VALIDATION_EVIDENCE,
                reference_id="project_evidence_validation",
                reference_revision=1,
            ),
            ProjectCapabilityBasis(
                kind=ProjectCapabilityBasisKind.RESUME_APPROVAL,
                reference_id="approval_001",
                reference_revision=1,
            ),
        ),
        created_by="user",
    )

    assert state.state is ProjectCapabilityLevel.RESUME_READY
