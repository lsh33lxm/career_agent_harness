from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.capability import CapabilityEvidenceScope
from career_harness.core.job import (
    JobRef,
    JobRequirement,
    JobRequirementImportance,
    JobRequirementStatus,
    JobRevision,
)
from career_harness.core.lifecycle import ActorKind
from career_harness.db.models import (
    JobRequirementEvidenceRefRow,
    JobRequirementRevisionRow,
    JobRequirementScopeRow,
    JobRevisionEvidenceRefRow,
    JobRevisionRow,
)


class JobRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_job(self, job_id: str, revision: int | None = None) -> JobRevision | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                JobRevisionRow,
                JobRevisionRow.job_id,
                job_id,
                JobRevisionRow.revision,
                revision,
            )
            return self._to_job_revision(session, row) if row is not None else None

    def get_requirement(
        self, requirement_id: str, revision: int | None = None
    ) -> JobRequirement | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                JobRequirementRevisionRow,
                JobRequirementRevisionRow.requirement_id,
                requirement_id,
                JobRequirementRevisionRow.revision,
                revision,
            )
            return self._to_requirement(session, row) if row is not None else None

    def list_requirements_for_job(
        self,
        job_id: str,
        job_revision: int,
        *,
        latest_only: bool = True,
        status: JobRequirementStatus | None = None,
    ) -> tuple[JobRequirement, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(JobRequirementRevisionRow)
                .where(JobRequirementRevisionRow.job_id == job_id)
                .order_by(
                    JobRequirementRevisionRow.requirement_id,
                    JobRequirementRevisionRow.revision.desc(),
                )
            ).all()
            if latest_only:
                latest_rows: dict[str, JobRequirementRevisionRow] = {}
                for row in rows:
                    latest_rows.setdefault(row.requirement_id, row)
                rows = list(latest_rows.values())
            rows = [row for row in rows if row.job_revision == job_revision]
            if status is not None:
                rows = [row for row in rows if row.status == status.value]
            return tuple(self._to_requirement(session, row) for row in rows)

    @staticmethod
    def _get_revisioned_row(
        session: Session,
        row_type: type[JobRevisionRow] | type[JobRequirementRevisionRow],
        identity_column: object,
        identity: str,
        revision_column: object,
        revision: int | None,
    ) -> JobRevisionRow | JobRequirementRevisionRow | None:
        if revision is not None:
            return session.get(row_type, (identity, revision))
        return session.scalars(
            select(row_type)
            .where(identity_column == identity)
            .order_by(revision_column.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _to_job_revision(session: Session, row: JobRevisionRow) -> JobRevision:
        refs = session.scalars(
            select(JobRevisionEvidenceRefRow)
            .where(
                JobRevisionEvidenceRefRow.job_id == row.job_id,
                JobRevisionEvidenceRefRow.job_revision == row.revision,
            )
            .order_by(JobRevisionEvidenceRefRow.ordinal)
        ).all()
        JobRepository._require_contiguous(
            [item.ordinal for item in refs], row.source_evidence_count, "job revision evidence"
        )
        return JobRevision(
            job_id=row.job_id,
            revision=row.revision,
            schema_version=row.schema_version,
            content_sha256=row.content_sha256,
            source_evidence_refs=tuple(item.evidence_ref_id for item in refs),
            observed_at=row.observed_at,
        )

    @staticmethod
    def _to_requirement(session: Session, row: JobRequirementRevisionRow) -> JobRequirement:
        scopes = session.scalars(
            select(JobRequirementScopeRow)
            .where(
                JobRequirementScopeRow.requirement_id == row.requirement_id,
                JobRequirementScopeRow.requirement_revision == row.revision,
            )
            .order_by(JobRequirementScopeRow.ordinal)
        ).all()
        refs = session.scalars(
            select(JobRequirementEvidenceRefRow)
            .where(
                JobRequirementEvidenceRefRow.requirement_id == row.requirement_id,
                JobRequirementEvidenceRefRow.requirement_revision == row.revision,
            )
            .order_by(JobRequirementEvidenceRefRow.ordinal)
        ).all()
        JobRepository._require_contiguous(
            [item.ordinal for item in scopes],
            row.required_scope_count,
            "job requirement scope",
        )
        JobRepository._require_contiguous(
            [item.ordinal for item in refs],
            row.source_evidence_count,
            "job requirement evidence",
        )
        return JobRequirement(
            requirement_id=row.requirement_id,
            revision=row.revision,
            schema_version=row.schema_version,
            job=JobRef(job_id=row.job_id, revision=row.job_revision),
            requirement_text=row.requirement_text,
            importance=JobRequirementImportance(row.importance),
            capability_id=row.capability_id,
            graph_version_id=row.graph_version_id,
            required_scopes=tuple(CapabilityEvidenceScope(item.scope) for item in scopes),
            source_evidence_refs=tuple(item.evidence_ref_id for item in refs),
            status=JobRequirementStatus(row.status),
            proposed_by=row.proposed_by,
            proposed_by_kind=ActorKind(row.proposed_by_kind),
            proposed_at=row.proposed_at,
            reviewed_by=row.reviewed_by,
            reviewed_by_kind=(
                ActorKind(row.reviewed_by_kind) if row.reviewed_by_kind is not None else None
            ),
            review_reason=row.review_reason,
            reviewed_at=row.reviewed_at,
        )

    @staticmethod
    def _require_contiguous(ordinals: list[int], expected_count: int, label: str) -> None:
        if len(ordinals) != expected_count or ordinals != list(range(expected_count)):
            raise RuntimeError(f"persisted {label} aggregate is incomplete")
