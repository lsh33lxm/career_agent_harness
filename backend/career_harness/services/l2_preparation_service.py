"""Resolve exact canonical inputs; prepare an in-memory, non-authorizing preview."""

import hashlib
from pathlib import PureWindowsPath

from career_harness.adapters.cli_analysis import canonical_json, digest, prepare_claude_invocation
from career_harness.core.project.l2 import (
    AnalysisProvider,
    AnalysisRequest,
    PreparationError,
    PreparedInvocation,
    UnsupportedProviderError,
)
from career_harness.core.project.models import ProjectEnhancementTaskStatus
from career_harness.db.project_repository import ProjectRepository
from career_harness.services.project_scanner import _is_hard_denied


class L2PreparationService:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def prepare(self, request: AnalysisRequest) -> PreparedInvocation:
        try:
            return self._prepare(request)
        except UnsupportedProviderError:
            raise
        except (ValueError, TypeError, RuntimeError):
            # Repository validation can contain canonical task text or filesystem locators.
            raise PreparationError("L2 preparation rejected invalid or mismatched inputs") from None

    def _prepare(self, request: AnalysisRequest) -> PreparedInvocation:
        if request.provider is not AnalysisProvider.CLAUDE:
            raise UnsupportedProviderError("provider does not support tools-disabled L2 analysis")
        task = self.repository.get_enhancement_task(request.task.entity_id, request.task.revision)
        project = self.repository.get_project(request.project.entity_id, request.project.revision)
        scope = self.repository.get_scan_scope(request.scope.entity_id, request.scope.revision)
        manifest = self.repository.get_source_manifest(request.manifest_id)
        if task is None or project is None or scope is None or manifest is None:
            raise PreparationError("missing exact canonical input")
        if (
            (task.task_id, task.revision) != (request.task.entity_id, request.task.revision)
            or (project.project_id, project.revision)
            != (request.project.entity_id, request.project.revision)
            or (scope.scope_id, scope.revision) != (request.scope.entity_id, request.scope.revision)
            or manifest.manifest_id != request.manifest_id
            or task.project_id != project.project_id
            or scope.project_id != project.project_id
            or (manifest.scan_scope_id, manifest.scan_scope_revision)
            != (scope.scope_id, scope.revision)
            or task.status
            not in {ProjectEnhancementTaskStatus.READY, ProjectEnhancementTaskStatus.IN_PROGRESS}
        ):
            raise PreparationError("canonical input identity or lifecycle mismatch")
        if _task_contains_root_locator(task, project.root_locator):
            raise PreparationError("L2 task content contains the canonical project locator")
        entries = {entry.relative_path: entry for entry in manifest.entries}
        if len({path.casefold() for path in entries}) != len(manifest.entries):
            raise PreparationError("manifest paths have case collisions")
        for file in request.files:
            scope.require_permitted(file.relative_path)
            if _is_hard_denied(file.relative_path):
                raise PreparationError("context contains a forbidden path")
            entry = entries.get(file.relative_path)
            content = file.content.encode("utf-8")
            if (
                entry is None
                or entry.byte_length != len(content)
                or entry.sha256 != hashlib.sha256(content).hexdigest()
            ):
                raise PreparationError("context does not match the exact source manifest")
        files = [
            file.model_dump() for file in sorted(request.files, key=lambda file: file.relative_path)
        ]
        # Serialize an allowlist, never project metadata, root_locator or environment.
        task_data = task.model_dump(
            mode="json",
            include={
                "task_id",
                "revision",
                "project_id",
                "target_gap_id",
                "target_capability_id",
                "learning_plan",
                "files_to_review",
                "change_plan",
                "experiment_plan",
                "validation_plan",
                "expected_evidence",
                "status",
            },
        )
        payload = {
            "instruction": (
                "Analyze supplied context only. Return an unreviewed plan or diff proposal; "
                "do not claim verified evidence or mastery."
            ),
            "task": task_data,
            "refs": {
                "project": request.project.model_dump(),
                "scope": request.scope.model_dump(),
                "manifest_id": manifest.manifest_id,
            },
            "scope": {"allowed_paths": scope.allowed_paths, "denied_paths": scope.denied_paths},
            "files": files,
        }
        return prepare_claude_invocation(
            request, prompt=canonical_json(payload), context_digest=digest(files)
        )


def _task_contains_root_locator(task: object, root_locator: str) -> bool:
    """Reject accidental project locator disclosure in task text only."""
    root = root_locator.strip().replace("\\", "/").casefold().rstrip("/")
    windows_root = str(PureWindowsPath(root_locator)).replace("\\", "/").casefold().rstrip("/")
    variants = {root, windows_root}
    fields = (
        "learning_plan",
        "files_to_review",
        "change_plan",
        "experiment_plan",
        "validation_plan",
        "expected_evidence",
    )
    for field in fields:
        for value in getattr(task, field, ()):
            normalized = value.replace("\\", "/").casefold()
            if any(variant and variant in normalized for variant in variants):
                return True
    return False
