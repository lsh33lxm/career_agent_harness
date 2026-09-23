import pytest
from pydantic import ValidationError

from career_harness.core.project import (
    ProjectPathError,
    ProjectScanScope,
    ProjectScopeViolation,
)


def make_scope() -> ProjectScanScope:
    return ProjectScanScope(
        scope_id="scope_001",
        project_id="project_001",
        allowed_paths=("src", "docs", "README.md"),
        denied_paths=("src/secrets", "docs/private.md"),
        created_by="user",
    )


def test_scan_scope_is_explicit_and_deny_wins() -> None:
    scope = make_scope()

    assert scope.permits("src/service.py") is True
    assert scope.permits("src/secrets/token.txt") is False
    assert scope.permits("SRC/SECRETS/token.txt") is False
    assert scope.permits("docs/private.md") is False
    assert scope.permits("README.md") is True


def test_scan_scope_rejects_paths_not_explicitly_allowed() -> None:
    scope = make_scope()

    assert scope.permits("tests/test_service.py") is False
    with pytest.raises(ProjectScopeViolation, match="not allowed"):
        scope.require_permitted("tests/test_service.py")


@pytest.mark.parametrize(
    "path",
    (
        "/etc/passwd",
        "C:/Users/example/.env",
        "C:\\Users\\example\\.env",
        "../outside.txt",
        "src/../../outside.txt",
    ),
)
def test_scan_scope_rejects_absolute_paths_and_traversal(path: str) -> None:
    with pytest.raises((ProjectPathError, ValidationError)):
        ProjectScanScope(
            scope_id="scope_001",
            project_id="project_001",
            allowed_paths=(path,),
            created_by="user",
        )

    with pytest.raises(ProjectPathError):
        make_scope().permits(path)


def test_scan_scope_normalizes_relative_windows_separators() -> None:
    scope = ProjectScanScope(
        scope_id="scope_001",
        project_id="project_001",
        allowed_paths=("src\\package",),
        created_by="user",
    )

    assert scope.allowed_paths == ("src/package",)
    assert scope.require_permitted("src\\package\\module.py") == "src/package/module.py"


def test_scan_scope_cannot_enable_symlink_traversal() -> None:
    with pytest.raises(ValidationError):
        ProjectScanScope(
            scope_id="scope_001",
            project_id="project_001",
            allowed_paths=("src",),
            follow_symlinks=True,
            created_by="user",
        )
