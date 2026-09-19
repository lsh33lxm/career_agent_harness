from __future__ import annotations

import ctypes
import hashlib
import ntpath
import os
import stat
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from ctypes import wintypes
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Protocol

from career_harness.core.common import utc_now
from career_harness.core.project import (
    ProjectScanScope,
    ProjectSourceEntry,
    ProjectSourceManifest,
    normalize_project_path,
)
from career_harness.db.project_repository import ProjectRepository

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


def _is_scope_relevant(scope: ProjectScanScope, relative_path: str) -> bool:
    if any(_is_same_or_descendant(relative_path, denied) for denied in scope.denied_paths):
        return False
    if scope.permits(relative_path):
        return True
    return any(_is_same_or_descendant(allowed, relative_path) for allowed in scope.allowed_paths)


def _validate_root_locator(root_locator: str) -> Path:
    if not root_locator or not root_locator.strip() or "\x00" in root_locator:
        raise ProjectScanError("project root locator must be an absolute local path")

    windows_text = root_locator.replace("/", "\\")
    if windows_text.startswith(("\\\\?\\", "\\\\.\\")):
        raise ProjectScanError("project root cannot use a Windows device namespace")
    if windows_text.startswith("\\\\"):
        raise ProjectScanError("project root cannot be a UNC path")

    root = Path(root_locator)
    path_parts = PureWindowsPath(root_locator).parts if os.name == "nt" else root.parts
    if not root.is_absolute() or ".." in path_parts:
        raise ProjectScanError("project root locator must be absolute without traversal")
    if _is_hard_denied(root_locator.replace("\\", "/")):
        raise ProjectScanError("project root is within a hard-denied location")
    return root


class _AnchoredReader(Protocol):
    def scan(self, root: Path, scope: ProjectScanScope) -> list[ProjectSourceEntry]: ...


class _PosixAnchoredReader:
    def scan(self, root: Path, scope: ProjectScanScope) -> list[ProjectSourceEntry]:
        no_follow = getattr(os, "O_NOFOLLOW", None)
        directory = getattr(os, "O_DIRECTORY", None)
        if (
            no_follow is None
            or directory is None
            or os.open not in os.supports_dir_fd
            or os.listdir not in os.supports_fd
        ):
            raise ProjectScanError("platform lacks safe handle-anchored scan primitives")

        try:
            root_fd = os.open(root, os.O_RDONLY | no_follow | directory)
        except OSError as exc:
            raise ProjectScanError("project root cannot be opened safely") from exc
        try:
            root_stat = os.fstat(root_fd)
            if not stat.S_ISDIR(root_stat.st_mode):
                raise ProjectScanError("project root must be a local directory")
            return self._scan_directory(root_fd, ".", scope)
        finally:
            os.close(root_fd)

    def _scan_directory(
        self, directory_fd: int, relative_directory: str, scope: ProjectScanScope
    ) -> list[ProjectSourceEntry]:
        try:
            names = sorted(os.listdir(directory_fd), key=lambda item: (item.casefold(), item))
        except OSError as exc:
            raise ProjectScanError("an allowed directory cannot be enumerated safely") from exc

        found: list[ProjectSourceEntry] = []
        for name in names:
            relative = normalize_project_path(
                name if relative_directory == "." else f"{relative_directory}/{name}"
            )
            if _is_hard_denied(relative) or not _is_scope_relevant(scope, relative):
                continue

            child_fd = self._open_child(directory_fd, name)
            try:
                child_stat = os.fstat(child_fd)
                if stat.S_ISDIR(child_stat.st_mode):
                    found.extend(self._scan_directory(child_fd, relative, scope))
                elif stat.S_ISREG(child_stat.st_mode) and scope.permits(relative):
                    found.append(self._read_file(child_fd, relative, child_stat))
            finally:
                os.close(child_fd)
        return found

    @staticmethod
    def _open_child(directory_fd: int, name: str) -> int:
        try:
            return os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        except OSError as exc:
            raise ProjectScanError(
                "project entry cannot be opened without following links"
            ) from exc

    @staticmethod
    def _read_file(
        file_fd: int, relative_path: str, before: os.stat_result
    ) -> ProjectSourceEntry:
        digest = hashlib.sha256()
        byte_length = 0
        try:
            while chunk := os.read(file_fd, _CHUNK_SIZE):
                digest.update(chunk)
                byte_length += len(chunk)
            after = os.fstat(file_fd)
        except OSError as exc:
            raise ProjectScanError("project file cannot be read safely") from exc
        if _stat_identity(before) != _stat_identity(after) or byte_length != after.st_size:
            raise ProjectScanError("project file changed while it was being scanned")
        return ProjectSourceEntry(
            relative_path=relative_path,
            sha256=digest.hexdigest(),
            byte_length=byte_length,
        )


def _stat_identity(file_stat: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        file_stat.st_dev,
        file_stat.st_ino,
        file_stat.st_mode,
        file_stat.st_size,
        file_stat.st_mtime_ns,
    )


class _ByHandleFileInformation(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    ]


