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
    OpportunityRecordRow,
    PersonalCapabilityStateRow,
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

