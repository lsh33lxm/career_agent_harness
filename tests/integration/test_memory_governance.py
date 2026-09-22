from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text

from career_harness.api.app import create_app
from career_harness.api.memory import MemoryApi
from career_harness.config import Settings
from career_harness.core.memory.models import (
    MemoryCreator,
    MemoryProposalStatus,
    MemoryScope,
    MemoryType,
)
from career_harness.db.memory_repository import MemoryRepository
from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url


def _repository(tmp_path: Path) -> tuple[MemoryRepository, object]:
    database_url = sqlite_url(tmp_path / "memory.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    return MemoryRepository(engine), engine


def test_memory_is_review_gated_scoped_revisioned_and_tombstoned(tmp_path: Path) -> None:
    repository, engine = _repository(tmp_path)
    proposal = repository.create_proposal(
        memory_type=MemoryType.PREFERENCE,
        scope_kind=MemoryScope.USER,
        scope_id="local-user",
        content="偏好远程工作",
        source_type="conversation",
        source_locator="conversation://session-1/turn-2",
        source_refs=("turn-2",),
        confidence=0.8,
        created_by=MemoryCreator.LLM,
    )
    assert repository.search(scope_kind=MemoryScope.USER, scope_id="local-user") == ()
    assert repository.list_proposals(
        scope_kind=MemoryScope.USER,
        scope_id="local-user",
        status=MemoryProposalStatus.PENDING,
    ) == (proposal,)

    reviewed = repository.review_proposal(
        proposal.proposal_id,
        decision=MemoryProposalStatus.APPROVED,
        reason="用户确认并修正",
        edited_content="偏好远程或混合办公",
    )
    assert reviewed.approved_content == "偏好远程或混合办公"
    result = repository.search(
        scope_kind=MemoryScope.USER, scope_id="local-user", query="混合办公"
    )[0]
    assert result.memory.content == "偏好远程或混合办公"
    assert result.memory.source_locator == "conversation://session-1/turn-2"
    assert result.memory.created_by is MemoryCreator.LLM
    assert result.memory.confirmed_by == "user"
    assert repository.search(scope_kind=MemoryScope.WORKSPACE, scope_id="local-user") == ()

    deleted = repository.tombstone(result.memory.memory_id, reason="用户要求删除")
    assert deleted.status == "tombstoned"
    assert deleted.revision == 2
    assert repository.search(scope_kind=MemoryScope.USER, scope_id="local-user") == ()
    with engine.connect() as connection:
        events = (
            connection.execute(
                text("SELECT event_type FROM domain_event WHERE entity_id=:id"),
                {"id": result.memory.memory_id},
            )
            .scalars()
            .all()
        )
    assert events == ["memory.confirmed", "memory.tombstoned"]


def test_memory_affinity_and_consolidation_remain_review_gated(tmp_path: Path) -> None:
    repository, _engine_instance = _repository(tmp_path)
    proposals = [
        repository.create_proposal(
            memory_type=MemoryType.PREFERENCE,
            scope_kind=MemoryScope.USER,
            scope_id="candidate_001",
            content=content,
            source_type="conversation",
            source_locator=f"conversation://{index}",
            source_refs=(f"evidence_{index}",),
        )
        for index, content in enumerate(("偏好本地优先工作方式", "偏好可审计的工作方式"), 1)
    ]
    tuple(
        repository.review_proposal(
            item.proposal_id, decision=MemoryProposalStatus.APPROVED, reason="确认"
        )
        for item in proposals
    )
    affinity = repository.affinity(
        scope_kind=MemoryScope.USER,
        scope_id="candidate_001",
        source_ref="evidence_1",
    )
    assert len(affinity) == 1
    first_memory_id = affinity[0].memory.memory_id
    second_memory_id = repository.search(
        scope_kind=MemoryScope.USER, scope_id="candidate_001", query="可审计"
    )[0].memory.memory_id
    consolidated = repository.propose_consolidation(
        scope_kind=MemoryScope.USER,
        scope_id="candidate_001",
        memory_ids=(first_memory_id, second_memory_id),
        source_locator="memory://consolidation/1",
    )
    assert consolidated.status is MemoryProposalStatus.PENDING
    assert consolidated.source_refs == ("evidence_1", "evidence_2")


@pytest.mark.asyncio
async def test_memory_api_exposes_chinese_workflow_without_internal_ids(tmp_path: Path) -> None:
    repository, _engine = _repository(tmp_path)
    app = create_app(Settings.for_test("memory-api-test-token"), memory_api=MemoryApi(repository))
    headers = {"Authorization": "Bearer memory-api-test-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/memory/proposals",
            headers=headers,
            json={"memory_type": "interest", "content": "关注 Agent 工程岗位"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal_id"]
        pending = await client.get("/api/v1/memory/proposals", headers=headers)
        assert pending.json()[0]["proposal_id"] == proposal_id
        approved = await client.post(
            f"/api/v1/memory/proposals/{proposal_id}/review",
            headers=headers,
            json={"decision": "approved", "reason": "用户确认"},
        )
        assert approved.status_code == 200
        searched = await client.get("/api/v1/memory", headers=headers, params={"query": "Agent"})
        assert searched.status_code == 200
        memory_id = searched.json()[0]["memory"]["memory_id"]
        deleted = await client.post(
            f"/api/v1/memory/{memory_id}/delete",
            headers=headers,
            json={"reason": "用户删除"},
        )
        assert deleted.json()["status"] == "tombstoned"


def test_memory_migration_is_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    assert "memory_item" in inspect(engine).get_table_names()
    command.downgrade(config, "0025_github_project_analysis")
    assert "memory_item" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "memory_item" in inspect(engine).get_table_names()
