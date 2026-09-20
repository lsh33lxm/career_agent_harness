import hashlib
import json
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from career_harness.core.project import (
    Project,
    ProjectEnhancementTask,
    ProjectScanScope,
    ProjectSourceEntry,
    ProjectSourceManifest,
)
from career_harness.core.project.l2 import (
    AnalysisRequest,
    ContextFile,
    PreparationError,
    UnsupportedProviderError,
)
from career_harness.db.project_repository import ProjectRepository
from career_harness.services.l2_preparation_service import L2PreparationService

SECRET = "private-source-sentinel"
NOW = datetime(2026, 9, 20, tzinfo=UTC)


def request_data():
    return {
        "task": {"entity_id": "task_001", "revision": 1},
        "project": {"entity_id": "project_001", "revision": 1},
        "scope": {"entity_id": "scope_001", "revision": 1},
        "manifest_id": "manifest_001",
        "provider": "claude",
        "model": "sonnet",
        "max_budget_usd": "1.25",
        "timeout_seconds": 60,
        "files": [{"relative_path": "src/a.py", "content": SECRET}],
    }


def inputs():
    request = AnalysisRequest.model_validate(request_data())
    project = Project(
        project_id="project_001",
        display_name="Test",
        root_locator="Z:/private-root",
        created_at=NOW,
        created_by="user",
    )
    scope = ProjectScanScope(
        scope_id="scope_001",
        project_id="project_001",
        allowed_paths=("src",),
        denied_paths=("src/private",),
        created_at=NOW,
        created_by="user",
    )
    task = ProjectEnhancementTask(
        task_id="task_001",
        project_id="project_001",
        target_gap_id="gap_001",
        target_capability_id="capability_001",
        learning_plan=("Learn",),
        files_to_review=("src/a.py",),
        change_plan=("Propose",),
        experiment_plan=("Try",),
        validation_plan=("Review",),
        expected_evidence=("Candidate",),
        status="ready",
        created_at=NOW,
        created_by="user",
    )
    manifest = ProjectSourceManifest(
        manifest_id="manifest_001",
        scan_scope_id="scope_001",
        scan_scope_revision=1,
        generated_at=NOW,
        entries=(
            ProjectSourceEntry(
                relative_path="src/a.py",
                sha256=hashlib.sha256(SECRET.encode()).hexdigest(),
                byte_length=len(SECRET.encode()),
            ),
            ProjectSourceEntry(
                relative_path="src/b.py", sha256=hashlib.sha256(b"b").hexdigest(), byte_length=1
            ),
        ),
    )
    repository = Mock(spec=ProjectRepository)
    repository.get_project.return_value = project
    repository.get_scan_scope.return_value = scope
    repository.get_enhancement_task.return_value = task
    repository.get_source_manifest.return_value = manifest
    return request, repository


def test_preview_is_private_deterministic_and_not_consent():
    request, repo = inputs()
    preview = L2PreparationService(repo).prepare(request)
    assert preview == L2PreparationService(repo).prepare(request)
    assert preview.argv == (
        "--print",
        "--safe-mode",
        "--tools",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--no-chrome",
        "--input-format",
        "text",
        "--output-format",
        "json",
        "--model",
        "sonnet",
        "--max-budget-usd",
        "1.25",
    )
    assert SECRET in preview.stdin
    assert SECRET not in repr(preview) and SECRET not in repr(request)
    assert SECRET not in repr(request.files[0]) and SECRET not in str(preview.argv)
    assert "private-root" not in preview.stdin
    assert "root_locator" not in preview.stdin
    assert not preview.permissions.execution_authorized
    assert not preview.permissions.process_egress_isolated
    assert not preview.permissions.runtime_zero_host_writes_guaranteed
    assert preview.permissions.output_authority == "unreviewed_proposal"
    repo.get_project.assert_called_with("project_001", 1)
    repo.get_scan_scope.assert_called_with("scope_001", 1)
    repo.get_enhancement_task.assert_called_with("task_001", 1)
    repo.get_source_manifest.assert_called_with("manifest_001")


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "--dangerously-skip-permissions"),
        ("model", "x --flag"),
        ("model", "x\nflag"),
        ("model", "x" * 129),
        ("max_budget_usd", "0"),
        ("max_budget_usd", "NaN"),
        ("max_budget_usd", "101"),
        ("timeout_seconds", 0),
        ("timeout_seconds", 3601),
        ("max_output_bytes", 262145),
        ("files", []),
    ],
)
def test_request_bounds_and_cli_injection_rejected_without_content(field, value):
    data = request_data()
    data[field] = value
    with pytest.raises(ValidationError) as error:
        AnalysisRequest.model_validate(data)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("path", ["../a", "C:/a", "/a", "a\x00b", ".", "src/a:secret", "src/\na"])
def test_hostile_file_paths_are_rejected(path):
    with pytest.raises(ValidationError) as error:
        ContextFile(relative_path=path, content=SECRET)
    assert SECRET not in str(error.value)