WindowsNameLister = Callable[[Path], Sequence[str]]
WindowsReparseDetector = Callable[[Path, _ByHandleFileInformation], bool]
WindowsDriveTypeGetter = Callable[[str], int]


class _WindowsAnchoredReader:
    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x00000001
    _OPEN_EXISTING = 3
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_TYPE_DISK = 0x0001
    _DRIVE_FIXED = 3
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    def __init__(
        self,
        *,
        name_lister: WindowsNameLister | None = None,
        reparse_detector: WindowsReparseDetector | None = None,
        drive_type_getter: WindowsDriveTypeGetter | None = None,
    ) -> None:
        if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
            raise ProjectScanError("Windows handle scanning is unavailable")
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_functions()
        self._name_lister = name_lister or self._list_names
        self._reparse_detector = reparse_detector or self._has_reparse_attribute
        self._drive_type_getter = drive_type_getter or self._kernel32.GetDriveTypeW

    def _configure_functions(self) -> None:
        self._kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self._kernel32.CreateFileW.restype = wintypes.HANDLE
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32.GetFileInformationByHandle.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ByHandleFileInformation),
        ]
        self._kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
        self._kernel32.GetFinalPathNameByHandleW.argtypes = [
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self._kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self._kernel32.GetFileType.argtypes = [wintypes.HANDLE]
        self._kernel32.GetFileType.restype = wintypes.DWORD
        self._kernel32.ReadFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        self._kernel32.ReadFile.restype = wintypes.BOOL
        self._kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        self._kernel32.GetDriveTypeW.restype = wintypes.UINT

    def scan(self, root: Path, scope: ProjectScanScope) -> list[ProjectSourceEntry]:
        if self._drive_type_getter(root.anchor) != self._DRIVE_FIXED:
            raise ProjectScanError("project root must be on a fixed local drive")

        with self._open_handle(root) as root_handle:
            root_info = self._get_information(root_handle)
            self._reject_reparse(root, root_info)
            if not root_info.dwFileAttributes & self._FILE_ATTRIBUTE_DIRECTORY:
                raise ProjectScanError("project root must be a local directory")
            root_final_path = self._get_final_path(root_handle)
            return self._scan_directory(root_handle, root, ".", root_final_path, scope)

    def _scan_directory(
        self,
        _directory_handle: int,
        directory_path: Path,
        relative_directory: str,
        root_final_path: str,
        scope: ProjectScanScope,
    ) -> list[ProjectSourceEntry]:
        # Keeping this no-delete-share handle alive pins the directory during enumeration.
        try:
            names = sorted(
                self._name_lister(directory_path),
                key=lambda item: (item.casefold(), item),
            )
        except OSError as exc:
            raise ProjectScanError("an allowed directory cannot be enumerated safely") from exc

        found: list[ProjectSourceEntry] = []
        for name in names:
            relative = normalize_project_path(
                name if relative_directory == "." else f"{relative_directory}/{name}"
            )
            if _is_hard_denied(relative) or not _is_scope_relevant(scope, relative):
                continue

            child_path = directory_path / name
            with self._open_handle(child_path) as child_handle:
                child_info = self._get_information(child_handle)
                self._reject_reparse(child_path, child_info)
                child_final_path = self._get_final_path(child_handle)
                if not _windows_path_is_within(child_final_path, root_final_path):
                    raise ProjectScanError("opened project entry escapes the project root")
                if child_info.dwFileAttributes & self._FILE_ATTRIBUTE_DIRECTORY:
                    found.extend(
                        self._scan_directory(
                            child_handle,
                            child_path,
                            relative,
                            root_final_path,
                            scope,
                        )
                    )
                elif scope.permits(relative):
                    found.append(self._read_file(child_handle, relative, child_info))
        return found

    @contextmanager
    def _open_handle(self, path: Path) -> Iterator[int]:
        handle = self._kernel32.CreateFileW(
            str(path),
            self._GENERIC_READ,
            self._FILE_SHARE_READ,
            None,
            self._OPEN_EXISTING,
            self._FILE_FLAG_BACKUP_SEMANTICS | self._FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle == self._INVALID_HANDLE_VALUE:
            raise ProjectScanError(
                "project entry cannot be opened without following reparse points"
            )
        try:
            if self._kernel32.GetFileType(handle) != self._FILE_TYPE_DISK:
                raise ProjectScanError("project entry is not a local disk file")
            yield handle
        finally:
            self._kernel32.CloseHandle(handle)

    def _get_information(self, handle: int) -> _ByHandleFileInformation:
        information = _ByHandleFileInformation()
        if not self._kernel32.GetFileInformationByHandle(handle, ctypes.byref(information)):
            raise ProjectScanError("project entry metadata cannot be read from its handle")
        return information

    def _get_final_path(self, handle: int) -> str:
        size = 32768
        buffer = ctypes.create_unicode_buffer(size)
        written = self._kernel32.GetFinalPathNameByHandleW(handle, buffer, size, 0)
        if not written or written >= size:
            raise ProjectScanError("project entry final path cannot be verified")
        value = buffer.value
        if value.startswith("\\\\?\\UNC\\"):
            return f"\\\\{value[8:]}"
        if value.startswith("\\\\?\\"):
            return value[4:]
        return value

    def _read_file(
        self, handle: int, relative_path: str, before: _ByHandleFileInformation
    ) -> ProjectSourceEntry:
        digest = hashlib.sha256()
        byte_length = 0
        buffer = ctypes.create_string_buffer(_CHUNK_SIZE)
        bytes_read = wintypes.DWORD()
        while True:
            if not self._kernel32.ReadFile(
                handle,
                buffer,
                _CHUNK_SIZE,
                ctypes.byref(bytes_read),
                None,
            ):
                raise ProjectScanError("project file cannot be read safely")
            if bytes_read.value == 0:
                break
            digest.update(buffer.raw[: bytes_read.value])
            byte_length += bytes_read.value
        after = self._get_information(handle)
        if _windows_file_identity(before) != _windows_file_identity(after):
            raise ProjectScanError("project file changed while it was being scanned")
        if byte_length != _windows_file_size(after):
            raise ProjectScanError("project file length changed while it was being scanned")
        return ProjectSourceEntry(
            relative_path=relative_path,
            sha256=digest.hexdigest(),
            byte_length=byte_length,
        )

    @staticmethod
    def _list_names(path: Path) -> tuple[str, ...]:
        with os.scandir(path) as entries:
            return tuple(entry.name for entry in entries)

    @staticmethod
    def _has_reparse_attribute(
        _path: Path, information: _ByHandleFileInformation
    ) -> bool:
        return bool(
            information.dwFileAttributes & _WindowsAnchoredReader._FILE_ATTRIBUTE_REPARSE_POINT
        )

    def _reject_reparse(self, path: Path, information: _ByHandleFileInformation) -> None:
        if self._reparse_detector(path, information):
            raise ProjectScanError("project scan refuses links and reparse points")


def _windows_file_size(information: _ByHandleFileInformation) -> int:
    return (information.nFileSizeHigh << 32) | information.nFileSizeLow


def _windows_file_identity(
    information: _ByHandleFileInformation,
) -> tuple[int, int, int, int, int, int]:
    return (
        information.dwVolumeSerialNumber,
        information.nFileIndexHigh,
        information.nFileIndexLow,
        information.nFileSizeHigh,
        information.nFileSizeLow,
        information.ftLastWriteTime.dwHighDateTime << 32
        | information.ftLastWriteTime.dwLowDateTime,
    )


def _windows_path_is_within(path: str, root: str) -> bool:
    normalized_path = ntpath.normcase(ntpath.normpath(path))
    normalized_root = ntpath.normcase(ntpath.normpath(root))
    try:
        return ntpath.commonpath((normalized_path, normalized_root)) == normalized_root
    except ValueError:
        return False


def _default_anchored_reader() -> _AnchoredReader:
    if os.name == "nt":
        return _WindowsAnchoredReader()
    if os.name == "posix":
        return _PosixAnchoredReader()
    raise ProjectScanError("platform lacks a safe project scanning implementation")


class LocalProjectScanner:
    def __init__(
        self,
        repository: ProjectRepository,
        *,
        anchored_reader: _AnchoredReader | None = None,
    ) -> None:
        self._repository = repository
        self._anchored_reader = anchored_reader or _default_anchored_reader()

    def scan(
        self,
        project_id: str,
        scope_id: str,
        scope_revision: int,
        *,
        manifest_id: str,
        project_revision: int | None = None,
        generated_at: datetime | None = None,
    ) -> ProjectSourceManifest:
        if not isinstance(project_id, str) or not isinstance(scope_id, str):
            raise ProjectScanError("project and scope must be loaded by canonical ID")
        if (
            not isinstance(scope_revision, int)
            or isinstance(scope_revision, bool)
            or scope_revision < 1
        ):
            raise ProjectScanError("scan scope revision must be exact and positive")
        if project_revision is not None and (
            not isinstance(project_revision, int)
            or isinstance(project_revision, bool)
            or project_revision < 1
        ):
            raise ProjectScanError("project revision must be positive when provided")

        scan_inputs = self._repository.get_scan_inputs(
            project_id,
            scope_id,
            scope_revision,
            project_revision=project_revision,
        )
        if scan_inputs is None:
            raise ProjectScanError("canonical project or exact scan scope was not found")
        project, scope = scan_inputs
        if scope.follow_symlinks is not False:
            raise ProjectScanError("scan scope cannot follow links")

        root = _validate_root_locator(project.root_locator)
        entries = self._anchored_reader.scan(root, scope)
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


def scan_project(
    repository: ProjectRepository,
    project_id: str,
    scope_id: str,
    scope_revision: int,
    *,
    manifest_id: str,
    project_revision: int | None = None,
    generated_at: datetime | None = None,
) -> ProjectSourceManifest:
    return LocalProjectScanner(repository).scan(
        project_id,
        scope_id,
        scope_revision,
        manifest_id=manifest_id,
        project_revision=project_revision,
        generated_at=generated_at,
    )
