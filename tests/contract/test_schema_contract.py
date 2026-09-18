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

