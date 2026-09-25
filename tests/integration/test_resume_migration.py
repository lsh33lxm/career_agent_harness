from pathlib import Path

from alembic import command
from sqlalchemy import inspect

from career_harness.db.migrations import alembic_config
from career_harness.db.session import create_sqlite_engine, sqlite_url

RESUME_TABLES = {
    "resume_identity",
    "resume_base_revision",
    "resume_patch_identity",
    "resume_patch_revision",
    "resume_revision_record",
    "resume_revision_patch_ref",
}


def test_resume_migration_rehearsal_is_additive_and_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "resume-rehearsal.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0010_fact_promotion")
    engine = create_sqlite_engine(database_url)
    assert not RESUME_TABLES & set(inspect(engine).get_table_names())
    engine.dispose()

    command.upgrade(config, "0011_resume_core")
    engine = create_sqlite_engine(database_url)
    assert set(inspect(engine).get_table_names()) >= RESUME_TABLES
    with engine.connect() as connection:
        triggers = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_resume%'"
            ).scalars()
        )
    assert "trg_resume_revision_record_seal" in triggers
    assert "trg_resume_revision_patch_ref_sealed" in triggers
    engine.dispose()

    command.downgrade(config, "0010_fact_promotion")
    engine = create_sqlite_engine(database_url)
    assert not RESUME_TABLES & set(inspect(engine).get_table_names())
    assert "fact_revision" in set(inspect(engine).get_table_names())
    engine.dispose()

    command.upgrade(config, "0011_resume_core")
    engine = create_sqlite_engine(database_url)
    assert set(inspect(engine).get_table_names()) >= RESUME_TABLES
    engine.dispose()