def test_utf8_bytes_and_aggregate_limits_and_duplicates():
    for content in ("中" * 22000, "\ud800"):
        with pytest.raises(ValidationError):
            ContextFile(relative_path="src/a.py", content=content)
    for files in (
        [{"relative_path": "src/a.py", "content": SECRET}] * 2,
        [{"relative_path": path, "content": SECRET} for path in ("src/a.py", "SRC/A.py")],
        [{"relative_path": f"src/{i}.py", "content": "a" * 65536} for i in range(5)],
        [{"relative_path": f"src/{i}.py", "content": "a"} for i in range(33)],
    ):
        with pytest.raises(ValidationError) as error:
            AnalysisRequest.model_validate({**request_data(), "files": files})
        assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "method", ["get_project", "get_scan_scope", "get_enhancement_task", "get_source_manifest"]
)
def test_missing_exact_inputs_fail(method):
    request, repo = inputs()
    getattr(repo, method).return_value = None
    with pytest.raises(PreparationError):
        L2PreparationService(repo).prepare(request)


@pytest.mark.parametrize(
    "method,field,value",
    [
        ("get_project", "project_id", "project_other"),
        ("get_project", "revision", 2),
        ("get_scan_scope", "scope_id", "scope_other"),
        ("get_scan_scope", "revision", 2),
        ("get_scan_scope", "project_id", "project_other"),
        ("get_enhancement_task", "task_id", "task_other"),
        ("get_enhancement_task", "revision", 2),
        ("get_enhancement_task", "project_id", "project_other"),
        ("get_source_manifest", "manifest_id", "manifest_other"),
        ("get_source_manifest", "scan_scope_id", "scope_other"),
        ("get_source_manifest", "scan_scope_revision", 2),
    ],
)
def test_exact_identity_and_cross_links_fail(method, field, value):
    request, repo = inputs()
    original = getattr(repo, method).return_value
    getattr(repo, method).return_value = original.model_copy(update={field: value})
    with pytest.raises(PreparationError):
        L2PreparationService(repo).prepare(request)


@pytest.mark.parametrize(
    "status", ["proposed", "awaiting_validation", "completed", "cancelled", "in_progress"]
)
def test_task_lifecycle(status):
    request, repo = inputs()
    original = repo.get_enhancement_task.return_value
    repo.get_enhancement_task.return_value = ProjectEnhancementTask.model_validate(
        {**original.model_dump(), "status": status}
    )
    if status == "in_progress":
        assert L2PreparationService(repo).prepare(request)
    else:
        with pytest.raises(PreparationError):
            L2PreparationService(repo).prepare(request)


@pytest.mark.parametrize(
    "path",
    [
        "src/private/a.py",
        "outside.py",
        "src/.env",
        "src/.env.local",
        "src/secrets/key",
        "src/sessions/a",
        "src/credentials.json",
        "src/browser/a",
    ],
)
def test_scope_and_scanner_secret_exclusions(path):
    request, repo = inputs()
    request = AnalysisRequest.model_validate(
        {**request_data(), "files": [{"relative_path": path, "content": SECRET}]}
    )
    manifest = repo.get_source_manifest.return_value
    repo.get_source_manifest.return_value = manifest.model_copy(
        update={"entries": (manifest.entries[0].model_copy(update={"relative_path": path}),)}
    )
    with pytest.raises(PreparationError) as error:
        L2PreparationService(repo).prepare(request)
    assert SECRET not in str(error.value) and path not in str(error.value)


@pytest.mark.parametrize("fault", ["hash", "length", "missing_path", "case_collision"])
def test_exact_manifest_bytes_and_case_collisions(fault):
    request, repo = inputs()
    manifest = repo.get_source_manifest.return_value
    entry = manifest.entries[0]
    updates = {
        "hash": {"sha256": "a" * 64},
        "length": {"byte_length": 999},
        "missing_path": {"relative_path": "src/other.py"},
    }
    entries = (
        (entry, entry.model_copy(update={"relative_path": "SRC/A.py"}))
        if fault == "case_collision"
        else (entry.model_copy(update=updates[fault]),)
    )
    repo.get_source_manifest.return_value = manifest.model_copy(update={"entries": entries})
    with pytest.raises(PreparationError):
        L2PreparationService(repo).prepare(request)


def test_codex_is_typed_unsupported_and_does_not_read_repository():
    request, repo = inputs()
    request = AnalysisRequest.model_validate({**request_data(), "provider": "codex"})
    with pytest.raises(UnsupportedProviderError):
        L2PreparationService(repo).prepare(request)
    assert repo.mock_calls == []


def test_manifest_order_and_file_order_are_irrelevant():
    request, repo = inputs()
    data = request_data()
    data["files"].append({"relative_path": "src/b.py", "content": "b"})
    first = L2PreparationService(repo).prepare(AnalysisRequest.model_validate(data))
    manifest = repo.get_source_manifest.return_value
    repo.get_source_manifest.return_value = manifest.model_copy(
        update={"entries": tuple(reversed(manifest.entries))}
    )
    data["files"].reverse()
    assert L2PreparationService(repo).prepare(AnalysisRequest.model_validate(data)) == first


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "opus"),
        ("max_budget_usd", "2"),
        ("timeout_seconds", 90),
        ("max_output_bytes", 100),
    ],
)
def test_limits_and_model_change_digest(field, value):
    request, repo = inputs()
    first = L2PreparationService(repo).prepare(request)
    changed = AnalysisRequest.model_validate({**request_data(), field: value})
    assert L2PreparationService(repo).prepare(changed).request_digest != first.request_digest


