from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from career_harness.core.resume import ResumeBase, ResumePatch, ResumePatchStatus, ResumeRevision
from career_harness.db.models import (
    ResumeBaseRevisionRow,
    ResumeIdentityRow,
    ResumePatchIdentityRow,
    ResumePatchRevisionRow,
    ResumeRevisionPatchRefRow,
    ResumeRevisionRow,
)


class ResumeBaseWrite:
    def __init__(self, base: ResumeBase) -> None:
        self.base = base

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "resume-base-write-v1",
            "base": self.base.model_dump(mode="json", exclude={"created_at"}),
        }

    def stage(self, session: Session, *, entity_revision: int, occurred_at: datetime) -> None:
        if self.base.revision != entity_revision:
            raise ValueError("typed and generic ResumeBase revisions must match")
        identity = session.get(ResumeIdentityRow, self.base.resume_id)
        if identity is None:
            if self.base.revision != 1:
                raise ValueError("the first ResumeBase revision must be revision one")
            session.add(
                ResumeIdentityRow(
                    resume_id=self.base.resume_id, candidate_id=self.base.candidate_id
                )
            )
            session.flush()
        elif identity.candidate_id != self.base.candidate_id:
            raise ValueError("ResumeBase candidate identity cannot change")
        session.add(
            ResumeBaseRevisionRow(
                resume_id=self.base.resume_id,
                revision=self.base.revision,
                schema_version=self.base.schema_version,
                sections=self.base.sections,
                created_at=occurred_at,
                created_by=self.base.created_by,
            )
        )


class ResumePatchWrite:
    def __init__(self, patch: ResumePatch) -> None:
        self.patch = patch

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "resume-patch-write-v1",
            "patch": self.patch.model_dump(mode="json", exclude={"proposed_at", "reviewed_at"}),
        }

    def stage(self, session: Session, *, entity_revision: int, occurred_at: datetime) -> None:
        patch = self.patch
        if patch.revision != entity_revision:
            raise ValueError("typed and generic ResumePatch revisions must match")
        identity = session.get(ResumePatchIdentityRow, patch.patch_id)
        if identity is None:
            if patch.revision != 1 or patch.status is not ResumePatchStatus.PROPOSED:
                raise ValueError("a new ResumePatch starts as proposed revision one")
            if session.get(ResumeBaseRevisionRow, (patch.resume_id, patch.base_revision)) is None:
                raise ValueError("ResumePatch requires an exact ResumeBase revision")
            session.add(
                ResumePatchIdentityRow(
                    patch_id=patch.patch_id,
                    resume_id=patch.resume_id,
                    base_revision=patch.base_revision,
                )
            )
            session.flush()
        elif (identity.resume_id, identity.base_revision) != (patch.resume_id, patch.base_revision):
            raise ValueError("ResumePatch base identity cannot change")
        session.add(
            ResumePatchRevisionRow(
                patch_id=patch.patch_id,
                revision=patch.revision,
                operations=[item.model_dump(mode="json") for item in patch.operations],
                generator_run_id=patch.generator_run_id,
                status=patch.status.value,
                proposed_by=patch.proposed_by,
                proposed_by_kind=patch.proposed_by_kind.value,
                proposed_at=patch.proposed_at,
                reviewed_by=patch.reviewed_by,
                reviewed_by_kind=patch.reviewed_by_kind.value if patch.reviewed_by_kind else None,
                review_reason=patch.review_reason,
                reviewed_at=occurred_at if patch.status is not ResumePatchStatus.PROPOSED else None,
            )
        )


class ResumeRevisionWrite:
    def __init__(self, revision: ResumeRevision) -> None:
        self.revision = revision

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "resume-revision-write-v1",
            "revision": self.revision.model_dump(mode="json", exclude={"created_at"}),
        }

    def stage(self, session: Session, *, entity_revision: int, occurred_at: datetime) -> None:
        if entity_revision != 1:
            raise ValueError("ResumeRevision is immutable and has one generic revision")
        revision = self.revision
        for ordinal, ref in enumerate(revision.accepted_patch_refs):
            session.add(
                ResumeRevisionPatchRefRow(
                    revision_id=revision.revision_id,
                    ordinal=ordinal,
                    patch_id=ref.entity_id,
                    patch_revision=ref.revision,
                )
            )
        session.flush()
        session.add(
            ResumeRevisionRow(
                revision_id=revision.revision_id,
                resume_id=revision.resume_id,
                base_revision=revision.base_revision,
                content=revision.content,
                content_sha256=revision.content_sha256,
                patch_count=len(revision.accepted_patch_refs),
                created_at=occurred_at,
                created_by=revision.created_by,
            )
        )
