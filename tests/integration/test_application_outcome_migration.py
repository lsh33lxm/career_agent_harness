from pathlib import Path

from alembic import command
from sqlalchemy import inspect

from career_harness.db.migrations import alembic_config
from career_harness.db.session import create_sqlite_engine, sqlite_url

TABLES = {
    "application_identity",
    "application_revision_record",
    "outcome_record",
    "outcome_evidence_ref",
}


def test_application_outcome_migration_is_additive_and_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "application-outcome.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0011_resume_core")
    engine = create_sqlite_engine(database_url)
    assert not TABLES & set(inspect(engine).get_table_names())
    engine.dispose()

    command.upgrade(config, "0012_application_outcome")
    engine = create_sqlite_engine(database_url)
    assert set(inspect(engine).get_table_names()) >= TABLES
    with engine.connect() as connection:
        triggers = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND (name LIKE 'trg_application%' OR name LIKE 'trg_outcome%')"
            ).scalars()
        )
    assert "trg_outcome_record_seal" in triggers
    assert "trg_outcome_evidence_ref_sealed" in triggers
    assert "trg_application_submission_stable" in triggers
    engine.dispose()

    command.downgrade(config, "0011_resume_core")
    engine = create_sqlite_engine(database_url)
    assert not TABLES & set(inspect(engine).get_table_names())
    assert "resume_revision_record" in set(inspect(engine).get_table_names())
    engine.dispose()

    command.upgrade(config, "0012_application_outcome")
    engine = create_sqlite_engine(database_url)
    assert set(inspect(engine).get_table_names()) >= TABLES
    engine.dispose()
