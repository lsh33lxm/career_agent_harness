from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.storage.artifact_store import ArtifactStore
from importers.agent_radar.archive import (
    ArchiveSelection,
    archive_inventory,
    artifact_location,
    load_verified_index,
)
from importers.agent_radar.inventory import build_manifest, source_metadata_signature
from importers.agent_radar.rehearsal import (
    create_rehearsal_database,
    import_archive,
    logical_rows,
    run_rehearsal,
)


def fixture(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    for name, value in {
        "one.txt": "historical observation",
        "two.txt": "historical observation",
        "config.json": '{"unknown": true}',
        "session.json": "do not preserve",
        "agent_radar_test_workspace/example.txt": "fixture",
        "secret-in-content.txt": "password=do-not-store",
    }.items():
        target = source / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(value)
    inventory = build_manifest(source).model_dump_json(indent=2).encode()
    store = ArtifactStore(tmp_path / "artifacts")
    selections = tuple(
        ArchiveSelection(relative_path=name, inspected=True, reason="reviewed")
        for name in (
            "one.txt",
            "two.txt",
            "session.json",
            "agent_radar_test_workspace/example.txt",
        )
    )
    return source, inventory, store, selections


def test_preservation_exclusions_provenance_and_restore(tmp_path: Path):
    source, inventory, store, selections = fixture(tmp_path)
    before = source_metadata_signature(source)
    index, index_sha = archive_inventory(inventory, source, store, selections)
    assert source_metadata_signature(source) == before
    assert load_verified_index(store, index_sha) == index
    entries = {e.source.relative_path: e for e in index.entries}
    assert entries["one.txt"].archive_location == entries["two.txt"].archive_location
    assert entries["config.json"].disposition == "deferred"
    assert entries["session.json"].disposition == "excluded"
    assert entries["agent_radar_test_workspace/example.txt"].disposition == "excluded"
    assert all(e.candidate_authority == "unknown" for e in index.entries)
    report = run_rehearsal(tmp_path / "rehearsal", store, index_sha)
    assert report.preserved_paths == 2
    assert report.row_counts == {
        "evidence_artifact": 1,
        "evidence_source": 2,
        "source_snapshot": 2,
        "evidence_ref": 2,
    }
    assert not report.canonical_cutover
    assert logical_rows(tmp_path / "rehearsal" / "first.rehearsal.db") == logical_rows(
        tmp_path / "rehearsal" / "restored.rehearsal.db"
    )


@pytest.mark.parametrize("fault", [None, "hash", "credential", "parent", "uninspected"])
def test_source_code_path_exception_is_exact_and_cannot_bypass_credentials(tmp_path, fault):
    source = tmp_path / "source"
    source.mkdir()
    name = "secrets/phase1_profile.py" if fault == "parent" else "phase1_profile.py"
    path = source / name
    path.parent.mkdir(exist_ok=True)
    path.write_text('password="sensitive"' if fault == "credential" else 'print("statistics")')
    manifest = build_manifest(source)
    selection = ArchiveSelection(
        relative_path=name,
        reason="reviewed source code, not a session profile",
        inspected=fault != "uninspected",
        source_code_exception_sha256="0" * 64
        if fault == "hash"
        else manifest.source_files[0].sha256,
    )
    store = ArtifactStore(tmp_path / "artifacts")
    if fault in {"hash", "parent", "uninspected"}:
        with pytest.raises(ValueError, match="exception"):
            archive_inventory(manifest.model_dump_json().encode(), source, store, (selection,))
    else:
        index, index_sha = archive_inventory(
            manifest.model_dump_json().encode(), source, store, (selection,)
        )
        assert index.entries[0].disposition == (
            "excluded" if fault == "credential" else "preserved"
        )
        assert load_verified_index(store, index_sha) == index


def test_uninspected_selection_and_unknown_content_deferred(tmp_path: Path):
    source, inventory, store, _ = fixture(tmp_path)
    index, _ = archive_inventory(
        inventory,
        source,
        store,
        (ArchiveSelection(relative_path="config.json", reason="not yet reviewed"),),
    )
    assert not any(e.disposition == "preserved" for e in index.entries)


def test_changed_source_and_corrupted_artifact_fail_closed(tmp_path: Path):
    source, inventory, store, selections = fixture(tmp_path)
    index, sha = archive_inventory(inventory, source, store, selections)
    preserved = next(e for e in index.entries if e.disposition == "preserved")
    (store.root / artifact_location(preserved.source.sha256)).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_verified_index(store, sha)
    with pytest.raises(ValueError, match="hash mismatch"):
        archive_inventory(inventory, source, store, selections)
    (source / "one.txt").write_bytes(b"changed")
    with pytest.raises((ValueError, RuntimeError)):
        archive_inventory(inventory, source, store, selections)


def test_refuses_production_unknown_db_and_conflicting_rows(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ACH_DATA_DIR", str(tmp_path / "production"))
    with pytest.raises(ValueError, match="production"):
        create_rehearsal_database(tmp_path / "production" / "career_harness.db")
    with pytest.raises(ValueError, match="rehearsal"):
        create_rehearsal_database(tmp_path / "arbitrary.db")
    source, inventory, store, selections = fixture(tmp_path)
    _, index_sha = archive_inventory(inventory, source, store, selections)
    db = tmp_path / "test.rehearsal.db"
    create_rehearsal_database(db)
    import_archive(db, store, index_sha)
    source_id = logical_rows(db)["evidence_source"][0][0]
    db = tmp_path / "conflict.rehearsal.db"
    create_rehearsal_database(db)
    engine = create_sqlite_engine(sqlite_url(db))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO evidence_source(source_id, source_type, locator) "
                "VALUES (:id, 'wrong', 'conflicting origin')"
            ),
            {"id": source_id},
        )
    engine.dispose()
    before = logical_rows(db)
    with pytest.raises(ValueError, match="conflicting"):
        import_archive(db, store, index_sha)
    assert logical_rows(db) == before
    with pytest.raises(FileExistsError):
        create_rehearsal_database(db)


