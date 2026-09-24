from pathlib import Path

from alembic import command
from sqlalchemy import inspect

from career_harness.db.migrations import alembic_config
from career_harness.db.session import create_sqlite_engine, sqlite_url

TABLES = {
    "interview_identity",
    "interview_revision_record",
    "interview_evidence_ref",
}


def test_interview_migration_is_additive_and_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "interview-core.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0012_application_outcome")
    engine = create_sqlite_engine(database_url)
    assert not TABLES & set(inspect(engine).get_table_names())
    engine.dispose()

    command.upgrade(config, "0013_interview_core")
    engine = create_sqlite_engine(database_url)
    assert set(inspect(engine).get_table_names()) >= TABLES
    with engine.connect() as connection:
        triggers = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND name LIKE 'trg_interview%'"
            ).scalars()
        )
    assert "trg_interview_revision_seal" in triggers
    assert "trg_interview_evidence_ref_sealed" in triggers
    for table in TABLES:
        assert f"trg_{table}_no_update" in triggers
        assert f"trg_{table}_no_delete" in triggers
    engine.dispose()

    command.downgrade(config, "0012_application_outcome")
    engine = create_sqlite_engine(database_url)
    assert not TABLES & set(inspect(engine).get_table_names())
    assert "application_revision_record" in set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        triggers = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND name LIKE 'trg_interview%'"
            ).scalars()
        )
    assert not triggers
    engine.dispose()

    command.upgrade(config, "0013_interview_core")
    engine = create_sqlite_engine(database_url)
    assert set(inspect(engine).get_table_names()) >= TABLES
    engine.dispose()
