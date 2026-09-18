from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.models import (
    Base,
    CandidateCapabilityNodeRow,
    CapabilityEvidenceBindingRow,
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityInvestmentStateRow,
    CapabilityNodeRow,
    ContextManifestAssetRefRow,
    ContextManifestKnowledgeRefRow,
    ContextManifestRow,
    EntityRevisionRow,
    EntityStateRow,
    OpportunityRecordRow,
    PersonalCapabilityStateRow,
    ProjectCapabilityBasisRow,
    ProjectCapabilityStateRow,
    ProjectEnhancementTaskRow,
    ProjectEvidenceRow,
    ProjectIdentityRow,
    ProjectRecordRow,
    ProjectScanScopeRow,
    ProjectSourceEntryRow,
    ProjectSourceManifestRow,
    UserPriorityRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url


def test_fresh_database_bootstraps_to_head(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "fresh.db")
    upgrade_to_head(database_url)

    tables = set(inspect(create_sqlite_engine(database_url)).get_table_names())

    assert {
        "alembic_version",
        "candidate_capability_node",
        "capability_evidence_binding",
        "capability_graph_version",
        "capability_identity",
        "capability_investment_state",
        "capability_market_binding",
        "capability_node",
        "capability_relation",
        "context_manifest",
        "context_manifest_asset_ref",
        "context_manifest_knowledge_ref",
        "domain_event",
        "entity_revision",
        "entity_state",
        "idempotency_record",
        "migration_mismatch",
        "opportunity_admission_decision",
        "opportunity_admission_proposal",
        "opportunity_record",
        "outbox_message",
        "personal_capability_state",
        "project_capability_basis",
        "project_capability_state",
        "project_enhancement_task",
        "project_evidence",
        "project_identity",
        "project_record",
        "project_scan_scope",
        "project_source_entry",
        "project_source_manifest",
        "suggested_priority",
        "user_priority",
        "watchlist_item",
    } <= tables
    assert set(Base.metadata.tables) <= tables


def test_migration_is_repeatable(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "repeatable.db")
    upgrade_to_head(database_url)
    upgrade_to_head(database_url)


def test_migrated_schema_matches_declared_metadata_columns(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "metadata-parity.db")
    upgrade_to_head(database_url)
    inspector = inspect(create_sqlite_engine(database_url))

    for table_name, table in Base.metadata.tables.items():
        migrated_columns = {column["name"] for column in inspector.get_columns(table_name)}
        declared_columns = {column.name for column in table.columns}
        assert migrated_columns == declared_columns, table_name


def test_opportunity_migration_preserves_foundation_data(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "existing.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0001_foundation")
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO entity_state "
            "(entity_id, entity_kind, revision, schema_version, state, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("candidate_001", "candidate", 1, 1, "{}", now.isoformat()),
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT entity_id, revision FROM entity_state WHERE entity_id = ?",
            ("candidate_001",),
        ).one()
    assert row == ("candidate_001", 1)


