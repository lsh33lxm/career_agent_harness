from __future__ import annotations

import time
from pathlib import Path

import pytest

from career_harness.core.plugin.contracts import PluginType
from career_harness.core.plugin.runtime import CancellationToken, PluginContext
from career_harness.db.backup import create_backup, restore_backup, verify_backup
from career_harness.db.migrations import alembic_config, upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.plugin_service import (
    PluginLifecycleManager,
    PluginRegistry,
    PluginRunner,
    PluginStateError,
    RegisteredPlugin,
)


def _manager(tmp_path: Path) -> PluginLifecycleManager:
    database_url = sqlite_url(tmp_path / "plugins.db")
    upgrade_to_head(database_url)
    return PluginLifecycleManager(create_sqlite_engine(database_url))


def test_echo_install_invoke_disable_and_rollback_are_audited(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manifest = manager.registry.get("echo-fixture").manifest
    assert manager.install_preview(manifest)["safe_to_install"] is True
    assert manager.install(manifest, idempotency_key="install-echo-001")["idempotent"] is False
    assert manager.install(manifest, idempotency_key="install-echo-001")["idempotent"] is True
    assert manager.enable("echo-fixture")["enabled"] is True
    assert manager.update_preview("echo-fixture")["approval"] == "pending"
    first = manager.invoke(
        "echo-fixture",
        request_id="echo-request-001",
        capability="fixture.echo",
        payload={"value": 1},
    )
    second = manager.invoke(
        "echo-fixture",
        request_id="echo-request-001",
        capability="fixture.echo",
        payload={"value": 1},
    )
    assert first.status.value == "ok"
    assert second.output_hash == first.output_hash
    assert manager.disable("echo-fixture")["enabled"] is False
    assert manager.invoke(
        "echo-fixture",
        request_id="echo-request-002",
        capability="fixture.echo",
        payload={},
    ).error.code == "plugin_disabled"
    assert manager.rollback("echo-fixture")["enabled"] is False
    assert [entry["action"] for entry in manager.audit("echo-fixture")] == [
        "install",
        "enable",
        "update_preview",
        "disable",
        "rollback",
    ]
    with manager.engine.connect() as connection:
        event_types = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT event_type FROM domain_event WHERE entity_id = 'echo-fixture'"
            )
        }
        plan_count = connection.exec_driver_sql(
            "SELECT count(*) FROM plugin_update_plans WHERE plugin_id = 'echo-fixture'"
        ).scalar_one()
    assert {"plugin.install", "plugin.enable", "plugin.disable", "plugin.rollback"} <= event_types
    assert plan_count == 1


def test_versioned_shadow_switch_and_rollback_keep_old_release_available(tmp_path: Path) -> None:
    base = PluginRegistry().get("echo-fixture")
    candidate_manifest = base.manifest.model_copy(
        update={
            "version": "1.1.0",
            "source": base.manifest.source.model_copy(
                update={"ref": "v1.1.0", "commit": "builtin-echo-fixture-v1.1"}
            ),
        }
    )
    registry = PluginRegistry(
        (base, RegisteredPlugin(candidate_manifest, base.handler))
    )
    database_url = sqlite_url(tmp_path / "versioned.db")
    upgrade_to_head(database_url)
    manager = PluginLifecycleManager(create_sqlite_engine(database_url), registry=registry)
    manager.install(base.manifest)
    manager.enable("echo-fixture")
    manager.install(candidate_manifest)
    preview = manager.update_preview(
        "echo-fixture", capability="fixture.echo", fixture={"stable": True}
    )
    assert preview["candidate_version"] == "1.1.0"
    assert preview["tests"]["safe_to_switch"] is True
    switched = manager.switch("echo-fixture", version="1.1.0")
    assert switched["current_version"] == "1.1.0"
    assert manager.invoke(
        "echo-fixture",
        request_id="versioned-invoke-001",
        capability="fixture.echo",
        payload={"stable": True},
    ).plugin_version == "1.1.0"
    assert manager.rollback("echo-fixture")["rolled_back_to"] == "1.0.0"
    assert manager.uninstall_preview("echo-fixture")["core_truth_deleted"] is False


