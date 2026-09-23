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
from career_harness.services.github_project_service import (
    GitHubProjectService,
    normalize_github_url,
)
from career_harness.services.legacy_import_service import LegacyImportService
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
        if connector.connector_type != "local_folder":
            raise ValueError("source connector is not a local folder")
        root = self._root(str(connector.config["root_path"]))
        self._verify_root(root)
        return {"ok": True, "connector_type": connector.connector_type, "root": str(root)}

    def sync(self, connector_id: str, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncRun:
        connector = self.repository.get(connector_id)
        if connector.connector_type != "local_folder":
            raise ValueError("source connector is not a local folder")
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


class LegacyAgentRadarConnectorService:
    def __init__(
        self,
        repository: SourceConnectorRepository,
        legacy_import: LegacyImportService,
    ) -> None:
        self.repository = repository
        self.legacy_import = legacy_import

    def create(self, *, display_name: str, root_path: str) -> SourceConnector:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValueError("connector display name is required")
        requested_root = Path(root_path)
        if not requested_root.is_absolute():
            raise ValueError("Legacy Agent Radar connector requires an absolute path")
        inspection = self.legacy_import.inspect_source(requested_root)
        return self.repository.create_legacy_agent_radar(
            display_name=cleaned_name,
            root_path=str(inspection["root"]),
        )

    def get_or_create(self, *, display_name: str, root_path: str) -> SourceConnector:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValueError("connector display name is required")
        requested_root = Path(root_path)
        if not requested_root.is_absolute():
            raise ValueError("Legacy Agent Radar connector requires an absolute path")
        inspection = self.legacy_import.inspect_source(requested_root)
        canonical_root = os.path.normcase(str(inspection["root"]))
        for connector in self.repository.list():
            if connector.connector_type != "legacy_agent_radar":
                continue
            configured_root = os.path.normcase(str(connector.config.get("root_path", "")))
            if configured_root == canonical_root:
                return connector
        return self.repository.create_legacy_agent_radar(
            display_name=cleaned_name,
            root_path=str(inspection["root"]),
        )

    def test_connection(self, connector_id: str) -> dict[str, Any]:
        connector = self._connector(connector_id)
        inspection = self.legacy_import.inspect_source(
            Path(str(connector.config["root_path"]))
        )
        return {
            "ok": True,
            "connector_type": connector.connector_type,
            **inspection,
        }

    def sync(self, connector_id: str, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncRun:
        connector = self._connector(connector_id)
        if connector.status is ConnectorStatus.PAUSED:
            raise ValueError("paused source connector cannot sync")
        run = self.repository.start_run(connector, mode)
        try:
            report = self.legacy_import.run(Path(str(connector.config["root_path"])))
            totals = report.totals
            if totals["failed_count"]:
                failures = [
                    reason
                    for file_report in report.files
                    for reason in file_report.failures
                ]
                detail = failures[0] if failures else "unknown import failure"
                raise RuntimeError(f"Legacy import reported failures: {detail}")
            cursor = {
                "batch_id": report.batch_id,
                "completed_at": report.finished_at.isoformat(),
                "source_signature": report.source_signature_after,
                "read_count": totals["read_count"],
                "duplicate_count": totals["duplicate_count"],
            }
            return self.repository.complete_run(
                run.sync_run_id,
                cursor,
                SyncStats(
                    created=totals["new_count"],
                    updated=totals["updated_count"],
                    skipped=totals["unchanged_count"],
                    failed=totals["failed_count"],
                ),
            )
        except Exception as error:
            self.repository.fail_run(run.sync_run_id, str(error))
            raise

    def _connector(self, connector_id: str) -> SourceConnector:
        connector = self.repository.get(connector_id)
        if connector.connector_type != "legacy_agent_radar":
            raise ValueError("source connector is not Legacy Agent Radar")
        return connector


class GitHubConnectorService:
    def __init__(
        self,
        repository: SourceConnectorRepository,
        github_projects: GitHubProjectService,
    ) -> None:
        self.repository = repository
        self.github_projects = github_projects

    def create(
        self,
        *,
        display_name: str,
        repository_url: str,
        use_private_token: bool,
        confirm_read_only_network: bool,
    ) -> SourceConnector:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValueError("connector display name is required")
        if not confirm_read_only_network:
            raise ValueError("必须确认只读 GitHub 网络请求")
        normalized_url, _owner, _repository = normalize_github_url(repository_url)
        self._require_token(use_private_token)
        return self.repository.create_github(
            display_name=cleaned_name,
            repository_url=normalized_url,
            use_private_token=use_private_token,
        )

    def get_or_create(
        self,
        *,
        display_name: str,
        repository_url: str,
        use_private_token: bool,
        confirm_read_only_network: bool,
    ) -> SourceConnector:
        cleaned_name = display_name.strip()
        if not cleaned_name:
            raise ValueError("connector display name is required")
        if not confirm_read_only_network:
            raise ValueError("必须确认只读 GitHub 网络请求")
        normalized_url, _owner, _repository = normalize_github_url(repository_url)
        self._require_token(use_private_token)
        for connector in self.repository.list():
            if connector.connector_type != "github":
                continue
            if (
                connector.config.get("repository_url") == normalized_url
                and bool(connector.config.get("use_private_token")) == use_private_token
            ):
                return connector
        return self.repository.create_github(
            display_name=cleaned_name,
            repository_url=normalized_url,
            use_private_token=use_private_token,
        )

    def test_connection(self, connector_id: str) -> dict[str, Any]:
        connector = self._connector(connector_id)
        repository_url = str(connector.config["repository_url"])
        normalize_github_url(repository_url)
        use_private_token = bool(connector.config.get("use_private_token"))
        self._require_token(use_private_token)
        return {
            "ok": True,
            "connector_type": connector.connector_type,
            "repository_url": repository_url,
            "credential_ready": not use_private_token
            or self.github_projects.token_status()["configured"],
            "network_verified": bool(
                connector.sync_cursor and connector.sync_cursor.get("commit_sha")
            ),
            "last_verified_commit": (
                connector.sync_cursor.get("commit_sha") if connector.sync_cursor else None
            ),
        }

    def sync(self, connector_id: str, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncRun:
        connector = self._connector(connector_id)
        if connector.status is ConnectorStatus.PAUSED:
            raise ValueError("paused source connector cannot sync")
        run = self.repository.start_run(connector, mode)
        try:
            analysis = self.github_projects.analyze(
                str(connector.config["repository_url"]),
                bool(connector.config.get("use_private_token")),
            )
            previous_commit = (
                str(connector.sync_cursor.get("commit_sha"))
                if connector.sync_cursor and connector.sync_cursor.get("commit_sha")
                else None
            )
            commit_sha = str(analysis["commit_sha"])
            stats = SyncStats(
                created=1 if previous_commit is None else 0,
                updated=1 if previous_commit not in (None, commit_sha) else 0,
                skipped=1 if previous_commit == commit_sha else 0,
            )
            cursor = {
                "completed_at": datetime.now(UTC).isoformat(),
                "repository_url": analysis["repository_url"],
                "commit_sha": commit_sha,
                "analysis_id": analysis["analysis_id"],
                "project_id": analysis["project_id"],
            }
            return self.repository.complete_run(run.sync_run_id, cursor, stats)
        except Exception as error:
            self.repository.fail_run(run.sync_run_id, str(error))
            raise

    def _require_token(self, use_private_token: bool) -> None:
        if use_private_token and not self.github_projects.token_status()["configured"]:
            raise ValueError("尚未配置 GitHub 只读令牌")

    def _connector(self, connector_id: str) -> SourceConnector:
        connector = self.repository.get(connector_id)
        if connector.connector_type != "github":
            raise ValueError("source connector is not GitHub")
        if not connector.config.get("read_only_network_confirmed"):
            raise ValueError("GitHub connector lacks read-only network confirmation")
        return connector
