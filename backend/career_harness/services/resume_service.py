from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, OpaqueId
from career_harness.core.job import JobRequirementStatus
from career_harness.core.lifecycle import ActorKind
from career_harness.core.resume import (
    ResumeBase,
    ResumePatch,
    ResumePatchAction,
    ResumePatchOperation,
    ResumePatchStatus,
    ResumeRevision,
    RevisionRef,
)
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.fact_repository import FactRepository
from career_harness.db.job_repository import JobRepository
from career_harness.db.resume_repository import ResumeRepository
from career_harness.db.resume_writes import ResumeBaseWrite, ResumePatchWrite, ResumeRevisionWrite
from career_harness.services.command_service import CommandService


def canonical_value_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _actor_kind(actor: str) -> ActorKind:
    if actor == ActorKind.USER.value:
        return ActorKind.USER
    if actor.startswith(f"{ActorKind.RULE.value}:"):
        return ActorKind.RULE
    return ActorKind.AGENT


class ResumeService:
    def __init__(self, commands: CommandService) -> None:
        self.commands = commands
        engine = commands.engine
        self.repository = ResumeRepository(engine)
        self.facts = FactRepository(engine)
        self.evidence = EvidenceRepository(engine)
        self.jobs = JobRepository(engine)

    def save_base_revision(
        self,
        command: Command,
        *,
        candidate_id: OpaqueId,
        sections: dict[str, Any],
    ) -> ResumeBase:
        self._require(command, EntityKind.RESUME, user=True)
        base = ResumeBase(
            resume_id=command.target.entity_id,
            candidate_id=candidate_id,
            revision=command.expected_revision + 1,
            sections=sections,
            created_at=command.issued_at,
            created_by=command.actor,
        )
        result = self.commands.commit(
            command,
            base.model_dump(mode="json", exclude={"created_at"}),
            event_type="resume_base.saved",
            event_payload={
                "resume_id": base.resume_id,
                "candidate_id": base.candidate_id,
                "base_revision": base.revision,
            },
            transactional_write=ResumeBaseWrite(base),
        )
        persisted = self.repository.get_base(base.resume_id, result.revision)
        if persisted is None:
            raise RuntimeError("ResumeBase commit did not persist the typed aggregate")
        return persisted

    def propose_patch(
        self,
        command: Command,
        *,
        resume_id: OpaqueId,
        base_revision: int,
        operations: tuple[ResumePatchOperation, ...],
        generator_run_id: OpaqueId | None = None,
    ) -> ResumePatch:
        self._require(command, EntityKind.RESUME_PATCH)
        if command.expected_revision != 0:
            raise ValueError("a ResumePatch proposal requires expected revision zero")
        if self.repository.get_base(resume_id, base_revision) is None:
            raise ValueError("ResumePatch requires an exact ResumeBase revision")
        self._validate_operations(operations)
        patch = ResumePatch(
            patch_id=command.target.entity_id,
            resume_id=resume_id,
            base_revision=base_revision,
            revision=1,
            operations=operations,
            generator_run_id=generator_run_id,
            proposed_by=command.actor,
            proposed_by_kind=_actor_kind(command.actor),
            proposed_at=command.issued_at,
        )
        return self._commit_patch(command, patch, "resume_patch.proposed")

    def review_patch(
        self,
        command: Command,
        *,
        decision: ResumePatchStatus,
        review_reason: str,
    ) -> ResumePatch:
        self._require(command, EntityKind.RESUME_PATCH, user=True)
        if decision not in {ResumePatchStatus.ACCEPTED, ResumePatchStatus.REJECTED}:
            raise ValueError("resume patch review must accept or reject")
        proposal = self.repository.get_patch(command.target.entity_id, command.expected_revision)
        if proposal is None or proposal.status is not ResumePatchStatus.PROPOSED:
            raise ValueError("review requires the exact proposed ResumePatch revision")
        if proposal.proposed_by_kind is ActorKind.AGENT and command.actor == proposal.proposed_by:
            raise ValueError("the proposer cannot review its own ResumePatch")
        patch = proposal.model_copy(
            update={
                "revision": command.expected_revision + 1,
                "status": decision,
                "reviewed_by": command.actor,
                "reviewed_by_kind": ActorKind.USER,
                "review_reason": review_reason,
                "reviewed_at": command.issued_at,
            }
        )
        return self._commit_patch(command, patch, "resume_patch.reviewed")

    def create_revision(
        self,
        command: Command,
        *,
        resume_id: OpaqueId,
        base_revision: int,
        accepted_patch_refs: tuple[RevisionRef, ...],
    ) -> ResumeRevision:
        self._require(command, EntityKind.RESUME_REVISION, user=True)
        if command.expected_revision != 0:
            raise ValueError("ResumeRevision creation requires expected revision zero")
        base = self.repository.get_base(resume_id, base_revision)
        if base is None:
            raise ValueError("ResumeRevision requires an exact ResumeBase revision")
        content = copy.deepcopy(base.sections)
        for ref in accepted_patch_refs:
            patch = self.repository.get_patch(ref.entity_id, ref.revision)
            if patch is None or patch.status is not ResumePatchStatus.ACCEPTED:
                raise ValueError("ResumeRevision requires exact accepted ResumePatch revisions")
            if (patch.resume_id, patch.base_revision) != (resume_id, base_revision):
                raise ValueError("every ResumePatch must target the selected ResumeBase revision")
            for operation in patch.operations:
                self._apply_operation(content, operation)
        revision = ResumeRevision(
            revision_id=command.target.entity_id,
            resume_id=resume_id,
            base_revision=base_revision,
            accepted_patch_refs=accepted_patch_refs,
            content=content,
            content_sha256=canonical_value_hash(content),
            created_at=command.issued_at,
            created_by=command.actor,
        )
        result = self.commands.commit(
            command,
            revision.model_dump(mode="json", exclude={"created_at"}),
            event_type="resume_revision.created",
            event_payload={
                "revision_id_ref": revision.revision_id,
                "resume_id": resume_id,
                "base_revision": base_revision,
                "patch_count": len(accepted_patch_refs),
                "content_sha256": revision.content_sha256,
            },
            transactional_write=ResumeRevisionWrite(revision),
        )
        persisted = self.repository.get_revision(revision.revision_id)
        if persisted is None or result.revision != 1:
            raise RuntimeError("ResumeRevision commit did not persist the typed aggregate")
        return persisted

    def _validate_operations(self, operations: tuple[ResumePatchOperation, ...]) -> None:
        for operation in operations:
            for ref in operation.fact_refs:
                fact = self.facts.get_fact(ref.entity_id, ref.revision)
                if fact is None:
                    raise ValueError("ResumePatch contains a dangling canonical Fact ref")
            for evidence_ref in operation.evidence_refs:
                if self.evidence.get(evidence_ref) is None:
                    raise ValueError("ResumePatch contains a dangling EvidenceRef")
            for ref in operation.requirement_refs:
                requirement = self.jobs.get_requirement(ref.entity_id, ref.revision)
                if requirement is None or requirement.status is not JobRequirementStatus.ACCEPTED:
                    raise ValueError("ResumePatch requires exact accepted JobRequirement refs")

    def _commit_patch(self, command: Command, patch: ResumePatch, event_type: str) -> ResumePatch:
        result = self.commands.commit(
            command,
            patch.model_dump(mode="json", exclude={"proposed_at", "reviewed_at"}),
            event_type=event_type,
            event_payload={
                "patch_id": patch.patch_id,
                "resume_id": patch.resume_id,
                "base_revision": patch.base_revision,
                "status": patch.status.value,
                "operation_count": len(patch.operations),
            },
            transactional_write=ResumePatchWrite(patch),
        )
        persisted = self.repository.get_patch(patch.patch_id, result.revision)
        if persisted is None:
            raise RuntimeError("ResumePatch commit did not persist the typed aggregate")
        return persisted

    @staticmethod
    def _apply_operation(content: dict[str, Any], operation: ResumePatchOperation) -> None:
        parts = [
            part.replace("~1", "/").replace("~0", "~")
            for part in operation.target_path.split("/")[1:]
        ]
        if not parts:
            raise ValueError("resume patch cannot replace the document root")
        parent: Any = content
        for part in parts[:-1]:
            parent = parent[int(part)] if isinstance(parent, list) else parent[part]
        key = parts[-1]
        current = parent[int(key)] if isinstance(parent, list) else parent[key]
        if canonical_value_hash(current) != operation.expected_value_hash:
            raise ValueError("ResumePatch expected_value_hash does not match the base content")
        if operation.action is ResumePatchAction.SET:
            if isinstance(parent, list):
                parent[int(key)] = operation.proposed_value
            else:
                parent[key] = operation.proposed_value
        elif operation.action is ResumePatchAction.REMOVE:
            if isinstance(parent, list):
                parent.pop(int(key))
            else:
                del parent[key]
        elif not isinstance(current, list):
            raise ValueError("ResumePatch insert target must be a list")
        else:
            current.append(operation.proposed_value)

    @staticmethod
    def _require(command: Command, kind: EntityKind, *, user: bool = False) -> None:
        if command.target.kind is not kind:
            raise ValueError(f"command requires a {kind.value} target")
        if user and command.actor != "user":
            raise ValueError("only the user may perform this Resume command")
