from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_harness.core.project import ProjectEvidenceFreshness, ProjectSourceManifest
from career_harness.db.models import (
    ProjectEvidenceRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
)


class ProjectRescanWrite:
    """Stages one immutable source manifest revision from a rescan.

    The rescan diff is a record, not a mutation: staging only inserts the new
    manifest and its entries, and never touches Project Evidence rows. The diff
    itself is derivable from the immutable manifest history, so it is returned to
    the caller rather than persisted.
    """

    def __init__(
        self,
        manifest: ProjectSourceManifest,
        *,
        project_id: str,
        previous_manifest_id: str | None,
    ) -> None:
        self.manifest = manifest
        self.project_id = project_id
        self.previous_manifest_id = previous_manifest_id

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "project-rescan-write-v1",
            "manifest": self.manifest.model_dump(mode="json", exclude={"generated_at"}),
            "project_id": self.project_id,
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        manifest = self.manifest
        if entity_revision != 1:
            raise ValueError("a ProjectSourceManifest is immutable with exactly one revision")
        if session.get(ProjectSourceManifestRow, manifest.manifest_id) is not None:
            raise ValueError("manifest identity must be unique")
        latest = session.scalars(
            select(ProjectSourceManifestRow)
            .where(ProjectSourceManifestRow.project_id == self.project_id)
            .order_by(
                ProjectSourceManifestRow.generated_at.desc(),
                ProjectSourceManifestRow.manifest_id.desc(),
            )
            .limit(1)
        ).first()
        latest_id = latest.manifest_id if latest is not None else None
        if latest_id != self.previous_manifest_id:
            raise ValueError("rescan must build on the latest persisted manifest for the project")
        session.add(
            ProjectSourceManifestRow(
                manifest_id=manifest.manifest_id,
                project_id=self.project_id,
                scan_scope_id=manifest.scan_scope_id,
                scan_scope_revision=manifest.scan_scope_revision,
                generated_at=occurred_at,
            )
        )
        session.flush()
        for entry in manifest.entries:
            session.add(
                ProjectSourceEntryRow(
                    manifest_id=manifest.manifest_id,
                    relative_path=entry.relative_path,
                    sha256=entry.sha256,
                    byte_length=entry.byte_length,
                )
            )


class ProjectEvidenceStaleWrite:
    """Appends a STALE revision of existing evidence; content is never rewritten."""

    def __init__(self, *, evidence_id: str, reason: str, actor: str) -> None:
        self.evidence_id = evidence_id
        self.reason = reason
        self.actor = actor

    def idempotency_payload(self) -> dict[str, Any]:
        return {
            "contract": "project-evidence-stale-write-v1",
            "evidence_id": self.evidence_id,
            "reason": self.reason,
            "actor": self.actor,
        }

    def stage(
        self,
        session: Session,
        *,
        entity_revision: int,
        occurred_at: datetime,
    ) -> None:
        latest = session.scalars(
            select(ProjectEvidenceRow)
            .where(ProjectEvidenceRow.evidence_id == self.evidence_id)
            .order_by(ProjectEvidenceRow.revision.desc())
            .limit(1)
        ).first()
        if latest is None:
            raise ValueError("staleness transition requires existing Project Evidence")
        if latest.revision + 1 != entity_revision:
            raise ValueError("typed and generic Project Evidence revisions must match")
        if latest.freshness != ProjectEvidenceFreshness.CURRENT.value:
            raise ValueError("only CURRENT Project Evidence can be marked stale")
        session.add(
            ProjectEvidenceRow(
                evidence_id=latest.evidence_id,
                revision=entity_revision,
                project_id=latest.project_id,
                summary=latest.summary,
                claim_kind=latest.claim_kind,
                manifest_id=latest.manifest_id,
                scanner=latest.scanner,
                scanner_version=latest.scanner_version,
                authority=latest.authority,
                freshness=ProjectEvidenceFreshness.STALE.value,
                review_status=latest.review_status,
                reviewed_by=latest.reviewed_by,
                reviewed_by_kind=latest.reviewed_by_kind,
                review_reason=latest.review_reason,
                observed_at=occurred_at,
                schema_version=latest.schema_version,
                created_at=latest.created_at,
                created_by=latest.created_by,
            )
        )