def test_opportunity_migration_downgrades_on_disposable_database(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "downgrade.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "0001_foundation")

    tables = set(inspect(create_sqlite_engine(database_url)).get_table_names())
    assert "entity_state" in tables
    assert not {
        "opportunity_admission_decision",
        "opportunity_admission_proposal",
        "opportunity_record",
        "suggested_priority",
        "user_priority",
        "watchlist_item",
    } & tables


def test_user_priority_database_constraint_rejects_agent_actor(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "priority-authority.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)

    with engine.begin() as connection:
        connection.execute(
            OpportunityRecordRow.__table__.insert(),
            {
                "opportunity_id": "opportunity_001",
                "job_id": "job_001",
                "job_revision": 1,
                "state": "qualified",
                "revision": 1,
                "schema_version": 1,
                "admitted_at": now,
                "admitted_by": "user",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            UserPriorityRow.__table__.insert(),
            {
                "opportunity_id": "opportunity_001",
                "revision": 1,
                "level": "high",
                "actor": "agent",
                "set_at": now,
            },
        )


def test_capability_migration_downgrades_to_opportunity_schema(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "capability-downgrade.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "0002_opportunity_core")

    tables = set(inspect(create_sqlite_engine(database_url)).get_table_names())
    assert "opportunity_record" in tables
    assert not {
        "capability_graph_version",
        "capability_identity",
        "capability_node",
        "personal_capability_state",
    } & tables


@pytest.mark.parametrize("actor_kind", ["agent", "model"])
def test_unsupported_actor_cannot_release_official_capability_graph(
    tmp_path: Path, actor_kind: str
) -> None:
    database_url = sqlite_url(tmp_path / "capability-authority.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            CapabilityGraphVersionRow.__table__.insert(),
            {
                "graph_version_id": "graph_version_001",
                "version_label": "v1.0",
                "change_note": "Initial graph.",
                "released_at": datetime.now(UTC),
                "released_by": "model-run-001",
                "released_by_kind": actor_kind,
            },
        )


def test_official_graph_upgrade_does_not_overwrite_personal_overlay(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "capability-overlay.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)

    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_observability"},
        )
        connection.execute(
            CapabilityNodeRow.__table__.insert(),
            {
                "capability_id": "capability_observability",
                "graph_version_id": "graph_version_001",
                "canonical_name": "Agent Observability",
                "description": "Observe agent behavior.",
                "layer": "track",
                "lifecycle_status": "active",
            },
        )
        connection.execute(
            CapabilityGraphVersionRow.__table__.insert(),
            {
                "graph_version_id": "graph_version_001",
                "version_label": "v1.0",
                "change_note": "Initial graph.",
                "released_at": now,
                "released_by": "user",
                "released_by_kind": "user",
            },
        )
        connection.execute(
            CapabilityNodeRow.__table__.insert(),
            {
                "capability_id": "capability_observability",
                "graph_version_id": "graph_version_002",
                "canonical_name": "Agent Observability",
                "description": "Observe and diagnose agent behavior.",
                "layer": "track",
                "lifecycle_status": "active",
            },
        )
        connection.execute(
            CapabilityGraphVersionRow.__table__.insert(),
            {
                "graph_version_id": "graph_version_002",
                "version_label": "v1.1",
                "parent_graph_version_id": "graph_version_001",
                "change_note": "Clarify observability.",
                "released_at": now,
                "released_by": "user",
                "released_by_kind": "user",
            },
        )
        connection.execute(
            PersonalCapabilityStateRow.__table__.insert(),
            [
                {
                    "personal_state_id": "personal_state_001",
                    "candidate_id": "candidate_001",
                    "capability_id": "capability_observability",
                    "understand": True,
                    "explain": True,
                    "apply": False,
                    "evidence": False,
                    "interview_ready": False,
                    "revision": 1,
                    "schema_version": 1,
                    "updated_at": now,
                    "updated_by": "user",
                    "updated_by_kind": "user",
                },
                {
                    "personal_state_id": "personal_state_001",
                    "candidate_id": "candidate_001",
                    "capability_id": "capability_observability",
                    "understand": True,
                    "explain": True,
                    "apply": True,
                    "evidence": False,
                    "interview_ready": False,
                    "revision": 2,
                    "schema_version": 1,
                    "updated_at": now,
                    "updated_by": "user",
                    "updated_by_kind": "user",
                },
            ],
        )

    with engine.connect() as connection:
        node_count = connection.exec_driver_sql(
            "SELECT COUNT(*) FROM capability_node WHERE capability_id = ?",
            ("capability_observability",),
        ).scalar_one()
        overlays = connection.exec_driver_sql(
            "SELECT revision, understand, explain, apply "
            "FROM personal_capability_state WHERE personal_state_id = ? ORDER BY revision",
            ("personal_state_001",),
        ).all()

    assert node_count == 2
    assert overlays == [(1, 1, 1, 0), (2, 1, 1, 1)]

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            CapabilityNodeRow.__table__.update()
            .where(CapabilityNodeRow.graph_version_id == "graph_version_001")
            .values(description="Mutated after release."),
        )


def test_candidate_requires_source_evidence_at_database_boundary(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "candidate-evidence.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            CandidateCapabilityNodeRow.__table__.insert(),
            {
                "candidate_node_id": "candidate_node_001",
                "proposed_canonical_name": "Agent Evaluation",
                "proposed_description": "Evaluate agent systems.",
                "proposed_layer": "track",
                "source_evidence_refs": [],
                "discovered_by": "model-run-001",
                "status": "pending",
            },
        )


def test_evidence_binding_cannot_cross_capability_state(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "binding-capability.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)

    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            [
                {"capability_id": "capability_a"},
                {"capability_id": "capability_b"},
            ],
        )
        connection.execute(
            PersonalCapabilityStateRow.__table__.insert(),
            {
                "personal_state_id": "personal_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": False,
                "apply": False,
                "evidence": False,
                "interview_ready": False,
                "revision": 1,
                "schema_version": 1,
                "updated_at": now,
                "updated_by": "user",
                "updated_by_kind": "user",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            CapabilityEvidenceBindingRow.__table__.insert(),
            {
                "binding_id": "binding_001",
                "personal_state_id": "personal_state_001",
                "personal_state_revision": 1,
                "capability_id": "capability_b",
                "project_evidence_id": "project_evidence_001",
                "authority": "code_verified",
                "scopes": ["apply"],
                "bound_at": now,
                "bound_by": "project-scanner",
            },
        )


@pytest.mark.parametrize("actor_kind", ["agent", "model"])
def test_unsupported_actor_cannot_update_personal_capability_state(
    tmp_path: Path, actor_kind: str
) -> None:
    database_url = sqlite_url(tmp_path / "personal-state-authority.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)

    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_a"},
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            PersonalCapabilityStateRow.__table__.insert(),
            {
                "personal_state_id": "personal_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": False,
                "apply": False,
                "evidence": False,
                "interview_ready": False,
                "revision": 1,
                "schema_version": 1,
                "updated_at": datetime.now(UTC),
                "updated_by": "model-run-001",
                "updated_by_kind": actor_kind,
            },
        )


def test_investment_state_rejects_result_that_disagrees_with_factors(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "investment-consistency.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)

    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_a"},
        )
        connection.execute(
            CapabilityGraphVersionRow.__table__.insert(),
            {
                "graph_version_id": "graph_version_001",
                "version_label": "v1.0",
                "change_note": "Initial graph.",
                "released_at": now,
                "released_by": "user",
                "released_by_kind": "user",
            },
        )
        connection.execute(
            PersonalCapabilityStateRow.__table__.insert(),
            {
                "personal_state_id": "personal_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "understand": True,
                "explain": False,
                "apply": False,
                "evidence": False,
                "interview_ready": False,
                "revision": 1,
                "schema_version": 1,
                "updated_at": now,
                "updated_by": "user",
                "updated_by_kind": "user",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            CapabilityInvestmentStateRow.__table__.insert(),
            {
                "investment_state_id": "investment_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_a",
                "target_market_demand": 0.5,
                "opportunity_importance": 0.5,
                "cross_opportunity_reuse": 0.5,
                "project_proximity": 0.5,
                "evidence_feasibility": 0.5,
                "personal_interest": 0.5,
                "learning_cost": 0.5,
                "recommendation": "high",
                "score": 0.9,
                "reasons": ["Contradictory result."],
                "graph_version_id": "graph_version_001",
                "personal_state_id": "personal_state_001",
                "personal_state_revision": 1,
                "market_binding_ids": ["market_binding_001"],
                "opportunity_ids": [],
                "rule_version": "capability-investment-v1",
                "calculated_at": now,
            },
        )


def _insert_project_foundation(connection, now: datetime) -> None:  # type: ignore[no-untyped-def]
    connection.execute(
        ProjectIdentityRow.__table__.insert(),
        {"project_id": "project_001"},
    )
    connection.execute(
        ProjectRecordRow.__table__.insert(),
        {
            "project_id": "project_001",
            "revision": 1,
            "display_name": "Agent Gateway",
            "root_locator": "D:/projects/agent-gateway",
            "schema_version": 1,
            "created_at": now,
            "created_by": "user",
        },
    )
    connection.execute(
        ProjectScanScopeRow.__table__.insert(),
        {
            "scope_id": "scope_001",
            "revision": 1,
            "project_id": "project_001",
            "allowed_paths": ["src", "tests", "README.md"],
            "denied_paths": ["src/secrets", ".env"],
            "follow_symlinks": False,
            "schema_version": 1,
            "created_at": now,
            "created_by": "user",
        },
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
        {
            "manifest_id": "manifest_001",
            "relative_path": "src/router.py",
            "sha256": "a" * 64,
            "byte_length": 128,
        },
    )


def test_project_migration_preserves_capability_data_and_downgrades(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "project-migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0003_capability_core")
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_observability"},
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        capability_id = connection.exec_driver_sql(
            "SELECT capability_id FROM capability_identity"
        ).scalar_one()
    assert capability_id == "capability_observability"

    command.downgrade(config, "0003_capability_core")
    tables = set(inspect(engine).get_table_names())
    assert "capability_identity" in tables
    assert not {
        "project_identity",
        "project_scan_scope",
        "project_source_manifest",
        "project_evidence",
        "project_enhancement_task",
    } & tables


@pytest.mark.parametrize(
    ("allowed_paths", "follow_symlinks"),
    [
        ([], False),
        (["../outside"], False),
        (["src/./nested"], False),
        (["src"], True),
    ],
)
def test_project_scope_database_boundary_is_explicit_and_no_follow(
    tmp_path: Path,
    allowed_paths: list[str],
    follow_symlinks: bool,
) -> None:
    database_url = sqlite_url(tmp_path / "project-scope.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            {"project_id": "project_001"},
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectScanScopeRow.__table__.insert(),
            {
                "scope_id": "scope_001",
                "revision": 1,
                "project_id": "project_001",
                "allowed_paths": allowed_paths,
                "denied_paths": [],
                "follow_symlinks": follow_symlinks,
                "schema_version": 1,
                "created_at": now,
                "created_by": "user",
            },
        )


def test_source_manifest_is_pinned_to_project_and_scope_revision(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "manifest-scope.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            [{"project_id": "project_001"}, {"project_id": "project_002"}],
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
                "created_at": now,
                "created_by": "user",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectSourceManifestRow.__table__.insert(),
            {
                "manifest_id": "manifest_wrong_project",
                "project_id": "project_002",
                "scan_scope_id": "scope_001",
                "scan_scope_revision": 1,
                "generated_at": now,
            },
        )


def test_project_scope_revision_cannot_rebind_to_another_project(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "scope-stable-identity.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            [{"project_id": "project_001"}, {"project_id": "project_002"}],
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
                "created_at": now,
                "created_by": "user",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectScanScopeRow.__table__.insert(),
            {
                "scope_id": "scope_001",
                "revision": 2,
                "project_id": "project_002",
                "allowed_paths": ["src"],
                "denied_paths": [],
                "follow_symlinks": False,
                "schema_version": 1,
                "created_at": now,
                "created_by": "user",
            },
        )


@pytest.mark.parametrize(
    "relative_path",
    ["docs/notes.md", "src/secrets/token.txt", "src/./secrets/token.txt"],
)
def test_source_entry_cannot_escape_or_override_denied_scope(
    tmp_path: Path, relative_path: str
) -> None:
    database_url = sqlite_url(tmp_path / "source-scope.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectSourceEntryRow.__table__.insert(),
            {
                "manifest_id": "manifest_001",
                "relative_path": relative_path,
                "sha256": "b" * 64,
                "byte_length": 64,
            },
        )


def test_scope_paths_are_compared_literally_not_as_sql_patterns(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "source-literal-scope.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            {"project_id": "project_001"},
        )
        connection.execute(
            ProjectScanScopeRow.__table__.insert(),
            {
                "scope_id": "scope_001",
                "revision": 1,
                "project_id": "project_001",
                "allowed_paths": ["src_foo"],
                "denied_paths": [],
                "follow_symlinks": False,
                "schema_version": 1,
                "created_at": now,
                "created_by": "user",
            },
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

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectSourceEntryRow.__table__.insert(),
            {
                "manifest_id": "manifest_001",
                "relative_path": "srcXfoo/router.py",
                "sha256": "b" * 64,
                "byte_length": 64,
            },
        )


def test_evidence_source_manifest_cannot_change_after_use(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "source-frozen.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            {
                "evidence_id": "project_evidence_001",
                "revision": 1,
                "project_id": "project_001",
                "summary": "Router has an explicit fallback branch.",
                "claim_kind": "technical_observation",
                "manifest_id": "manifest_001",
                "scanner": "fixture-scanner",
                "scanner_version": "1",
                "authority": "code_verified",
                "freshness": "current",
                "review_status": "accepted",
                "reviewed_by": "project-evidence-policy-v1",
                "reviewed_by_kind": "rule",
                "review_reason": "Technical observation is supported by the manifest.",
                "observed_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "rule:project-scan",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectSourceEntryRow.__table__.insert(),
            {
                "manifest_id": "manifest_001",
                "relative_path": "tests/test_router.py",
                "sha256": "b" * 64,
                "byte_length": 64,
            },
        )


@pytest.mark.parametrize(
    ("authority", "claim_kind", "review_status"),
    [
        ("ai_inferred", "technical_observation", "accepted"),
        ("code_verified", "technical_observation", "accepted"),
        ("code_verified", "performance", "proposed"),
        ("code_verified", "personal_contribution", "proposed"),
    ],
)
def test_project_evidence_authority_is_enforced_at_database_boundary(
    tmp_path: Path,
    authority: str,
    claim_kind: str,
    review_status: str,
) -> None:
    database_url = sqlite_url(tmp_path / "project-evidence-authority.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            {
                "evidence_id": "project_evidence_001",
                "revision": 1,
                "project_id": "project_001",
                "summary": "Unverified claim.",
                "claim_kind": claim_kind,
                "manifest_id": "manifest_001",
                "scanner": "fixture-scanner",
                "scanner_version": "1",
                "authority": authority,
                "freshness": "current",
                "review_status": review_status,
                "observed_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "agent",
            },
        )


def test_capability_binding_pins_exact_project_evidence_revision(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "project-evidence-binding.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            {
                "evidence_id": "project_evidence_001",
                "revision": 1,
                "project_id": "project_001",
                "summary": "Router has an explicit fallback branch.",
                "claim_kind": "technical_observation",
                "manifest_id": "manifest_001",
                "scanner": "fixture-scanner",
                "scanner_version": "1",
                "authority": "code_verified",
                "freshness": "current",
                "review_status": "accepted",
                "reviewed_by": "project-evidence-policy-v1",
                "reviewed_by_kind": "rule",
                "review_reason": "Technical observation is supported by the manifest.",
                "observed_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "rule:project-scan",
            },
        )
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_observability"},
        )
        connection.execute(
            PersonalCapabilityStateRow.__table__.insert(),
            {
                "personal_state_id": "personal_state_001",
                "candidate_id": "candidate_001",
                "capability_id": "capability_observability",
                "understand": True,
                "explain": True,
                "apply": True,
                "evidence": True,
                "interview_ready": False,
                "revision": 1,
                "schema_version": 1,
                "updated_at": now,
                "updated_by": "rule:project-evidence",
                "updated_by_kind": "rule",
            },
        )

    binding = {
        "binding_id": "binding_001",
        "personal_state_id": "personal_state_001",
        "personal_state_revision": 1,
        "capability_id": "capability_observability",
        "project_evidence_id": "project_evidence_001",
        "authority": "code_verified",
        "scopes": ["apply", "evidence"],
        "bound_at": now,
        "bound_by": "rule:project-evidence",
    }
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(CapabilityEvidenceBindingRow.__table__.insert(), binding)

    with engine.begin() as connection:
        connection.execute(
            CapabilityEvidenceBindingRow.__table__.insert(),
            {**binding, "project_evidence_revision": 1},
        )


def test_project_capability_resume_ready_requires_validation_and_approval(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "project-capability-basis.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_observability"},
        )
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            {
                "evidence_id": "evidence_validation",
                "revision": 1,
                "project_id": "project_001",
                "summary": "Focused validation tests passed.",
                "claim_kind": "validation",
                "manifest_id": "manifest_001",
                "scanner": "fixture-scanner",
                "scanner_version": "1",
                "authority": "document_supported",
                "freshness": "current",
                "review_status": "accepted",
                "reviewed_by": "project-evidence-policy-v1",
                "reviewed_by_kind": "rule",
                "review_reason": "Validation result is documented by the manifest.",
                "observed_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "rule:project-scan",
            },
        )

    state = {
        "capability_state_id": "project_capability_001",
        "revision": 1,
        "project_id": "project_001",
        "capability_id": "capability_observability",
        "state": "resume_ready",
        "finalized_at": now,
        "schema_version": 1,
        "created_at": now,
        "created_by": "agent",
    }
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(ProjectCapabilityStateRow.__table__.insert(), state)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            {
                "basis_id": "basis_validation_001",
                "capability_state_id": "project_capability_001",
                "state_revision": 1,
                "basis_kind": "validation_evidence",
                "project_evidence_id": "evidence_validation",
                "project_evidence_revision": 1,
            },
        )

    approval_state = {
        "subject_id": "project_capability_other",
        "subject_revision": 1,
        "purpose": "project_capability_resume_ready",
        "status": "approved",
        "proposer_kind": "agent",
        "approver_kind": "user",
    }
    with engine.begin() as connection:
        connection.execute(
            EntityStateRow.__table__.insert(),
            {
                "entity_id": "approval_001",
                "entity_kind": "approval",
                "revision": 1,
                "schema_version": 1,
                "state": approval_state,
                "updated_at": now,
            },
        )
        connection.execute(
            EntityRevisionRow.__table__.insert(),
            {
                "revision_id": "approval_revision_001",
                "entity_id": "approval_001",
                "revision": 1,
                "schema_version": 1,
                "state": approval_state,
                "created_at": now,
                "created_by": "user",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            {
                "basis_id": "basis_wrong_approval_001",
                "capability_state_id": "project_capability_001",
                "state_revision": 1,
                "basis_kind": "resume_approval",
                "approval_id": "approval_001",
                "approval_revision": 1,
            },
        )

    exact_approval_state = {**approval_state, "subject_id": "project_capability_001"}
    with engine.begin() as connection:
        connection.execute(
            EntityStateRow.__table__.insert(),
            {
                "entity_id": "approval_002",
                "entity_kind": "approval",
                "revision": 1,
                "schema_version": 1,
                "state": exact_approval_state,
                "updated_at": now,
            },
        )
        connection.execute(
            EntityRevisionRow.__table__.insert(),
            {
                "revision_id": "approval_revision_002",
                "entity_id": "approval_002",
                "revision": 1,
                "schema_version": 1,
                "state": exact_approval_state,
                "created_at": now,
                "created_by": "user",
            },
        )
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            {
                "basis_id": "basis_validation_001",
                "capability_state_id": "project_capability_001",
                "state_revision": 1,
                "basis_kind": "validation_evidence",
                "project_evidence_id": "evidence_validation",
                "project_evidence_revision": 1,
            },
        )
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            {
                "basis_id": "basis_approval_001",
                "capability_state_id": "project_capability_001",
                "state_revision": 1,
                "basis_kind": "resume_approval",
                "approval_id": "approval_002",
                "approval_revision": 1,
            },
        )
        connection.execute(ProjectCapabilityStateRow.__table__.insert(), state)

    with engine.connect() as connection:
        persisted_state = connection.execute(
            ProjectCapabilityStateRow.__table__.select().where(
                ProjectCapabilityStateRow.capability_state_id
                == "project_capability_001"
            )
        ).one()
        basis_ids = set(
            connection.execute(
                ProjectCapabilityBasisRow.__table__.select().where(
                    ProjectCapabilityBasisRow.capability_state_id
                    == "project_capability_001"
                )
            ).scalars()
        )
    assert persisted_state.state == "resume_ready"
    assert basis_ids == {"basis_validation_001", "basis_approval_001"}

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectCapabilityStateRow.__table__.update()
            .where(
                ProjectCapabilityStateRow.capability_state_id
                == "project_capability_001"
            )
            .values(state="validated")
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            EntityRevisionRow.__table__.update()
            .where(EntityRevisionRow.entity_id == "approval_002")
            .values(created_by="attacker")
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            EntityRevisionRow.__table__.delete().where(
                EntityRevisionRow.entity_id == "approval_002"
            )
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            {
                "basis_id": "basis_after_finalize_001",
                "capability_state_id": "project_capability_001",
                "state_revision": 1,
                "basis_kind": "validation_evidence",
                "project_evidence_id": "evidence_validation",
                "project_evidence_revision": 1,
            },
        )


