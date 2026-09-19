from __future__ import annotations

import uuid

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.match_gap import MatchAssessment, MatchClassification
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.match_repository import (
    MatchAssessmentRecord,
    MatchGapRecord,
    MatchRepository,
)
from career_harness.db.match_writes import MatchAssessmentWrite
from career_harness.services.command_service import CommandService


class MatchAssessmentCommit(FrozenModel):
    assessment: MatchAssessmentRecord
    commit: CommandCommitResult


def derive_gap_id(command_id: OpaqueId, requirement_id: OpaqueId) -> OpaqueId:
    """Deterministic per command so an idempotent replay hashes to the same request."""
    seed = f"agent-career-harness:gap:{command_id}:{requirement_id}"
    return f"gap_{uuid.uuid5(uuid.NAMESPACE_URL, seed).hex}"


class MatchService:
    def __init__(self, commands: CommandService, repository: MatchRepository) -> None:
        self.commands = commands
        self.repository = repository

    def record_assessment(
        self,
        command: Command,
        *,
        assessment: MatchAssessment,
        candidate_id: OpaqueId,
    ) -> MatchAssessmentCommit:
        """Persist an immutable policy-produced MatchAssessment as a canonical proposal."""
        if command.target.kind is not EntityKind.MATCH_ASSESSMENT:
            raise ValueError("command requires a match_assessment target")
        if command.expected_revision != 0:
            raise ValueError("a new MatchAssessment requires expected revision zero")
        assessment_id = command.target.entity_id
        manifest = assessment.inputs
        manifest_requirements = {
            (item.requirement_id, item.revision): item for item in manifest.requirements
        }
        gaps = tuple(
            MatchGapRecord(
                gap_id=derive_gap_id(command.command_id, result.requirement.entity_id),
                assessment_id=assessment_id,
                requirement_id=result.requirement.entity_id,
                requirement_revision=result.requirement.revision,
                capability_id=manifest_requirements[
                    (result.requirement.entity_id, result.requirement.revision)
                ].capability_id,
                classification=result.classification,
            )
            for result in assessment.requirements
            if result.classification is not MatchClassification.COVERED
        )
        counts = dict.fromkeys(MatchClassification, 0)
        for result in assessment.requirements:
            counts[result.classification] += 1
        metadata = {
            "assessment_id": assessment_id,
            "opportunity_id": manifest.opportunity.entity_id,
            "opportunity_revision": manifest.opportunity.revision,
            "job_id": manifest.job.entity_id,
            "job_revision": manifest.job.revision,
            "candidate_id": candidate_id,
            "policy_version": manifest.policy_version,
            "requirement_count": len(assessment.requirements),
            "covered_count": counts[MatchClassification.COVERED],
            "quick_to_strengthen_count": counts[MatchClassification.QUICK_TO_STRENGTHEN],
            "clear_gap_count": counts[MatchClassification.CLEAR_GAP],
            "gap_ids": [gap.gap_id for gap in gaps],
        }
        commit = self.commands.commit(
            command,
            metadata,
            event_type="match.assessed",
            event_payload=dict(metadata),
            transactional_write=MatchAssessmentWrite(
                assessment_id=assessment_id,
                candidate_id=candidate_id,
                assessment=assessment,
                gaps=gaps,
                created_by=command.actor,
            ),
        )
        persisted = self.repository.get_assessment(assessment_id)
        if persisted is None:
            raise RuntimeError("MatchAssessment commit did not persist the typed aggregate")
        return MatchAssessmentCommit(assessment=persisted, commit=commit)
