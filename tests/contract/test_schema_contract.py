from sqlalchemy import inspect

from career_harness.db.models import Base


def test_transaction_boundary_tables_are_declared() -> None:
    tables = set(inspect(Base.metadata).tables)
    assert {"entity_state", "entity_revision", "domain_event", "outbox_message"} <= tables


def test_idempotency_key_is_unique_contract() -> None:
    table = Base.metadata.tables["idempotency_record"]
    assert table.c.idempotency_key.primary_key


def test_evidence_provenance_uses_typed_tables() -> None:
    tables = set(inspect(Base.metadata).tables)
    assert {
        "evidence_artifact",
        "evidence_source",
        "source_snapshot",
        "evidence_ref",
    } <= tables
    evidence_ref = Base.metadata.tables["evidence_ref"]
    assert {"evidence_ref_id", "snapshot_id", "artifact_id", "selector"} <= set(
        evidence_ref.c.keys()
    )


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


def test_context_manifest_stores_audit_references_without_compiled_content() -> None:
    tables = set(inspect(Base.metadata).tables)
    assert {
        "context_manifest",
        "context_manifest_asset_ref",
        "context_manifest_knowledge_ref",
    } <= tables

    context_tables = {
        table_name: set(Base.metadata.tables[table_name].c.keys())
        for table_name in (
            "context_manifest",
            "context_manifest_asset_ref",
            "context_manifest_knowledge_ref",
        )
    }
    manifest_columns = context_tables["context_manifest"]
    assert {
        "manifest_id",
        "task_type",
        "input_hash",
        "provider",
        "model_id",
        "run_id",
        "included_count",
        "excluded_count",
        "knowledge_ref_count",
    } <= manifest_columns
    forbidden_content_columns = {
        "task_input",
        "payload",
        "compiled_context",
        "compiled_prompt",
        "content",
        "prompt",
        "messages",
        "vertical_knowledge_payload",
        "authorizes_fact_mutation",
    }
    assert all(
        not forbidden_content_columns & columns for columns in context_tables.values()
    )

