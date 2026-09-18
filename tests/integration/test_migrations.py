from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.models import Base, OpportunityRecordRow, UserPriorityRow
from career_harness.db.session import create_sqlite_engine, sqlite_url


def test_fresh_database_bootstraps_to_head(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "fresh.db")
    upgrade_to_head(database_url)

    tables = set(inspect(create_sqlite_engine(database_url)).get_table_names())

    assert {
        "alembic_version",
        "domain_event",
        "entity_revision",
        "entity_state",
        "idempotency_record",
        "migration_mismatch",
        "opportunity_admission_decision",
        "opportunity_admission_proposal",
        "opportunity_record",
        "outbox_message",
        "suggested_priority",
        "user_priority",
        "watchlist_item",
    } <= tables
    assert set(Base.metadata.tables) <= tables


def test_migration_is_repeatable(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "repeatable.db")
    upgrade_to_head(database_url)
    upgrade_to_head(database_url)


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