def test_task_and_verified_content_change_digest():
    request, repo = inputs()
    service = L2PreparationService(repo)
    first = service.prepare(request)
    task = repo.get_enhancement_task.return_value
    for field in (
        "learning_plan",
        "change_plan",
        "experiment_plan",
        "validation_plan",
        "expected_evidence",
    ):
        repo.get_enhancement_task.return_value = task.model_copy(update={field: ("changed",)})
        assert service.prepare(request).request_digest != first.request_digest
    repo.get_enhancement_task.return_value = task
    changed = AnalysisRequest.model_validate(
        {**request_data(), "files": [{"relative_path": "src/b.py", "content": "b"}]}
    )
    other = service.prepare(changed)
    assert other.request_digest != first.request_digest
    assert other.context_digest != first.context_digest
    assert json.loads(other.stdin)["files"][0]["content"] == "b"


def test_repository_validation_error_is_sanitized():
    request, repo = inputs()
    repo.get_project.side_effect = ValueError(SECRET)
    with pytest.raises(PreparationError) as error:
        L2PreparationService(repo).prepare(request)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "field,method,id_field",
    [
        ("task", "get_enhancement_task", "task_id"),
        ("project", "get_project", "project_id"),
        ("scope", "get_scan_scope", "scope_id"),
    ],
)
def test_exact_revisions_change_digest(field, method, id_field):
    request, repo = inputs()
    first = L2PreparationService(repo).prepare(request)
    data = request_data()
    data[field]["revision"] = 2
    original = getattr(repo, method).return_value
    getattr(repo, method).return_value = original.model_copy(update={"revision": 2})
    if field == "scope":
        manifest = repo.get_source_manifest.return_value
        repo.get_source_manifest.return_value = manifest.model_copy(
            update={"scan_scope_revision": 2}
        )
    assert (
        L2PreparationService(repo).prepare(AnalysisRequest.model_validate(data)).request_digest
        != first.request_digest
    )


def test_manifest_identity_and_scope_boundaries_change_digest():
    request, repo = inputs()
    first = L2PreparationService(repo).prepare(request)
    manifest = repo.get_source_manifest.return_value
    repo.get_source_manifest.return_value = manifest.model_copy(
        update={"manifest_id": "manifest_new"}
    )
    changed = AnalysisRequest.model_validate({**request_data(), "manifest_id": "manifest_new"})
    assert L2PreparationService(repo).prepare(changed).request_digest != first.request_digest
    repo.get_source_manifest.return_value = manifest
    scope = repo.get_scan_scope.return_value
    repo.get_scan_scope.return_value = scope.model_copy(update={"denied_paths": ("src/other",)})
    assert L2PreparationService(repo).prepare(request).request_digest != first.request_digest


@pytest.mark.parametrize(
    "ref",
    [
        {"entity_id": "../invalid", "revision": 1},
        {"entity_id": "task_001", "revision": 0},
        {"entity_id": "task_001", "revision": True},
        {"entity_id": "task_001", "revision": "1"},
    ],
)
def test_hostile_exact_refs_hide_request_contents(ref):
    with pytest.raises(ValidationError) as error:
        AnalysisRequest.model_validate({**request_data(), "task": ref})
    assert SECRET not in str(error.value)


def test_nested_validation_and_oversized_prompt_hide_content():
    data = request_data()
    data["files"][0]["relative_path"] = "../outside"
    with pytest.raises(ValidationError) as error:
        AnalysisRequest.model_validate(data)
    assert SECRET not in str(error.value)
    request, repo = inputs()
    task = repo.get_enhancement_task.return_value
    repo.get_enhancement_task.return_value = task.model_copy(
        update={"learning_plan": (SECRET * 70,) * 400}
    )
    with pytest.raises(PreparationError) as error:
        L2PreparationService(repo).prepare(request)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "field",
    [
        "learning_plan",
        "files_to_review",
        "change_plan",
        "experiment_plan",
        "validation_plan",
        "expected_evidence",
    ],
)
@pytest.mark.parametrize("locator", ["Z:/private-root", "z:\\private-root", "Z:\\PRIVATE-ROOT"])
def test_task_locator_variants_are_rejected_without_leaking_locator(field, locator):
    request, repo = inputs()
    task = repo.get_enhancement_task.return_value
    repo.get_enhancement_task.return_value = task.model_copy(
        update={field: (f"review {locator} now",)}
    )
    with pytest.raises(PreparationError) as error:
        L2PreparationService(repo).prepare(request)
    assert "private-root" not in str(error.value).casefold()


def test_task_without_project_locator_still_prepares():
    request, repo = inputs()
    preview = L2PreparationService(repo).prepare(request)
    assert preview.permissions.execution_authorized is False