def test_unsafe_plugin_is_quarantined_and_cannot_be_enabled(tmp_path: Path) -> None:
    base = PluginRegistry().get("echo-fixture")
    unsafe = base.manifest.model_copy(
        update={
            "id": "unsafe-fixture",
            "type": PluginType.MCP_PLUGIN,
            "source": base.manifest.source.model_copy(update={"license": "NOASSERTION"}),
        }
    )
    manager = PluginLifecycleManager(
        _manager(tmp_path).engine,
        registry=PluginRegistry((RegisteredPlugin(unsafe, base.handler),)),
    )
    assert manager.install(unsafe)["status"] == "quarantined"
    with pytest.raises(PluginStateError, match="quarantined"):
        manager.enable("unsafe-fixture")


def test_permission_capability_timeout_and_cancellation_fail_loudly(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manifest = manager.registry.get("echo-fixture").manifest
    manager.install(manifest)
    manager.enable("echo-fixture")
    denied = manager.invoke(
        "echo-fixture",
        request_id="echo-denied-001",
        capability="not-declared",
        payload={},
    )
    assert denied.error is not None
    assert denied.error.code == "permission_denied"

    def slow(_payload: dict[str, object], context: PluginContext) -> dict[str, object]:
        time.sleep(0.1)
        context.cancellation.raise_if_cancelled()
        return {}

    slow_manifest = manifest.model_copy(
        update={
            "id": "slow-plugin",
            "capabilities": ("slow.run",),
            "cost_limits": {"max_runtime_ms": 100, "max_output_bytes": 1000},
        }
    )
    registry = PluginRegistry(
        (
            RegisteredPlugin(slow_manifest, slow),
        )
    )
    runner = PluginRunner()
    timeout = runner.invoke(
        registry.get("slow-plugin"),
        request_id="slow-timeout-001",
        capability="slow.run",
        payload={},
        context=PluginContext(),
        timeout_ms=10,
    )
    assert timeout.error is not None
    assert timeout.error.code == "timeout"

    token = CancellationToken()
    token.cancel()
    cancelled = runner.invoke(
        registry.get("slow-plugin"),
        request_id="slow-cancel-001",
        capability="slow.run",
        payload={},
        context=PluginContext(cancellation=token),
    )
    assert cancelled.error is not None
    assert cancelled.error.code == "cancelled"


def test_plugin_context_has_no_raw_engine_attribute(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manifest = manager.registry.get("echo-fixture").manifest
    manager.install(manifest)
    manager.enable("echo-fixture")
    observed: dict[str, bool] = {}

    def inspect_context(_payload: dict[str, object], context: PluginContext) -> dict[str, object]:
        observed["engine"] = hasattr(context.core, "engine")
        observed["connection"] = hasattr(context.core, "connection")
        return {}

    inspect_manifest = manifest.model_copy(
        update={"id": "inspect-plugin", "capabilities": ("inspect.run",)}
    )
    registry = PluginRegistry((RegisteredPlugin(inspect_manifest, inspect_context),))
    result = PluginRunner().invoke(
        registry.get("inspect-plugin"),
        request_id="inspect-request-001",
        capability="inspect.run",
        payload={},
        context=PluginContext(),
    )
    assert result.status.value == "ok"
    assert observed == {"engine": False, "connection": False}


def test_plugin_migration_downgrades_without_touching_v1_5_tables(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "plugin-downgrade.db")
    config = alembic_config(database_url)
    from alembic import command

    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    manager = PluginLifecycleManager(engine)
    manager.install(manager.registry.get("career-kb-local").manifest)
    command.downgrade(config, "0013_interview_core")
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "interview_identity" in tables
    assert not {"plugin_packages", "plugin_runs", "plugin_audit_events"} & tables


def test_plugin_installation_survives_backup_and_restore_rehearsal(tmp_path: Path) -> None:
    source_database = tmp_path / "source" / "career_harness.db"
    source_database.parent.mkdir()
    upgrade_to_head(sqlite_url(source_database))
    manager = PluginLifecycleManager(create_sqlite_engine(sqlite_url(source_database)))
    manager.install(manager.registry.get("echo-fixture").manifest)
    backup_root = tmp_path / "backup"
    create_backup(source_database, tmp_path / "artifacts", backup_root)
    assert verify_backup(backup_root) == ()
    restored_database = tmp_path / "restored" / "career_harness.db"
    restore_backup(backup_root, restored_database, tmp_path / "restored" / "artifacts")
    restored = PluginLifecycleManager(
        create_sqlite_engine(sqlite_url(restored_database))
    )
    item = next(
        item for item in restored.catalog() if item["manifest"]["id"] == "echo-fixture"
    )
    assert item["installed"] is True
