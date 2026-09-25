from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine

from career_harness.core.project import (
    ProjectCapabilityBasisKind,
    ProjectCapabilityLevel,
    ProjectEnhancementTaskStatus,
    ProjectEvidenceReviewStatus,
)
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CapabilityIdentityRow,
    ProjectCapabilityBasisRow,
    ProjectCapabilityStateRow,
    ProjectEnhancementTaskRow,
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
            CapabilityIdentityRow.__table__.insert(),
            [
                {"capability_id": "capability_001"},
                {"capability_id": "capability_002"},
            ],
        )
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
        accepted_evidence = {
            **base_evidence,
            "review_status": "accepted",
            "reviewed_by": "project-evidence-policy-v1",
            "reviewed_by_kind": "rule",
            "review_reason": "Fixture evidence satisfies the declared authority.",
        }
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            [
                {
                    **accepted_evidence,
                    "evidence_id": "evidence_code",
                    "revision": 1,
                    "summary": "The provider boundary is explicit.",
                    "authority": "code_verified",
                    "created_at": now,
                },
                {
                    **accepted_evidence,
                    "evidence_id": "evidence_user",
                    "revision": 1,
                    "summary": "The user confirms understanding of the provider boundary.",
                    "authority": "user_confirmed",
                    "created_at": now,
                },
                {
                    **accepted_evidence,
                    "evidence_id": "evidence_change",
                    "revision": 1,
                    "summary": "The provider boundary was changed.",
                    "claim_kind": "change",
                    "authority": "code_verified",
                    "created_at": now,
                },
                {
                    **accepted_evidence,
                    "evidence_id": "evidence_validation",
                    "revision": 1,
                    "summary": "The provider boundary passed focused validation.",
                    "claim_kind": "validation",
                    "authority": "code_verified",
                    "created_at": now,
                },
            ],
        )
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            [
                {
                    "basis_id": "basis_state_001_r1_code",
                    "capability_state_id": "state_001",
                    "state_revision": 1,
                    "basis_kind": "code_evidence",
                    "project_evidence_id": "evidence_code",
                    "project_evidence_revision": 1,
                    "approval_id": None,
                    "approval_revision": None,
                },
                {
                    "basis_id": "basis_state_001_r2_user",
                    "capability_state_id": "state_001",
                    "state_revision": 2,
                    "basis_kind": "user_confirmation",
                    "project_evidence_id": "evidence_user",
                    "project_evidence_revision": 1,
                    "approval_id": None,
                    "approval_revision": None,
                },
                {
                    "basis_id": "basis_state_001_r2_change",
                    "capability_state_id": "state_001",
                    "state_revision": 2,
                    "basis_kind": "change_evidence",
                    "project_evidence_id": "evidence_change",
                    "project_evidence_revision": 1,
                    "approval_id": None,
                    "approval_revision": None,
                },
                {
                    "basis_id": "basis_state_002_r1_code",
                    "capability_state_id": "state_002",
                    "state_revision": 1,
                    "basis_kind": "code_evidence",
                    "project_evidence_id": "evidence_code",
                    "project_evidence_revision": 1,
                    "approval_id": None,
                    "approval_revision": None,
                },
                {
                    "basis_id": "basis_state_003_r1_validation",
                    "capability_state_id": "state_003",
                    "state_revision": 1,
                    "basis_kind": "validation_evidence",
                    "project_evidence_id": "evidence_validation",
                    "project_evidence_revision": 1,
                    "approval_id": None,
                    "approval_revision": None,
                },
            ],
        )
        base_state = {
            "project_id": "project_001",
            "schema_version": 1,
            "created_by": "user",
        }
        connection.execute(
            ProjectCapabilityStateRow.__table__.insert(),
            [
                {
                    **base_state,
                    "capability_state_id": "state_001",
                    "revision": 1,
                    "capability_id": "capability_001",
                    "state": "existing",
                    "finalized_at": now,
                    "created_at": now,
                },
                {
                    **base_state,
                    "capability_state_id": "state_001",
                    "revision": 2,
                    "capability_id": "capability_001",
                    "state": "modified",
                    "finalized_at": now + timedelta(seconds=2),
                    "created_at": now + timedelta(seconds=2),
                },
                {
                    **base_state,
                    "capability_state_id": "state_002",
                    "revision": 1,
                    "capability_id": "capability_001",
                    "state": "existing",
                    "finalized_at": now + timedelta(seconds=1),
                    "created_at": now + timedelta(seconds=1),
                },
                {
                    **base_state,
                    "capability_state_id": "state_003",
                    "revision": 1,
                    "capability_id": "capability_002",
                    "state": "validated",
                    "finalized_at": now + timedelta(seconds=3),
                    "created_at": now + timedelta(seconds=3),
                },
            ],
        )
        task_plan = {
            "project_id": "project_001",
            "learning_plan": ["Learn tracing fundamentals."],
            "files_to_review": ["src/router.py"],
            "change_plan": ["Add tracing spans."],
            "experiment_plan": ["Capture fallback traces."],
            "validation_plan": ["Run focused tests."],
            "expected_evidence": ["A passing trace test."],
            "schema_version": 1,
            "created_by": "user",
        }
        connection.execute(
            ProjectEnhancementTaskRow.__table__.insert(),
            [
                {
                    **task_plan,
                    "task_id": "task_001",
                    "revision": 1,
                    "target_gap_id": "gap_001",
                    "target_capability_id": "capability_001",
                    "status": "proposed",
                    "created_at": now,
                },
                {
                    **task_plan,
                    "task_id": "task_001",
                    "revision": 2,
                    "target_gap_id": "gap_001",
                    "target_capability_id": "capability_001",
                    "status": "ready",
                    "created_at": now + timedelta(seconds=1),
                },
                {
                    **task_plan,
                    "task_id": "task_002",
                    "revision": 1,
                    "target_gap_id": "gap_001",
                    "target_capability_id": "capability_001",
                    "status": "in_progress",
                    "created_at": now + timedelta(seconds=2),
                },
                {
                    **task_plan,
                    "task_id": "task_003",
                    "revision": 1,
                    "target_gap_id": "gap_002",
                    "target_capability_id": "capability_002",
                    "status": "awaiting_validation",
                    "created_at": now + timedelta(seconds=3),
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
    assert repository.get_scan_inputs("project_001", "scope_001", 1, project_revision=99) is None


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
        ("evidence_change", 1),
        ("evidence_code", 1),
        ("evidence_user", 1),
        ("evidence_validation", 1),
    )
    all_revisions = repository.list_evidence_for_project("project_001", latest_only=False)
    assert tuple((item.evidence_id, item.revision) for item in all_revisions) == (
        ("evidence_001", 2),
        ("evidence_001", 1),
        ("evidence_002", 1),
        ("evidence_change", 1),
        ("evidence_code", 1),
        ("evidence_user", 1),
        ("evidence_validation", 1),
    )
    assert repository.list_evidence_for_project("missing") == ()


def test_repository_reads_capability_state_exact_or_identity_latest(tmp_path: Path) -> None:
    engine, now = _database(tmp_path)
    repository = ProjectRepository(engine)

    exact = repository.get_project_capability_state("state_001", 1)
    latest = repository.get_project_capability_state("state_001")

    assert exact is not None and latest is not None
    assert (exact.revision, exact.state) == (1, ProjectCapabilityLevel.EXISTING)
    assert tuple(
        (item.kind, item.reference_id, item.reference_revision) for item in exact.basis
    ) == ((ProjectCapabilityBasisKind.CODE_EVIDENCE, "evidence_code", 1),)
    assert (latest.revision, latest.state) == (2, ProjectCapabilityLevel.MODIFIED)
    assert tuple(
        (item.kind, item.reference_id, item.reference_revision) for item in latest.basis
    ) == (
        (ProjectCapabilityBasisKind.CHANGE_EVIDENCE, "evidence_change", 1),
        (ProjectCapabilityBasisKind.USER_CONFIRMATION, "evidence_user", 1),
    )
    assert latest.finalized_at.replace(tzinfo=UTC) == now + timedelta(seconds=2)
    assert repository.get_project_capability_state("missing") is None
    assert repository.get_project_capability_state("state_001", 99) is None


def test_repository_lists_capability_states_per_identity_with_stable_order(
    tmp_path: Path,
) -> None:
    engine, _ = _database(tmp_path)
    repository = ProjectRepository(engine)

    latest = repository.list_project_capability_states(
        "project_001", capability_id="capability_001"
    )
    history = repository.list_project_capability_states(
        "project_001", capability_id="capability_001", latest_only=False
    )

    assert tuple((item.capability_state_id, item.revision) for item in latest) == (
        ("state_001", 2),
        ("state_002", 1),
    )
    assert tuple((item.capability_state_id, item.revision) for item in history) == (
        ("state_001", 2),
        ("state_001", 1),
        ("state_002", 1),
    )
    assert tuple(
        item.capability_state_id
        for item in repository.list_project_capability_states(
            "project_001", capability_id="capability_002"
        )
    ) == ("state_003",)
    assert repository.list_project_capability_states("missing") == ()


def test_repository_reads_and_filters_enhancement_task_history(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path)
    repository = ProjectRepository(engine)

    exact = repository.get_enhancement_task("task_001", 1)
    latest = repository.get_enhancement_task("task_001")

    assert exact is not None and latest is not None
    assert (exact.revision, exact.status) == (1, ProjectEnhancementTaskStatus.PROPOSED)
    assert (latest.revision, latest.status) == (2, ProjectEnhancementTaskStatus.READY)
    assert latest.files_to_review == ("src/router.py",)
    assert tuple(
        (item.task_id, item.revision)
        for item in repository.list_enhancement_tasks("project_001", "gap_001")
    ) == (("task_001", 2), ("task_002", 1))
    assert tuple(
        (item.task_id, item.revision)
        for item in repository.list_enhancement_tasks("project_001", "gap_001", latest_only=False)
    ) == (("task_001", 2), ("task_001", 1), ("task_002", 1))
    assert repository.get_enhancement_task("missing") is None
    assert repository.get_enhancement_task("task_001", 99) is None
    assert repository.list_enhancement_tasks("missing") == ()
    assert repository.list_enhancement_tasks("project_001", "missing") == ()


def test_repository_fails_loud_for_capability_state_missing_basis(tmp_path: Path) -> None:
    engine, _ = _database(tmp_path)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TRIGGER trg_project_capability_basis_no_delete")
        connection.execute(
            ProjectCapabilityBasisRow.__table__.delete().where(
                ProjectCapabilityBasisRow.capability_state_id == "state_002"
            )
        )

    with pytest.raises(ValidationError):
        ProjectRepository(engine).get_project_capability_state("state_002")
