from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field

from career_harness.core.evidence.models import ArtifactClass
from career_harness.storage.artifact_store import ArtifactStore
from importers.agent_radar.inventory import read_source_bytes, source_metadata_signature
from importers.agent_radar.models import LegacyImportManifest, SourceFile, StrictModel


class ArchiveSelection(StrictModel):
    relative_path: str
    reason: str = Field(min_length=1)
    artifact_class: ArtifactClass = ArtifactClass.SENSITIVE
    source_class: str = "unknown"
    inspected: bool = False


class ArchiveEntry(StrictModel):
    source: SourceFile
    source_class: str = "unknown"
    candidate_authority: Literal["unknown"] = "unknown"
    disposition: Literal["preserved", "excluded", "deferred"]
    reason: str
    archive_location: str | None = None
    artifact_class: ArtifactClass = ArtifactClass.SENSITIVE


class ArchiveIndex(StrictModel):
    schema_version: int = 1
    inventory_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    entries: tuple[ArchiveEntry, ...]


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def artifact_location(sha256: str) -> str:
    return f"{sha256[:2]}/{sha256[2:4]}/{sha256}"


def verified_content(store: ArtifactStore, sha256: str) -> bytes:
    if not re.fullmatch(r"[a-f0-9]{64}", sha256):
        raise ValueError("invalid artifact digest")
    location = artifact_location(sha256)
    size = (store.root / location).stat(follow_symlinks=False).st_size
    try:
        return read_source_bytes(
            store.root,
            location,
            expected_size=size,
            expected_sha256=sha256,
        )
    except ValueError as exc:
        raise ValueError("artifact hash mismatch or unsafe artifact path") from exc


def _put(store: ArtifactStore, content: bytes, kind: ArtifactClass) -> str:
    sha = digest(content)
    target = store.root / artifact_location(sha)
    if target.exists() and verified_content(store, sha) != content:
        raise ValueError("existing artifact differs")
    result = store.put(content, kind)
    verified_content(store, result.sha256)
    return result.sha256


def _excluded(relative: str) -> bool:
    parts = PurePosixPath(relative.replace("\\", "/")).parts
    return any(
        part.casefold() == "agent_radar_test_workspace"
        or re.search(
            r"(?i)(credential|secret|session|profile|cookie|token|password|\.env|\.ssh)"
            r"|(?i:id_rsa|id_ed25519)|(?i:\.(pem|key|p12|pfx)$)",
            part,
        )
        for part in parts
    )


def archive_inventory(
    inventory_bytes: bytes,
    source_root: Path,
    store: ArtifactStore,
    selections: tuple[ArchiveSelection, ...] = (),
) -> tuple[ArchiveIndex, str]:
    """Preserve only explicitly inspected entries; never infer claim authority."""
    manifest = LegacyImportManifest.model_validate_json(inventory_bytes)
    if source_root.resolve() != Path(manifest.source_workspace).resolve():
        raise ValueError("inventory source mismatch")
    if store.root.is_relative_to(source_root.resolve()):
        raise ValueError("archive destination must be outside source")
    sources = {item.relative_path: item for item in manifest.source_files}
    chosen = {item.relative_path: item for item in selections}
    if len(sources) != len(manifest.source_files) or len(chosen) != len(selections):
        raise ValueError("duplicate source or selection path")
    if chosen.keys() - sources.keys():
        raise ValueError("selection absent from inventory")
    if manifest.source_hashes != {p: f.sha256 for p, f in sources.items()}:
        raise ValueError("inventory hash map mismatch")
    before = source_metadata_signature(source_root)
    entries: list[ArchiveEntry] = []
    for source in manifest.source_files:
        selection = chosen.get(source.relative_path)
        disposition: Literal["preserved", "excluded", "deferred"] = "deferred"
        reason = "not inspected and explicitly selected; legacy dependency remains"
        location = None
        kind = selection.artifact_class if selection else ArtifactClass.SENSITIVE
        if _excluded(source.relative_path) or kind == ArtifactClass.CREDENTIAL_SESSION:
            disposition, reason = "excluded", "fixture or credential/session path"
        elif selection and selection.inspected:
            content = read_source_bytes(
                source_root,
                source.relative_path,
                expected_size=source.size,
                expected_sha256=source.sha256,
                expected_modified_at=source.modified_at,
            )
            # Inspection is explicit; obvious embedded credential material still fails closed.
            if re.search(
                rb"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY|"
                rb"(?:api[_-]?key|password|access_token)[\"']?\s*[=:]\s*[^\s])",
                content,
            ):
                disposition, reason = "excluded", "credential content marker"
            else:
                _put(store, content, kind)
                disposition, reason = "preserved", selection.reason
                location = artifact_location(source.sha256)
        entries.append(
            ArchiveEntry(
                source=source,
                source_class=selection.source_class if selection else "unknown",
                disposition=disposition,
                reason=reason,
                archive_location=location,
                artifact_class=kind,
            )
        )
    if source_metadata_signature(source_root) != before:
        raise RuntimeError("source metadata changed during archive")
    inventory_sha = _put(store, inventory_bytes, ArtifactClass.SENSITIVE)
    index = ArchiveIndex(inventory_sha256=inventory_sha, entries=tuple(entries))
    index_sha = _put(store, index.model_dump_json().encode(), ArtifactClass.SENSITIVE)
    return index, index_sha


def load_verified_index(store: ArtifactStore, index_sha: str) -> ArchiveIndex:
    index = ArchiveIndex.model_validate_json(verified_content(store, index_sha))
    manifest = LegacyImportManifest.model_validate_json(
        verified_content(store, index.inventory_sha256)
    )
    if tuple(entry.source for entry in index.entries) != manifest.source_files:
        raise ValueError("index inventory provenance mismatch")
    sources = {source.relative_path: source.sha256 for source in manifest.source_files}
    if len(sources) != len(manifest.source_files) or sources != manifest.source_hashes:
        raise ValueError("inventory hash map mismatch")
    for entry in index.entries:
        if entry.disposition != "preserved" and entry.archive_location is not None:
            raise ValueError("unpreserved entry has archive location")
        if entry.disposition == "preserved":
            if (
                _excluded(entry.source.relative_path)
                or entry.artifact_class == ArtifactClass.CREDENTIAL_SESSION
            ):
                raise ValueError("excluded entry cannot be preserved")
            if entry.archive_location != artifact_location(entry.source.sha256):
                raise ValueError("archive location mismatch")
            if len(verified_content(store, entry.source.sha256)) != entry.source.size:
                raise ValueError("artifact size mismatch")
    return index
