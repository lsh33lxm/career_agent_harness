from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_harness.core.common import OpaqueId
from career_harness.core.match_gap import (
    MatchAssessment,
    MatchClassification,
    MatchInputManifest,
    RequirementInputRef,
)
from career_harness.db.match_repository import MatchGapRecord
from career_harness.db.models import (
    CapabilityNodeRow,
    EntityRevisionRow,
    JobRequirementRevisionRow,
    JobRequirementScopeRow,
    JobRevisionRow,
    MatchAssessmentRow,
    MatchGapRow,
    MatchRequirementResultRow,
    OpportunityRecordRow,
)


class MatchAssessmentWrite:
    """Stages the immutable Match aggregate inside the caller's command transaction."""

    def __init__(
        self,
        *,
        assessment_id: OpaqueId,
        candidate_id: OpaqueId,
        assessment: MatchAssessment,
        gaps: tuple[MatchGapRecord, ...],
        created_by: str,
    ) -> None:
        self.assessment_id = assessment_id
        self.candidate_id = candidate_id
        self.assessment = assessment
        self.gaps = gaps
        self.created_by = created_by

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "match-assessment-write-v1",
            "assessment_id": self.assessment_id,
            "candidate_id": self.candidate_id,
            "assessment": self.assessment.model_dump(mode="json"),
            "gaps": [gap.model_dump(mode="json") for gap in self.gaps],
            "created_by": self.created_by,
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        if entity_revision != 1:
            raise ValueError("a MatchAssessment is immutable with exactly one revision")
        manifest = self.assessment.inputs
        manifest_requirements = self._validate_frozen_inputs(session, manifest)
        self._validate_results(session, manifest, manifest_requirements)
        self._validate_gaps(manifest_requirements)

        session.add(
            MatchAssessmentRow(
                assessment_id=self.assessment_id,
                opportunity_id=manifest.opportunity.entity_id,
                opportunity_revision=manifest.opportunity.revision,
                job_id=manifest.job.entity_id,
                job_revision=manifest.job.revision,
                candidate_id=self.candidate_id,
                policy_version=manifest.policy_version,
                manifest=_canonical_manifest(manifest),
                created_at=occurred_at,
                created_by=self.created_by,
            )
        )
        session.flush()
        for result in self.assessment.requirements:
            session.add(
                MatchRequirementResultRow(
                    assessment_id=self.assessment_id,
                    requirement_id=result.requirement.entity_id,
                    requirement_revision=result.requirement.revision,
                    capability_id=manifest_requirements[
                        (result.requirement.entity_id, result.requirement.revision)
                    ].capability_id,
                    classification=result.classification.value,
                    covered_scopes=[scope.value for scope in result.covered_scopes],
                    missing_scopes=[scope.value for scope in result.missing_scopes],
                    reasons=[reason.model_dump(mode="json") for reason in result.reasons],
                )
            )
        session.flush()
        for gap in self.gaps:
            session.add(
                MatchGapRow(
                    gap_id=gap.gap_id,
                    assessment_id=gap.assessment_id,
                    requirement_id=gap.requirement_id,
                    requirement_revision=gap.requirement_revision,
                    capability_id=gap.capability_id,
                    classification=gap.classification.value,
                )
            )

    def _validate_frozen_inputs(
        self, session: Session, manifest: MatchInputManifest
    ) -> dict[tuple[str, int], RequirementInputRef]:
        opportunity_id = manifest.opportunity.entity_id
        opportunity_record = session.get(OpportunityRecordRow, opportunity_id)
        if opportunity_record is None:
            raise ValueError("MatchAssessment requires a canonical Opportunity")
        if (opportunity_record.job_id, opportunity_record.job_revision) != (
            manifest.job.entity_id,
            manifest.job.revision,
        ):
            raise ValueError("MatchAssessment job must match the frozen Opportunity JobRef")
        frozen_opportunity = session.scalars(
            select(EntityRevisionRow).where(
                EntityRevisionRow.entity_id == opportunity_id,
                EntityRevisionRow.revision == manifest.opportunity.revision,
            )
        ).first()
        if frozen_opportunity is None:
            raise ValueError("MatchAssessment requires an exact frozen Opportunity revision")
        if session.get(JobRevisionRow, (manifest.job.entity_id, manifest.job.revision)) is None:
            raise ValueError("MatchAssessment requires an exact canonical Job revision")
        for node in manifest.official_capabilities:
            if session.get(CapabilityNodeRow, (node.capability_id, node.graph_version_id)) is None:
                raise ValueError("MatchAssessment requires exact official capability membership")
        for personal_state in manifest.personal_states:
            if personal_state.candidate_id != self.candidate_id:
                raise ValueError("manifest personal states belong to another candidate")
        return {(item.requirement_id, item.revision): item for item in manifest.requirements}

    def _validate_results(
        self,
        session: Session,
        manifest: MatchInputManifest,
        manifest_requirements: dict[tuple[str, int], RequirementInputRef],
    ) -> None:
        for result in self.assessment.requirements:
            key = (result.requirement.entity_id, result.requirement.revision)
            requirement_ref = manifest_requirements[key]
            row = session.get(JobRequirementRevisionRow, key)
            if row is None:
                raise ValueError(
                    "Match result requires the exact persisted JobRequirement revision"
                )
            if row.status != "accepted":
                raise ValueError("Match result requires an accepted JobRequirement revision")
            if (row.job_id, row.job_revision) != (manifest.job.entity_id, manifest.job.revision):
                raise ValueError("Match result requirement must belong to the frozen Job revision")
            if row.capability_id != requirement_ref.capability_id:
                raise ValueError(
                    "Match result capability mapping disagrees with the persisted requirement"
                )
            if row.graph_version_id != requirement_ref.graph_version_id:
                raise ValueError(
                    "Match result graph version disagrees with the persisted requirement"
                )
            persisted_scopes = set(
                session.scalars(
                    select(JobRequirementScopeRow.scope).where(
                        JobRequirementScopeRow.requirement_id == key[0],
                        JobRequirementScopeRow.requirement_revision == key[1],
                    )
                )
            )
            if persisted_scopes != {scope.value for scope in requirement_ref.required_scopes}:
                raise ValueError("persisted JobRequirement scopes drifted from the frozen manifest")

    def _validate_gaps(
        self, manifest_requirements: dict[tuple[str, int], RequirementInputRef]
    ) -> None:
        results = {
            (result.requirement.entity_id, result.requirement.revision): result
            for result in self.assessment.requirements
        }
        gap_ids = [gap.gap_id for gap in self.gaps]
        if len(gap_ids) != len(set(gap_ids)):
            raise ValueError("gap ids must be unique within an assessment")
        gap_keys: set[tuple[str, int]] = set()
        for gap in self.gaps:
            if gap.assessment_id != self.assessment_id:
                raise ValueError("a Gap must belong to the staged assessment")
            key = (gap.requirement_id, gap.requirement_revision)
            result = results.get(key)
            if result is None:
                raise ValueError("a Gap must reference a result of the same assessment")
            if result.classification is MatchClassification.COVERED:
                raise ValueError("a Gap cannot be minted for a covered result")
            if gap.classification is not result.classification:
                raise ValueError("a Gap must keep the classification of its result")
            if gap.capability_id != manifest_requirements[key].capability_id:
                raise ValueError("a Gap must keep the capability mapping of its requirement")
            gap_keys.add(key)
        expected = {
            key
            for key, result in results.items()
            if result.classification is not MatchClassification.COVERED
        }
        if gap_keys != expected:
            raise ValueError("every non-covered result requires exactly one Gap")


def _canonical_manifest(manifest: MatchInputManifest) -> str:
    return json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
