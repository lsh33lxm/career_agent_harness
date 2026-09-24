from importers.agent_radar.models import LegacyImportManifest, ReconciliationRecord


def test_manifest_contract_requires_candidate_status_and_approval_list() -> None:
    schema = LegacyImportManifest.model_json_schema()
    assert "manifest_status" in schema["properties"]
    assert "approved_entities" in schema["properties"]
    assert "source_hashes" in schema["properties"]


def test_reconciliation_contract_has_required_disposition_fields() -> None:
    required = set(ReconciliationRecord.model_json_schema()["required"])
    assert {
        "source_path",
        "source_hash",
        "legacy_key",
        "candidate_core_identity",
        "mismatch",
        "disposition",
        "reason",
    } <= required

