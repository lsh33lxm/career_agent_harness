import hashlib
import os
import stat
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from career_harness.core.project import Project, ProjectScanScope
from career_harness.services.project_scanner import (
    LocalProjectScanner,
    ProjectScanError,
    has_reparse_attribute,
)


def _project(root: Path) -> Project:
    return Project(
        project_id="project_001",
        display_name="Fixture Project",
        root_locator=str(root),
        created_by="user",
    )


def _scope(*allowed: str, denied: tuple[str, ...] = (), revision: int = 3) -> ProjectScanScope:
    return ProjectScanScope(
        scope_id="scope_001",
        project_id="project_001",
        revision=revision,
        allowed_paths=allowed,
        denied_paths=denied,
        created_by="user",
    )


def test_scanner_reads_allowed_file_and_directory_deterministically(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src" / "nested").mkdir(parents=True)
    (root / "src" / "z.py").write_bytes(b"print('z')\n")
    (root / "src" / "nested" / "A.py").write_bytes(b"print('a')\n")
    (root / "README.md").write_bytes(b"read me")
    (root / "outside.txt").write_bytes(b"outside")
    generated_at = datetime(2026, 9, 19, tzinfo=UTC)
    scanner = LocalProjectScanner()

    first = scanner.scan(
        _project(root),
        _scope("src", "README.md"),
        manifest_id="manifest_001",
        generated_at=generated_at,
    )
    second = scanner.scan(
        _project(root),
        _scope("src", "README.md"),
        manifest_id="manifest_001",
        generated_at=generated_at,
    )

    assert first == second
    assert (first.scan_scope_id, first.scan_scope_revision) == ("scope_001", 3)
    assert tuple(entry.relative_path for entry in first.entries) == (
        "README.md",
        "src/nested/A.py",
        "src/z.py",
    )
    by_path = {entry.relative_path: entry for entry in first.entries}
    assert by_path["src/z.py"].sha256 == hashlib.sha256(b"print('z')\n").hexdigest()
    assert by_path["src/z.py"].byte_length == len(b"print('z')\n")
    assert "outside" not in first.model_dump_json()


def test_scanner_applies_deny_and_hard_deny_before_stat(tmp_path: Path) -> None:
    root = tmp_path / "project"
    paths = {
        "src/keep.py": b"safe",
        "src/denied/no.py": b"denied",
        ".env": b"TOKEN=secret",
        ".env.local": b"TOKEN=secret",
        "secrets/token.txt": b"secret",
        "sessions/session.json": b"session",
        "browser/profile/Cookies": b"cookies",
        "profile/credentials.json": b"credentials",
        "Chrome/User Data/Default/History": b"history",
        "Chrome/User Data/Default/Preferences": b"preferences",
        "Chrome/User Data/Default/Local Extension Settings/data": b"extension-data",
    }
    for relative_path, content in paths.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    scanner = LocalProjectScanner()
    original_stat = scanner._stat_no_follow
    stat_paths: list[str] = []

    def tracking_stat(path: Path, message: str) -> os.stat_result:
        with suppress(ValueError):
            stat_paths.append(path.relative_to(root).as_posix())
        return original_stat(path, message)

    scanner._stat_no_follow = tracking_stat  # type: ignore[method-assign]
    manifest = scanner.scan(
        _project(root),
        _scope(".", denied=("src/denied",)),
        manifest_id="manifest_001",
    )

    assert tuple(entry.relative_path for entry in manifest.entries) == ("src/keep.py",)
    assert not any(
        path == blocked or path.startswith(f"{blocked}/")
        for path in stat_paths
        for blocked in (
            ".env",
            ".env.local",
            "src/denied",
            "secrets",
            "sessions",
            "browser/profile/Cookies",
            "profile/credentials.json",
            "Chrome",
        )
    )
    serialized = manifest.model_dump_json()
    assert all(content.decode() not in serialized for content in paths.values())


def test_scanner_descends_to_a_nested_explicit_allow(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src" / "nested").mkdir(parents=True)
    (root / "src" / "nested" / "allowed.py").write_text("allowed", encoding="utf-8")
    (root / "src" / "outside.py").write_text("outside", encoding="utf-8")

    manifest = LocalProjectScanner().scan(
        _project(root),
        _scope("src/nested/allowed.py"),
        manifest_id="manifest_001",
    )

    assert tuple(entry.relative_path for entry in manifest.entries) == (
        "src/nested/allowed.py",
    )


@pytest.mark.parametrize("invalid_path", ["../outside", "C:/outside", "/outside"])
def test_scanner_scope_rejects_traversal_and_absolute_paths(invalid_path: str) -> None:
    with pytest.raises(ValueError):
        _scope(invalid_path)


def test_scanner_rejects_missing_file_root_and_cross_project_scope(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ProjectScanError, match="unavailable"):
        LocalProjectScanner().scan(
            _project(missing), _scope("."), manifest_id="manifest_001"
        )

    file_root = tmp_path / "file.txt"
    file_root.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ProjectScanError, match="directory"):
        LocalProjectScanner().scan(
            _project(file_root), _scope("."), manifest_id="manifest_001"
        )

    root = tmp_path / "project"
    root.mkdir()
    wrong_scope = _scope(".").model_copy(update={"project_id": "project_002"})
    with pytest.raises(ProjectScanError, match="different project"):
        LocalProjectScanner().scan(
            _project(root), wrong_scope, manifest_id="manifest_001"
        )

    unsafe_scope = _scope(".").model_copy(update={"follow_symlinks": True})
    with pytest.raises(ProjectScanError, match="cannot follow"):
        LocalProjectScanner().scan(
            _project(root), unsafe_scope, manifest_id="manifest_001"
        )


def test_scanner_rejects_ambiguous_root_locator(tmp_path: Path) -> None:
    project = _project(tmp_path).model_copy(update={"root_locator": "relative/project"})
    with pytest.raises(ProjectScanError, match="absolute without traversal"):
        LocalProjectScanner().scan(project, _scope("."), manifest_id="manifest_001")

    traversal = _project(tmp_path).model_copy(
        update={"root_locator": str(tmp_path / "nested" / "..")}
    )
    with pytest.raises(ProjectScanError, match="absolute without traversal"):
        LocalProjectScanner().scan(traversal, _scope("."), manifest_id="manifest_001")


def test_scanner_rejects_browser_profile_root_before_stat(tmp_path: Path) -> None:
    root = tmp_path / "Chrome" / "User Data" / "Default"
    root.mkdir(parents=True)
    (root / "History").write_text("browser history", encoding="utf-8")
    scanner = LocalProjectScanner()
    stat_called = False

    def unexpected_stat(_path: Path, _message: str) -> os.stat_result:
        nonlocal stat_called
        stat_called = True
        raise AssertionError("hard-denied root must not be stat'ed")

    scanner._stat_no_follow = unexpected_stat  # type: ignore[method-assign]
    with pytest.raises(ProjectScanError, match="hard-denied"):
        scanner.scan(_project(root), _scope("."), manifest_id="manifest_001")
    assert not stat_called


def _make_symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")


def test_scanner_rejects_root_symlink(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    real_root.mkdir()
    (real_root / "safe.txt").write_text("safe", encoding="utf-8")
    linked_root = tmp_path / "linked"
    _make_symlink_or_skip(linked_root, real_root, target_is_directory=True)

    with pytest.raises(ProjectScanError, match="links and reparse"):
        LocalProjectScanner().scan(
            _project(linked_root), _scope("."), manifest_id="manifest_001"
        )


def test_scanner_rejects_nested_symlink(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    _make_symlink_or_skip(root / "linked.txt", outside, target_is_directory=False)

    with pytest.raises(ProjectScanError, match="links and reparse"):
        LocalProjectScanner().scan(
            _project(root), _scope("."), manifest_id="manifest_001"
        )


def test_windows_reparse_attribute_detection_is_testable(monkeypatch: pytest.MonkeyPatch) -> None:
    flag = 0x400
    monkeypatch.setattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", flag, raising=False)

    assert has_reparse_attribute(SimpleNamespace(st_file_attributes=flag))  # type: ignore[arg-type]
    assert not has_reparse_attribute(SimpleNamespace(st_file_attributes=0))  # type: ignore[arg-type]


def test_scanner_rejects_simulated_reparse_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    with pytest.raises(ProjectScanError, match="links and reparse"):
        LocalProjectScanner(reparse_detector=lambda _file_stat: True).scan(
            _project(root), _scope("."), manifest_id="manifest_001"
        )


def test_scanner_rejects_simulated_nested_reparse(tmp_path: Path) -> None:
    root = tmp_path / "project"
    nested = root / "src"
    nested.mkdir(parents=True)
    (nested / "safe.py").write_text("safe", encoding="utf-8")
    nested_inode = nested.stat(follow_symlinks=False).st_ino

    with pytest.raises(ProjectScanError, match="links and reparse"):
        LocalProjectScanner(
            reparse_detector=lambda file_stat: file_stat.st_ino == nested_inode
        ).scan(_project(root), _scope("."), manifest_id="manifest_001")


def test_scanner_rejects_resolved_path_outside_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    candidate = root / "escape.txt"
    candidate.write_text("safe before simulated race", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    original_resolve = Path.resolve

    def redirected_resolve(path: Path, strict: bool = False) -> Path:
        if path.name == "escape.txt":
            return outside
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", redirected_resolve)
    with pytest.raises(ProjectScanError, match="escapes"):
        LocalProjectScanner().scan(
            _project(root), _scope("."), manifest_id="manifest_001"
        )
