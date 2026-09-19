import hashlib
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from career_harness.core.project import (
    Project,
    ProjectScanScope,
    ProjectSourceEntry,
)
from career_harness.services.project_scanner import (
    LocalProjectScanner,
    ProjectScanError,
    _windows_path_is_within,
    _WindowsAnchoredReader,
    has_reparse_attribute,
)

WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt", reason="Windows handle seam")


def _project(root: Path | str, *, revision: int = 1) -> Project:
    return Project(
        project_id="project_001",
        revision=revision,
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


class _StubRepository:
    def __init__(self, project: Project, scope: ProjectScanScope) -> None:
        self.project = project
        self.scope = scope
        self.calls: list[tuple[str, str, int, int | None]] = []

    def get_scan_inputs(
        self,
        project_id: str,
        scope_id: str,
        scope_revision: int,
        *,
        project_revision: int | None = None,
    ) -> tuple[Project, ProjectScanScope] | None:
        self.calls.append((project_id, scope_id, scope_revision, project_revision))
        if (
            project_id != self.project.project_id
            or scope_id != self.scope.scope_id
            or scope_revision != self.scope.revision
            or project_revision not in {None, self.project.revision}
        ):
            return None
        return self.project, self.scope


class _RecordingReader:
    def __init__(self, entries: list[ProjectSourceEntry] | None = None) -> None:
        self.entries = entries or []
        self.calls: list[tuple[Path, ProjectScanScope]] = []

    def scan(self, root: Path, scope: ProjectScanScope) -> list[ProjectSourceEntry]:
        self.calls.append((root, scope))
        return list(self.entries)


def _scanner(
    root: Path | str,
    scope: ProjectScanScope,
    *,
    anchored_reader: object | None = None,
    project_revision: int = 1,
) -> tuple[LocalProjectScanner, _StubRepository]:
    repository = _StubRepository(_project(root, revision=project_revision), scope)
    scanner = LocalProjectScanner(  # type: ignore[arg-type]
        repository,
        anchored_reader=anchored_reader,  # type: ignore[arg-type]
    )
    return scanner, repository


def _scan(
    scanner: LocalProjectScanner,
    *,
    generated_at: datetime | None = None,
    project_revision: int | None = None,
):
    return scanner.scan(
        "project_001",
        "scope_001",
        3,
        manifest_id="manifest_001",
        generated_at=generated_at,
        project_revision=project_revision,
    )


def test_scanner_reads_canonical_scope_deterministically(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src" / "nested").mkdir(parents=True)
    (root / "src" / "z.py").write_bytes(b"print('z')\n")
    (root / "src" / "nested" / "A.py").write_bytes(b"print('a')\n")
    (root / "README.md").write_bytes(b"read me")
    (root / "outside.txt").write_bytes(b"outside")
    generated_at = datetime(2026, 9, 19, tzinfo=UTC)
    scanner, repository = _scanner(root, _scope("src", "README.md"))

    first = _scan(scanner, generated_at=generated_at, project_revision=1)
    second = _scan(scanner, generated_at=generated_at, project_revision=1)

    assert first == second
    assert repository.calls == [
        ("project_001", "scope_001", 3, 1),
        ("project_001", "scope_001", 3, 1),
    ]
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


def test_forged_scope_object_cannot_enter_scanner(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "safe.txt").write_text("safe", encoding="utf-8")
    (root / "forged-sentinel.txt").write_text("must not be scanned", encoding="utf-8")
    canonical_scope = _scope("safe.txt")
    forged_scope = canonical_scope.model_copy(update={"allowed_paths": (".",)})
    scanner, _repository = _scanner(root, canonical_scope)

    manifest = _scan(scanner)

    assert tuple(entry.relative_path for entry in manifest.entries) == ("safe.txt",)
    with pytest.raises(ProjectScanError, match="canonical ID"):
        scanner.scan(  # type: ignore[arg-type]
            _project(root),
            forged_scope,
            3,
            manifest_id="manifest_forged",
        )


@WINDOWS_ONLY
def test_scanner_applies_deny_and_hard_deny_before_handle_open(tmp_path: Path) -> None:
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
    }
    for relative_path, content in paths.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    opened: list[str] = []

    def tracking_reparse(path: Path, _information: object) -> bool:
        opened.append(path.relative_to(root).as_posix() if path != root else ".")
        return False

    reader = _WindowsAnchoredReader(reparse_detector=tracking_reparse)  # type: ignore[arg-type]
    scanner, _repository = _scanner(
        root,
        _scope(".", denied=("src/denied",)),
        anchored_reader=reader,
    )
    manifest = _scan(scanner)

    assert tuple(entry.relative_path for entry in manifest.entries) == ("src/keep.py",)
    assert not any(
        path == blocked or path.startswith(f"{blocked}/")
        for path in opened
        for blocked in (".env", "src/denied", "secrets", "sessions", "browser", "profile", "Chrome")
    )
    serialized = manifest.model_dump_json()
    assert all(content.decode() not in serialized for content in paths.values())


def test_scanner_descends_to_a_nested_explicit_allow(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src" / "nested").mkdir(parents=True)
    (root / "src" / "nested" / "allowed.py").write_text("allowed", encoding="utf-8")
    (root / "src" / "outside.py").write_text("outside", encoding="utf-8")
    scanner, _repository = _scanner(root, _scope("src/nested/allowed.py"))

    manifest = _scan(scanner)

    assert tuple(entry.relative_path for entry in manifest.entries) == (
        "src/nested/allowed.py",
    )


@pytest.mark.parametrize("invalid_path", ["../outside", "C:/outside", "/outside"])
def test_scanner_scope_rejects_traversal_and_absolute_paths(invalid_path: str) -> None:
    with pytest.raises(ValueError):
        _scope(invalid_path)


def test_scanner_requires_canonical_exact_inputs(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    scanner, _repository = _scanner(root, _scope("."))

    with pytest.raises(ProjectScanError, match="not found"):
        scanner.scan("missing", "scope_001", 3, manifest_id="manifest_001")
    with pytest.raises(ProjectScanError, match="exact and positive"):
        scanner.scan("project_001", "scope_001", 0, manifest_id="manifest_001")
    with pytest.raises(ProjectScanError, match="exact and positive"):
        scanner.scan(  # type: ignore[arg-type]
            "project_001", "scope_001", "3", manifest_id="manifest_001"
        )
    with pytest.raises(ProjectScanError, match="not found"):
        _scan(scanner, project_revision=2)


def test_scanner_rejects_file_root_and_unsafe_scope(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    scanner, _repository = _scanner(missing_root, _scope("."))
    with pytest.raises(ProjectScanError, match="opened"):
        _scan(scanner)

    file_root = tmp_path / "file.txt"
    file_root.write_text("not a directory", encoding="utf-8")
    scanner, _repository = _scanner(file_root, _scope("."))
    with pytest.raises(ProjectScanError, match="directory"):
        _scan(scanner)

    root = tmp_path / "project"
    root.mkdir()
    unsafe_scope = _scope(".").model_copy(update={"follow_symlinks": True})
    scanner, _repository = _scanner(root, unsafe_scope)
    with pytest.raises(ProjectScanError, match="cannot follow"):
        _scan(scanner)


@pytest.mark.parametrize(
    ("root_locator", "message"),
    [
        ("relative/project", "absolute without traversal"),
        (r"\\server\share\project", "UNC"),
        (r"\\?\C:\project", "device namespace"),
        (r"\\.\C:\project", "device namespace"),
    ],
)
def test_scanner_rejects_ambiguous_or_remote_namespace_before_reader(
    root_locator: str, message: str
) -> None:
    reader = _RecordingReader()
    scanner, _repository = _scanner(root_locator, _scope("."), anchored_reader=reader)

    with pytest.raises(ProjectScanError, match=message):
        _scan(scanner)
    assert reader.calls == []


def test_scanner_rejects_traversal_and_browser_root_before_reader(tmp_path: Path) -> None:
    reader = _RecordingReader()
    traversal = str(tmp_path / "nested" / "..")
    scanner, _repository = _scanner(traversal, _scope("."), anchored_reader=reader)
    with pytest.raises(ProjectScanError, match="absolute without traversal"):
        _scan(scanner)
    assert reader.calls == []

    browser_root = tmp_path / "Chrome" / "User Data" / "Default"
    scanner, _repository = _scanner(browser_root, _scope("."), anchored_reader=reader)
    with pytest.raises(ProjectScanError, match="hard-denied"):
        _scan(scanner)
    assert reader.calls == []


@WINDOWS_ONLY
@pytest.mark.parametrize("drive_type", [0, 2, 4])
def test_windows_non_fixed_drive_is_rejected_before_filesystem_open(
    tmp_path: Path, drive_type: int
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    enumerated = False

    def fail_if_enumerated(_path: Path):
        nonlocal enumerated
        enumerated = True
        return ()

    reader = _WindowsAnchoredReader(
        name_lister=fail_if_enumerated,
        drive_type_getter=lambda _anchor: drive_type,
    )
    opened = False

    def fail_if_opened(_path: Path) -> object:
        nonlocal opened
        opened = True
        raise AssertionError("network drive must be rejected before CreateFileW")

    reader._open_handle = fail_if_opened  # type: ignore[method-assign]
    scanner, _repository = _scanner(root, _scope("."), anchored_reader=reader)
    with pytest.raises(ProjectScanError, match="fixed local drive"):
        _scan(scanner)
    assert not enumerated
    assert not opened


@WINDOWS_ONLY
def test_windows_fixed_drive_is_scanned(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "safe.txt").write_text("safe", encoding="utf-8")
    reader = _WindowsAnchoredReader(
        drive_type_getter=lambda _anchor: _WindowsAnchoredReader._DRIVE_FIXED
    )
    scanner, _repository = _scanner(root, _scope("."), anchored_reader=reader)

    manifest = _scan(scanner)

    assert tuple(entry.relative_path for entry in manifest.entries) == ("safe.txt",)


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
    scanner, _repository = _scanner(linked_root, _scope("."))

    with pytest.raises(ProjectScanError, match="links and reparse"):
        _scan(scanner)


def test_scanner_rejects_nested_symlink(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    _make_symlink_or_skip(root / "linked.txt", outside, target_is_directory=False)
    scanner, _repository = _scanner(root, _scope("."))

    with pytest.raises(ProjectScanError, match="links and reparse"):
        _scan(scanner)


def test_windows_reparse_attribute_detection_is_testable(monkeypatch: pytest.MonkeyPatch) -> None:
    flag = 0x400
    monkeypatch.setattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", flag, raising=False)

    assert has_reparse_attribute(SimpleNamespace(st_file_attributes=flag))  # type: ignore[arg-type]
    assert not has_reparse_attribute(SimpleNamespace(st_file_attributes=0))  # type: ignore[arg-type]


@WINDOWS_ONLY
def test_scanner_rejects_simulated_root_and_nested_reparse(tmp_path: Path) -> None:
    root = tmp_path / "project"
    nested = root / "src"
    nested.mkdir(parents=True)
    (nested / "safe.py").write_text("safe", encoding="utf-8")

    root_reader = _WindowsAnchoredReader(reparse_detector=lambda _path, _info: True)
    scanner, _repository = _scanner(root, _scope("."), anchored_reader=root_reader)
    with pytest.raises(ProjectScanError, match="links and reparse"):
        _scan(scanner)

    nested_reader = _WindowsAnchoredReader(
        reparse_detector=lambda path, _info: path.name == "src"
    )
    scanner, _repository = _scanner(root, _scope("."), anchored_reader=nested_reader)
    with pytest.raises(ProjectScanError, match="links and reparse"):
        _scan(scanner)


@WINDOWS_ONLY
def test_enumeration_to_open_replacement_is_rechecked_before_read(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    candidate = root / "safe.txt"
    candidate.write_text("safe", encoding="utf-8")
    enumeration_completed = False

    def swapping_lister(path: Path) -> tuple[str, ...]:
        nonlocal enumeration_completed
        with os.scandir(path) as entries:
            names = tuple(entry.name for entry in entries)
        enumeration_completed = True
        return names

    def detect_post_enumeration_reparse(path: Path, _information: object) -> bool:
        return enumeration_completed and path == candidate

    reader = _WindowsAnchoredReader(  # type: ignore[arg-type]
        name_lister=swapping_lister,
        reparse_detector=detect_post_enumeration_reparse,
    )
    read_called = False

    def unexpected_read(*_args: object) -> ProjectSourceEntry:
        nonlocal read_called
        read_called = True
        raise AssertionError("a simulated replacement must be rejected before read")

    reader._read_file = unexpected_read  # type: ignore[method-assign]
    scanner, _repository = _scanner(root, _scope("."), anchored_reader=reader)

    with pytest.raises(ProjectScanError, match="links and reparse"):
        _scan(scanner)
    assert not read_called


@WINDOWS_ONLY
def test_handle_final_path_escape_is_rejected_before_read(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "safe.txt").write_text("safe", encoding="utf-8")
    reader = _WindowsAnchoredReader()
    final_paths = iter((str(root), str(tmp_path / "outside.txt")))
    read_called = False

    def simulated_final_path(_handle: int) -> str:
        return next(final_paths)

    def unexpected_read(*_args: object) -> ProjectSourceEntry:
        nonlocal read_called
        read_called = True
        raise AssertionError("an escaped final path must be rejected before read")

    reader._get_final_path = simulated_final_path  # type: ignore[method-assign]
    reader._read_file = unexpected_read  # type: ignore[method-assign]
    scanner, _repository = _scanner(root, _scope("."), anchored_reader=reader)

    with pytest.raises(ProjectScanError, match="escapes"):
        _scan(scanner)
    assert not read_called
    assert not _windows_path_is_within(r"C:\outside\file.py", r"C:\project")
