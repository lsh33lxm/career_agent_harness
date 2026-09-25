from __future__ import annotations

from sqlalchemy.orm import Session

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.job_repository import JobRepository
from career_harness.db.job_writes import JobRequirementWrite, JobRevisionWrite
from career_harness.services.command_service import CommandService


class JobRevisionCommit(FrozenModel):
    job: JobRevision
    commit: CommandCommitResult


class JobRequirementCommit(FrozenModel):
    requirement: JobRequirement
    commit: CommandCommitResult


class JobService:
    def __init__(self, commands: CommandService, repository: JobRepository) -> None:
        self.commands = commands
        self.repository = repository

    def record_revision(
        self,
        command: Command,
        *,
        content_sha256: str,
        source_evidence_refs: tuple[OpaqueId, ...],
        schema_version: int = 1,
        session: Session | None = None,
    ) -> JobRevisionCommit:
        self._require_target(command, EntityKind.JOB)
        job = JobRevision(
            job_id=command.target.entity_id,
            revision=command.expected_revision + 1,
            schema_version=schema_version,
            content_sha256=content_sha256,
            source_evidence_refs=source_evidence_refs,
            observed_at=command.issued_at,
        )
        state = job.model_dump(mode="json", exclude={"observed_at"})
        commit = self.commands.commit(
            command,
            state,
            event_type="job.revision_created",
            event_payload={
                "job_id": job.job_id,
                "source_evidence_count": len(source_evidence_refs),
            },
            transactional_write=JobRevisionWrite(job),
            session=session,
        )
        persisted = (
            job
            if session is not None
            else self._require_job(job.job_id, commit.revision)
        )
        return JobRevisionCommit(job=persisted, commit=commit)

    def propose_requirement(
        self,
        command: Command,
        *,
        job: JobRef,
        requirement_text: str,
        importance: JobRequirementImportance,
        required_scopes: tuple[CapabilityEvidenceScope, ...],
        source_evidence_refs: tuple[OpaqueId, ...],
        capability_id: OpaqueId | None = None,
        graph_version_id: OpaqueId | None = None,
    ) -> JobRequirementCommit:
        self._require_target(command, EntityKind.JOB_REQUIREMENT)
        if command.expected_revision != 0:
            raise ValueError("a new JobRequirement proposal requires expected revision zero")
        requirement = JobRequirement(
            requirement_id=command.target.entity_id,
            revision=1,
            job=job,
            requirement_text=requirement_text,
            importance=importance,
            capability_id=capability_id,
            graph_version_id=graph_version_id,
            required_scopes=required_scopes,
            source_evidence_refs=source_evidence_refs,
            status=JobRequirementStatus.PROPOSED,
            proposed_by=command.actor,
            proposed_by_kind=(
                ActorKind.USER if command.actor == ActorKind.USER.value else ActorKind.AGENT
            ),
            proposed_at=command.issued_at,
        )
        return self._commit_requirement(command, requirement, "job_requirement.proposed")

    def review_requirement(
        self,
        command: Command,
        *,
        decision: JobRequirementStatus,
        review_reason: str,
        final_requirement_text: str | None = None,
        capability_id: OpaqueId | None = None,
        graph_version_id: OpaqueId | None = None,
    ) -> JobRequirementCommit:
        self._require_target(command, EntityKind.JOB_REQUIREMENT)
        if command.actor != ActorKind.USER.value:
            raise ValueError("P0 JobRequirement review requires a user command")
        if decision not in {
            JobRequirementStatus.ACCEPTED,
            JobRequirementStatus.REJECTED,
            JobRequirementStatus.SUPERSEDED,
        }:
            raise ValueError("review decision must be accepted, rejected or superseded")
        proposal = self.repository.get_requirement(
            command.target.entity_id, command.expected_revision
        )
        if proposal is None or proposal.status is not JobRequirementStatus.PROPOSED:
            raise ValueError("review requires the exact proposed JobRequirement revision")
        requirement_data = proposal.model_dump(mode="python")
        requirement_data.update(
            {
                "revision": command.expected_revision + 1,
                "requirement_text": final_requirement_text or proposal.requirement_text,
                "status": decision,
                "capability_id": capability_id,
                "graph_version_id": graph_version_id,
                "reviewed_by": command.actor,
                "reviewed_by_kind": ActorKind.USER,
                "review_reason": review_reason,
                "reviewed_at": command.issued_at,
            }
        )
        requirement = JobRequirement.model_validate(requirement_data)
        return self._commit_requirement(command, requirement, "job_requirement.reviewed")

    def _commit_requirement(
        self,
        command: Command,
        requirement: JobRequirement,
        event_type: str,
    ) -> JobRequirementCommit:
        state = requirement.model_dump(mode="json", exclude={"proposed_at", "reviewed_at"})
        commit = self.commands.commit(
            command,
            state,
            event_type=event_type,
            event_payload={
                "requirement_id": requirement.requirement_id,
                "job_id": requirement.job.job_id,
                "job_revision": requirement.job.revision,
                "status": requirement.status.value,
            },
            transactional_write=JobRequirementWrite(requirement),
        )
        persisted = self.repository.get_requirement(requirement.requirement_id, commit.revision)
        if persisted is None:
            raise RuntimeError("JobRequirement commit did not persist the typed aggregate")
        return JobRequirementCommit(requirement=persisted, commit=commit)

    @staticmethod
    def _require_target(command: Command, kind: EntityKind) -> None:
        if command.target.kind is not kind:
            raise ValueError(f"command requires a {kind.value} target")

    def _require_job(self, job_id: str, revision: int) -> JobRevision:
        persisted = self.repository.get_job(job_id, revision)
        if persisted is None:
            raise RuntimeError("Job revision commit did not persist the typed aggregate")
        return persisted
