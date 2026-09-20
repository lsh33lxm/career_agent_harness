"""Incremental rescan and explicit evidence staleness over a disposable database."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.project import ProjectSourceEntry
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    EntityRevisionRow,
    EntityStateRow,
    ProjectEvidenceRow,
    ProjectIdentityRow,
    ProjectRecordRow,
    ProjectScanScopeRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
)
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.project_scan_service import ProjectScanService

SCANNER_VERSION = "test-scanner-1"


def _engine(tmp_path: Path) -> tuple[object, ProjectScanService]:
    url = sqlite_url(tmp_path / "rescan.db")
    upgrade_to_head(url)
    engine = create_sqlite_engine(url)
    with engine.begin() as connection:
        connection.execute(ProjectIdentityRow.__table__.insert(), {"project_id": "project_001"})
        connection.execute(
            ProjectRecordRow.__table__.insert(),
            {
                "project_id": "project_001",
                "revision": 1,
                "display_name": "Fixture Project",
                "root_locator": str(tmp_path / "repo"),
                "schema_version": 1,
                "created_at": datetime.now(UTC),
                "created_by": "user",
            },
        )
        connection.execute(
            ProjectScanScopeRow.__table__.insert(),
            {
                "scope_id": "scope_001",
                "revision": 1,
                "project_id": "project_001",
                "allowed_paths": ["src"],
                "denied_paths": [],
                "follow_symlinks": False,
                "schema_version": 1,
                "created_at": datetime.now(UTC),
                "created_by": "user",
            },
        )
    repository = ProjectRepository(engine)
    service = ProjectScanService(
        CommandService(engine), repository, scanner=_FakeScanner(repository)
    )
    return engine, service


class _FakeScanner:
    """Replaces the anchored filesystem readers; the real scanner is covered elsewhere."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository
        self.entries: list[ProjectSourceEntry] = [_entry("src/agent.py", b"print()")]

    def scan(self, project_id, scope_id, scope_revision, *, manifest_id, **_kwargs):  # type: ignore[no-untyped-def]
        from career_harness.core.project import ProjectSourceManifest

        inputs = self._repository.get_scan_inputs(project_id, scope_id, scope_revision)
        if inputs is None:
            raise ValueError("canonical project or exact scan scope was not found")
        return ProjectSourceManifest(
            manifest_id=manifest_id,
            scan_scope_id=scope_id,
            scan_scope_revision=scope_revision,
            entries=tuple(self.entries),
        )


def _entry(path: str, content: bytes) -> ProjectSourceEntry:
    import hashlib

    return ProjectSourceEntry(
        relative_path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
    )


def _rescan_command(manifest_id: str, *, key: str | None = None) -> Command:
    return Command(
        command_id=f"command_{manifest_id}",
        command_type="project.rescan",
        target=EntityRef(entity_id=manifest_id, kind=EntityKind.PROJECT_SOURCE_MANIFEST),
        expected_revision=0,
        idempotency_key=key or f"idempotency-{manifest_id}",
        actor="user",
    )


def _seed_current_evidence(connection) -> None:  # type: ignore[no-untyped-def]
    connection.execute(
        EntityStateRow.__table__.insert(),
        {
            "entity_id": "evidence_001",
            "entity_kind": "project_evidence",
            "revision": 1,
            "schema_version": 1,
            "state": {"evidence_id": "evidence_001", "revision": 1, "freshness": "current"},
            "updated_at": datetime.now(UTC),
        },
    )
    connection.execute(
        EntityRevisionRow.__table__.insert(),
        {
            "revision_id": "revision_evidence_001_1",
            "entity_id": "evidence_001",
            "revision": 1,
            "schema_version": 1,
            "state": {"evidence_id": "evidence_001", "revision": 1, "freshness": "current"},
            "created_at": datetime.now(UTC),
            "created_by": "scanner",
        },
    )
    connection.execute(
        ProjectSourceManifestRow.__table__.insert(),
        {
            "manifest_id": "manifest_000",
            "project_id": "project_001",
            "scan_scope_id": "scope_001",
            "scan_scope_revision": 1,
            "generated_at": datetime.now(UTC),
        },
    )
    entry = _entry("src/agent.py", b"print()")
    connection.execute(
        ProjectSourceEntryRow.__table__.insert(),
        {
            "manifest_id": "manifest_000",
            "relative_path": entry.relative_path,
            "sha256": entry.sha256,
            "byte_length": entry.byte_length,
        },
    )
    connection.execute(
        ProjectEvidenceRow.__table__.insert(),
        {
            "evidence_id": "evidence_001",
            "revision": 1,
            "project_id": "project_001",
            "summary": "Validated agent workflow implementation.",
            "claim_kind": "technical_observation",
            "manifest_id": "manifest_000",
            "scanner": "test-scanner",
            "scanner_version": "1",
            "authority": "document_supported",
            "freshness": "current",
            "review_status": "accepted",
            "reviewed_by": "user",
            "reviewed_by_kind": "user",
            "review_reason": "Reviewed.",
            "observed_at": datetime.now(UTC),
            "schema_version": 1,
            "created_at": datetime.now(UTC),
            "created_by": "scanner",
        },
    )


