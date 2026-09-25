from __future__ import annotations

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, FrozenModel
from career_harness.core.context import (
    BasicContextCompiler,
    CompiledContext,
    ContextCompilationRequest,
    ContextCompilerPort,
    ContextManifest,
    context_input_hash,
)
from career_harness.core.revisions import CommandCommitResult
from career_harness.db.context_repository import ContextManifestRepository
from career_harness.db.context_writes import ContextManifestWrite
from career_harness.services.command_service import CommandService


class ContextCompilationCommit(FrozenModel):
    compiled: CompiledContext
    commit: CommandCommitResult

    @property
    def manifest(self) -> ContextManifest:
        return self.compiled.manifest


class ContextService:
    def __init__(
        self,
        commands: CommandService,
        manifests: ContextManifestRepository,
        compiler: ContextCompilerPort | None = None,
    ) -> None:
        self.commands = commands
        self.manifests = manifests
        self.compiler = compiler or BasicContextCompiler()

    def compile_and_record(
        self,
        command: Command,
        request: ContextCompilationRequest,
    ) -> ContextCompilationCommit:
        self._validate_command(command, request)
        compiled = self.compiler.compile(request)
        self._validate_compiled(request, compiled)
        manifest = compiled.manifest
        counts = {
            "included_count": len(manifest.included),
            "excluded_count": len(manifest.excluded),
            "knowledge_ref_count": len(manifest.vertical_knowledge_refs),
        }
        metadata = {
            "manifest_id": manifest.manifest_id,
            "contract_version": manifest.contract_version,
            "task_type": manifest.task_type,
            "selection_policy_version": manifest.selection_policy_version,
            "compression_policy_version": manifest.compression_policy_version,
            "run_id": manifest.run_id,
            "input_hash": manifest.input_hash,
            **counts,
        }
        commit = self.commands.commit(
            command,
            metadata,
            event_type="context.compiled",
            event_payload=metadata,
            transactional_write=ContextManifestWrite(manifest),
        )
        persisted = self.manifests.get(manifest.manifest_id)
        if persisted is None:
            raise RuntimeError("context manifest commit did not persist the typed aggregate")
        return ContextCompilationCommit(
            compiled=compiled.model_copy(update={"manifest": persisted}),
            commit=commit,
        )

    @staticmethod
    def _validate_command(command: Command, request: ContextCompilationRequest) -> None:
        if command.target.kind is not EntityKind.CONTEXT_MANIFEST:
            raise ValueError("context compilation requires a context manifest target")
        if command.target.entity_id != request.manifest_id:
            raise ValueError("command target must match the context manifest")
        if command.expected_revision != 0:
            raise ValueError("context manifest creation requires expected revision zero")
        if command.actor != request.actor:
            raise ValueError("command actor must match the context manifest actor")

    @staticmethod
    def _validate_compiled(
        request: ContextCompilationRequest,
        compiled: CompiledContext,
    ) -> None:
        manifest = compiled.manifest
        manifest_fields = {
            "manifest_id": request.manifest_id,
            "task_type": request.task_type,
            "provider": request.provider,
            "model_id": request.model_id,
            "capabilities": request.capabilities,
            "skills": request.skills,
            "actor": request.actor,
            "run_id": request.run_id,
        }
        if any(getattr(manifest, field) != value for field, value in manifest_fields.items()):
            raise ValueError("compiled manifest metadata must match the compilation request")
        if compiled.task_type != request.task_type or compiled.task_input != request.task_input:
            raise ValueError("compiled task input must match the compilation request")

        candidates_by_id = {asset.ref.asset_id: asset for asset in request.candidates}
        dispositions = manifest.included + manifest.excluded
        if len(dispositions) != len(candidates_by_id):
            raise ValueError("compiled manifest must classify every request candidate exactly once")
        if any(
            candidates_by_id.get(item.ref.asset_id) is None
            or candidates_by_id[item.ref.asset_id].ref != item.ref
            for item in dispositions
        ):
            raise ValueError("compiled manifest asset references must come from the request")
        expected_assets = tuple(candidates_by_id[item.ref.asset_id] for item in manifest.included)
        if compiled.assets != expected_assets:
            raise ValueError("compiled context assets must preserve request payloads")

        expected_knowledge = tuple(
            sorted(
                request.vertical_knowledge,
                key=lambda item: (item.ref.knowledge_id, item.ref.revision),
            )
        )
        if compiled.vertical_knowledge != expected_knowledge:
            raise ValueError("compiled vertical knowledge must preserve request inputs")
        if manifest.input_hash != context_input_hash(request, compiled.assets):
            raise ValueError("compiled context input hash does not match the request")
