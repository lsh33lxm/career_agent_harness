from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkbookMetadata(StrictModel):
    sheet_count: int = Field(ge=0)
    sheet_names: tuple[str, ...]


class SourceFile(StrictModel):
    relative_path: str
    source_group: str
    size: int = Field(ge=0)
    modified_at: datetime
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    category: str
    legacy_key: str
    workbook_metadata: WorkbookMetadata | None = None


class SkippedEntry(StrictModel):
    relative_path: str
    reason: str


class LegacyImportManifest(StrictModel):
    schema_version: int = 1
    manifest_status: str = "candidate_unapproved"
    source_workspace: str
    source_files: tuple[SourceFile, ...]
    source_hashes: dict[str, str]
    snapshot_candidates: tuple[str, ...]
    snapshot_sources: tuple[str, ...]
    legacy_keys: tuple[str, ...]
    identity_mapping: dict[str, str | None]
    approved_entities: tuple[str, ...] = ()
    excluded_entities: tuple[str, ...] = ()
    deferred_mismatches: tuple[str, ...] = ()
    skipped_entries: tuple[SkippedEntry, ...] = ()
    importer_version: str
    generated_at: datetime


class Disposition(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ReconciliationRecord(StrictModel):
    source_path: str
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    legacy_key: str
    candidate_core_identity: str | None
    mismatch: str
    disposition: Disposition
    reason: str