def test_project_capability_basis_cannot_cross_project_boundary(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "project-capability-project-scope.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            {"project_id": "project_002"},
        )
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_observability"},
        )
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            {
                "evidence_id": "evidence_validation",
                "revision": 1,
                "project_id": "project_001",
                "summary": "Focused validation tests passed.",
                "claim_kind": "validation",
                "manifest_id": "manifest_001",
                "scanner": "fixture-scanner",
                "scanner_version": "1",
                "authority": "document_supported",
                "freshness": "current",
                "review_status": "accepted",
                "reviewed_by": "project-evidence-policy-v1",
                "reviewed_by_kind": "rule",
                "review_reason": "Validation result is documented by the manifest.",
                "observed_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "rule:project-scan",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ProjectCapabilityBasisRow.__table__.insert(),
            {
                "basis_id": "basis_cross_project_001",
                "capability_state_id": "project_capability_002",
                "state_revision": 1,
                "basis_kind": "validation_evidence",
                "project_evidence_id": "evidence_validation",
                "project_evidence_revision": 1,
            },
        )
        connection.execute(
            ProjectCapabilityStateRow.__table__.insert(),
            {
                "capability_state_id": "project_capability_002",
                "revision": 1,
                "project_id": "project_002",
                "capability_id": "capability_observability",
                "state": "validated",
                "finalized_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "agent",
            },
        )

    with engine.connect() as connection:
        state_count = connection.exec_driver_sql(
            "SELECT count(*) FROM project_capability_state "
            "WHERE capability_state_id = ?",
            ("project_capability_002",),
        ).scalar_one()
        basis_count = connection.exec_driver_sql(
            "SELECT count(*) FROM project_capability_basis "
            "WHERE capability_state_id = ?",
            ("project_capability_002",),
        ).scalar_one()
    assert (state_count, basis_count) == (0, 0)


