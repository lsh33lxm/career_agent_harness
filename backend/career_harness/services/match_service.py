from __future__ import annotations

import uuid

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.match_gap import (
    MATCH_POLICY_VERSION,
    MatchAssessment,
    MatchClassification,
    assess_match,
)
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.match_repository import (
    MatchAssessmentRecord,
    MatchGapRecord,
    MatchRepository,
)
from career_harness.db.match_writes import MatchAssessmentWrite
from career_harness.services.command_service import CommandService
from career_harness.services.match_resolver import MatchInputResolver


class MatchReplayError(RuntimeError):
    """A stored MatchAssessment cannot be faithfully replayed from canonical inputs."""


class MatchAssessmentCommit(FrozenModel):
    assessment: MatchAssessmentRecord
    commit: CommandCommitResult


def derive_gap_id(command_id: OpaqueId, requirement_id: OpaqueId) -> OpaqueId:
    """Deterministic per command so an idempotent replay hashes to the same request."""
    seed = f"agent-career-harness:gap:{command_id}:{requirement_id}"
    return f"gap_{uuid.uuid5(uuid.NAMESPACE_URL, seed).hex}"


class MatchService:
    def __init__(
        self,
        commands: CommandService,
        repository: MatchRepository,
        resolver: MatchInputResolver | None = None,
    ) -> None:
        self.commands = commands
        self.repository = repository
        self.resolver = resolver

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

    def assess(
        self,
        command: Command,
        *,
        candidate_id: OpaqueId,
        opportunity_id: OpaqueId,
        opportunity_revision: int,
        requirements: tuple[tuple[OpaqueId, int], ...],
        project_capability_states: tuple[tuple[OpaqueId, int], ...] = (),
    ) -> MatchAssessmentCommit:
        """Resolve exact frozen inputs, run the pure policy and persist the proposal.

        The assessment is a proposal only: it never mutates Career Facts, Personal
        Capability State, priorities, ontology or Resume material.
        """
        inputs = self._require_resolver().resolve(
            opportunity_id=opportunity_id,
            opportunity_revision=opportunity_revision,
            candidate_id=candidate_id,
            requirements=requirements,
            project_capability_states=project_capability_states,
        )
        return self.record_assessment(
            command, assessment=assess_match(inputs), candidate_id=candidate_id
        )

    def replay(self, assessment_id: str) -> MatchAssessmentRecord:
        """Re-resolve a stored manifest through exact reads and verify the stored output.

        Replay never writes and never uses latest-at-read APIs. Any drift, missing ref or
        unsupported stored policy version fails loud.
        """
        record = self.repository.get_assessment(assessment_id)
        if record is None:
            raise MatchReplayError(f"unknown match assessment: {assessment_id}")
        if record.header.policy_version != MATCH_POLICY_VERSION:
            raise MatchReplayError(
                f"unsupported match policy version: {record.header.policy_version}"
            )
        inputs = self._require_resolver().resolve_manifest(
            record.manifest, candidate_id=record.header.candidate_id
        )
        replayed = assess_match(inputs)
        if replayed.inputs != record.manifest:
            raise MatchReplayError(
                f"re-resolved inputs drift from the stored manifest: {assessment_id}"
            )
        if replayed.requirements != record.results:
            raise MatchReplayError(
                f"replayed results drift from the stored results: {assessment_id}"
            )
        return record

    def _require_resolver(self) -> MatchInputResolver:
        if self.resolver is None:
            raise RuntimeError("MatchService assess/replay requires a MatchInputResolver")
        return self.resolver
