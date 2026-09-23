from pathlib import Path

import pytest

from career_harness.db import migrations
from career_harness.platform import AppPaths, EnvironmentSecretProvider


def test_app_paths_keep_browser_sessions_outside_artifact_store(tmp_path: Path) -> None:
    paths = AppPaths.resolve(environment={"ACH_DATA_DIR": str(tmp_path / "app-data")})
    paths.ensure_directories()

    assert paths.database.parent == paths.root
    assert paths.artifacts.parent == paths.root
    assert paths.browser_sessions.parent == paths.root
    assert not paths.browser_sessions.is_relative_to(paths.artifacts)
    assert paths.browser_sessions.is_dir()


def test_secret_values_are_redacted() -> None:
    provider = EnvironmentSecretProvider({"ACH_SECRET_FEISHU_TOKEN": "test-secret-value"})
    value = provider.require("feishu-token")

    assert value.reveal() == "test-secret-value"
    assert "test-secret-value" not in repr(value)
    assert str(value) == "[REDACTED]"


def test_missing_required_secret_names_key_without_value() -> None:
    provider = EnvironmentSecretProvider({})

    with pytest.raises(LookupError, match="missing-key"):
        provider.require("missing-key")


def test_migration_resources_resolve_from_pyinstaller_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(migrations.sys, "_MEIPASS", str(tmp_path), raising=False)

    config = migrations.alembic_config("sqlite:///C:/tmp/example.db")

    assert config.config_file_name == str(tmp_path / "alembic.ini")
    assert config.get_main_option("script_location") == str(tmp_path / "migrations")