def test_l1_enhancement_task_rejects_empty_plan_and_allows_new_revision(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "project-enhancement.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            {"project_id": "project_001"},
        )
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_observability"},
        )

    task = {
        "task_id": "enhancement_001",
        "revision": 1,
        "project_id": "project_001",
        "target_gap_id": "gap_001",
        "target_capability_id": "capability_observability",
        "learning_plan": ["Learn tracing."],
        "files_to_review": ["src/router.py"],
        "change_plan": [" "],
        "experiment_plan": ["Capture a trace."],
        "validation_plan": ["Run focused tests."],
        "expected_evidence": ["Trace and test output candidates."],
        "status": "proposed",
        "schema_version": 1,
        "created_at": now,
        "created_by": "user",
    }
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(ProjectEnhancementTaskRow.__table__.insert(), task)

    task["change_plan"] = ["Add spans around provider calls."]
    task["files_to_review"] = ["src/./router.py"]
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(ProjectEnhancementTaskRow.__table__.insert(), task)

    task["files_to_review"] = ["src/router.py"]
    with engine.begin() as connection:
        connection.execute(ProjectEnhancementTaskRow.__table__.insert(), task)
        connection.execute(
            ProjectEnhancementTaskRow.__table__.insert(),
            {**task, "revision": 2, "status": "ready"},
        )

    with engine.connect() as connection:
        revisions = connection.exec_driver_sql(
            "SELECT revision, status FROM project_enhancement_task "
            "WHERE task_id = ? ORDER BY revision",
            ("enhancement_001",),
        ).all()
    assert revisions == [(1, "proposed"), (2, "ready")]


