from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

CHUNK_SIZE = 1024 * 1024
DATABASE_FILENAME = "career_harness.db"
ARTIFACT_DIRECTORY = "artifacts"
MANIFEST_FILENAME = "backup_manifest.json"


class BackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    database_file: str = DATABASE_FILENAME
    database_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_hashes: dict[str, str]
    created_at: datetime


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_link_or_reparse(path: Path) -> bool:
    file_stat = path.stat(follow_symlinks=False)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _artifact_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    result: list[Path] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name for name in directories if not _is_link_or_reparse(current_path / name)
        ]
        for filename in filenames:
            path = current_path / filename
            if _is_link_or_reparse(path):
                raise ValueError("artifact backup refuses links and reparse points")
            result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix())


def _write_manifest(manifest: BackupManifest, path: Path) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".backup-", delete=False
        ) as handle:
            handle.write(manifest.model_dump_json(indent=2))
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def create_backup(source_database: Path, artifact_root: Path, destination: Path) -> BackupManifest:
    source_database = source_database.resolve(strict=True)
    artifact_root = artifact_root.resolve()
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("backup destination must be absent or empty")
    destination.mkdir(parents=True, exist_ok=True)

    database_backup = destination / DATABASE_FILENAME
    source_uri = f"{source_database.as_uri()}?mode=ro"
    with (
        sqlite3.connect(source_uri, uri=True) as source,
        sqlite3.connect(database_backup) as target,
    ):
        source.backup(target)

    artifact_hashes: dict[str, str] = {}
    destination_artifacts = destination / ARTIFACT_DIRECTORY
    for source_artifact in _artifact_files(artifact_root):
        relative = source_artifact.relative_to(artifact_root)
        target_artifact = destination_artifacts / relative
        target_artifact.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_artifact, target_artifact)
        artifact_hashes[relative.as_posix()] = _sha256_file(target_artifact)

    manifest = BackupManifest(
        database_sha256=_sha256_file(database_backup),
        artifact_hashes=artifact_hashes,
        created_at=datetime.now(UTC),
    )
    _write_manifest(manifest, destination / MANIFEST_FILENAME)
    failures = verify_backup(destination)
    if failures:
        raise RuntimeError(f"backup verification failed: {failures}")
    return manifest


def load_backup_manifest(backup_root: Path) -> BackupManifest:
    return BackupManifest.model_validate_json(
        (backup_root / MANIFEST_FILENAME).read_text(encoding="utf-8")
    )


def verify_backup(backup_root: Path) -> tuple[str, ...]:
    root = backup_root.resolve(strict=True)
    manifest = load_backup_manifest(root)
    failures: list[str] = []
    database = root / manifest.database_file
    if not database.is_file() or _sha256_file(database) != manifest.database_sha256:
        failures.append("database_hash_mismatch")
    else:
        with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                failures.append("database_integrity_check_failed")

    for relative_path, expected_hash in manifest.artifact_hashes.items():
        artifact = (root / ARTIFACT_DIRECTORY / relative_path).resolve()
        if not artifact.is_relative_to(root / ARTIFACT_DIRECTORY):
            failures.append(f"artifact_outside_backup:{relative_path}")
        elif not artifact.is_file() or _sha256_file(artifact) != expected_hash:
            failures.append(f"artifact_hash_mismatch:{relative_path}")
    return tuple(failures)


def restore_backup(backup_root: Path, database_target: Path, artifact_target: Path) -> None:
    root = backup_root.resolve(strict=True)
    failures = verify_backup(root)
    if failures:
        raise RuntimeError(f"backup verification failed: {failures}")
    if database_target.exists() or artifact_target.exists():
        raise FileExistsError("restore targets must not exist")

    manifest = load_backup_manifest(root)
    database_target.parent.mkdir(parents=True, exist_ok=True)
    artifact_target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=database_target.parent, prefix=".database-restore-", delete=False
    ) as temporary_database_handle:
        temporary_database = Path(temporary_database_handle.name)
    temporary_artifacts = Path(
        tempfile.mkdtemp(dir=artifact_target.parent, prefix=".artifact-restore-")
    )
    artifacts_committed = False
    database_committed = False
    try:
        shutil.copyfile(root / manifest.database_file, temporary_database)
        if _sha256_file(temporary_database) != manifest.database_sha256:
            raise RuntimeError("restored database hash mismatch")

        for relative_path, expected_hash in manifest.artifact_hashes.items():
            source = root / ARTIFACT_DIRECTORY / relative_path
            target = temporary_artifacts / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if _sha256_file(target) != expected_hash:
                raise RuntimeError(f"restored artifact hash mismatch: {relative_path}")
        temporary_artifacts.replace(artifact_target)
        artifacts_committed = True
        temporary_database.replace(database_target)
        database_committed = True
    finally:
        if temporary_database.exists():
            temporary_database.unlink()
        if temporary_artifacts.exists():
            shutil.rmtree(temporary_artifacts)
        if artifacts_committed and not database_committed and artifact_target.exists():
            shutil.rmtree(artifact_target)


def manifest_as_json(manifest: BackupManifest) -> str:
    return json.dumps(manifest.model_dump(mode="json"), sort_keys=True)