@pytest.mark.parametrize("content", ["api_key = synthetic-placeholder", '{"api_key":"sample"}'])
def test_embedded_credentials_excluded_and_exact_bytes_bound(tmp_path: Path, content: str):
    source, _, store, _ = fixture(tmp_path)
    (source / "plain.txt").write_text(content)
    inventory = build_manifest(source).model_dump_json().encode()
    selections = (ArchiveSelection(relative_path="plain.txt", inspected=True, reason="reviewed"),)
    index, index_sha = archive_inventory(inventory, source, store, selections)
    assert (
        next(e for e in index.entries if e.source.relative_path == "plain.txt").disposition
        == "excluded"
    )
    index2, index_sha2 = archive_inventory(inventory + b"\n", source, store, selections)
    assert index.inventory_sha256 != index2.inventory_sha256
    assert index_sha != index_sha2


def test_inventory_mismatch_and_unknown_selection_refused(tmp_path: Path):
    import json

    source, inventory, store, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="absent"):
        archive_inventory(
            inventory,
            source,
            store,
            (ArchiveSelection(relative_path="absent", inspected=True, reason="reviewed"),),
        )
    content = json.loads(inventory)
    content["source_hashes"] = {}
    with pytest.raises(ValueError, match="hash map"):
        archive_inventory(json.dumps(content).encode(), source, store)


def test_source_mtime_change_refused(tmp_path: Path):
    import os

    source, inventory, store, selections = fixture(tmp_path)
    target = source / "one.txt"
    metadata = target.stat()
    os.utime(target, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 2_000_000_000))
    with pytest.raises(ValueError):
        archive_inventory(inventory, source, store, selections)