def _context_manifest_row(now: datetime) -> dict[str, object]:
    return {
        "manifest_id": "context_manifest_001",
        "contract_version": "v1.4-contract-0.2.0",
        "task_type": "opportunity_gap_analysis",
        "selection_policy_version": "context-relevance-v1",
        "compression_policy_version": "context-no-compression-v1",
        "provider": "local-test-provider",
        "model_id": "test-model",
        "capabilities": ["structured_generation"],
        "skills": ["gap_analysis"],
        "input_hash": "a" * 64,
        "actor": "user",
        "run_id": "run_001",
        "created_at": now,
        "included_count": 0,
        "excluded_count": 0,
        "knowledge_ref_count": 0,
    }


def test_context_manifest_migration_preserves_project_data_and_downgrades(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "context-migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0004_project_evidence")
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            ProjectIdentityRow.__table__.insert(),
            {"project_id": "project_001"},
        )

    command.upgrade(config, "head")
    with engine.connect() as connection:
        project_id = connection.exec_driver_sql(
            "SELECT project_id FROM project_identity"
        ).scalar_one()
    assert project_id == "project_001"

    command.downgrade(config, "0004_project_evidence")
    tables = set(inspect(engine).get_table_names())
    assert "project_identity" in tables
    assert not {
        "context_manifest",
        "context_manifest_asset_ref",
        "context_manifest_knowledge_ref",
    } & tables


