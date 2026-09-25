from datetime import UTC, datetime

from importers.agent_radar.models import LegacyImportManifest, SourceFile
from importers.agent_radar.reconcile import build_reconciliation, render_reconciliation_report


def _source(relative_path: str, source_group: str, digest: str) -> SourceFile:
    return SourceFile(
        relative_path=relative_path,
        source_group=source_group,
        size=1,
        modified_at=datetime.now(UTC),
        sha256=digest,
        category="structured_data",
        legacy_key="file:jobs.json",
    )


def test_conflicting_candidates_are_deferred() -> None:
    first_hash = "a" * 64
    second_hash = "b" * 64
    manifest = LegacyImportManifest(
        source_workspace="C:/legacy",
        source_files=(
            _source("work/jobs.json", "work", first_hash),
            _source("data/jobs.json", "data", second_hash),
        ),
        source_hashes={"work/jobs.json": first_hash, "data/jobs.json": second_hash},
        snapshot_candidates=(),
        snapshot_sources=(),
        legacy_keys=("file:jobs.json",),
        identity_mapping={"file:jobs.json": None},
        importer_version="test",
        generated_at=datetime.now(UTC),
    )

    records = build_reconciliation(manifest)

    assert len(records) == 2
    assert {record.disposition.value for record in records} == {"deferred"}
    report = render_reconciliation_report(manifest, records)
    assert "NEEDS USER APPROVAL" in report
    assert "declared canonical" in report

