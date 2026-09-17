from __future__ import annotations

from pathlib import Path

import pytest

from importers.agent_radar.inventory import (
    build_manifest,
    source_metadata_signature,
    verify_manifest,
    write_manifest,
)


def test_inventory_is_read_only_and_verifiable(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "work").mkdir()
    (source / "data").mkdir()
    (source / "work" / "jobs.json").write_text('{"source":"work"}', encoding="utf-8")
    (source / "data" / "jobs.json").write_text('{"source":"data"}', encoding="utf-8")
    before = source_metadata_signature(source)

    manifest = build_manifest(source)
    output = tmp_path / "new-repo" / "LEGACY_IMPORT_MANIFEST.json"
    write_manifest(manifest, output)
    after = source_metadata_signature(source)

    assert before == after
    assert tuple(verify_manifest(manifest)) == ()
    assert len(manifest.source_files) == 2
    assert manifest.approved_entities == ()
    assert manifest.manifest_status == "candidate_unapproved"
    assert output.exists()


def test_output_inside_source_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "source.json").write_text("{}", encoding="utf-8")
    manifest = build_manifest(source)

    with pytest.raises(ValueError, match="outside"):
        write_manifest(manifest, source / "LEGACY_IMPORT_MANIFEST.json")


def test_symlink_is_not_followed_when_supported(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    outside = tmp_path / "outside"
    source.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("not part of inventory", encoding="utf-8")
    link = source / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available")

    manifest = build_manifest(source)

    assert manifest.source_files == ()
    assert manifest.skipped_entries[0].relative_path == "linked"