def test_empty_context_manifest_is_valid_and_stores_no_compiled_content(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "context-manifest.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            ContextManifestRow.__table__.insert(),
            _context_manifest_row(now),
        )

    with engine.connect() as connection:
        manifest = connection.execute(ContextManifestRow.__table__.select()).one()
    assert manifest.contract_version == "v1.4-contract-0.2.0"
    assert (manifest.included_count, manifest.excluded_count) == (0, 0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("capabilities", [f"capability_{index}" for index in range(65)]),
        ("skills", ["raw prompt sentinel " + "x" * 110]),
    ],
)
def test_context_manifest_tool_names_cannot_bypass_content_boundary(
    tmp_path: Path,
    field: str,
    value: list[str],
) -> None:
    database_url = sqlite_url(tmp_path / f"context-manifest-{field}.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestRow.__table__.insert(),
            {**_context_manifest_row(now), field: value},
        )


@pytest.mark.parametrize(
    "matched_terms",
    [
        [f"term_{index}" for index in range(65)],
        ["raw prompt sentinel " + "x" * 110],
    ],
)
def test_context_manifest_terms_cannot_bypass_content_boundary(
    tmp_path: Path,
    matched_terms: list[str],
) -> None:
    database_url = sqlite_url(tmp_path / f"context-terms-{len(matched_terms)}.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_001",
                "asset_id": "personal_context_001",
                "disposition": "included",
                "ordinal": 0,
                "asset_class": "personal_context",
                "asset_revision": 1,
                "reason": "relevance_term_match",
                "matched_terms": matched_terms,
            },
        )