def test_broken_index_and_missing_artifact_fail_before_database_write(tmp_path: Path):
    from career_harness.core.evidence.models import ArtifactClass

    source, inventory, store, selections = fixture(tmp_path)
    index, index_sha = archive_inventory(inventory, source, store, selections)
    broken = index.model_copy(update={"entries": index.entries[:-1]})
    broken_sha = store.put(broken.model_dump_json().encode(), ArtifactClass.SENSITIVE).sha256
    db = tmp_path / "broken.rehearsal.db"
    create_rehearsal_database(db)
    before = logical_rows(db)
    with pytest.raises(ValueError, match="provenance"):
        import_archive(db, store, broken_sha)
    preserved = next(e for e in index.entries if e.disposition == "preserved")
    (store.root / preserved.archive_location).unlink()
    with pytest.raises(FileNotFoundError):
        import_archive(db, store, index_sha)
    assert logical_rows(db) == before


def test_existing_unmarked_db_cannot_be_imported(tmp_path: Path):
    import sqlite3

    source, inventory, store, selections = fixture(tmp_path)
    _, index_sha = archive_inventory(inventory, source, store, selections)
    db = tmp_path / "unmarked.rehearsal.db"
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    before = db.read_bytes()
    with pytest.raises(sqlite3.OperationalError):
        import_archive(db, store, index_sha)
    assert db.read_bytes() == before


def test_reconciliation_retains_duplicates_conflicts_and_version_candidates(tmp_path: Path):
    from importers.agent_radar.reconciliation_summary import reconcile_summary

    source = tmp_path / "source"
    for relative, content in {
        "a/report.json": "same",
        "b/report.json": "same",
        "c/report.json": "changed",
        "d/other.json": "same",
        "stats_v1.xlsx": "first",
        "stats_v2.xlsx": "second",
    }.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    summary = reconcile_summary(build_manifest(source))
    assert len(summary.same_key_same_hash) == 1
    assert len(summary.same_key_different_hash) == 1
    assert len(summary.cross_path_hash_duplicates) == 1
    assert len(summary.cross_path_hash_duplicates[0].members) == 3
    assert any(
        set(g.members) == {"stats_v1.xlsx", "stats_v2.xlsx"}
        for g in summary.version_family_candidates
    )
    assert summary.archive_member_inspection == "not_performed"
    assert all(g.authority == "unresolved_candidate" for g in summary.same_key_different_hash)


def test_existing_dangling_ref_rejected_without_importing_rows(tmp_path: Path):
    import sqlite3

    source, inventory, store, selections = fixture(tmp_path)
    _, index_sha = archive_inventory(inventory, source, store, selections)
    db = tmp_path / "dangling.rehearsal.db"
    create_rehearsal_database(db)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO evidence_ref(evidence_ref_id,snapshot_id,artifact_id) "
            "VALUES ('dangling-ref','missing-snapshot','missing-artifact')"
        )
    with sqlite3.connect(db) as connection:
        before = tuple(connection.iterdump())
    with pytest.raises(ValueError, match="foreign key"):
        import_archive(db, store, index_sha)
    with sqlite3.connect(db) as connection:
        assert tuple(connection.iterdump()) == before
        assert connection.execute("SELECT COUNT(*) FROM evidence_source").fetchone() == (0,)


def test_pending_dangling_ref_rolls_back_entire_import(tmp_path: Path, monkeypatch):
    from career_harness.db.models import EvidenceSourceRow
    from importers.agent_radar import rehearsal

    source, inventory, store, selections = fixture(tmp_path)
    _, index_sha = archive_inventory(inventory, source, store, selections)
    db = tmp_path / "pending.rehearsal.db"
    create_rehearsal_database(db)
    before = logical_rows(db)
    original_upsert = rehearsal._upsert_exact
    injected = False

    def inject_invalid_pending_ref(session, row):
        nonlocal injected
        original_upsert(session, row)
        if isinstance(row, EvidenceSourceRow) and not injected:
            injected = True
            session.connection().exec_driver_sql("PRAGMA defer_foreign_keys=ON")
            session.connection().exec_driver_sql(
                "INSERT INTO evidence_ref(evidence_ref_id,snapshot_id,artifact_id) "
                "VALUES ('pending-ref','missing-snapshot','missing-artifact')"
            )

    monkeypatch.setattr(rehearsal, "_upsert_exact", inject_invalid_pending_ref)
    with pytest.raises(ValueError, match="foreign key"):
        import_archive(db, store, index_sha)
    assert injected
    assert logical_rows(db) == before
