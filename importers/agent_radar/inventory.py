from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

from importers.agent_radar.models import (
    LegacyImportManifest,
    SkippedEntry,
    SourceFile,
    WorkbookMetadata,
)

IMPORTER_VERSION = "0.1.0"
CHUNK_SIZE = 1024 * 1024
WORKBOOK_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _is_reparse_point(path: Path) -> bool:
    file_attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(file_attributes & reparse_flag)


def _walk_files(root: Path) -> tuple[list[Path], list[SkippedEntry]]:
    files: list[Path] = []
    skipped: list[SkippedEntry] = []
    pending = [root]

    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                if entry.is_symlink() or _is_reparse_point(path):
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
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _workbook_metadata(path: Path) -> WorkbookMetadata | None:
    if path.suffix.casefold() not in {".xlsx", ".xlsm"}:
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            workbook_xml = archive.read("xl/workbook.xml")
        root = ElementTree.fromstring(workbook_xml)
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
    source_root = source_workspace.resolve(strict=True)
    if not source_root.is_dir():
        raise ValueError("source workspace must be a directory")

    paths, skipped = _walk_files(source_root)
    source_files: list[SourceFile] = []
    for path in paths:
        relative = path.relative_to(source_root)
        file_stat = path.stat(follow_symlinks=False)
        digest = sha256_file(path)
        source_files.append(
            SourceFile(
                relative_path=relative.as_posix(),
                source_group=_source_group(relative),
                size=file_stat.st_size,
                modified_at=datetime.fromtimestamp(file_stat.st_mtime, UTC),
                sha256=digest,
                category=_category(relative),
                legacy_key=f"file:{relative.name.casefold()}",
                workbook_metadata=_workbook_metadata(path),
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
    source_root = Path(manifest.source_workspace).resolve(strict=True)
    for source_file in manifest.source_files:
        path = (source_root / Path(source_file.relative_path)).resolve(strict=True)
        if not path.is_relative_to(source_root):
            yield f"outside_source:{source_file.relative_path}"
            continue
        file_stat = path.stat(follow_symlinks=False)
        if file_stat.st_size != source_file.size:
            yield f"size_changed:{source_file.relative_path}"
            continue
        if sha256_file(path) != source_file.sha256:
            yield f"hash_changed:{source_file.relative_path}"


def source_metadata_signature(source_workspace: Path) -> str:
    root = source_workspace.resolve(strict=True)
    paths, skipped = _walk_files(root)
    digest = hashlib.sha256()
    for path in paths:
        file_stat = path.stat(follow_symlinks=False)
        line = (
            f"{path.relative_to(root).as_posix()}\0{file_stat.st_size}\0"
            f"{file_stat.st_mtime_ns}\n"
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