def test_first_scan_and_rescan_diff_is_recorded(tmp_path: Path) -> None:
    engine, service = _engine(tmp_path)

    first = service.rescan(
        _rescan_command("manifest_001"),
        project_id="project_001",
        scope_id="scope_001",
        scope_revision=1,
        manifest_id="manifest_001",
    )
    assert first.diff.added == ("src/agent.py",)
    assert first.diff.changed == () and first.diff.removed == ()

    # Change one file and add another; rescan must record the auditable diff.
    scanner = service.scanner
    assert isinstance(scanner, _FakeScanner)
    scanner.entries = [
        _entry("src/agent.py", b"print('v2')"),
        _entry("src/tools.py", b"x = 1"),
    ]
    second = service.rescan(
        _rescan_command("manifest_002"),
        project_id="project_001",
        scope_id="scope_001",
        scope_revision=1,
        manifest_id="manifest_002",
    )
    assert second.diff.added == ("src/tools.py",)
    assert second.diff.changed == ("src/agent.py",)
    assert second.diff.removed == ()
    assert second.manifest.scan_scope_revision == 1
    assert second.manifest.entries[0].relative_path == "src/agent.py"

    # No-change rescan records an empty diff.
    third = service.rescan(
        _rescan_command("manifest_003"),
        project_id="project_001",
        scope_id="scope_001",
        scope_revision=1,
        manifest_id="manifest_003",
    )
    assert third.diff == type(third.diff)(added=(), changed=(), removed=())


def test_rescan_is_idempotent_and_pins_exact_scope(tmp_path: Path) -> None:
    engine, service = _engine(tmp_path)
    command = _rescan_command("manifest_001")

    first = service.rescan(
        command,
        project_id="project_001",
        scope_id="scope_001",
        scope_revision=1,
        manifest_id="manifest_001",
    )
    replay = service.rescan(
        command,
        project_id="project_001",
        scope_id="scope_001",
        scope_revision=1,
        manifest_id="manifest_001",
    )
    assert replay.commit == first.commit
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ProjectSourceManifestRow)) == 1

    with pytest.raises(IdempotencyConflict):
        service.rescan(
            _rescan_command("manifest_002", key="idempotency-manifest_001"),
            project_id="project_001",
            scope_id="scope_001",
            scope_revision=1,
            manifest_id="manifest_002",
        )


def test_mark_stale_appends_a_revision_without_rewriting_content(tmp_path: Path) -> None:
    engine, service = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_current_evidence(connection)

    commit = service.mark_stale_evidence(
        Command(
            command_id="command_stale_001",
            command_type="project_evidence.mark_stale",
            target=EntityRef(entity_id="evidence_001", kind=EntityKind.PROJECT_EVIDENCE),
            expected_revision=1,
            idempotency_key="idempotency-stale-001",
            actor="user",
        ),
        evidence_id="evidence_001",
        reason="rescan manifest_002 changed src/agent.py",
    )
    assert commit.commit.revision == 2

    repository = ProjectRepository(engine)
    original = repository.get_evidence("evidence_001", 1)
    stale = repository.get_evidence("evidence_001")
    assert original is not None and original.freshness.value == "current"
    assert stale is not None and stale.freshness.value == "stale"
    # Content fields are copied verbatim; only freshness changes.
    assert stale.summary == original.summary
    assert stale.source_manifest == original.source_manifest
    assert stale.review_status == original.review_status


def test_stale_transition_fails_loud_on_missing_or_non_current(tmp_path: Path) -> None:
    engine, service = _engine(tmp_path)
    with engine.begin() as connection:
        _seed_current_evidence(connection)

    def _command_for(evidence_id: str, revision: int, key: str) -> Command:
        return Command(
            command_id=f"command_{key}",
            command_type="project_evidence.mark_stale",
            target=EntityRef(entity_id=evidence_id, kind=EntityKind.PROJECT_EVIDENCE),
            expected_revision=revision,
            idempotency_key=f"idempotency-{key}",
            actor="user",
        )

    with pytest.raises(ValueError, match="existing Project Evidence"):
        service.mark_stale_evidence(
            _command_for("evidence_missing", 0, "missing"),
            evidence_id="evidence_missing",
            reason="unknown evidence",
        )

    service.mark_stale_evidence(
        _command_for("evidence_001", 1, "first"), evidence_id="evidence_001", reason="r1"
    )
    with pytest.raises(ValueError, match="only CURRENT"):
        service.mark_stale_evidence(
            _command_for("evidence_001", 2, "second"),
            evidence_id="evidence_001",
            reason="already stale",
        )

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ProjectEvidenceRow)) == 2
