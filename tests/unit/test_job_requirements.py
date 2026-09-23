from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind
from career_harness.core.opportunity import JobRef as OpportunityJobRef
from career_harness.core.opportunity.models import JobRef as OpportunityModelsJobRef

OBSERVED_AT = datetime(2026, 9, 19, tzinfo=UTC)


def requirement_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "requirement_id": "job_requirement_001",
        "revision": 1,
        "job": JobRef(job_id="job_001", revision=3),
        "requirement_text": "Build observable production services.",
        "importance": JobRequirementImportance.REQUIRED,
        "required_scopes": (
            CapabilityEvidenceScope.UNDERSTAND,
            CapabilityEvidenceScope.APPLY,
        ),
        "source_evidence_refs": ("evidence_job_description",),
        "proposed_by": "model-run-001",
        "proposed_by_kind": ActorKind.AGENT,
        "proposed_at": OBSERVED_AT,
    }
    fields.update(overrides)
    return fields


def review_fields(actor: ActorKind = ActorKind.USER) -> dict[str, object]:
    return {
        "reviewed_by": "user" if actor is ActorKind.USER else "requirement-policy-v1",
        "reviewed_by_kind": actor,
        "review_reason": "The requirement is directly supported by the job description.",
        "reviewed_at": OBSERVED_AT,
    }


def test_job_ref_legacy_imports_are_the_same_class() -> None:
    assert OpportunityJobRef is JobRef
    assert OpportunityModelsJobRef is JobRef
    assert OpportunityJobRef(job_id="job_001", revision=2) == JobRef(
        job_id="job_001", revision=2
    )


def test_job_revision_is_evidence_backed_frozen_and_extra_forbid() -> None:
    revision = JobRevision(
        job_id="job_001",
        revision=2,
        schema_version=1,
        content_sha256="a" * 64,
        source_evidence_refs=("evidence_capture", "evidence_company_page"),
        observed_at=OBSERVED_AT,
    )

    assert revision.source_evidence_refs == ("evidence_capture", "evidence_company_page")
    with pytest.raises(ValidationError, match="frozen"):
        revision.revision = 3
    with pytest.raises(ValidationError, match="Extra inputs"):
        JobRevision(
            job_id="job_001",
            revision=2,
            content_sha256="a" * 64,
            source_evidence_refs=("evidence_capture",),
            observed_at=OBSERVED_AT,
            parser_claim="trusted",
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"revision": 0},
        {"schema_version": 0},
        {"content_sha256": "not-a-sha256"},
        {"content_sha256": "A" * 64},
        {"source_evidence_refs": ()},
        {"source_evidence_refs": ("evidence_capture", "evidence_capture")},
    ],
)
def test_job_revision_rejects_invalid_revision_hash_or_evidence(
    overrides: dict[str, object],
) -> None:
    fields: dict[str, object] = {
        "job_id": "job_001",
        "revision": 1,
        "schema_version": 1,
        "content_sha256": "a" * 64,
        "source_evidence_refs": ("evidence_capture",),
        "observed_at": OBSERVED_AT,
    }
    fields.update(overrides)

    with pytest.raises(ValidationError):
        JobRevision(**fields)


def test_agent_can_propose_unmapped_requirement_without_review_decision() -> None:
    requirement = JobRequirement(**requirement_fields())

    assert requirement.status is JobRequirementStatus.PROPOSED
    assert requirement.proposed_by_kind is ActorKind.AGENT
    assert requirement.capability_id is None
    assert requirement.graph_version_id is None

    with pytest.raises(ValidationError, match="cannot carry a review decision"):
        JobRequirement(**requirement_fields(**review_fields()))


@pytest.mark.parametrize(
    ("status", "reviewer"),
    [
        (JobRequirementStatus.ACCEPTED, ActorKind.USER),
        (JobRequirementStatus.ACCEPTED, ActorKind.RULE),
        (JobRequirementStatus.REJECTED, ActorKind.USER),
        (JobRequirementStatus.SUPERSEDED, ActorKind.RULE),
    ],
)
def test_reviewed_requirement_requires_user_or_rule_authority(
    status: JobRequirementStatus, reviewer: ActorKind
) -> None:
    mapping = (
        {"capability_id": "capability_observability", "graph_version_id": "graph_001"}
        if status is JobRequirementStatus.ACCEPTED
        else {}
    )
    requirement = JobRequirement(
        **requirement_fields(status=status, **mapping, **review_fields(reviewer))
    )

    assert requirement.status is status
    assert requirement.reviewed_by_kind is reviewer


@pytest.mark.parametrize(
    "status",
    [
        JobRequirementStatus.ACCEPTED,
        JobRequirementStatus.REJECTED,
        JobRequirementStatus.SUPERSEDED,
    ],
)
def test_agent_cannot_review_any_decided_requirement(status: JobRequirementStatus) -> None:
    mapping = (
        {"capability_id": "capability_observability", "graph_version_id": "graph_001"}
        if status is JobRequirementStatus.ACCEPTED
        else {}
    )

    with pytest.raises(ValidationError, match="agent cannot review"):
        JobRequirement(
            **requirement_fields(status=status, **mapping, **review_fields(ActorKind.AGENT))
        )


def test_reviewed_requirement_requires_complete_review_metadata() -> None:
    with pytest.raises(ValidationError, match="complete reviewer metadata"):
        JobRequirement(
            **requirement_fields(
                status=JobRequirementStatus.REJECTED,
                reviewed_by="user",
                reviewed_by_kind=ActorKind.USER,
            )
        )


@pytest.mark.parametrize(
    "mapping",
    [
        {"capability_id": "capability_observability"},
        {"graph_version_id": "graph_001"},
    ],
)
def test_official_capability_and_graph_version_are_atomic(mapping: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="provided together"):
        JobRequirement(**requirement_fields(**mapping))


def test_accepted_requirement_requires_official_mapping() -> None:
    with pytest.raises(ValidationError, match="official capability mapping"):
        JobRequirement(
            **requirement_fields(
                status=JobRequirementStatus.ACCEPTED,
                **review_fields(ActorKind.USER),
            )
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"required_scopes": ()},
        {"required_scopes": (CapabilityEvidenceScope.APPLY, CapabilityEvidenceScope.APPLY)},
        {"source_evidence_refs": ()},
        {"source_evidence_refs": ("evidence_jd", "evidence_jd")},
    ],
)
def test_requirement_scopes_and_source_refs_are_non_empty_and_unique(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        JobRequirement(**requirement_fields(**overrides))


def test_job_requirement_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        JobRequirement(**requirement_fields(match_score=0.9))
