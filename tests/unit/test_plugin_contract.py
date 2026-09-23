from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from career_harness.core.plugin.contracts import (
    PluginEnvelope,
    PluginEnvelopeStatus,
    PluginError,
    PluginManifest,
)
from career_harness.core.plugin.manifest import manifest_schema, validate_manifest
from career_harness.workers.plugin_echo import run_ndjson


def _manifest() -> dict[str, object]:
    return {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.2.3",
        "api_version": "1",
        "type": "worker_plugin",
        "source": {
            "repo": "builtin://test-plugin",
            "ref": "v1",
            "commit": "abcdef1234567",
            "license": "Apache-2.0",
        },
        "capabilities": ["test.echo"],
        "permissions": {
            "network": [],
            "filesystem": [],
            "secrets": [],
            "external_write": False,
            "scope": ["read_models"],
        },
        "data_contracts": ["PluginEnvelope"],
        "healthcheck": {"command": "health", "timeout_ms": 1000},
        "replacement": {"compatible_capabilities": ["test.echo"]},
        "dependencies": [],
        "core_compatibility": {"min_version": "0.1.0", "max_version": "0.x"},
        "config_schema": {},
        "data_migration_version": 0,
        "cost_limits": {"max_runtime_ms": 1000, "max_output_bytes": 10000},
        "user_visible_description": "offline fixture",
        "security_url": "about:blank",
        "terms_url": "about:blank",
    }


def test_manifest_schema_and_canonical_hash_are_stable() -> None:
    assert manifest_schema()["$id"].endswith("plugin-manifest-v1.json")
    first = validate_manifest(_manifest())
    second = PluginManifest.model_validate(first.model_dump())
    assert first.content_hash() == second.content_hash()


def test_manifest_rejects_unknown_fields_and_bad_api_version() -> None:
    value = _manifest()
    value["unknown"] = True
    with pytest.raises(ValidationError):
        validate_manifest(value)
    value = _manifest()
    value["api_version"] = "2"
    with pytest.raises(ValidationError):
        validate_manifest(value)


def test_error_envelope_is_stable_and_timezone_aware() -> None:
    envelope = PluginEnvelope.error_envelope(
        request_id="request-001",
        plugin_id="test-plugin",
        plugin_version="1.2.3",
        capability="test.echo",
        input_hash="a" * 64,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        error=PluginError(code="blocked", message="approval required"),
        status=PluginEnvelopeStatus.BLOCKED,
    )
    assert envelope.status is PluginEnvelopeStatus.BLOCKED
    assert envelope.finished_at.tzinfo is not None


def test_echo_worker_ndjson_is_deterministic() -> None:
    from io import StringIO

    output = StringIO()
    run_ndjson(['{"request_id":"r1","payload":{"x":1}}'], output)
    assert output.getvalue() == (
        '{"data": {"echo": {"x": 1}, "fixture": true}, '
        '"request_id": "r1", "status": "ok"}\n'
    )
