from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import Field, ValidationError, model_validator
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.common import FrozenModel, OpaqueId
from career_harness.core.match_gap import (
    ExactRevisionRef,
    MatchClassification,
    MatchInputManifest,
    MatchReason,
    RequirementMatchResult,
)
from career_harness.db.models import (
    MatchAssessmentRow,
    MatchGapRow,
    MatchRequirementResultRow,
)


class MatchAssessmentHeader(FrozenModel):
    assessment_id: OpaqueId
    opportunity_id: OpaqueId
    opportunity_revision: int = Field(ge=1)
    job_id: OpaqueId
    job_revision: int = Field(ge=1)
    candidate_id: OpaqueId
    policy_version: str
    created_at: datetime
    created_by: str


class MatchGapRecord(FrozenModel):
    gap_id: OpaqueId
    assessment_id: OpaqueId
    requirement_id: OpaqueId
    requirement_revision: int = Field(ge=1)
    capability_id: OpaqueId
    classification: MatchClassification

    @model_validator(mode="after")
    def gap_is_never_covered(self) -> Self:
        if self.classification is MatchClassification.COVERED:
            raise ValueError("a Gap can only record a non-covered requirement result")
        return self


class MatchAssessmentRecord(FrozenModel):
    header: MatchAssessmentHeader
    manifest: MatchInputManifest
    results: tuple[RequirementMatchResult, ...] = Field(min_length=1)
    gaps: tuple[MatchGapRecord, ...] = ()


class MatchRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_assessment(self, assessment_id: str) -> MatchAssessmentRecord | None:
        with Session(self.engine) as session:
            row = session.get(MatchAssessmentRow, assessment_id)
            if row is None:
                return None
            return self._to_record(session, row)

    def get_gap(self, gap_id: str) -> MatchGapRecord | None:
        with Session(self.engine) as session:
            row = session.get(MatchGapRow, gap_id)
            return self._to_gap(row) if row is not None else None

    def list_gaps_for_assessment(self, assessment_id: str) -> tuple[MatchGapRecord, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(MatchGapRow)
                .where(MatchGapRow.assessment_id == assessment_id)
                .order_by(MatchGapRow.requirement_id, MatchGapRow.requirement_revision)
            ).all()
            return tuple(self._to_gap(row) for row in rows)

    def list_assessments_for_opportunity(
        self, opportunity_id: str
    ) -> tuple[MatchAssessmentHeader, ...]:
        """Stable latest-first listing; replay must use get_assessment, never this listing."""
        with Session(self.engine) as session:
            rows = session.scalars(
                select(MatchAssessmentRow)
                .where(MatchAssessmentRow.opportunity_id == opportunity_id)
                .order_by(
                    MatchAssessmentRow.created_at.desc(),
                    MatchAssessmentRow.assessment_id.desc(),
                )
            ).all()
            return tuple(self._to_header(row) for row in rows)

    @classmethod
    def _to_record(cls, session: Session, row: MatchAssessmentRow) -> MatchAssessmentRecord:
        header = cls._to_header(row)
        try:
            manifest = MatchInputManifest.model_validate_json(row.manifest)
        except ValidationError as err:
            raise RuntimeError("persisted match assessment manifest is malformed") from err
        if (
            manifest.opportunity.entity_id != header.opportunity_id
            or manifest.opportunity.revision != header.opportunity_revision
            or manifest.job.entity_id != header.job_id
            or manifest.job.revision != header.job_revision
            or manifest.policy_version != header.policy_version
        ):
            raise RuntimeError("persisted match assessment manifest disagrees with its header")

        result_rows = session.scalars(
            select(MatchRequirementResultRow)
            .where(MatchRequirementResultRow.assessment_id == row.assessment_id)
            .order_by(
                MatchRequirementResultRow.requirement_id,
                MatchRequirementResultRow.requirement_revision,
            )
        ).all()
        if not result_rows:
            raise RuntimeError("persisted match assessment has no requirement results")
        results = tuple(cls._to_result(row) for row in result_rows)
        manifest_keys = {(item.requirement_id, item.revision) for item in manifest.requirements}
        result_keys = {(item.requirement.entity_id, item.requirement.revision) for item in results}
        if result_keys != manifest_keys:
            raise RuntimeError("persisted match results disagree with the manifest requirements")

        gaps = cls._gaps_for(session, row.assessment_id)
        gap_keys = {(gap.requirement_id, gap.requirement_revision) for gap in gaps}
        expected_gap_keys = {
            (item.requirement.entity_id, item.requirement.revision)
            for item in results
            if item.classification is not MatchClassification.COVERED
        }
        if gap_keys != expected_gap_keys:
            raise RuntimeError("persisted match gaps are inconsistent with requirement results")
        results_by_key = {
            (item.requirement.entity_id, item.requirement.revision): item for item in results
        }
        manifest_capabilities = {
            (item.requirement_id, item.revision): item.capability_id
            for item in manifest.requirements
        }
        for gap in gaps:
            key = (gap.requirement_id, gap.requirement_revision)
            result = results_by_key[key]
            if gap.classification is not result.classification:
                raise RuntimeError("persisted match gap classification disagrees with its result")
            if gap.capability_id != manifest_capabilities[key]:
                raise RuntimeError("persisted match gap capability disagrees with the manifest")
        return MatchAssessmentRecord(header=header, manifest=manifest, results=results, gaps=gaps)

    @staticmethod
    def _to_header(row: MatchAssessmentRow) -> MatchAssessmentHeader:
        return MatchAssessmentHeader(
            assessment_id=row.assessment_id,
            opportunity_id=row.opportunity_id,
            opportunity_revision=row.opportunity_revision,
            job_id=row.job_id,
            job_revision=row.job_revision,
            candidate_id=row.candidate_id,
            policy_version=row.policy_version,
            created_at=row.created_at,
            created_by=row.created_by,
        )

    @staticmethod
    def _to_result(row: MatchRequirementResultRow) -> RequirementMatchResult:
        try:
            return RequirementMatchResult(
                requirement=ExactRevisionRef(
                    entity_id=row.requirement_id,
                    revision=row.requirement_revision,
                ),
                classification=MatchClassification(row.classification),
                covered_scopes=tuple(
                    CapabilityEvidenceScope(scope) for scope in row.covered_scopes
                ),
                missing_scopes=tuple(
                    CapabilityEvidenceScope(scope) for scope in row.missing_scopes
                ),
                reasons=tuple(MatchReason.model_validate(item) for item in row.reasons),
            )
        except (ValidationError, ValueError) as err:
            raise RuntimeError("persisted match requirement result is malformed") from err

    @classmethod
    def _gaps_for(cls, session: Session, assessment_id: str) -> tuple[MatchGapRecord, ...]:
        rows = session.scalars(
            select(MatchGapRow)
            .where(MatchGapRow.assessment_id == assessment_id)
            .order_by(MatchGapRow.requirement_id, MatchGapRow.requirement_revision)
        ).all()
        return tuple(cls._to_gap(row) for row in rows)

    @staticmethod
    def _to_gap(row: MatchGapRow) -> MatchGapRecord:
        try:
            return MatchGapRecord(
                gap_id=row.gap_id,
                assessment_id=row.assessment_id,
                requirement_id=row.requirement_id,
                requirement_revision=row.requirement_revision,
                capability_id=row.capability_id,
                classification=MatchClassification(row.classification),
            )
        except (ValidationError, ValueError) as err:
            raise RuntimeError("persisted match gap is malformed") from err
