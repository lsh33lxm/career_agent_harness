from __future__ import annotations

import os
import zipfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from importers.agent_radar import inventory
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


@pytest.mark.parametrize("component", ["root", "ancestor", "file"])
def test_windows_reparse_at_any_component_fails_closed(tmp_path, monkeypatch, component):
    if os.name != "nt":
        pytest.skip("Windows handle reparse validation")
    from career_harness.services.project_scanner import _WindowsAnchoredReader

    source = tmp_path / "parent" / "legacy"
    source.mkdir(parents=True)
    file = source / "data.json"
    file.write_bytes(b"safe")
    manifest = build_manifest(source)
    denied = {"root": source, "ancestor": source.parent, "file": file}[component]
    original = _WindowsAnchoredReader._reject_reparse

    def reject(self, path, information):
        if path == denied:
            information.dwFileAttributes |= self._FILE_ATTRIBUTE_REPARSE_POINT
        return original(self, path, information)

    monkeypatch.setattr(_WindowsAnchoredReader, "_reject_reparse", reject)
    assert tuple(verify_manifest(manifest)) == ("unsafe_or_changed_source:data.json",)
    with pytest.raises(ValueError, match="reparse"):
        inventory.sha256_file(file)
    if component != "file":
        with pytest.raises(ValueError, match="reparse"):
            build_manifest(source)


def test_root_and_ancestor_symlinks_are_not_resolved_away(tmp_path):
    source = tmp_path / "real" / "legacy"
    source.mkdir(parents=True)
    (source / "a").write_bytes(b"safe")
    link = tmp_path / "linked"
    try:
        link.symlink_to(source.parent, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available")
    for path in (link, link / "legacy"):
        with pytest.raises((OSError, ValueError)):
            build_manifest(path)


def test_verify_rejects_replaced_symlink_even_inside_source(tmp_path):
    source = tmp_path / "legacy"
    source.mkdir()
    original = source / "a"
    original.write_bytes(b"safe")
    manifest = build_manifest(source)
    (source / "b").write_bytes(b"safe")
    original.unlink()
    try:
        original.symlink_to(source / "b")
    except OSError:
        pytest.skip("symlink creation is not available")
    assert tuple(verify_manifest(manifest)) == ("unsafe_or_changed_source:a",)


@pytest.mark.parametrize("relative", ["../outside", "/outside", "C:/outside", "../legacy/a"])
def test_verify_rejects_untrusted_manifest_paths(tmp_path, relative):
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "a").write_bytes(b"safe")
    manifest = build_manifest(source)
    forged = manifest.model_copy(
        update={
            "source_files": (
                manifest.source_files[0].model_copy(update={"relative_path": relative}),
            )
        }
    )
    assert tuple(verify_manifest(forged)) == (f"outside_source:{relative}",)


def test_file_metadata_change_during_read_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / "source.json"
    path.write_bytes(b"same size")
    original = os.fstat
    calls = 0

    def changed(fd):
        nonlocal calls
        value = original(fd)
        calls += 1
        return SimpleNamespace(
            **{
                name: getattr(value, name) + (1 if name == "st_mtime_ns" and calls > 1 else 0)
                for name in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
            }
        )

    # Inject a metadata race without attempting a prohibited write to a pinned Windows file.
    with inventory._safe_file(path) as handle:
        assert handle.read() == b"same size"
    monkeypatch.setattr(inventory.os, "fstat", changed)
    with pytest.raises(ValueError, match="changed"):
        inventory.sha256_file(path)


def test_verify_detects_mtime_only_change(tmp_path):
    source = tmp_path / "legacy"
    source.mkdir()
    path = source / "a"
    path.write_bytes(b"safe")
    manifest = build_manifest(source)
    previous = path.stat()
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000))
    assert tuple(verify_manifest(manifest)) == ("mtime_changed:a",)


@pytest.mark.parametrize("fault", ["xml_size", "zip_size", "members", "doctype_utf16"])
def test_workbook_metadata_is_bounded_and_rejects_dtd(tmp_path, monkeypatch, fault):
    source = tmp_path / "legacy"
    source.mkdir()
    xml = (
        b'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<sheets><sheet name="Safe"/></sheets></workbook>'
    )
    if fault == "doctype_utf16":
        xml = '<!DOCTYPE workbook [<!ENTITY x "test">]><workbook>&x;</workbook>'.encode("utf-16")
    with zipfile.ZipFile(source / "book.xlsx", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", xml)
    if fault == "xml_size":
        monkeypatch.setattr(inventory, "MAX_WORKBOOK_XML_BYTES", 10)
    elif fault == "zip_size":
        monkeypatch.setattr(inventory, "MAX_WORKBOOK_BYTES", 10)
    elif fault == "members":
        monkeypatch.setattr(inventory, "MAX_WORKBOOK_ENTRIES", 0)
    with pytest.raises(ValueError, match="workbook"):
        build_manifest(source)


def test_valid_workbook_metadata_and_hash_share_safe_read(tmp_path):
    source = tmp_path / "legacy"
    source.mkdir()
    with zipfile.ZipFile(source / "book.xlsx", "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Safe"/></sheets></workbook>',
        )
    manifest = build_manifest(source)
    assert manifest.source_files[0].workbook_metadata.sheet_names == ("Safe",)
    assert tuple(verify_manifest(manifest)) == ()


@pytest.mark.parametrize("fault", [None, "size", "hash", "mtime", "traversal"])
def test_manifest_bound_byte_reader(tmp_path, fault):
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "a").write_bytes(b"safe")
    entry = build_manifest(source).source_files[0]
    kwargs = {
        "relative_path": entry.relative_path,
        "expected_size": entry.size,
        "expected_sha256": entry.sha256,
        "expected_modified_at": entry.modified_at,
    }
    if fault == "size":
        kwargs["expected_size"] = entry.size + 1
    elif fault == "hash":
        kwargs["expected_sha256"] = "0" * 64
    elif fault == "mtime":
        kwargs["expected_modified_at"] = entry.modified_at + timedelta(seconds=1)
    elif fault == "traversal":
        kwargs["relative_path"] = "../legacy/a"
    if fault is None:
        assert inventory.read_source_bytes(source, **kwargs) == b"safe"
    else:
        with pytest.raises(ValueError):
            inventory.read_source_bytes(source, **kwargs)