def test_context_manifest_persists_ordered_audit_references_atomically(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "context-manifest-aggregate.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    included = {
        "manifest_id": "context_manifest_001",
        "asset_id": "personal_context_001",
        "disposition": "included",
        "ordinal": 0,
        "asset_class": "personal_context",
        "asset_revision": 2,
        "reason": "relevance_term_match",
        "matched_terms": ["agent engineering"],
    }

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(ContextManifestAssetRefRow.__table__.insert(), included)

    with engine.begin() as connection:
        connection.execute(ContextManifestAssetRefRow.__table__.insert(), included)
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_001",
                "asset_id": "career_state_001",
                "disposition": "excluded",
                "ordinal": 0,
                "asset_class": "career_state",
                "asset_revision": 3,
                "reason": "no_relevance_match",
                "matched_terms": [],
            },
        )
        connection.execute(
            ContextManifestKnowledgeRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_001",
                "ordinal": 0,
                "knowledge_id": "knowledge_agent_roles",
                "knowledge_revision": 7,
            },
        )
        connection.execute(
            ContextManifestRow.__table__.insert(),
            {
                **_context_manifest_row(now),
                "included_count": 1,
                "excluded_count": 1,
                "knowledge_ref_count": 1,
            },
        )

    with engine.connect() as connection:
        manifest = connection.execute(ContextManifestRow.__table__.select()).one()
        refs = connection.execute(
            ContextManifestAssetRefRow.__table__.select().order_by(
                ContextManifestAssetRefRow.disposition,
                ContextManifestAssetRefRow.ordinal,
            )
        ).all()
    assert manifest.contract_version == "v1.4-contract-0.2.0"
    assert manifest.capabilities == ["structured_generation"]
    assert [(row.asset_id, row.disposition, row.ordinal) for row in refs] == [
        ("career_state_001", "excluded", 0),
        ("personal_context_001", "included", 0),
    ]

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {**included, "asset_id": "personal_context_002", "ordinal": 1},
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestRow.__table__.update().values(model_id="changed-model")
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(ContextManifestRow.__table__.delete())

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.update().values(asset_revision=3)
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(ContextManifestKnowledgeRefRow.__table__.delete())


