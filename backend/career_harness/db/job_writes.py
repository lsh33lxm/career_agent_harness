from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from career_harness.core.job import JobRequirement, JobRequirementStatus, JobRevision
from career_harness.db.models import (
    CapabilityNodeRow,
    EvidenceRefRow,
    JobIdentityRow,
    JobRequirementEvidenceRefRow,
    JobRequirementIdentityRow,
    JobRequirementRevisionRow,
    JobRequirementScopeRow,
    JobRevisionEvidenceRefRow,
    JobRevisionRow,
)


class JobRevisionWrite:
    def __init__(self, job: JobRevision) -> None:
        self.job = job

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "job-revision-write-v1",
            "job": self.job.model_dump(mode="json", exclude={"observed_at"}),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        if self.job.revision != entity_revision:
            raise ValueError("typed and generic Job revisions must match")
        for evidence_ref_id in self.job.source_evidence_refs:
            if session.get(EvidenceRefRow, evidence_ref_id) is None:
                raise ValueError("Job revision requires canonical source EvidenceRefs")

        identity = session.get(JobIdentityRow, self.job.job_id)
        if identity is None:
            if self.job.revision != 1:
                raise ValueError("the first Job revision must be revision one")
            session.add(JobIdentityRow(job_id=self.job.job_id))
            session.flush()

        for ordinal, evidence_ref_id in enumerate(self.job.source_evidence_refs):
            session.add(
                JobRevisionEvidenceRefRow(
                    job_id=self.job.job_id,
                    job_revision=self.job.revision,
                    ordinal=ordinal,
                    evidence_ref_id=evidence_ref_id,
                )
            )
        session.flush()
        session.add(
            JobRevisionRow(
                job_id=self.job.job_id,
                revision=self.job.revision,
                schema_version=self.job.schema_version,
                content_sha256=self.job.content_sha256,
                observed_at=occurred_at,
                source_evidence_count=len(self.job.source_evidence_refs),
            )
        )


class JobRequirementWrite:
    def __init__(self, requirement: JobRequirement) -> None:
        self.requirement = requirement

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "job-requirement-write-v1",
            "requirement": self.requirement.model_dump(
                mode="json", exclude={"proposed_at", "reviewed_at"}
            ),
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        requirement = self.requirement
        if requirement.revision != entity_revision:
            raise ValueError("typed and generic JobRequirement revisions must match")
        if session.get(JobRevisionRow, (requirement.job.job_id, requirement.job.revision)) is None:
            raise ValueError("JobRequirement requires an exact canonical Job revision")
        for evidence_ref_id in requirement.source_evidence_refs:
            if session.get(EvidenceRefRow, evidence_ref_id) is None:
                raise ValueError("JobRequirement requires canonical source EvidenceRefs")
        if (
            requirement.status is JobRequirementStatus.ACCEPTED
            and session.get(
                CapabilityNodeRow,
                (requirement.capability_id, requirement.graph_version_id),
            )
            is None
        ):
            raise ValueError(
                "accepted JobRequirement requires exact official capability membership"
            )

        identity = session.get(JobRequirementIdentityRow, requirement.requirement_id)
        if identity is None:
            if requirement.revision != 1:
                raise ValueError("the first JobRequirement revision must be revision one")
            session.add(
                JobRequirementIdentityRow(
                    requirement_id=requirement.requirement_id,
                    job_id=requirement.job.job_id,
                )
            )
            session.flush()
        elif identity.job_id != requirement.job.job_id:
            raise ValueError("JobRequirement identity cannot move to another Job")

        for ordinal, scope in enumerate(requirement.required_scopes):
            session.add(
                JobRequirementScopeRow(
                    requirement_id=requirement.requirement_id,
                    requirement_revision=requirement.revision,
                    ordinal=ordinal,
                    scope=scope.value,
                )
            )
        for ordinal, evidence_ref_id in enumerate(requirement.source_evidence_refs):
            session.add(
                JobRequirementEvidenceRefRow(
                    requirement_id=requirement.requirement_id,
                    requirement_revision=requirement.revision,
                    ordinal=ordinal,
                    evidence_ref_id=evidence_ref_id,
                )
            )
        session.flush()
        session.add(
            JobRequirementRevisionRow(
                requirement_id=requirement.requirement_id,
                revision=requirement.revision,
                schema_version=requirement.schema_version,
                job_id=requirement.job.job_id,
                job_revision=requirement.job.revision,
                requirement_text=requirement.requirement_text,
                importance=requirement.importance.value,
                capability_id=requirement.capability_id,
                graph_version_id=requirement.graph_version_id,
                required_scope_count=len(requirement.required_scopes),
                source_evidence_count=len(requirement.source_evidence_refs),
                status=requirement.status.value,
                proposed_by=requirement.proposed_by,
                proposed_by_kind=requirement.proposed_by_kind.value,
                proposed_at=(
                    occurred_at
                    if requirement.status is JobRequirementStatus.PROPOSED
                    else requirement.proposed_at
                ),
                reviewed_by=requirement.reviewed_by,
                reviewed_by_kind=(
                    requirement.reviewed_by_kind.value
                    if requirement.reviewed_by_kind is not None
                    else None
                ),
                review_reason=requirement.review_reason,
                reviewed_at=(
                    occurred_at if requirement.status is not JobRequirementStatus.PROPOSED else None
                ),
            )
        )
