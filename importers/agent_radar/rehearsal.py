from __future__ import annotations

import json
import sqlite3
from datetime import UTC
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from career_harness.db.backup import create_backup, restore_backup
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    Base,
    EvidenceArtifactRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    SourceSnapshotRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform.paths import AppPaths
from career_harness.storage.artifact_store import ArtifactStore
from importers.agent_radar.archive import load_verified_index, verified_content
from importers.agent_radar.models import LegacyImportManifest, StrictModel

TABLES = (EvidenceArtifactRow, EvidenceSourceRow, SourceSnapshotRow, EvidenceRefRow)


class RehearsalReport(StrictModel):
    index_sha256: str
    inventory_sha256: str
    preserved_paths: int
    deferred_paths: int
    excluded_paths: int
    row_counts: dict[str, int]
    logical_sha256: str
    canonical_cutover: Literal[False] = False


def _id(kind: str, value: str) -> str:
    return f"legacy-{kind}-{uuid5(NAMESPACE_URL, value)}"


def _guard(database: Path) -> None:
    production = AppPaths.resolve().database
    if database.resolve() == production.resolve() or (
        database.exists() and production.exists() and database.samefile(production)
    ):
        raise ValueError("production database refused")
    if not database.name.endswith(".rehearsal.db"):
        raise ValueError("disposable database must end in .rehearsal.db")


def create_rehearsal_database(database: Path) -> None:
    _guard(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation refuses even an unrelated existing empty file.
    with database.open("xb"):
        pass
    upgrade_to_head(sqlite_url(database))
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE legacy_rehearsal_guard (marker TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO legacy_rehearsal_guard VALUES ('disposable-only')")


def _check_marker(database: Path) -> None:
    _guard(database)
    with sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True) as connection:
        if connection.execute("SELECT marker FROM legacy_rehearsal_guard").fetchall() != [
            ("disposable-only",)
        ]:
            raise ValueError("not an explicitly created rehearsal database")


def _upsert_exact(session: Session, row: Base) -> None:
    table = row.__table__
    primary_key = list(table.primary_key)[0].name
    existing = session.get(type(row), getattr(row, primary_key))
    if existing is None:
        session.add(row)
        session.flush()
    elif any(getattr(existing, c.name) != getattr(row, c.name) for c in table.columns):
        raise ValueError("conflicting existing provenance row")


def logical_rows(database: Path) -> dict[str, list[list[object]]]:
    _check_marker(database)
    with sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("database integrity failure")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("database foreign key failure")
        return {
            row.__tablename__: [
                list(item)
                for item in connection.execute(f'SELECT * FROM "{row.__tablename__}" ORDER BY 1')
            ]
            for row in TABLES
        }


def import_archive(database: Path, store: ArtifactStore, index_sha: str) -> RehearsalReport:
    _check_marker(database)
    index = load_verified_index(store, index_sha)
    manifest = LegacyImportManifest.model_validate_json(
        verified_content(store, index.inventory_sha256)
    )
    if manifest.generated_at.tzinfo is None:
        raise ValueError("inventory capture time must include timezone")
    engine = create_sqlite_engine(sqlite_url(database))
    try:
        with Session(engine) as session, session.begin():
            for entry in index.entries:
                if entry.disposition != "preserved":
                    continue
                source = entry.source
                # Batch-pinned identity preserves every origin, including duplicate bytes.
                key = f"{index.inventory_sha256}:{source.relative_path}"
                artifact_id = _id("artifact", f"{source.sha256}:{entry.artifact_class}")
                source_id = _id("source", key)
                snapshot_id = _id("snapshot", key)
                _upsert_exact(
                    session,
                    EvidenceArtifactRow(
                        artifact_id=artifact_id,
                        sha256=source.sha256,
                        media_type="application/octet-stream",
                        artifact_class=entry.artifact_class.value,
                        byte_length=source.size,
                    ),
                )
                _upsert_exact(
                    session,
                    EvidenceSourceRow(
                        source_id=source_id,
                        source_type="legacy_historical_unconfirmed",
                        locator=f"legacy-inventory:{index.inventory_sha256}/{source.relative_path}",
                    ),
                )
                _upsert_exact(
                    session,
                    SourceSnapshotRow(
                        snapshot_id=snapshot_id,
                        source_id=source_id,
                        captured_at=manifest.generated_at.astimezone(UTC).replace(tzinfo=None),
                        artifact_id=artifact_id,
                    ),
                )
                _upsert_exact(
                    session,
                    EvidenceRefRow(
                        evidence_ref_id=_id("ref", f"{index_sha}:{key}"),
                        snapshot_id=snapshot_id,
                        artifact_id=artifact_id,
                        selector=f"archive-index:{index_sha};inventory:{index.inventory_sha256}",
                    ),
                )
        # Check exact reference chain through the existing read repository.
        from career_harness.db.evidence_repository import EvidenceRepository

        repository = EvidenceRepository(engine)
        with Session(engine) as session:
            refs = session.scalars(select(EvidenceRefRow.evidence_ref_id)).all()
        for ref_id in refs:
            if repository.get(ref_id) is None:
                raise ValueError("missing evidence provenance")
    finally:
        engine.dispose()
    rows = logical_rows(database)
    from importers.agent_radar.archive import digest

    return RehearsalReport(
        index_sha256=index_sha,
        inventory_sha256=index.inventory_sha256,
        preserved_paths=sum(e.disposition == "preserved" for e in index.entries),
        deferred_paths=sum(e.disposition == "deferred" for e in index.entries),
        excluded_paths=sum(e.disposition == "excluded" for e in index.entries),
        row_counts={table: len(items) for table, items in rows.items()},
        logical_sha256=digest(json.dumps(rows, sort_keys=True).encode()),
    )


def run_rehearsal(root: Path, store: ArtifactStore, index_sha: str) -> RehearsalReport:
    """Exclusive disposable targets; retain the rehearsal and restore evidence for audit."""
    if root.exists():
        raise FileExistsError("rehearsal root must not exist")
    root.mkdir(parents=True)
    first, rebuilt = root / "first.rehearsal.db", root / "rebuilt.rehearsal.db"
    create_rehearsal_database(first)
    report = import_archive(first, store, index_sha)
    if import_archive(first, store, index_sha) != report:
        raise ValueError("reimport is not idempotent")
    create_rehearsal_database(rebuilt)
    if import_archive(rebuilt, store, index_sha) != report:
        raise ValueError("rebuild is not deterministic")
    create_backup(first, store.root, root / "backup")
    restored = root / "restored.rehearsal.db"
    restored_artifacts = root / "restored-artifacts"
    restore_backup(root / "backup", restored, restored_artifacts)
    if logical_rows(restored) != logical_rows(first):
        raise ValueError("restore logical rows differ")
    if import_archive(restored, ArtifactStore(restored_artifacts), index_sha) != report:
        raise ValueError("restore provenance differs")
    (root / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
