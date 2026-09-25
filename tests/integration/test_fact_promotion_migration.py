from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url

FACT_TABLES = (
    "extracted_claim_identity",
    "extracted_claim_revision",
    "extracted_claim_evidence_ref",
    "fact_identity",
    "fact_revision",
    "fact_evidence_ref",
)


def _seed_evidence_ref(connection, evidence_ref_id: str) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC).isoformat()
    connection.exec_driver_sql(
        "INSERT INTO evidence_artifact "
        "(artifact_id, sha256, media_type, artifact_class, byte_length) "
        "VALUES (?, ?, ?, ?, ?)",
        (f"artifact_{evidence_ref_id}", "a" * 64, "text/plain", "public_source", 16),
    )
    connection.exec_driver_sql(
        "INSERT INTO evidence_source (source_id, source_type, locator) VALUES (?, ?, ?)",
        (f"source_{evidence_ref_id}", "test_fixture", f"test://{evidence_ref_id}"),
    )
    connection.exec_driver_sql(
        "INSERT INTO source_snapshot (snapshot_id, source_id, captured_at, artifact_id) "
        "VALUES (?, ?, ?, ?)",
        (
            f"snapshot_{evidence_ref_id}",
            f"source_{evidence_ref_id}",
            now,
            f"artifact_{evidence_ref_id}",
        ),
    )
    connection.exec_driver_sql(
        "INSERT INTO evidence_ref (evidence_ref_id, snapshot_id, artifact_id, selector) "
        "VALUES (?, ?, ?, ?)",
        (
            evidence_ref_id,
            f"snapshot_{evidence_ref_id}",
            f"artifact_{evidence_ref_id}",
            None,
        ),
    )


def _seed_proposed_claim(connection, claim_id: str = "claim_001") -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC).isoformat()
    _seed_evidence_ref(connection, f"evidence_{claim_id}")
    connection.exec_driver_sql(
        "INSERT INTO extracted_claim_identity (claim_id) VALUES (?)", (claim_id,)
    )
    connection.exec_driver_sql(
        "INSERT INTO extracted_claim_evidence_ref "
        "(claim_id, claim_revision, ordinal, evidence_ref_id) VALUES (?, ?, ?, ?)",
        (claim_id, 1, 0, f"evidence_{claim_id}"),
    )
    connection.exec_driver_sql(
        "INSERT INTO extracted_claim_revision "
        "(claim_id, revision, schema_version, claim_type, subject_entity_id, "
        "subject_entity_kind, proposed_value, extractor, extractor_version, confidence, "
        "status, evidence_count, proposed_by, proposed_by_kind, proposed_at, "
        "reviewed_by, reviewed_by_kind, review_reason, reviewed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            claim_id,
            1,
            1,
            "skill",
            "candidate_001",
            "candidate",
            '{"name": "agents"}',
            "agent:extractor",
            "extractor-1",
            0.9,
            "proposed",
            1,
            "agent:extractor",
            "agent",
            now,
            None,
            None,
            None,
            None,
        ),
    )


def test_fact_migration_rehearsal_upgrades_and_downgrades_on_disposable_database(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "fact-rehearsal.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0009_match_gap_persistence")
    engine = create_sqlite_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert not set(FACT_TABLES) & tables

    command.upgrade(config, "0010_fact_promotion")
    tables = set(inspect(engine).get_table_names())
    assert set(FACT_TABLES) <= tables
    with engine.connect() as connection:
        triggers = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' AND ("
                "name LIKE 'trg_extracted_claim%' OR name LIKE 'trg_fact%')"
            ).scalars()
        )
    assert {
        f"trg_{table}_{action}" for table in FACT_TABLES for action in ("no_update", "no_delete")
    } <= triggers
    assert {
        "trg_extracted_claim_revision_seal",
        "trg_extracted_claim_evidence_ref_sealed",
        "trg_fact_revision_seal",
        "trg_fact_evidence_ref_sealed",
    } <= triggers

    command.downgrade(config, "0009_match_gap_persistence")
    engine.dispose()
    engine = create_sqlite_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert not set(FACT_TABLES) & tables
    assert "match_assessment" in tables
    with engine.connect() as connection:
        remaining = connection.exec_driver_sql(
            "SELECT count(*) FROM sqlite_master WHERE type = 'trigger' AND ("
            "name LIKE 'trg_extracted_claim%' OR name LIKE 'trg_fact%')"
        ).scalar_one()
    assert remaining == 0

    command.upgrade(config, "0010_fact_promotion")
    engine.dispose()
    engine = create_sqlite_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert set(FACT_TABLES) <= tables
    engine.dispose()


