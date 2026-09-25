from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.context import (
    BasicContextCompiler,
    CompiledContext,
    ContextAsset,
    ContextAssetClass,
    ContextAssetRef,
    ContextCompilationRequest,
    MarketEvidenceScope,
    VerticalKnowledgeAsset,
    VerticalKnowledgeRef,
)
from career_harness.db.context_repository import ContextManifestRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    ContextManifestAssetRefRow,
    ContextManifestKnowledgeRefRow,
    ContextManifestRow,
    DomainEventRow,
    EntityRevisionRow,
    EntityStateRow,
    IdempotencyRecordRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.command_service import CommandService, IdempotencyConflict
from career_harness.services.context_service import ContextService

SENSITIVE_SENTINEL = "do-not-persist-context-payload"


class WrongManifestCompiler:
    def compile(self, request: ContextCompilationRequest) -> CompiledContext:
        wrong_request = request.model_copy(update={"manifest_id": "context_manifest_other"})
        return BasicContextCompiler().compile(wrong_request)


def _command(
    *,
    manifest_id: str = "context_manifest_001",
    kind: EntityKind = EntityKind.CONTEXT_MANIFEST,
    expected_revision: int = 0,
    actor: str = "agent",
    key: str = "context-compile-001",
) -> Command:
    return Command(
        command_id=f"command_{manifest_id}",
        command_type="context.compile",
        target=EntityRef(entity_id=manifest_id, kind=kind),
        expected_revision=expected_revision,
        idempotency_key=key,
        actor=actor,
    )


def _request(
    *,
    manifest_id: str = "context_manifest_001",
    run_id: str = "run_001",
    actor: str = "agent",
    explicit_asset_ids: tuple[str, ...] = ("personal_context_001",),
) -> ContextCompilationRequest:
    return ContextCompilationRequest(
        manifest_id=manifest_id,
        task_type="opportunity_gap_analysis",
        task_input={"private_instruction": SENSITIVE_SENTINEL},
        candidates=(
            ContextAsset(
                ref=ContextAssetRef(
                    asset_id="market_evidence_001",
                    asset_class=ContextAssetClass.MARKET_EVIDENCE,
                    revision=4,
                ),
                title="Broad market sample",
                payload={"private_market_payload": SENSITIVE_SENTINEL},
                relevance_terms=("observability",),
                market_scope=MarketEvidenceScope.BROAD,
            ),
            ContextAsset(
                ref=ContextAssetRef(
                    asset_id="career_state_001",
                    asset_class=ContextAssetClass.CAREER_STATE,
                    revision=3,
                ),
                title="Current direction",
                payload={"private_state_payload": SENSITIVE_SENTINEL},
                relevance_terms=("observability",),
            ),
            ContextAsset(
                ref=ContextAssetRef(
                    asset_id="personal_context_001",
                    asset_class=ContextAssetClass.PERSONAL_CONTEXT,
                    revision=2,
                ),
                title="Working preferences",
                payload={"private_context_payload": SENSITIVE_SENTINEL},
                relevance_terms=("observability",),
            ),
        ),
        allowed_asset_classes=(
            ContextAssetClass.PERSONAL_CONTEXT,
            ContextAssetClass.CAREER_STATE,
        ),
        relevance_terms=("observability",),
        explicit_asset_ids=explicit_asset_ids,
        vertical_knowledge=(
            VerticalKnowledgeAsset(
                ref=VerticalKnowledgeRef(knowledge_id="knowledge_tracing", revision=5),
                payload={"private_knowledge_payload": SENSITIVE_SENTINEL},
            ),
            VerticalKnowledgeAsset(
                ref=VerticalKnowledgeRef(knowledge_id="knowledge_agents", revision=7),
                payload={"private_knowledge_payload": SENSITIVE_SENTINEL},
            ),
        ),
        provider="local-test-provider",
        model_id="test-model",
        capabilities=("structured_generation",),
        skills=("gap_analysis",),
        actor=actor,
        run_id=run_id,
    )


def _service(tmp_path: Path, *, clock_time: datetime | None = None):
    database_url = sqlite_url(tmp_path / "context-service.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    repository = ContextManifestRepository(engine)
    compiler = (
        BasicContextCompiler(clock=lambda: clock_time)
        if clock_time is not None
        else BasicContextCompiler()
    )
    return engine, repository, ContextService(CommandService(engine), repository, compiler)


def test_context_compilation_commits_typed_manifest_and_audit_atomically(
    tmp_path: Path,
) -> None:
    transient_time = datetime(2020, 1, 1, tzinfo=UTC)
    engine, repository, service = _service(tmp_path, clock_time=transient_time)

    first = service.compile_and_record(_command(), _request())
    replay_service = ContextService(
        CommandService(engine),
        repository,
        BasicContextCompiler(clock=lambda: datetime(2030, 1, 1, tzinfo=UTC)),
    )
    replay = replay_service.compile_and_record(_command(), _request())

    assert replay.commit == first.commit
    assert replay.manifest == first.manifest
    assert first.manifest.created_at != transient_time
    assert first.manifest.authorizes_fact_mutation is False
    assert [item.ref.asset_id for item in first.manifest.included] == [
        "personal_context_001",
        "career_state_001",
    ]
    assert [item.ref.asset_id for item in first.manifest.excluded] == ["market_evidence_001"]
    assert [item.knowledge_id for item in first.manifest.vertical_knowledge_refs] == [
        "knowledge_agents",
        "knowledge_tracing",
    ]
    assert repository.get("context_manifest_001") == first.manifest
    assert repository.list_for_run("run_001") == (first.manifest,)

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EntityStateRow)) == 1
        assert session.scalar(select(func.count()).select_from(EntityRevisionRow)) == 1
        assert session.scalar(select(func.count()).select_from(DomainEventRow)) == 1
        assert session.scalar(select(func.count()).select_from(IdempotencyRecordRow)) == 1
        assert session.scalar(select(func.count()).select_from(ContextManifestRow)) == 1
        assert session.scalar(select(func.count()).select_from(ContextManifestAssetRefRow)) == 3
        assert session.scalar(select(func.count()).select_from(ContextManifestKnowledgeRefRow)) == 2

        state = session.get(EntityStateRow, "context_manifest_001")
        event = session.scalar(select(DomainEventRow))
        revision = session.scalar(select(EntityRevisionRow))
        idempotency = session.scalar(select(IdempotencyRecordRow))
        assert state is not None and event is not None
        assert revision is not None and idempotency is not None
        expected_metadata_keys = {
            "manifest_id",
            "contract_version",
            "task_type",
            "selection_policy_version",
            "compression_policy_version",
            "run_id",
            "input_hash",
            "included_count",
            "excluded_count",
            "knowledge_ref_count",
        }
        assert set(state.state) == expected_metadata_keys
        assert set(event.payload) == expected_metadata_keys | {"revision_id"}
        assert event.event_type == "context.compiled"
        persisted_audit = json.dumps(
            {
                "state": state.state,
                "revision": revision.state,
                "event": event.payload,
                "idempotency": idempotency.response,
            }
        )
        assert SENSITIVE_SENTINEL not in persisted_audit


