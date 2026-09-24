import hashlib
from pathlib import Path

import pytest
from sqlalchemy import event

from career_harness.core.project.l2 import AnalysisRequest, PreparationError
from career_harness.db.models import ProjectSourceEntryRow, ProjectSourceManifestRow
from career_harness.db.project_repository import ProjectRepository
from career_harness.services.l2_preparation_service import L2PreparationService
from tests.integration.test_project_repository import _database
from tests.unit.test_l2_preparation import SECRET, request_data


def seeded(tmp_path: Path):
    engine, now = _database(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            ProjectSourceManifestRow.__table__.insert(),
            {
                "manifest_id": "manifest_l2",
                "project_id": "project_001",
                "scan_scope_id": "scope_001",
                "scan_scope_revision": 1,
                "generated_at": now,
            },
        )
        connection.execute(
            ProjectSourceEntryRow.__table__.insert(),
            {
                "manifest_id": "manifest_l2",
                "relative_path": "src/a.py",
                "sha256": hashlib.sha256(SECRET.encode()).hexdigest(),
                "byte_length": len(SECRET.encode()),
            },
        )
    data = request_data()
    data["task"]["revision"] = 2
    data["manifest_id"] = "manifest_l2"
    return engine, data


def test_exact_database_reads_are_select_only_and_do_not_access_project(
    tmp_path: Path, monkeypatch
):
    engine, data = seeded(tmp_path)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    def forbidden(*args, **kwargs):
        raise AssertionError("no filesystem content read or process execution is allowed")

    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        service = L2PreparationService(ProjectRepository(engine))
        prepared = service.prepare(AnalysisRequest.model_validate(data))
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
    assert prepared.project.revision == prepared.scope.revision == 1
    assert prepared.task.revision == 2
    assert SECRET in prepared.stdin
    assert "agent-gateway-v1" not in prepared.stdin
    assert "agent-gateway-v2" not in prepared.stdin
    assert not prepared.permissions.execution_authorized


@pytest.mark.parametrize("field", ["task", "project", "scope", "manifest_id"])
def test_database_does_not_substitute_latest_for_missing_exact_ref(tmp_path: Path, field):
    engine, data = seeded(tmp_path)
    if field == "manifest_id":
        data[field] = "manifest_missing"
    else:
        data[field]["revision"] = 99
    with pytest.raises(PreparationError):
        L2PreparationService(ProjectRepository(engine)).prepare(
            AnalysisRequest.model_validate(data)
        )


def test_database_exact_task_state_and_manifest_scope_are_not_replaced(tmp_path: Path):
    engine, data = seeded(tmp_path)
    service = L2PreparationService(ProjectRepository(engine))
    data["task"]["revision"] = 1  # latest is READY, but this exact revision is PROPOSED
    with pytest.raises(PreparationError):
        service.prepare(AnalysisRequest.model_validate(data))
    data["task"]["revision"] = 2
    data["scope"]["revision"] = 2  # existing, but the frozen manifest pins revision 1
    with pytest.raises(PreparationError):
        service.prepare(AnalysisRequest.model_validate(data))
