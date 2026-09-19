from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from career_harness.core.common import utc_now
from career_harness.core.project import (
    Project,
    ProjectScanScope,
    ProjectSourceEntry,
    ProjectSourceManifest,
    normalize_project_path,
)

_CHUNK_SIZE = 1024 * 1024
_BROWSER_COMPONENTS = {
    ".mozilla",
    "browser",
    "browser-profile",
    "browser_profiles",
    "browsers",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "profile",
    "profiles",
    "user data",
}
_CREDENTIAL_COMPONENTS = {
    ".git-credentials",
    "cookies",
    "cookies.sqlite",
    "credential",
    "credentials",
    "credentials.json",
    "key4.db",
    "local state",
    "login data",
    "logins.json",
    "network",
    "web data",
}


class ProjectScanError(ValueError):
    """Raised when a project cannot be scanned within the required safety boundary."""


ReparseDetector = Callable[[os.stat_result], bool]


def has_reparse_attribute(file_stat: os.stat_result) -> bool:
    """Return whether a stat result carries the Windows reparse-point flag."""

    attributes = getattr(file_stat, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag)


def _is_hard_denied(relative_path: str) -> bool:
    parts = tuple(part.casefold() for part in relative_path.split("/") if part != ".")
    if any(part == ".env" or part.startswith(".env.") for part in parts):
        return True
    if any(part in {"secrets", "sessions"} for part in parts):
        return True
    part_set = set(parts)
    if part_set & _CREDENTIAL_COMPONENTS:
        return True
    return bool(part_set & _BROWSER_COMPONENTS)


def _is_same_or_descendant(path: str, parent: str) -> bool:
    path_key = path.casefold()
    parent_key = parent.casefold()
    return parent_key == "." or path_key == parent_key or path_key.startswith(f"{parent_key}/")


