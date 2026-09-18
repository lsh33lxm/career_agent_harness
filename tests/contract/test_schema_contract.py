from sqlalchemy import inspect

from career_harness.db.models import Base


def test_transaction_boundary_tables_are_declared() -> None:
    tables = set(inspect(Base.metadata).tables)
    assert {"entity_state", "entity_revision", "domain_event", "outbox_message"} <= tables


def test_idempotency_key_is_unique_contract() -> None:
    table = Base.metadata.tables["idempotency_record"]
    assert table.c.idempotency_key.primary_key


def test_capability_graph_and_personal_overlay_use_separate_tables() -> None:
    tables = set(inspect(Base.metadata).tables)

    assert {
        "capability_graph_version",
        "capability_identity",
        "capability_node",
        "capability_relation",
        "candidate_capability_node",
        "personal_capability_state",
        "capability_evidence_binding",
        "capability_market_binding",
        "capability_investment_state",
    } <= tables
    assert Base.metadata.tables["capability_node"] is not Base.metadata.tables[
        "personal_capability_state"
    ]


def test_project_evidence_records_use_separate_typed_tables() -> None:
    tables = set(inspect(Base.metadata).tables)

    assert {
        "project_identity",
        "project_record",
        "project_scan_scope",
        "project_source_manifest",
        "project_source_entry",
        "project_evidence",
        "project_capability_basis",
        "project_capability_state",
        "project_enhancement_task",
    } <= tables
    assert "scan_scope_revision" in Base.metadata.tables["project_source_manifest"].c
    state_table = Base.metadata.tables["project_capability_state"]
    assert "basis" not in state_table.c
    assert not state_table.c.state.nullable
    assert not state_table.c.finalized_at.nullable
    assert {
        "basis_kind",
        "project_evidence_id",
        "project_evidence_revision",
        "approval_id",
        "approval_revision",
    } <= set(Base.metadata.tables["project_capability_basis"].c.keys())