def test_context_manifest_rejects_invalid_shape_and_partial_aggregate(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "context-manifest-authority.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_001",
                "asset_id": "personal_context_001",
                "disposition": "included",
                "ordinal": 0,
                "asset_class": "personal_context",
                "asset_revision": 2,
                "reason": "relevance_term_match",
                "matched_terms": ["Observability"],
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_002",
                "asset_id": "personal_context_001",
                "disposition": "included",
                "ordinal": 1,
                "asset_class": "personal_context",
                "asset_revision": 2,
                "reason": "explicit_reference",
                "matched_terms": [],
            },
        )
        connection.execute(
            ContextManifestRow.__table__.insert(),
            {
                **_context_manifest_row(now),
                "manifest_id": "context_manifest_002",
                "included_count": 1,
            },
        )


def test_context_manifest_requires_exact_project_evidence_revision(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "context-project-evidence.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        _insert_project_foundation(connection, now)
        connection.execute(
            ProjectEvidenceRow.__table__.insert(),
            {
                "evidence_id": "project_evidence_001",
                "revision": 1,
                "project_id": "project_001",
                "summary": "Router has an explicit fallback branch.",
                "claim_kind": "technical_observation",
                "manifest_id": "manifest_001",
                "scanner": "fixture-scanner",
                "scanner_version": "1",
                "authority": "code_verified",
                "freshness": "current",
                "review_status": "accepted",
                "reviewed_by": "project-evidence-policy-v1",
                "reviewed_by_kind": "rule",
                "review_reason": "Technical observation is supported by the manifest.",
                "observed_at": now,
                "schema_version": 1,
                "created_at": now,
                "created_by": "rule:project-scan",
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_wrong_revision",
                "asset_id": "project_evidence_001",
                "disposition": "included",
                "ordinal": 0,
                "asset_class": "project_evidence",
                "asset_revision": 2,
                "reason": "relevance_term_match",
                "matched_terms": ["observability"],
            },
        )

    with engine.begin() as connection:
        connection.execute(
            ContextManifestAssetRefRow.__table__.insert(),
            {
                "manifest_id": "context_manifest_001",
                "asset_id": "project_evidence_001",
                "disposition": "included",
                "ordinal": 0,
                "asset_class": "project_evidence",
                "asset_revision": 1,
                "reason": "relevance_term_match",
                "matched_terms": ["observability"],
            },
        )
        connection.execute(
            ContextManifestRow.__table__.insert(),
            {**_context_manifest_row(now), "included_count": 1},
        )

