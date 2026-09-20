from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from typing import BinaryIO
from xml.etree import ElementTree

from importers.agent_radar.models import (
    LegacyImportManifest,
    SkippedEntry,
    SourceFile,
    WorkbookMetadata,
)

IMPORTER_VERSION = "0.1.1"
CHUNK_SIZE = 1024 * 1024
MAX_WORKBOOK_BYTES = 128 * 1024 * 1024
MAX_WORKBOOK_XML_BYTES = 2 * 1024 * 1024
MAX_WORKBOOK_ENTRIES = 10_000
WORKBOOK_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


class _WorkbookTreeBuilder(ElementTree.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("workbook XML cannot declare a document type")


def _absolute_source(path: Path) -> Path:
    # Do not resolve links away before inspecting every component.
    if ".." in path.parts:
        raise ValueError("source path cannot contain parent traversal")
    absolute = path.absolute()
    if os.name == "nt" and (absolute.drive.startswith("\\\\") or ":" in str(absolute)[2:]):
        raise ValueError("source must be a local path without alternate streams")
    return absolute


@contextmanager
def _pinned_entry(path: Path, *, directory: bool = False) -> Iterator[int | None]:
    path = _absolute_source(path)
    with ExitStack() as stack:
        if os.name == "nt":
            from career_harness.services.project_scanner import _WindowsAnchoredReader

            reader = _WindowsAnchoredReader()
            if reader._drive_type_getter(path.anchor) != reader._DRIVE_FIXED:
                raise ValueError("source must be on a fixed local drive")
            # Read-share-only handles prevent replacement of any ancestor or the leaf.
            for component in (*reversed(path.parents), path):
                handle = stack.enter_context(reader._open_handle(component))
                info = reader._get_information(handle)
                reader._reject_reparse(component, info)
                is_directory = bool(info.dwFileAttributes & reader._FILE_ATTRIBUTE_DIRECTORY)
                if is_directory != (component != path or directory):
                    raise ValueError("source entry has an unexpected file type")
            yield None
        elif os.name == "posix" and hasattr(os, "O_NOFOLLOW"):
            fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            stack.callback(os.close, fd)
            for index, part in enumerate(path.parts[1:]):
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if directory or index < len(path.parts) - 2:
                    flags |= os.O_DIRECTORY
                fd = os.open(part, flags, dir_fd=fd)
                stack.callback(os.close, fd)
            mode = os.fstat(fd).st_mode
            if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
                raise ValueError("source entry has an unexpected file type")
            yield fd
        else:
            raise ValueError("platform lacks safe source reading primitives")


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


@contextmanager
def _safe_file(path: Path) -> Iterator[BinaryIO]:
    with (
        _pinned_entry(path) as fd,
        path.open("rb") if fd is None else os.fdopen(os.dup(fd), "rb") as handle,
    ):
        before = os.fstat(handle.fileno())
        yield handle
        after = os.fstat(handle.fileno())
        if _identity(before) != _identity(after):
            raise ValueError("source file changed during read")
        # Detect replacement of a POSIX directory entry while the old inode was open.
        if fd is not None:
            with _pinned_entry(path) as current_fd:
                if current_fd is None or _identity(after) != _identity(os.fstat(current_fd)):
                    raise ValueError("source file identity changed during read")


def _walk_files(root: Path) -> tuple[list[Path], list[SkippedEntry]]:
    files: list[Path] = []
    skipped: list[SkippedEntry] = []
    pending = [root]

    while pending:
        current = pending.pop()
        with (
            _pinned_entry(current, directory=True) as fd,
            os.scandir(current if fd is None else fd) as entries,
        ):
            for entry in entries:
                path = current / entry.name
                relative = path.relative_to(root).as_posix()
                attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                if entry.is_symlink() or attributes & getattr(
                    stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0
                ):
                    skipped.append(
                        SkippedEntry(relative_path=relative, reason="link_or_reparse_point")
                    )
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)

    return sorted(files, key=lambda item: item.relative_to(root).as_posix().casefold()), sorted(
        skipped, key=lambda item: item.relative_path.casefold()
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with _safe_file(path) as handle:
        expected_size = os.fstat(handle.fileno()).st_size
        length = 0
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            length += len(chunk)
        if length != expected_size:
            raise ValueError("source file length changed during read")
    return digest.hexdigest()


def _source_relative_path(value: str) -> Path:
    windows = PureWindowsPath(value)
    relative = Path(value)
    if (
        not value
        or value == "."
        or "\x00" in value
        or ":" in value
        or relative.is_absolute()
        or windows.drive
        or windows.root
        or ".." in relative.parts
        or ".." in windows.parts
    ):
        raise ValueError("source file requires a safe relative path")
    return relative


def read_source_bytes(
    source_workspace: Path,
    relative_path: str,
    *,
    expected_size: int,
    expected_sha256: str,
    expected_modified_at: datetime | None = None,
) -> bytes:
    """Read exact manifest bytes through pinned handles; never resolve links away."""
    if (
        type(expected_size) is not int
        or expected_size < 0
        or len(expected_sha256) != 64
        or any(char not in "0123456789abcdef" for char in expected_sha256)
    ):
        raise ValueError("invalid source byte expectations")
    path = _absolute_source(source_workspace) / _source_relative_path(relative_path)
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    length = 0
    with _safe_file(path) as handle:
        before = os.fstat(handle.fileno())
        if before.st_size != expected_size:
            raise ValueError("source byte length differs from manifest")
        if expected_modified_at is not None and (
            expected_modified_at.tzinfo is None
            or datetime.fromtimestamp(before.st_mtime, UTC) != expected_modified_at
        ):
            raise ValueError("source modification time differs from manifest")
        while chunk := handle.read(min(CHUNK_SIZE, expected_size - length + 1)):
            length += len(chunk)
            if length > expected_size:
                raise ValueError("source byte length differs from manifest")
            digest.update(chunk)
            chunks.append(chunk)
    if length != expected_size or digest.hexdigest() != expected_sha256:
        raise ValueError("source bytes differ from manifest")
    return b"".join(chunks)


def _source_group(relative_path: Path) -> str:
    parts = tuple(part.casefold() for part in relative_path.parts)
    if parts[:2] == ("codex", "data"):
        return "codex/data"
    return relative_path.parts[0] if len(relative_path.parts) > 1 else "workspace_root"


def _category(relative_path: Path) -> str:
    text = relative_path.as_posix().casefold()
    suffix = relative_path.suffix.casefold()
    if suffix in {".xlsx", ".xlsm"}:
        return "workbook"
    if "snapshot" in text:
        return "snapshot"
    if "manifest" in text:
        return "manifest"
    if relative_path.name.casefold() in {".env", "config.json", "config.yaml", "config.yml"}:
        return "configuration"
    if suffix in {".json", ".jsonl", ".csv", ".tsv"}:
        return "structured_data"
    if suffix in {".md", ".txt"}:
        return "documentation"
    if suffix in {".py", ".ps1", ".sh", ".js", ".ts"}:
        return "code"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return "media"
    return "other"


def _workbook_metadata(path: Path, handle: BinaryIO) -> WorkbookMetadata | None:
    if path.suffix.casefold() not in {".xlsx", ".xlsm"}:
        return None
    try:
        if os.fstat(handle.fileno()).st_size > MAX_WORKBOOK_BYTES:
            raise ValueError("workbook exceeds metadata inspection size limit")
        handle.seek(0)
        with zipfile.ZipFile(handle) as archive:
            if len(archive.infolist()) > MAX_WORKBOOK_ENTRIES:
                raise ValueError("workbook exceeds metadata entry limit")
            info = archive.getinfo("xl/workbook.xml")
            if info.file_size > MAX_WORKBOOK_XML_BYTES or info.flag_bits & 1:
                raise ValueError("workbook XML exceeds metadata limits")
            with archive.open(info) as member:
                workbook_xml = member.read(MAX_WORKBOOK_XML_BYTES + 1)
            if len(workbook_xml) > MAX_WORKBOOK_XML_BYTES:
                raise ValueError("workbook XML exceeds metadata limits")
        root = ElementTree.fromstring(
            workbook_xml, parser=ElementTree.XMLParser(target=_WorkbookTreeBuilder())
        )
        sheets = root.findall(f".//{{{WORKBOOK_NAMESPACE}}}sheet")
        names = tuple(sheet.attrib.get("name", "") for sheet in sheets)
        return WorkbookMetadata(sheet_count=len(names), sheet_names=names)
    except (KeyError, ElementTree.ParseError, zipfile.BadZipFile):
        return None


def _validate_output(source_root: Path, output_path: Path) -> None:
    resolved_output = output_path.resolve()
    if resolved_output == source_root or resolved_output.is_relative_to(source_root):
        raise ValueError("Importer output must be outside the read-only source workspace")


def build_manifest(source_workspace: Path) -> LegacyImportManifest:
    source_root = _absolute_source(source_workspace)

    paths, skipped = _walk_files(source_root)
    source_files: list[SourceFile] = []
    for path in paths:
        relative = path.relative_to(source_root)
        with _safe_file(path) as handle:
            file_stat = os.fstat(handle.fileno())
            hasher = hashlib.sha256()
            length = 0
            for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
                length += len(chunk)
            if length != file_stat.st_size:
                raise ValueError("source file length changed during read")
            digest = hasher.hexdigest()
            workbook_metadata = _workbook_metadata(path, handle)
        source_files.append(
            SourceFile(
                relative_path=relative.as_posix(),
                source_group=_source_group(relative),
                size=file_stat.st_size,
                modified_at=datetime.fromtimestamp(file_stat.st_mtime, UTC),
                sha256=digest,
                category=_category(relative),
                legacy_key=f"file:{relative.name.casefold()}",
                workbook_metadata=workbook_metadata,
            )
        )

    snapshot_candidates = tuple(
        item.relative_path
        for item in source_files
        if item.category == "snapshot" or "snapshot" in item.relative_path.casefold()
    )
    legacy_keys = tuple(sorted({item.legacy_key for item in source_files}))
    return LegacyImportManifest(
        source_workspace=str(source_root),
        source_files=tuple(source_files),
        source_hashes={item.relative_path: item.sha256 for item in source_files},
        snapshot_candidates=snapshot_candidates,
        snapshot_sources=snapshot_candidates,
        legacy_keys=legacy_keys,
        identity_mapping={key: None for key in legacy_keys},
        deferred_mismatches=("Canonical legacy authority is not yet approved.",),
        skipped_entries=tuple(skipped),
        importer_version=IMPORTER_VERSION,
        generated_at=datetime.now(UTC),
    )


def write_manifest(manifest: LegacyImportManifest, output_path: Path) -> None:
    source_root = Path(manifest.source_workspace).resolve(strict=True)
    _validate_output(source_root, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump_json(indent=2)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_manifest(path: Path) -> LegacyImportManifest:
    return LegacyImportManifest.model_validate_json(path.read_text(encoding="utf-8"))


def verify_manifest(manifest: LegacyImportManifest) -> Iterator[str]:
    source_root = _absolute_source(Path(manifest.source_workspace))
    for source_file in manifest.source_files:
        try:
            relative = _source_relative_path(source_file.relative_path)
        except ValueError:
            yield f"outside_source:{source_file.relative_path}"
            continue
        try:
            with _safe_file(source_root / relative) as handle:
                observed_mtime = datetime.fromtimestamp(os.fstat(handle.fileno()).st_mtime, UTC)
                digest = hashlib.sha256()
                length = 0
                for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                    digest.update(chunk)
                    length += len(chunk)
            if length != source_file.size:
                yield f"size_changed:{source_file.relative_path}"
            elif digest.hexdigest() != source_file.sha256:
                yield f"hash_changed:{source_file.relative_path}"
            elif observed_mtime != source_file.modified_at:
                yield f"mtime_changed:{source_file.relative_path}"
        except (OSError, ValueError):
            yield f"unsafe_or_changed_source:{source_file.relative_path}"


def source_metadata_signature(source_workspace: Path) -> str:
    root = _absolute_source(source_workspace)
    paths, skipped = _walk_files(root)
    digest = hashlib.sha256()
    for path in paths:
        file_stat = path.stat(follow_symlinks=False)
        line = (
            f"{path.relative_to(root).as_posix()}\0{file_stat.st_size}\0{file_stat.st_mtime_ns}\n"
        )
        digest.update(line.encode("utf-8"))
    for entry in skipped:
        digest.update(f"SKIP\0{entry.relative_path}\0{entry.reason}\n".encode())
    return digest.hexdigest()


def manifest_summary(manifest: LegacyImportManifest) -> str:
    bytes_total = sum(item.size for item in manifest.source_files)
    return json.dumps(
        {
            "source_workspace": manifest.source_workspace,
            "file_count": len(manifest.source_files),
            "bytes": bytes_total,
            "snapshot_candidates": len(manifest.snapshot_candidates),
            "workbooks": sum(item.workbook_metadata is not None for item in manifest.source_files),
            "skipped_entries": len(manifest.skipped_entries),
            "status": manifest.manifest_status,
        },
        ensure_ascii=False,
    )
