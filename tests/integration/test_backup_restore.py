from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect

from career_harness.core.evidence.models import ArtifactClass
from career_harness.db.backup import create_backup, restore_backup, verify_backup
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.storage import ArtifactStore


def test_database_and_artifacts_restore_with_verified_hashes(tmp_path: Path) -> None:
    source_database = tmp_path / "source" / "career_harness.db"
    source_database.parent.mkdir()
    upgrade_to_head(sqlite_url(source_database))
    source_artifacts = tmp_path / "source" / "artifacts"
    stored = ArtifactStore(source_artifacts).put(b"verified evidence", ArtifactClass.PERSONAL)

    backup_root = tmp_path / "backup"
    manifest = create_backup(source_database, source_artifacts, backup_root)
    assert verify_backup(backup_root) == ()
    relative_artifact = stored.path.relative_to(source_artifacts).as_posix()
    assert manifest.artifact_hashes[relative_artifact] == stored.sha256

    restored_database = tmp_path / "restored" / "career_harness.db"
    restored_artifacts = tmp_path / "restored" / "artifacts"
    restore_backup(backup_root, restored_database, restored_artifacts)

    tables = set(inspect(create_sqlite_engine(sqlite_url(restored_database))).get_table_names())
    assert "entity_state" in tables
    assert (restored_artifacts / relative_artifact).read_bytes() == b"verified evidence"


def test_restore_refuses_to_overwrite_existing_target(tmp_path: Path) -> None:
    source_database = tmp_path / "source.db"
    upgrade_to_head(sqlite_url(source_database))
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    backup_root = tmp_path / "backup"
    create_backup(source_database, artifacts, backup_root)
    existing_database = tmp_path / "existing.db"
    existing_database.write_bytes(b"keep")

    with pytest.raises(FileExistsError, match="must not exist"):
        restore_backup(backup_root, existing_database, tmp_path / "restored-artifacts")

    assert existing_database.read_bytes() == b"keep"
