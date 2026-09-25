from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.models import CapabilityIdentityRow
from career_harness.db.session import create_sqlite_engine, sqlite_url
from tests.support.job_data import seed_job_revision_rows

MATCH_TABLES = ("match_assessment", "match_requirement_result", "match_gap")


def _seed_match_prerequisites(connection) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    seed_job_revision_rows(connection, "job_001", 1)
    connection.execute(
        CapabilityIdentityRow.__table__.insert(),
        {"capability_id": "capability_agents"},
    )
    connection.exec_driver_sql(
        "INSERT INTO capability_node "
        "(capability_id, graph_version_id, canonical_name, description, layer, "
        "lifecycle_status) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "capability_agents",
            "graph_001",
            "Agent Engineering",
            "Build reliable agent systems.",
            "track",
            "active",
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO capability_graph_version "
        "(graph_version_id, version_label, parent_graph_version_id, change_note, "
        "released_at, released_by, released_by_kind) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "graph_001",
            "graph-1",
            None,
            "Initial graph.",
            now.isoformat(),
            "user",
            "user",
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO entity_state "
        "(entity_id, entity_kind, revision, schema_version, state, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "opportunity_001",
            "opportunity",
            1,
            1,
            '{"entity_id": "opportunity_001"}',
            now.isoformat(),
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO entity_revision "
        "(revision_id, entity_id, revision, schema_version, state, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "revision_opportunity_001_1",
            "opportunity_001",
            1,
            1,
            '{"entity_id": "opportunity_001"}',
            now.isoformat(),
            "user",
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO opportunity_record "
        "(opportunity_id, job_id, job_revision, state, revision, schema_version, "
        "admitted_at, admitted_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("opportunity_001", "job_001", 1, "qualified", 1, 1, now.isoformat(), "user"),
    )
    connection.exec_driver_sql(
        "INSERT INTO job_requirement_identity (requirement_id, job_id) VALUES (?, ?)",
        ("requirement_001", "job_001"),
    )
    connection.exec_driver_sql(
        "INSERT INTO job_requirement_scope "
        "(requirement_id, requirement_revision, ordinal, scope) VALUES (?, ?, ?, ?)",
        ("requirement_001", 1, 0, "understand"),
    )
    connection.exec_driver_sql(
        "INSERT INTO job_requirement_evidence_ref "
        "(requirement_id, requirement_revision, ordinal, evidence_ref_id) VALUES (?, ?, ?, ?)",
        ("requirement_001", 1, 0, "evidence_job_001_1"),
    )
    connection.exec_driver_sql(
        "INSERT INTO job_requirement_revision "
        "(requirement_id, revision, schema_version, job_id, job_revision, requirement_text, "
        "importance, capability_id, graph_version_id, required_scope_count, "
        "source_evidence_count, status, proposed_by, proposed_by_kind, proposed_at, "
        "reviewed_by, reviewed_by_kind, review_reason, reviewed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "requirement_001",
            1,
            1,
            "job_001",
            1,
            "Requirement text.",
            "required",
            "capability_agents",
            "graph_001",
            1,
            1,
            "accepted",
            "agent:extractor",
            "agent",
            now.isoformat(),
            "user",
            "user",
            "Confirmed.",
            now.isoformat(),
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO match_assessment "
        "(assessment_id, opportunity_id, opportunity_revision, job_id, job_revision, "
        "candidate_id, policy_version, manifest, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "assessment_001",
            "opportunity_001",
            1,
            "job_001",
            1,
            "candidate_001",
            "match-policy-v1",
            '{"policy_version": "match-policy-v1", "requirements": [{"requirement_id": '
            '"requirement_001", "revision": 1}]}',
            now.isoformat(),
            "agent:match",
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO match_requirement_result "
        "(assessment_id, requirement_id, requirement_revision, capability_id, classification, "
        "covered_scopes, missing_scopes, reasons) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "assessment_001",
            "requirement_001",
            1,
            "capability_agents",
            "clear_gap",
            "[]",
            '["understand"]',
            '[{"code": "no_qualified_recorded_support"}]',
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO match_gap "
        "(gap_id, assessment_id, requirement_id, requirement_revision, capability_id, "
        "classification) VALUES (?, ?, ?, ?, ?, ?)",
        ("gap_001", "assessment_001", "requirement_001", 1, "capability_agents", "clear_gap"),
    )


def test_match_migration_rehearsal_upgrades_and_downgrades_on_disposable_database(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "match-rehearsal.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0008_job_requirement_persistence")
    engine = create_sqlite_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert not set(MATCH_TABLES) & tables

    command.upgrade(config, "0009_match_gap_persistence")
    tables = set(inspect(engine).get_table_names())
    assert set(MATCH_TABLES) <= tables
    with engine.connect() as connection:
        triggers = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_match_%'"
            ).scalars()
        )
    assert triggers == {
        f"trg_{table}_{action}" for table in MATCH_TABLES for action in ("no_update", "no_delete")
    }

    command.downgrade(config, "0008_job_requirement_persistence")
    engine.dispose()
    engine = create_sqlite_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert not set(MATCH_TABLES) & tables
    assert "job_requirement_revision" in tables
    with engine.connect() as connection:
        remaining = connection.exec_driver_sql(
            "SELECT count(*) FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_match_%'"
        ).scalar_one()
    assert remaining == 0

    command.upgrade(config, "0009_match_gap_persistence")
    engine.dispose()
    engine = create_sqlite_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert set(MATCH_TABLES) <= tables
    engine.dispose()


def test_match_tables_are_immutable(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "match-immutable.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        _seed_match_prerequisites(connection)

    statements = (
        "UPDATE match_assessment SET candidate_id = 'candidate_002' "
        "WHERE assessment_id = 'assessment_001'",
        "DELETE FROM match_assessment WHERE assessment_id = 'assessment_001'",
        "UPDATE match_requirement_result SET classification = 'covered' "
        "WHERE assessment_id = 'assessment_001'",
        "DELETE FROM match_requirement_result WHERE assessment_id = 'assessment_001'",
        "UPDATE match_gap SET classification = 'quick_to_strengthen' WHERE gap_id = 'gap_001'",
        "DELETE FROM match_gap WHERE gap_id = 'gap_001'",
    )
    for statement in statements:
        with pytest.raises(IntegrityError, match="immutable"), engine.begin() as connection:
            connection.exec_driver_sql(statement)


def test_match_gap_rejects_covered_classification_at_database_boundary(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "match-gap-classification.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    with engine.begin() as connection:
        _seed_match_prerequisites(connection)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO match_gap "
            "(gap_id, assessment_id, requirement_id, requirement_revision, capability_id, "
            "classification) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "gap_covered",
                "assessment_001",
                "requirement_001",
                1,
                "capability_agents",
                "covered",
            ),
        )
