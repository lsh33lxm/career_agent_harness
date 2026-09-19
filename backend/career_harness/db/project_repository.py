from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.project import (
    Project,
    ProjectEvidence,
    ProjectEvidenceAuthority,
    ProjectEvidenceClaimKind,
    ProjectEvidenceFreshness,
    ProjectEvidenceReviewStatus,
    ProjectScanScope,
    ProjectSourceEntry,
    ProjectSourceManifest,
)
from career_harness.db.models import (
    ProjectEvidenceRow,
    ProjectRecordRow,
    ProjectScanScopeRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
)


class ProjectRepository:
    """Read-only access to revisioned project records and evidence aggregates."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_project(self, project_id: str, revision: int | None = None) -> Project | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                ProjectRecordRow,
                ProjectRecordRow.project_id,
                project_id,
                ProjectRecordRow.revision,
                revision,
            )
            return self._to_project(row) if row is not None else None

    def get_scan_scope(
        self, scope_id: str, revision: int | None = None
    ) -> ProjectScanScope | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                ProjectScanScopeRow,
                ProjectScanScopeRow.scope_id,
                scope_id,
                ProjectScanScopeRow.revision,
                revision,
            )
            return self._to_scan_scope(row) if row is not None else None

    def get_scan_inputs(
        self,
        project_id: str,
        scope_id: str,
        scope_revision: int,
        *,
        project_revision: int | None = None,
    ) -> tuple[Project, ProjectScanScope] | None:
        """Load canonical project metadata and an exact scope revision atomically."""

        with Session(self.engine) as session:
            project_row = self._get_revisioned_row(
                session,
                ProjectRecordRow,
                ProjectRecordRow.project_id,
                project_id,
                ProjectRecordRow.revision,
                project_revision,
            )
            scope_row = session.get(ProjectScanScopeRow, (scope_id, scope_revision))
            if project_row is None or scope_row is None:
                return None
            project = self._to_project(project_row)
            scope = self._to_scan_scope(scope_row)
            if scope.project_id != project.project_id:
                return None
            return project, scope

    def get_source_manifest(self, manifest_id: str) -> ProjectSourceManifest | None:
        with Session(self.engine) as session:
            row = session.get(ProjectSourceManifestRow, manifest_id)
            return self._to_source_manifest(session, row) if row is not None else None

    def get_evidence(
        self, evidence_id: str, revision: int | None = None
    ) -> ProjectEvidence | None:
        with Session(self.engine) as session:
            row = self._get_revisioned_row(
                session,
                ProjectEvidenceRow,
                ProjectEvidenceRow.evidence_id,
                evidence_id,
                ProjectEvidenceRow.revision,
                revision,
            )
            return self._to_evidence(session, row) if row is not None else None

    def list_evidence_for_project(
        self, project_id: str, *, latest_only: bool = True
    ) -> tuple[ProjectEvidence, ...]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ProjectEvidenceRow)
                .where(ProjectEvidenceRow.project_id == project_id)
                .order_by(ProjectEvidenceRow.evidence_id, ProjectEvidenceRow.revision.desc())
            ).all()
            if latest_only:
                latest_rows: dict[str, ProjectEvidenceRow] = {}
                for row in rows:
                    latest_rows.setdefault(row.evidence_id, row)
                rows = list(latest_rows.values())
            return tuple(self._to_evidence(session, row) for row in rows)

    @staticmethod
    def _get_revisioned_row(
        session: Session,
        row_type: type[ProjectRecordRow] | type[ProjectScanScopeRow] | type[ProjectEvidenceRow],
        identity_column: object,
        identity: str,
        revision_column: object,
        revision: int | None,
    ) -> ProjectRecordRow | ProjectScanScopeRow | ProjectEvidenceRow | None:
        if revision is not None:
            return session.get(row_type, (identity, revision))
        return session.scalars(
            select(row_type)
            .where(identity_column == identity)
            .order_by(revision_column.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _to_project(row: ProjectRecordRow) -> Project:
        return Project(
            project_id=row.project_id,
            revision=row.revision,
            display_name=row.display_name,
            root_locator=row.root_locator,
            schema_version=row.schema_version,
            created_at=row.created_at,
            created_by=row.created_by,
        )

    @staticmethod
    def _to_scan_scope(row: ProjectScanScopeRow) -> ProjectScanScope:
        return ProjectScanScope(
            scope_id=row.scope_id,
            project_id=row.project_id,
            revision=row.revision,
            allowed_paths=tuple(row.allowed_paths),
            denied_paths=tuple(row.denied_paths),
            follow_symlinks=row.follow_symlinks,
            schema_version=row.schema_version,
            created_at=row.created_at,
            created_by=row.created_by,
        )

    @staticmethod
    def _to_source_manifest(
        session: Session, row: ProjectSourceManifestRow
    ) -> ProjectSourceManifest:
        entry_rows = session.scalars(
            select(ProjectSourceEntryRow).where(
                ProjectSourceEntryRow.manifest_id == row.manifest_id
            )
        ).all()
        entries = tuple(
            ProjectSourceEntry(
                relative_path=entry.relative_path,
                sha256=entry.sha256,
                byte_length=entry.byte_length,
            )
            for entry in sorted(
                entry_rows, key=lambda item: (item.relative_path.casefold(), item.relative_path)
            )
        )
        return ProjectSourceManifest(
            manifest_id=row.manifest_id,
            scan_scope_id=row.scan_scope_id,
            scan_scope_revision=row.scan_scope_revision,
            entries=entries,
            generated_at=row.generated_at,
        )

    @classmethod
    def _to_evidence(cls, session: Session, row: ProjectEvidenceRow) -> ProjectEvidence:
        manifest_row = session.get(ProjectSourceManifestRow, row.manifest_id)
        if manifest_row is None:
            raise RuntimeError("persisted project evidence source manifest is missing")
        return ProjectEvidence(
            evidence_id=row.evidence_id,
            project_id=row.project_id,
            summary=row.summary,
            claim_kind=ProjectEvidenceClaimKind(row.claim_kind),
            source_manifest=cls._to_source_manifest(session, manifest_row),
            scanner=row.scanner,
            scanner_version=row.scanner_version,
            authority=ProjectEvidenceAuthority(row.authority),
            freshness=ProjectEvidenceFreshness(row.freshness),
            review_status=ProjectEvidenceReviewStatus(row.review_status),
            reviewed_by=row.reviewed_by,
            reviewed_by_kind=row.reviewed_by_kind,
            review_reason=row.review_reason,
            observed_at=row.observed_at,
            revision=row.revision,
            schema_version=row.schema_version,
            created_at=row.created_at,
            created_by=row.created_by,
        )
