"""PRD 29.7: real L1 task flow without CLI, providers or project modification."""

import json
import os
import shutil
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from career_harness.core.project import (
    L1ManualExecutor,
    ManualPlanRequest,
    ProjectEnhancementTaskStatus,
)
from career_harness.db.models import Base, DomainEventRow, ProjectRecordRow
from tests.integration.test_project_enhancement_service import (
    CAPABILITY_ID,
    PROJECT_ID,
    _command,
    _engine,
    _services,
    _write_counts,
)


def _protected_state(engine: Engine) -> dict[str, list[str]]:
    # Only task rows and the command/event/idempotency audit tables may change.
    writable = {
        "project_enhancement_task",
        "idempotency_record",
    }
    with engine.connect() as connection:
        return {
            table.name: sorted(
                json.dumps(dict(row), sort_keys=True, default=str)
                for row in connection.execute(select(table)).mappings()
                if not (
                    table.name in {"entity_state", "entity_revision", "domain_event"}
                    and row["entity_id"] == "task_offline_l1"
                )
            )
            for table in Base.metadata.sorted_tables
            if table.name not in writable
        }


def _source_tree(root: Path) -> dict[str, bytes | None]:
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def test_l1_plan_persistence_and_status_flow_need_no_cli_or_network(tmp_path, monkeypatch):
    engine, gap_id = _engine(tmp_path)
    repository, service = _services(engine)
    root = tmp_path / "synthetic-project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "policy.py").write_text("def policy():\n    return 'unchanged'\n")
    (root / "README.md").write_text("Synthetic offline acceptance source.\n")
    # Connect the real canonical Project to the synthetic target without changing old revisions.
    with engine.begin() as connection:
        connection.execute(
            ProjectRecordRow.__table__.insert(),
            {
                "project_id": PROJECT_ID,
                "revision": 2,
                "display_name": "Offline synthetic project",
                "root_locator": str(root),
                "schema_version": 1,
                "created_at": datetime.now(UTC),
                "created_by": "user",
            },
        )
    protected_before = _protected_state(engine)
    source_before = _source_tree(root)
    counts_before = _write_counts(engine)
    request = ManualPlanRequest(
        task_id="task_offline_l1",
        project_id=PROJECT_ID,
        target_gap_id=gap_id,
        target_capability_id=CAPABILITY_ID,
        learning_plan=("Study the canonical gap manually.",),
        files_to_review=("src/policy.py", "README.md"),
        change_plan=("Consider a policy regression test; do not change code now.",),
        experiment_plan=("Design a synthetic policy comparison.",),
        validation_plan=("Have the user review the proposed experiment.",),
        expected_evidence=("Future manually reviewed test output, not current evidence.",),
        requested_by="user",
    )
    forbidden_calls = []

    def unavailable(*args, **kwargs):
        forbidden_calls.append(True)
        raise AssertionError("offline L1 must not discover CLI, launch processes or use network")

    # Patch only after DB/bootstrap setup so test tooling can initialize normally.
    with monkeypatch.context() as blocked:
        blocked.setattr(shutil, "which", unavailable)
        blocked.setattr(subprocess, "Popen", unavailable)
        blocked.setattr(subprocess, "run", unavailable)
        blocked.setattr(os, "system", unavailable)
        blocked.setattr(os, "popen", unavailable)
        blocked.setattr(socket, "create_connection", unavailable)
        blocked.setattr(socket, "getaddrinfo", unavailable)
        blocked.setattr(socket.socket, "connect", unavailable)
        blocked.setattr(socket.socket, "connect_ex", unavailable)
        blocked.setattr(socket.socket, "sendto", unavailable)

        plan = L1ManualExecutor().generate_plan(request)
        assert plan.status is ProjectEnhancementTaskStatus.PROPOSED
        for field in (
            "learning_plan",
            "files_to_review",
            "change_plan",
            "experiment_plan",
            "validation_plan",
            "expected_evidence",
        ):
            assert getattr(plan, field) == getattr(request, field)
        assert _write_counts(engine) == counts_before  # Generation alone is not persistence.
        command = _command(plan.task_id, command_id="command_offline_propose").model_copy(
            update={"actor": "user"}
        )
        proposed = service.propose_enhancement_task(command, task=plan)
        assert repository.get_enhancement_task(plan.task_id, 1) == proposed.task
        assert proposed.task.target_gap_id == gap_id
        assert proposed.task.target_capability_id == CAPABILITY_ID
        after_propose = _write_counts(engine)
        assert service.propose_enhancement_task(command, task=plan) == proposed
        assert _write_counts(engine) == after_propose
        assert _protected_state(engine) == protected_before
        assert _source_tree(root) == source_before

        statuses = (
            ProjectEnhancementTaskStatus.READY,
            ProjectEnhancementTaskStatus.IN_PROGRESS,
            ProjectEnhancementTaskStatus.AWAITING_VALIDATION,
            ProjectEnhancementTaskStatus.COMPLETED,
        )
        for previous_revision, status in enumerate(statuses, start=1):
            transition = _command(
                plan.task_id,
                command_id=f"command_offline_{status.value}",
                command_type="project_enhancement.transition",
                expected_revision=previous_revision,
            ).model_copy(update={"actor": "user"})
            result = service.transition_enhancement_task(
                transition, task_id=plan.task_id, to_status=status
            )
            assert result.task.status is status
            assert result.task.revision == previous_revision + 1
            assert (
                repository.get_enhancement_task(plan.task_id, previous_revision + 1) == result.task
            )
            counts = _write_counts(engine)
            assert (
                service.transition_enhancement_task(
                    transition, task_id=plan.task_id, to_status=status
                )
                == result
            )
            assert _write_counts(engine) == counts
            # COMPLETED is workflow state; no code execution, Evidence or mastery promotion.
            assert _protected_state(engine) == protected_before
            assert _source_tree(root) == source_before
        assert repository.get_enhancement_task(plan.task_id, 1) == proposed.task
    assert forbidden_calls == []
    with Session(engine) as session:
        events = session.scalars(
            select(DomainEventRow)
            .where(DomainEventRow.entity_id == plan.task_id)
            .order_by(DomainEventRow.entity_revision)
        ).all()
        assert [event.event_type for event in events] == [
            "project_enhancement.proposed",
            *(["project_enhancement.status_changed"] * 4),
        ]
        assert [event.entity_revision for event in events] == [1, 2, 3, 4, 5]
