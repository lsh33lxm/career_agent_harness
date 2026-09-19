from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import Engine

from career_harness.core.project import ProjectEvidenceReviewStatus
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    ProjectEvidenceRow,
    ProjectIdentityRow,
    ProjectRecordRow,
    ProjectScanScopeRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
)
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.session import create_sqlite_engine, sqlite_url


def _database(tmp_path: Path) -> tuple[Engine, datetime]:
    database_url = sqlite_url(tmp_path / "project-read.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(ProjectIdentityRow.__table__.insert(), {"project_id": "project_001"})
        connection.execute(
            ProjectRecordRow.__table__.insert(),
            [
                {
                    "project_id": "project_001",
                    "revision": 1,
                    "display_name": "Agent Gateway",
                    "root_locator": "D:/projects/agent-gateway-v1",
                    "schema_version": 1,
                    "created_at": now,
                    "created_by": "user",
                },
                {
                    "project_id": "project_001",
                    "revision": 2,
                    "display_name": "Agent Gateway",
                    "root_locator": "D:/projects/agent-gateway-v2",
                    "schema_version": 1,
                    "created_at": now + timedelta(seconds=1),
                    "created_by": "user",
                },
            ],
        )
        connection.execute(
            ProjectScanScopeRow.__table__.insert(),
            [
                {
                    "scope_id": "scope_001",
                    "revision": 1,
                    "project_id": "project_001",
                    "allowed_paths": ["src"],
                    "denied_paths": [],
                    "follow_symlinks": False,
                    "schema_version": 1,
                    "created_at": now,
                    "created_by": "user",
                },
                {
                    "scope_id": "scope_001",
                    "revision": 2,
                    "project_id": "project_001",
                    "allowed_paths": ["src", "tests"],
                    "denied_paths": ["src/secrets"],
                    "follow_symlinks": False,
                    "schema_version": 1,
                    "created_at": now + timedelta(seconds=1),
                    "created_by": "user",
                },
            ],
        )
        connection.execute(
            ProjectSourceManifestRow.__table__.insert(),
            {
                "manifest_id": "manifest_001",
                "project_id": "project_001",
                "scan_scope_id": "scope_001",
                "scan_scope_revision": 1,
                "generated_at": now,
            },
        )
        connection.execute(
            ProjectSourceEntryRow.__table__.insert(),
            [
                {
                    "manifest_id": "manifest_001",
                    "relative_path": "src/B.py",
                    "sha256": "b" * 64,
                    "byte_length": 20,
                },
                {
                    "manifest_id": "manifest_001",
                    "relative_path": "src/a.py",
                    "sha256": "a" * 64,
                    "byte_length": 10,
                },
            ],
        )
        base_evidence = {
            "project_id": "project_001",
            "summary": "Router has an explicit fallback branch.",
            "claim_kind": "technical_observation",
            "manifest_id": "manifest_001",
            "scanner": "local-project-scanner",
            "scanner_version": "1",
            "authority": "code_verified",
            "freshness": "current",
            "review_status": "proposed",
            "reviewed_by": None,
            "reviewed_by_kind": None,
            "review_reason": None,
            "observed_at": now,
            "schema_version": 1,
            "created_by": "agent",
        }
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            [
                {
                    **base_evidence,
                    "evidence_id": "evidence_001",
                    "revision": 1,
                    "created_at": now,
                },
                {
                    **base_evidence,
                    "evidence_id": "evidence_001",
                    "revision": 2,
                    "summary": "Router fallback is covered by a focused test.",
                    "created_at": now + timedelta(seconds=1),
                },
                {
                    **base_evidence,
                    "evidence_id": "evidence_002",
                    "revision": 1,
                    "summary": "The provider boundary is explicit.",
                    "created_at": now,
                },
            ],
        )
    return engine, now


def test_repository_reads_project_and_scope_exact_or_latest(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path)
    repository = ProjectRepository(engine)

    assert repository.get_project("project_001", 1).root_locator.endswith("-v1")  # type: ignore[union-attr]
    assert repository.get_project("project_001").revision == 2  # type: ignore[union-attr]
    assert repository.get_scan_scope("scope_001", 1).allowed_paths == ("src",)  # type: ignore[union-attr]
    latest_scope = repository.get_scan_scope("scope_001")
    assert latest_scope is not None
    assert (latest_scope.revision, latest_scope.denied_paths) == (2, ("src/secrets",))
    assert repository.get_project("missing") is None
    assert repository.get_project("project_001", 99) is None
    assert repository.get_scan_scope("missing") is None


def test_repository_loads_canonical_project_and_exact_scope_for_scan(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path)
    repository = ProjectRepository(engine)

    latest = repository.get_scan_inputs("project_001", "scope_001", 1)
    exact = repository.get_scan_inputs(
        "project_001",
        "scope_001",
        2,
        project_revision=1,
    )

    assert latest is not None and exact is not None
    latest_project, exact_scope_one = latest
    exact_project, exact_scope_two = exact
    assert latest_project.revision == 2
    assert exact_scope_one.revision == 1
    assert exact_scope_one.allowed_paths == ("src",)
    assert exact_project.revision == 1
    assert exact_scope_two.revision == 2
    assert exact_scope_two.denied_paths == ("src/secrets",)
    assert repository.get_scan_inputs("project_001", "scope_001", 99) is None
    assert repository.get_scan_inputs(
        "project_001", "scope_001", 1, project_revision=99
    ) is None


def test_repository_rebuilds_sorted_manifest_and_evidence(tmp_path: Path) -> None:
    engine, now = _database(tmp_path)
    repository = ProjectRepository(engine)

    manifest = repository.get_source_manifest("manifest_001")
    assert manifest is not None
    assert manifest.scan_scope_id == "scope_001"
    assert manifest.scan_scope_revision == 1
    assert manifest.generated_at.replace(tzinfo=UTC) == now
    assert tuple(entry.relative_path for entry in manifest.entries) == ("src/a.py", "src/B.py")
    assert repository.get_source_manifest("missing") is None

    exact = repository.get_evidence("evidence_001", 1)
    latest = repository.get_evidence("evidence_001")
    assert exact is not None and latest is not None
    assert exact.revision == 1
    assert latest.revision == 2
    assert latest.review_status is ProjectEvidenceReviewStatus.PROPOSED
    assert latest.source_manifest == manifest
    assert repository.get_evidence("missing") is None
    assert repository.get_evidence("evidence_001", 99) is None


def test_repository_lists_latest_or_all_evidence_for_project(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path)
    repository = ProjectRepository(engine)

    latest = repository.list_evidence_for_project("project_001")
    assert tuple((item.evidence_id, item.revision) for item in latest) == (
        ("evidence_001", 2),
        ("evidence_002", 1),
    )
    all_revisions = repository.list_evidence_for_project("project_001", latest_only=False)
    assert tuple((item.evidence_id, item.revision) for item in all_revisions) == (
        ("evidence_001", 2),
        ("evidence_001", 1),
        ("evidence_002", 1),
    )
    assert repository.list_evidence_for_project("missing") == ()
