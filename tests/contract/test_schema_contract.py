from sqlalchemy import inspect

from career_harness.db.models import Base


def test_transaction_boundary_tables_are_declared() -> None:
    tables = set(inspect(Base.metadata).tables)
    assert {"entity_state", "entity_revision", "domain_event", "outbox_message"} <= tables


def test_idempotency_key_is_unique_contract() -> None:
    table = Base.metadata.tables["idempotency_record"]
    assert table.c.idempotency_key.primary_key

