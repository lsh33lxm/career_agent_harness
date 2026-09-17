from pathlib import Path

from sqlalchemy import inspect

from career_harness.db.migrations import upgrade_to_head
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
        "outbox_message",
    } <= tables


def test_migration_is_repeatable(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "repeatable.db")
    upgrade_to_head(database_url)
    upgrade_to_head(database_url)