class LocalProjectScanner:
    def __init__(self, *, reparse_detector: ReparseDetector = has_reparse_attribute) -> None:
        self._reparse_detector = reparse_detector

    def scan(
        self,
        project: Project,
        scope: ProjectScanScope,
        *,
        manifest_id: str,
        generated_at: datetime | None = None,
    ) -> ProjectSourceManifest:
        if scope.project_id != project.project_id:
            raise ProjectScanError("scan scope belongs to a different project")
        if scope.follow_symlinks is not False:
            raise ProjectScanError("scan scope cannot follow links")

        root = Path(project.root_locator)
        if not root.is_absolute() or ".." in root.parts:
            raise ProjectScanError("project root locator must be absolute without traversal")
        if _is_hard_denied("/".join(root.parts)):
            raise ProjectScanError("project root is within a hard-denied location")
        root_stat = self._stat_no_follow(root, "project root is unavailable")
        if not stat.S_ISDIR(root_stat.st_mode):
            raise ProjectScanError("project root must be a local directory")
        self._reject_link_or_reparse(root_stat)

        try:
            resolved_root = root.resolve(strict=True)
        except OSError as exc:
            raise ProjectScanError("project root cannot be resolved safely") from exc
        if resolved_root != root.absolute():
            raise ProjectScanError("project root cannot be a link or reparse alias")

        entries = self._walk(root, resolved_root, scope)
        if not entries:
            raise ProjectScanError("scan scope contains no eligible regular files")
        entries.sort(key=lambda item: (item.relative_path.casefold(), item.relative_path))
        return ProjectSourceManifest(
            manifest_id=manifest_id,
            scan_scope_id=scope.scope_id,
            scan_scope_revision=scope.revision,
            entries=tuple(entries),
            generated_at=generated_at or utc_now(),
        )

    def _walk(
        self, root: Path, resolved_root: Path, scope: ProjectScanScope
    ) -> list[ProjectSourceEntry]:
        found: list[ProjectSourceEntry] = []
        pending = [root]
        while pending:
            current = pending.pop()
            self._assert_safe_path(root, resolved_root, current)
            try:
                with os.scandir(current) as directory_entries:
                    ordered = sorted(
                        directory_entries,
                        key=lambda item: (item.name.casefold(), item.name),
                    )
            except OSError as exc:
                raise ProjectScanError("an allowed directory cannot be scanned safely") from exc

            for directory_entry in ordered:
                candidate = current / directory_entry.name
                relative = normalize_project_path(candidate.relative_to(root).as_posix())
                if _is_hard_denied(relative) or not self._is_scope_relevant(scope, relative):
                    continue

                candidate_stat = self._assert_safe_path(root, resolved_root, candidate)
                if stat.S_ISDIR(candidate_stat.st_mode):
                    pending.append(candidate)
                elif stat.S_ISREG(candidate_stat.st_mode) and scope.permits(relative):
                    found.append(self._read_entry(root, resolved_root, candidate, relative))
        return found

    @staticmethod
    def _is_scope_relevant(scope: ProjectScanScope, relative_path: str) -> bool:
        if any(_is_same_or_descendant(relative_path, denied) for denied in scope.denied_paths):
            return False
        if scope.permits(relative_path):
            return True
        return any(
            _is_same_or_descendant(allowed, relative_path) for allowed in scope.allowed_paths
        )

    def _assert_safe_path(
        self, root: Path, resolved_root: Path, candidate: Path
    ) -> os.stat_result:
        try:
            relative_parts = candidate.relative_to(root).parts
        except ValueError as exc:
            raise ProjectScanError("candidate path is outside the project root") from exc

        current = root
        current_stat = self._stat_no_follow(current, "project path is unavailable")
        self._reject_link_or_reparse(current_stat)
        for part in relative_parts:
            current = current / part
            current_stat = self._stat_no_follow(current, "project path changed during scan")
            self._reject_link_or_reparse(current_stat)

        try:
            resolved_candidate = candidate.resolve(strict=True)
        except OSError as exc:
            raise ProjectScanError("project path cannot be resolved safely") from exc
        if resolved_candidate != resolved_root and not resolved_candidate.is_relative_to(
            resolved_root
        ):
            raise ProjectScanError("resolved project path escapes the project root")
        return current_stat

    def _read_entry(
        self, root: Path, resolved_root: Path, path: Path, relative_path: str
    ) -> ProjectSourceEntry:
        before = self._assert_safe_path(root, resolved_root, path)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        digest = hashlib.sha256()
        byte_length = 0
        try:
            descriptor = os.open(path, flags)
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or not self._same_file_snapshot(before, opened):
                    raise ProjectScanError("project file changed before it could be read safely")
                while chunk := os.read(descriptor, _CHUNK_SIZE):
                    digest.update(chunk)
                    byte_length += len(chunk)
                after_open = os.fstat(descriptor)
            finally:
                os.close(descriptor)
        except ProjectScanError:
            raise
        except OSError as exc:
            raise ProjectScanError("project file cannot be read safely") from exc

        after_path = self._assert_safe_path(root, resolved_root, path)
        if not self._same_file_snapshot(opened, after_open) or not self._same_file_snapshot(
            after_open, after_path
        ):
            raise ProjectScanError("project file changed while it was being scanned")
        if byte_length != after_open.st_size:
            raise ProjectScanError("project file length changed while it was being scanned")
        return ProjectSourceEntry(
            relative_path=relative_path,
            sha256=digest.hexdigest(),
            byte_length=byte_length,
        )

    @staticmethod
    def _same_file_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
        return (
            left.st_dev,
            left.st_ino,
            left.st_mode,
            left.st_size,
            left.st_mtime_ns,
        ) == (
            right.st_dev,
            right.st_ino,
            right.st_mode,
            right.st_size,
            right.st_mtime_ns,
        )

    @staticmethod
    def _stat_no_follow(path: Path, message: str) -> os.stat_result:
        try:
            return path.stat(follow_symlinks=False)
        except OSError as exc:
            raise ProjectScanError(message) from exc

    def _reject_link_or_reparse(self, file_stat: os.stat_result) -> None:
        if stat.S_ISLNK(file_stat.st_mode) or self._reparse_detector(file_stat):
            raise ProjectScanError("project scan refuses links and reparse points")


def scan_project(
    project: Project,
    scope: ProjectScanScope,
    *,
    manifest_id: str,
    generated_at: datetime | None = None,
) -> ProjectSourceManifest:
    return LocalProjectScanner().scan(
        project,
        scope,
        manifest_id=manifest_id,
        generated_at=generated_at,
    )
