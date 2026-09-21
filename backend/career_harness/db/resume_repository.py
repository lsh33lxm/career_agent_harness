from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.lifecycle import ActorKind
from career_harness.core.resume import (
    ResumeBase,
    ResumePatch,
    ResumePatchOperation,
    ResumePatchStatus,
    ResumeRevision,
    RevisionRef,
)
from career_harness.db.models import (
    ResumeBaseRevisionRow,
    ResumeIdentityRow,
    ResumePatchIdentityRow,
    ResumePatchRevisionRow,
    ResumeRevisionPatchRefRow,
    ResumeRevisionRow,
)


class ResumeRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_base(self, resume_id: str, revision: int | None = None) -> ResumeBase | None:
        with Session(self.engine) as session:
            row = self._revision_row(
                session,
                ResumeBaseRevisionRow,
                ResumeBaseRevisionRow.resume_id,
                resume_id,
                ResumeBaseRevisionRow.revision,
                revision,
            )
            if row is None:
                return None
            identity = session.get(ResumeIdentityRow, resume_id)
            if identity is None:
                raise RuntimeError("persisted Resume identity is missing")
            return ResumeBase(
                resume_id=row.resume_id,
                candidate_id=identity.candidate_id,
                revision=row.revision,
                schema_version=row.schema_version,
                sections=row.sections,
                created_at=row.created_at,
                created_by=row.created_by,
            )

    def list_bases(self) -> tuple[ResumeBase, ...]:
        """Return the latest base revision for each resume identity."""

        with Session(self.engine) as session:
            rows = session.scalars(
                select(ResumeBaseRevisionRow).order_by(
                    ResumeBaseRevisionRow.resume_id,
                    ResumeBaseRevisionRow.revision.desc(),
                )
            ).all()
            latest: dict[str, ResumeBaseRevisionRow] = {}
            for row in rows:
                latest.setdefault(row.resume_id, row)
            result: list[ResumeBase] = []
            for resume_id, row in latest.items():
                identity = session.get(ResumeIdentityRow, resume_id)
                if identity is None:
                    raise RuntimeError("persisted Resume identity is missing")
                result.append(
                    ResumeBase(
                        resume_id=row.resume_id,
                        candidate_id=identity.candidate_id,
                        revision=row.revision,
                        schema_version=row.schema_version,
                        sections=row.sections,
                        created_at=row.created_at,
                        created_by=row.created_by,
                    )
                )
            return tuple(sorted(result, key=lambda item: item.resume_id))

    def list_revisions(self, resume_id: str) -> tuple[ResumeRevision, ...]:
        with Session(self.engine) as session:
            revision_ids = session.scalars(
                select(ResumeRevisionRow.revision_id)
                .where(ResumeRevisionRow.resume_id == resume_id)
                .order_by(ResumeRevisionRow.created_at.desc(), ResumeRevisionRow.revision_id)
            ).all()
        revisions = [self.get_revision(revision_id) for revision_id in revision_ids]
        if any(item is None for item in revisions):
            raise RuntimeError("persisted ResumeRevision disappeared during list read")
        return tuple(item for item in revisions if item is not None)

    def get_patch(self, patch_id: str, revision: int | None = None) -> ResumePatch | None:
        with Session(self.engine) as session:
            row = self._revision_row(
                session,
                ResumePatchRevisionRow,
                ResumePatchRevisionRow.patch_id,
                patch_id,
                ResumePatchRevisionRow.revision,
                revision,
            )
            if row is None:
                return None
            identity = session.get(ResumePatchIdentityRow, patch_id)
            if identity is None:
                raise RuntimeError("persisted ResumePatch identity is missing")
            return ResumePatch(
                patch_id=row.patch_id,
                resume_id=identity.resume_id,
                base_revision=identity.base_revision,
                revision=row.revision,
                operations=tuple(
                    ResumePatchOperation.model_validate(item) for item in row.operations
                ),
                generator_run_id=row.generator_run_id,
                status=ResumePatchStatus(row.status),
                proposed_by=row.proposed_by,
                proposed_by_kind=ActorKind(row.proposed_by_kind),
                proposed_at=row.proposed_at,
                reviewed_by=row.reviewed_by,
                reviewed_by_kind=(
                    ActorKind(row.reviewed_by_kind) if row.reviewed_by_kind else None
                ),
                review_reason=row.review_reason,
                reviewed_at=row.reviewed_at,
            )

    def get_revision(self, revision_id: str) -> ResumeRevision | None:
        with Session(self.engine) as session:
            row = session.get(ResumeRevisionRow, revision_id)
            if row is None:
                return None
            refs = session.scalars(
                select(ResumeRevisionPatchRefRow)
                .where(ResumeRevisionPatchRefRow.revision_id == revision_id)
                .order_by(ResumeRevisionPatchRefRow.ordinal)
            ).all()
            if len(refs) != row.patch_count or [item.ordinal for item in refs] != list(
                range(row.patch_count)
            ):
                raise RuntimeError("persisted ResumeRevision patch aggregate is incomplete")
            return ResumeRevision(
                revision_id=row.revision_id,
                resume_id=row.resume_id,
                base_revision=row.base_revision,
                accepted_patch_refs=tuple(
                    RevisionRef(entity_id=item.patch_id, revision=item.patch_revision)
                    for item in refs
                ),
                content=row.content,
                content_sha256=row.content_sha256,
                created_at=row.created_at,
                created_by=row.created_by,
            )

    @staticmethod
    def _revision_row(session, row_type, identity_column, identity, revision_column, revision):
        if revision is not None:
            return session.get(row_type, (identity, revision))
        return session.scalars(
            select(row_type)
            .where(identity_column == identity)
            .order_by(revision_column.desc())
            .limit(1)
        ).first()