def test_fact_tables_are_immutable(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "fact-immutable.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC).isoformat()
    with engine.begin() as connection:
        _seed_proposed_claim(connection)
        connection.exec_driver_sql(
            "INSERT INTO fact_identity (fact_id, candidate_id) VALUES (?, ?)",
            ("fact_001", "candidate_001"),
        )
        connection.exec_driver_sql(
            "INSERT INTO fact_evidence_ref "
            "(fact_id, fact_revision, ordinal, evidence_ref_id) VALUES (?, ?, ?, ?)",
            ("fact_001", 1, 0, "evidence_claim_001"),
        )
        connection.exec_driver_sql(
            "INSERT INTO fact_revision "
            "(fact_id, revision, schema_version, subject_entity_id, subject_entity_kind, "
            "fact_type, value, authority, source_claim_id, source_claim_revision, "
            "evidence_count, verified_at, verified_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fact_001",
                1,
                1,
                "candidate_001",
                "candidate",
                "skill",
                '{"name": "agents"}',
                "user_asserted",
                "claim_001",
                1,
                1,
                now,
                "user",
            ),
        )

    statements = (
        "UPDATE extracted_claim_identity SET claim_id = 'claim_002' WHERE claim_id = 'claim_001'",
        "DELETE FROM extracted_claim_identity WHERE claim_id = 'claim_001'",
        "UPDATE extracted_claim_revision SET status = 'accepted' WHERE claim_id = 'claim_001'",
        "DELETE FROM extracted_claim_revision WHERE claim_id = 'claim_001'",
        "UPDATE extracted_claim_evidence_ref SET ordinal = 7 WHERE claim_id = 'claim_001'",
        "DELETE FROM extracted_claim_evidence_ref WHERE claim_id = 'claim_001'",
        "UPDATE fact_identity SET candidate_id = 'candidate_002' WHERE fact_id = 'fact_001'",
        "DELETE FROM fact_identity WHERE fact_id = 'fact_001'",
        "UPDATE fact_revision SET authority = 'rule_verified' WHERE fact_id = 'fact_001'",
        "DELETE FROM fact_revision WHERE fact_id = 'fact_001'",
        "UPDATE fact_evidence_ref SET ordinal = 7 WHERE fact_id = 'fact_001'",
        "DELETE FROM fact_evidence_ref WHERE fact_id = 'fact_001'",
    )
    for statement in statements:
        with pytest.raises(IntegrityError, match="immutable"), engine.begin() as connection:
            connection.exec_driver_sql(statement)


def test_claim_revision_review_metadata_matches_status_at_database_boundary(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "claim-review-check.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC).isoformat()
    with engine.begin() as connection:
        _seed_proposed_claim(connection)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_evidence_ref "
            "(claim_id, claim_revision, ordinal, evidence_ref_id) VALUES (?, ?, ?, ?)",
            ("claim_001", 2, 0, "evidence_claim_001"),
        )
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_revision "
            "(claim_id, revision, schema_version, claim_type, subject_entity_id, "
            "subject_entity_kind, proposed_value, extractor, extractor_version, confidence, "
            "status, evidence_count, proposed_by, proposed_by_kind, proposed_at, "
            "reviewed_by, reviewed_by_kind, review_reason, reviewed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "claim_001",
                2,
                1,
                "skill",
                "candidate_001",
                "candidate",
                '{"name": "agents"}',
                "agent:extractor",
                "extractor-1",
                0.9,
                "accepted",
                1,
                "agent:extractor",
                "agent",
                now,
                "agent:extractor",
                "agent",
                "Self approved.",
                now,
            ),
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_evidence_ref "
            "(claim_id, claim_revision, ordinal, evidence_ref_id) VALUES (?, ?, ?, ?)",
            ("claim_001", 2, 0, "evidence_claim_001"),
        )
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_revision "
            "(claim_id, revision, schema_version, claim_type, subject_entity_id, "
            "subject_entity_kind, proposed_value, extractor, extractor_version, confidence, "
            "status, evidence_count, proposed_by, proposed_by_kind, proposed_at, "
            "reviewed_by, reviewed_by_kind, review_reason, reviewed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "claim_001",
                2,
                1,
                "skill",
                "candidate_001",
                "candidate",
                '{"name": "agents"}',
                "agent:extractor",
                "extractor-1",
                0.9,
                "proposed",
                1,
                "agent:extractor",
                "agent",
                now,
                "user",
                "user",
                "Proposed revisions carry no review metadata.",
                now,
            ),
        )


def test_claim_and_fact_aggregates_are_sealed(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "fact-seal.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC).isoformat()
    with engine.begin() as connection:
        _seed_evidence_ref(connection, "evidence_claim_002")

    with pytest.raises(IntegrityError, match="incomplete"), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_identity (claim_id) VALUES (?)", ("claim_002",)
        )
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_revision "
            "(claim_id, revision, schema_version, claim_type, subject_entity_id, "
            "subject_entity_kind, proposed_value, extractor, extractor_version, confidence, "
            "status, evidence_count, proposed_by, proposed_by_kind, proposed_at, "
            "reviewed_by, reviewed_by_kind, review_reason, reviewed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "claim_002",
                1,
                1,
                "skill",
                "candidate_001",
                "candidate",
                '{"name": "agents"}',
                "agent:extractor",
                "extractor-1",
                0.9,
                "proposed",
                1,
                "agent:extractor",
                "agent",
                now,
                None,
                None,
                None,
                None,
            ),
        )

    with engine.begin() as connection:
        _seed_proposed_claim(connection)
    with pytest.raises(IntegrityError, match="sealed"), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO extracted_claim_evidence_ref "
            "(claim_id, claim_revision, ordinal, evidence_ref_id) VALUES (?, ?, ?, ?)",
            ("claim_001", 1, 1, "evidence_claim_002"),
        )


def test_fact_revision_requires_an_existing_claim_revision_at_database_boundary(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "fact-claim-fk.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    now = datetime.now(UTC).isoformat()
    with engine.begin() as connection:
        _seed_evidence_ref(connection, "evidence_orphan_fact")
        connection.exec_driver_sql(
            "INSERT INTO fact_identity (fact_id, candidate_id) VALUES (?, ?)",
            ("fact_orphan", None),
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO fact_revision "
            "(fact_id, revision, schema_version, subject_entity_id, subject_entity_kind, "
            "fact_type, value, authority, source_claim_id, source_claim_revision, "
            "evidence_count, verified_at, verified_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "fact_orphan",
                1,
                1,
                "candidate_001",
                "candidate",
                "skill",
                '{"name": "agents"}',
                "user_asserted",
                "claim_missing",
                1,
                0,
                now,
                "user",
            ),
        )
