from pathlib import Path

import httpx
import pytest
from sqlalchemy import event

from career_harness.api.app import create_app
from career_harness.api.capability_inbox import CapabilityInboxApi
from career_harness.api.runtime import create_runtime_app
from career_harness.config import Settings
from career_harness.db.models import EntityStateRow
from career_harness.platform import AppPaths
from tests.integration.test_capability_review_service import (
    _engine,
    _propose,
    _services,
    _write_counts,
)

AUTH = {"Authorization": "Bearer test-inbox-token"}
HEADERS = {**AUTH, "X-Idempotency-Key": "idempotency-review-001"}
BODY = {
    "command_id": "command_review_001",
    "expected_revision": 1,
    "decision": "accept",
    "reason": "Reviewed evidence",
}
URL = "/api/v1/capability-inbox"


def setup(tmp_path: Path, actor="agent:scout"):
    engine = _engine(tmp_path, with_graph=True)
    repository, service = _services(engine)
    _propose(service, "candidate_node_001", actor=actor)
    app = create_app(
        Settings.for_test(token="test-inbox-token"),
        capability_inbox_api=CapabilityInboxApi(repository, service.commands, service),
    )
    return engine, httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_inbox_reads_auth_detail_missing_and_zero_writes(tmp_path):
    engine, client = setup(tmp_path)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    before = _write_counts(engine)
    event.listen(engine, "before_cursor_execute", capture)
    async with client:
        assert (await client.get(URL)).status_code == 401
        assert (await client.post(f"{URL}/candidate_node_001/review", json=BODY)).status_code == 401
        listing = await client.get(URL, headers=AUTH)
        detail = await client.get(f"{URL}/candidate_node_001", headers=AUTH)
        assert listing.json() == [detail.json()]
        assert detail.json()["revision"] == 1
        assert (await client.get(f"{URL}/missing", headers=AUTH)).status_code == 404
        assert (
            await client.post(f"{URL}/missing/review", headers=HEADERS, json=BODY)
        ).status_code == 404
    event.remove(engine, "before_cursor_execute", capture)
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
    assert _write_counts(engine) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["accept", "reject"])
async def test_inbox_review_exact_replay_history_and_competing_reviews(tmp_path, decision):
    engine, client = setup(tmp_path)
    body = {**BODY, "decision": decision}
    async with client:
        first = await client.post(f"{URL}/candidate_node_001/review", headers=HEADERS, json=body)
        assert first.status_code == 200, first.text
        before = _write_counts(engine)
        replay = await client.post(f"{URL}/candidate_node_001/review", headers=HEADERS, json=body)
        assert replay.json() == first.json()
        assert _write_counts(engine) == before
        result = first.json()
        assert result["candidate"]["reviewed_by"] == "user"
        assert result["candidate"]["status"] == ("accepted" if decision == "accept" else "ignored")
        assert bool(result["graph_version"]) == (decision == "accept")
        history = (await client.get(URL, headers=AUTH)).json()
        assert history[0]["revision"] == 2
        for changed, headers in (
            ({**body, "reason": "Different reason"}, HEADERS),
            (
                {**body, "command_id": "command_competing"},
                {**HEADERS, "X-Idempotency-Key": "different-key"},
            ),
            ({**body, "expected_revision": 2}, HEADERS),
        ):
            response = await client.post(
                f"{URL}/candidate_node_001/review", headers=headers, json=changed
            )
            assert response.status_code == 409
            assert "SQL" not in response.text
        assert _write_counts(engine) == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"actor": "admin"},
        {"merge_target": "capability_a"},
        {"graph_version_id": "graph_new"},
        {"reason": "   "},
        {"decision": "merge"},
        {"expected_revision": 0},
    ],
)
async def test_inbox_rejects_invalid_body_and_actor_injection(tmp_path, change):
    engine, client = setup(tmp_path)
    before = _write_counts(engine)
    async with client:
        result = await client.post(
            f"{URL}/candidate_node_001/review", headers=HEADERS, json={**BODY, **change}
        )
    assert result.status_code == 422
    assert _write_counts(engine) == before


@pytest.mark.asyncio
async def test_inbox_forbids_self_review_and_stale_revision(tmp_path):
    engine, client = setup(tmp_path, actor="user")
    before = _write_counts(engine)
    async with client:
        assert (
            await client.post(f"{URL}/candidate_node_001/review", headers=HEADERS, json=BODY)
        ).status_code == 409
    assert _write_counts(engine) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["missing", "kind", "payload", "id", "revision"])
async def test_inbox_generic_state_must_match_and_revision_is_not_guessed(tmp_path, fault):
    engine, client = setup(tmp_path)
    with engine.begin() as connection:
        if fault == "missing":
            # Retain the row but make get unable to resolve it via a fake repository result.
            pass
        elif fault == "kind":
            connection.execute(
                EntityStateRow.__table__.update()
                .where(EntityStateRow.entity_id == "candidate_node_001")
                .values(entity_kind="project")
            )
        elif fault in {"payload", "id"}:
            state = (
                connection.execute(
                    EntityStateRow.__table__.select().where(
                        EntityStateRow.entity_id == "candidate_node_001"
                    )
                )
                .mappings()
                .one()["state"]
            )
            state["proposed_description" if fault == "payload" else "candidate_node_id"] = (
                "mismatch"
            )
            connection.execute(
                EntityStateRow.__table__.update()
                .where(EntityStateRow.entity_id == "candidate_node_001")
                .values(state=state)
            )
        else:
            connection.execute(
                EntityStateRow.__table__.update()
                .where(EntityStateRow.entity_id == "candidate_node_001")
                .values(revision=7)
            )
    if fault == "missing":
        from unittest.mock import patch

        with patch("career_harness.services.command_service.CommandService.get", return_value=None):
            async with client:
                response = await client.get(URL, headers=AUTH)
    else:
        async with client:
            response = await client.get(URL, headers=AUTH)
    if fault == "revision":
        assert response.status_code == 200
        assert response.json()[0]["revision"] == 7
    else:
        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "capability inbox conflicts with canonical state; refresh required"
        )


@pytest.mark.asyncio
async def test_actual_runtime_wires_inbox(tmp_path):
    paths = AppPaths.resolve({"ACH_DATA_DIR": str(tmp_path / "runtime")})
    app = create_runtime_app(Settings.for_test(token="test-inbox-token"), paths)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(URL, headers=AUTH)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_stale_pending_review_rolls_back_and_list_is_sorted(tmp_path):
    engine, client = setup(tmp_path)
    _, service = _services(engine)
    _propose(service, "candidate_node_003")
    _propose(service, "candidate_node_002")
    before = _write_counts(engine)
    async with client:
        result = await client.post(
            f"{URL}/candidate_node_001/review",
            headers=HEADERS,
            json={**BODY, "expected_revision": 9},
        )
        assert result.status_code == 409
        listing = (await client.get(URL, headers=AUTH)).json()
    assert [item["candidate"]["candidate_node_id"] for item in listing] == [
        "candidate_node_001",
        "candidate_node_002",
        "candidate_node_003",
    ]
    assert _write_counts(engine) == before
