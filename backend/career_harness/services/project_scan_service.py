from __future__ import annotations

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel, OpaqueId
from career_harness.core.project import ProjectSourceManifest
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.project_repository import ProjectRepository
from career_harness.db.project_scan_writes import (
    ProjectEvidenceStaleWrite,
    ProjectRescanWrite,
)
from career_harness.services.command_service import CommandService
from career_harness.services.project_scanner import LocalProjectScanner


class RescanDiff(FrozenModel):
    """Auditable added/changed/removed record of one rescan; never a mutation."""

    added: tuple[str, ...]
    changed: tuple[str, ...]
    removed: tuple[str, ...]


class RescanCommit(FrozenModel):
    manifest: ProjectSourceManifest
    diff: RescanDiff
    commit: CommandCommitResult


class StaleMarkCommit(FrozenModel):
    evidence_id: OpaqueId
    commit: CommandCommitResult


class ProjectScanService:
    """Incremental rescan and explicit evidence staleness commands.

    A rescan records a new immutable manifest plus an auditable diff; it never
    rewrites accepted evidence. Staleness transitions are explicit commands that
    append a new revision and never rewrite evidence content.
    """

    def __init__(
        self,
        commands: CommandService,
        repository: ProjectRepository,
        *,
        scanner: LocalProjectScanner | None = None,
    ) -> None:
        self.commands = commands
        self.repository = repository
        self.scanner = scanner or LocalProjectScanner(repository)

    def rescan(
        self,
        command: Command,
        *,
        project_id: OpaqueId,
        scope_id: OpaqueId,
        scope_revision: int,
        manifest_id: OpaqueId,
    ) -> RescanCommit:
        """Scan within an exact scope revision and record the manifest plus diff."""
        if command.target.kind is not EntityKind.PROJECT_SOURCE_MANIFEST:
            raise ValueError("command requires a project_source_manifest target")
        if command.target.entity_id != manifest_id:
            raise ValueError("command target must be the new manifest")
        if command.expected_revision != 0:
            raise ValueError("a new manifest requires expected revision zero")
        manifest = self.scanner.scan(
            project_id,
            scope_id,
            scope_revision,
            manifest_id=manifest_id,
        )
        history = self.repository.list_manifests_for_project(project_id)
        previous = history[-1] if history else None
        diff = _diff_manifests(previous, manifest)
        next_state = {
            "manifest_id": manifest.manifest_id,
            "project_id": project_id,
            "scan_scope_id": manifest.scan_scope_id,
            "scan_scope_revision": manifest.scan_scope_revision,
            "entry_count": len(manifest.entries),
        }
        commit = self.commands.commit(
            command,
            next_state,
            event_type="project.rescanned",
            event_payload=dict(next_state),
            transactional_write=ProjectRescanWrite(
                manifest,
                project_id=project_id,
                previous_manifest_id=previous.manifest_id if previous else None,
            ),
        )
        persisted = self.repository.get_source_manifest(manifest_id)
        if persisted is None:
            raise RuntimeError("rescan commit did not persist the manifest")
        return RescanCommit(manifest=persisted, diff=diff, commit=commit)

    def mark_stale_evidence(
        self,
        command: Command,
        *,
        evidence_id: OpaqueId,
        reason: str,
    ) -> StaleMarkCommit:
        """Append a STALE revision of CURRENT evidence; content is never rewritten."""
        if command.target.kind is not EntityKind.PROJECT_EVIDENCE:
            raise ValueError("command requires a project_evidence target")
        if command.target.entity_id != evidence_id:
            raise ValueError("command target must be the marked evidence")
        current = self.repository.get_evidence(evidence_id)
        if current is None:
            raise ValueError("staleness transition requires existing Project Evidence")
        commit = self.commands.commit(
            command,
            {
                "evidence_id": evidence_id,
                "revision": command.expected_revision + 1,
                "freshness": "stale",
            },
            event_type="project_evidence.marked_stale",
            event_payload={
                "evidence_id": evidence_id,
                "from_revision": command.expected_revision,
                "to_revision": command.expected_revision + 1,
                "reason": reason,
            },
            transactional_write=ProjectEvidenceStaleWrite(
                evidence_id=evidence_id, reason=reason, actor=command.actor
            ),
        )
        persisted = self.repository.get_evidence(evidence_id)
        if persisted is None or persisted.freshness.value != "stale":
            raise RuntimeError("staleness transition did not persist the new revision")
        return StaleMarkCommit(evidence_id=evidence_id, commit=commit)


def _diff_manifests(
    previous: ProjectSourceManifest | None,
    current: ProjectSourceManifest,
) -> RescanDiff:
    before = (
        {entry.relative_path: (entry.sha256, entry.byte_length) for entry in previous.entries}
        if previous
        else {}
    )
    after = {entry.relative_path: (entry.sha256, entry.byte_length) for entry in current.entries}
    added = tuple(sorted(path for path in after if path not in before))
    removed = tuple(sorted(path for path in before if path not in after))
    changed = tuple(
        sorted(path for path in after if path in before and after[path] != before[path])
    )
    return RescanDiff(added=added, changed=changed, removed=removed)
