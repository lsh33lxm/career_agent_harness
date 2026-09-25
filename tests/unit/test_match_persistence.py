from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.match_gap import (
    ExactRevisionRef,
    MatchAssessment,
    MatchClassification,
    MatchInputManifest,
    MatchReason,
    MatchReasonCode,
    OfficialCapabilityInputRef,
    RequirementInputRef,
    RequirementMatchResult,
)
from career_harness.db.match_repository import MatchGapRecord
from career_harness.db.match_writes import MatchAssessmentWrite
from career_harness.services.command_service import CommandService
from career_harness.services.match_service import MatchService, derive_gap_id


def _assessment() -> MatchAssessment:
    return MatchAssessment(
        inputs=MatchInputManifest(
            opportunity=ExactRevisionRef(entity_id="opportunity_001", revision=1),
            job=ExactRevisionRef(entity_id="job_001", revision=1),
            requirements=(
                RequirementInputRef(
                    requirement_id="requirement_001",
                    revision=1,
                    capability_id="capability_agents",
                    graph_version_id="graph_001",
                    required_scopes=(
                        CapabilityEvidenceScope.UNDERSTAND,
                        CapabilityEvidenceScope.APPLY,
                    ),
                ),
            ),
            official_capabilities=(
                OfficialCapabilityInputRef(
                    capability_id="capability_agents",
                    graph_version_id="graph_001",
                ),
            ),
        ),
        requirements=(
            RequirementMatchResult(
                requirement=ExactRevisionRef(entity_id="requirement_001", revision=1),
                classification=MatchClassification.QUICK_TO_STRENGTHEN,
                covered_scopes=(CapabilityEvidenceScope.UNDERSTAND,),
                missing_scopes=(CapabilityEvidenceScope.APPLY,),
                reasons=(
                    MatchReason(
                        code=MatchReasonCode.PERSONAL_SCOPE_PROGRESS,
                        scopes=(CapabilityEvidenceScope.UNDERSTAND,),
                    ),
                ),
            ),
        ),
    )


def _gaps(assessment_id: str = "assessment_001") -> tuple[MatchGapRecord, ...]:
    return (
        MatchGapRecord(
            gap_id=derive_gap_id("command_assessment_001", "requirement_001"),
            assessment_id=assessment_id,
            requirement_id="requirement_001",
            requirement_revision=1,
            capability_id="capability_agents",
            classification=MatchClassification.QUICK_TO_STRENGTHEN,
        ),
    )


def _command(
    assessment_id: str = "assessment_001",
    *,
    kind: EntityKind = EntityKind.MATCH_ASSESSMENT,
    expected_revision: int = 0,
) -> Command:
    return Command(
        command_id=f"command_{assessment_id}",
        command_type="match_assessment.record",
        target=EntityRef(entity_id=assessment_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=f"idempotency-{assessment_id}",
        actor="agent:match",
    )


def test_derive_gap_id_is_deterministic_and_scoped() -> None:
    first = derive_gap_id("command_assessment_001", "requirement_001")
    assert first == derive_gap_id("command_assessment_001", "requirement_001")
    assert first != derive_gap_id("command_assessment_001", "requirement_002")
    assert first != derive_gap_id("command_assessment_002", "requirement_001")
    assert first.startswith("gap_")


def test_idempotency_payload_is_deterministic_and_carries_business_input() -> None:
    def build() -> MatchAssessmentWrite:
        return MatchAssessmentWrite(
            assessment_id="assessment_001",
            candidate_id="candidate_001",
            assessment=_assessment(),
            gaps=_gaps(),
            created_by="agent:match",
        )

    first = build().idempotency_payload()
    second = build().idempotency_payload()
    assert first == second
    assert first["contract"] == "match-assessment-write-v1"
    assert first["gaps"][0]["gap_id"] == derive_gap_id("command_assessment_001", "requirement_001")


def test_gap_record_rejects_covered_classification() -> None:
    with pytest.raises(ValidationError, match="non-covered"):
        MatchGapRecord(
            gap_id="gap_001",
            assessment_id="assessment_001",
            requirement_id="requirement_001",
            requirement_revision=1,
            capability_id="capability_agents",
            classification=MatchClassification.COVERED,
        )


def test_record_assessment_requires_match_target_and_new_entity() -> None:
    service = MatchService(CommandService(create_engine("sqlite://")), repository=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="match_assessment target"):
        service.record_assessment(
            _command(kind=EntityKind.OPPORTUNITY),
            assessment=_assessment(),
            candidate_id="candidate_001",
        )
    with pytest.raises(ValueError, match="expected revision zero"):
        service.record_assessment(
            _command(expected_revision=1),
            assessment=_assessment(),
            candidate_id="candidate_001",
        )