def test_context_replay_rejects_changed_refs_revisions_reasons_and_hash(tmp_path: Path) -> None:
    _, _, service = _service(tmp_path)
    command = _command()
    original = _request()
    service.compile_and_record(command, original)

    personal = original.candidates[2]
    changed_ref = personal.model_copy(
        update={"ref": personal.ref.model_copy(update={"asset_id": "personal_context_002"})}
    )
    changed_revision = personal.model_copy(
        update={"ref": personal.ref.model_copy(update={"revision": 9})}
    )
    changed_requests = (
        _request(explicit_asset_ids=()),
        original.model_copy(
            update={
                "candidates": (*original.candidates[:2], changed_ref),
                "explicit_asset_ids": ("personal_context_002",),
            }
        ),
        original.model_copy(update={"candidates": (*original.candidates[:2], changed_revision)}),
        original.model_copy(update={"task_input": {"changed": True}}),
    )

    for changed in changed_requests:
        with pytest.raises(IdempotencyConflict):
            service.compile_and_record(command, changed)


def test_context_typed_write_failure_rolls_back_generic_audit(tmp_path: Path) -> None:
    engine, _, service = _service(tmp_path)
    request = ContextCompilationRequest(
        manifest_id="context_manifest_missing_evidence",
        task_type="project_review",
        task_input={},
        candidates=(
            ContextAsset(
                ref=ContextAssetRef(
                    asset_id="project_evidence_missing",
                    asset_class=ContextAssetClass.PROJECT_EVIDENCE,
                    revision=1,
                ),
                title="Unpersisted evidence",
                payload={},
            ),
        ),
        allowed_asset_classes=(ContextAssetClass.PROJECT_EVIDENCE,),
        explicit_asset_ids=("project_evidence_missing",),
        provider="local-test-provider",
        model_id="test-model",
        actor="agent",
        run_id="run_rollback",
    )

    with pytest.raises(IntegrityError):
        service.compile_and_record(
            _command(
                manifest_id="context_manifest_missing_evidence",
                key="context-compile-rollback",
            ),
            request,
        )

    with Session(engine) as session:
        for row_type in (
            EntityStateRow,
            EntityRevisionRow,
            DomainEventRow,
            IdempotencyRecordRow,
            ContextManifestRow,
            ContextManifestAssetRefRow,
            ContextManifestKnowledgeRefRow,
        ):
            assert session.scalar(select(func.count()).select_from(row_type)) == 0


def test_context_rejects_compiler_output_for_another_manifest_before_writing(
    tmp_path: Path,
) -> None:
    engine, repository, _ = _service(tmp_path)
    service = ContextService(CommandService(engine), repository, WrongManifestCompiler())

    with pytest.raises(ValueError, match="metadata must match"):
        service.compile_and_record(_command(), _request())

    with Session(engine) as session:
        for row_type in (
            EntityStateRow,
            EntityRevisionRow,
            DomainEventRow,
            IdempotencyRecordRow,
            ContextManifestRow,
            ContextManifestAssetRefRow,
            ContextManifestKnowledgeRefRow,
        ):
            assert session.scalar(select(func.count()).select_from(row_type)) == 0


@pytest.mark.parametrize(
    ("command", "compilation_request", "message"),
    [
        (
            _command(kind=EntityKind.RUN),
            _request(),
            "context manifest target",
        ),
        (
            _command(manifest_id="context_manifest_other", key="context-wrong-id"),
            _request(),
            "target must match",
        ),
        (
            _command(expected_revision=1, key="context-wrong-revision"),
            _request(),
            "expected revision zero",
        ),
        (
            _command(actor="user", key="context-wrong-actor"),
            _request(),
            "actor must match",
        ),
    ],
)
def test_context_command_must_match_manifest_creation(
    tmp_path: Path,
    command: Command,
    compilation_request: ContextCompilationRequest,
    message: str,
) -> None:
    engine, _, service = _service(tmp_path)

    with pytest.raises(ValueError, match=message):
        service.compile_and_record(command, compilation_request)

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EntityStateRow)) == 0
        assert session.scalar(select(func.count()).select_from(ContextManifestRow)) == 0
