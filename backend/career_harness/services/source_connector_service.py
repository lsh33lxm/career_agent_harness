from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from career_harness.core.connectors.models import (
    ConnectorStatus,
    DeletePolicy,
    SourceConnector,
    SyncMode,
    SyncRun,
    SyncStats,
)
from career_harness.core.evidence.models import ArtifactClass
from career_harness.db.source_connector_repository import SourceConnectorRepository
from career_harness.storage import ArtifactStore

MAX_FILES_PER_SYNC = 10_000
MAX_FILE_BYTES = 50 * 1024 * 1024


class LocalFolderConnectorService:
    def __init__(
        self, repository: SourceConnectorRepository, artifact_store: ArtifactStore
    ) -> None:
        self.repository = repository
        self.artifact_store = artifact_store

    def create(self, *, display_name: str, root_path: str) -> SourceConnector:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValueError("connector display name is required")
        root = self._root(root_path)
        self._verify_root(root)
        return self.repository.create_local_folder(
            display_name=cleaned_name, root_path=str(root)
        )

    def test_connection(self, connector_id: str) -> dict[str, Any]:
        connector = self.repository.get(connector_id)
        root = self._root(str(connector.config["root_path"]))
        self._verify_root(root)
        return {"ok": True, "connector_type": connector.connector_type, "root": str(root)}

    def sync(self, connector_id: str, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncRun:
        connector = self.repository.get(connector_id)
        if connector.status is ConnectorStatus.PAUSED:
            raise ValueError("paused source connector cannot sync")
        run = self.repository.start_run(connector, mode)
        try:
            root = self._root(str(connector.config["root_path"]))
            self._verify_root(root)
            existing = self.repository.existing_resources(connector_id)
            seen: set[str] = set()
            manifest: list[str] = []
            created = updated = skipped = 0
            now = datetime.now(UTC)
            for path in self._files(root):
                relative = path.relative_to(root).as_posix()
                stat_before = path.stat(follow_symlinks=False)
                if stat_before.st_size > MAX_FILE_BYTES:
                    raise ValueError(f"source resource exceeds 50 MiB: {relative}")
                content = path.read_bytes()
                stat_after = path.stat(follow_symlinks=False)
                if (stat_before.st_size, stat_before.st_mtime_ns) != (
                    stat_after.st_size,
                    stat_after.st_mtime_ns,
                ):
                    raise RuntimeError(f"source resource changed during sync: {relative}")
                digest = hashlib.sha256(content).hexdigest()
                seen.add(relative)
                manifest.append(f"{relative}\0{digest}")
                previous = existing.get(relative)
                if (
                    previous
                    and previous["fingerprint"] == digest
                    and previous["status"] == "active"
                ):
                    skipped += 1
                    continue
                stored = self.artifact_store.put(content, ArtifactClass.PERSONAL)
                self.repository.upsert_resource(
                    connector_id=connector_id,
                    resource_key=relative,
                    fingerprint=digest,
                    artifact_sha256=stored.sha256,
                    byte_length=stored.byte_length,
                    source_modified_ns=stat_after.st_mtime_ns,
                    now=now,
                )
                if previous is None:
                    created += 1
                else:
                    updated += 1
            deleted = 0
            if connector.delete_policy is DeletePolicy.MARK_DELETED:
                deleted = self.repository.mark_missing(connector_id, seen, now)
            cursor = {
                "completed_at": now.isoformat(),
                "resource_count": len(seen),
                "manifest_sha256": hashlib.sha256(
                    "\n".join(sorted(manifest)).encode("utf-8")
                ).hexdigest(),
            }
            return self.repository.complete_run(
                run.sync_run_id,
                cursor,
                SyncStats(
                    created=created,
                    updated=updated,
                    skipped=skipped,
                    deleted=deleted,
                ),
            )
        except Exception as error:
            self.repository.fail_run(run.sync_run_id, str(error))
            raise

    @staticmethod
    def _root(value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            raise ValueError("local folder connector requires an absolute path")
        if path.is_symlink():
            raise ValueError("local folder connector root cannot be a symbolic link")
        return path.resolve(strict=False)

    @staticmethod
    def _verify_root(root: Path) -> None:
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError("local folder connector root is unavailable")
        if root.is_symlink():
            raise ValueError("local folder connector root cannot be a symbolic link")
        with os.scandir(root) as entries:
            next(iter(entries), None)

    @staticmethod
    def _files(root: Path) -> tuple[Path, ...]:
        result: list[Path] = []
        pending = [root]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_symlink():
                        continue
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        result.append(path)
                        if len(result) > MAX_FILES_PER_SYNC:
                            raise ValueError("source connector exceeds the 10000 file limit")
        return tuple(sorted(result, key=lambda item: item.as_posix().casefold()))
