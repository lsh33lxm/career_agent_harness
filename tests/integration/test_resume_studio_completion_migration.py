from datetime import UTC, datetime

from alembic import command
from sqlalchemy import inspect

from career_harness.db.migrations import alembic_config
from career_harness.db.session import create_sqlite_engine, sqlite_url


def test_resume_studio_completion_migration_is_reversible(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = sqlite_url(tmp_path / "resume-studio-completion.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0017_opportunity_radar")
    command.upgrade(config, "0018_resume_studio_completion")
    engine = create_sqlite_engine(database_url)

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("resume_render_run")}
    assert {
        "template_version",
        "renderer",
        "renderer_plugin_id",
        "renderer_plugin_version",
        "input_sha256",
    } <= columns
    assert "resume_render_review" in inspector.get_table_names()
    with engine.connect() as connection:
        triggers = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
    assert "trg_resume_render_run_no_update" in triggers
    assert "trg_resume_render_review_no_update" in triggers
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO resume_template_registration "
            "(template_id, name, version, renderer, content_sha256, description, "
            "definition, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "resume-render-typst-migration-fixture",
                "Typst fixture",
                "1.0.0",
                "typst_worker",
                "a" * 64,
                "Downgrade preservation fixture",
                "{}",
                "disabled",
                datetime.now(UTC),
            ),
        )

    command.downgrade(config, "0017_opportunity_radar")
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("resume_render_run")}
    assert "template_version" not in columns
    assert "resume_render_review" not in inspector.get_table_names()
    with engine.connect() as connection:
        renderer = connection.exec_driver_sql(
            "SELECT renderer FROM resume_template_registration "
            "WHERE template_id='resume-render-typst-migration-fixture'"
        ).scalar_one()
    assert renderer == "typst_worker"
