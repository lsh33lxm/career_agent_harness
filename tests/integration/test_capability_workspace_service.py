from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from career_harness.db.models import Base
from career_harness.services.capability_workspace_service import (
    CapabilityGraphNotFoundError,
    CapabilityWorkspaceService,
)
from tests.integration.test_capability_repository import _repository, _seed_capability_data


def _row_counts(service: CapabilityWorkspaceService) -> dict[str, int | None]:
    with Session(service.repository.engine) as session:
        return {
            table.name: session.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }


def test_service_builds_latest_candidate_workspace_without_writes(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    with connection.begin():
        _seed_capability_data(connection)
    connection.close()
    service = CapabilityWorkspaceService(repository)
    before = _row_counts(service)

    workspace = service.get_workspace(candidate_id="candidate_001")

    assert workspace.graph_version is not None
    assert workspace.graph_version.graph_version_id == "graph_version_002"
    assert [node.capability_id for node in workspace.nodes] == [
        "capability_a",
        "capability_b",
    ]
    alpha = workspace.projections[0]
    assert alpha.personal_state is not None
    assert (alpha.personal_state.personal_state_id, alpha.personal_state.revision) == (
        "personal_state_002",
        3,
    )
    assert alpha.evidence_bindings == ()
    assert [item.binding_id for item in alpha.target_market_bindings] == [
        "market_target_a",
        "market_target_b",
    ]
    assert [item.binding_id for item in alpha.broad_market_bindings] == ["market_broad"]
    assert alpha.investment_state is not None
    assert alpha.investment_state.investment_state_id == "investment_001"
    assert workspace.projections[1].personal_state is None
    assert _row_counts(service) == before


def test_service_pins_exact_graph_and_rejects_unknown_explicit_version(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    with connection.begin():
        _seed_capability_data(connection)
    connection.close()
    service = CapabilityWorkspaceService(repository)

    exact = service.get_workspace(
        candidate_id="candidate_001", graph_version_id="graph_version_001"
    )

    assert exact.graph_version is not None
    assert exact.graph_version.graph_version_id == "graph_version_001"
    assert [node.capability_id for node in exact.nodes] == ["capability_a"]
    try:
        service.get_workspace(candidate_id="candidate_001", graph_version_id="graph_missing")
    except CapabilityGraphNotFoundError as error:
        assert error.graph_version_id == "graph_missing"
    else:
        raise AssertionError("unknown exact graph must fail loud")


def test_empty_repository_returns_explicit_empty_workspace(tmp_path: Path) -> None:
    repository, connection = _repository(tmp_path)
    connection.close()

    workspace = CapabilityWorkspaceService(repository).get_workspace(
        candidate_id="candidate_unknown"
    )

    assert workspace.candidate_id == "candidate_unknown"
    assert workspace.graph_version is None
    assert workspace.projections == ()
