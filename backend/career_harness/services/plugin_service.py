from __future__ import annotations

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.plugin.contracts import (
    PluginEnvelope,
    PluginEnvelopeStatus,
    PluginError,
    PluginManifest,
    PluginType,
    stable_payload_hash,
)
from career_harness.core.plugin.runtime import (
    CancellationToken,
    PluginCancelled,
    PluginContext,
    PluginHandler,
)
from career_harness.workers.plugin_echo import echo_worker


class PluginNotFound(LookupError):
    pass


class PluginPermissionDenied(PermissionError):
    pass


class PluginStateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RegisteredPlugin:
    manifest: PluginManifest
    handler: PluginHandler


def _builtin_manifest(
    *,
    plugin_id: str,
    name: str,
    capabilities: tuple[str, ...],
    description: str,
) -> PluginManifest:
    return PluginManifest(
        id=plugin_id,
        name=name,
        version="1.0.0",
        api_version="1",
        type=(
            PluginType.WORKER_PLUGIN
            if plugin_id == "echo-fixture"
            else PluginType.BUILTIN_ADAPTER
        ),
        source={
            "repo": f"builtin://{plugin_id}",
            "ref": "v1",
            "commit": f"builtin-{plugin_id}-v1",
            "license": "Apache-2.0",
        },
        capabilities=capabilities,
        permissions={"scope": ("read_models",)},
        data_contracts=("PluginEnvelope",),
        healthcheck={"command": "health", "timeout_ms": 5000},
        replacement={"compatible_capabilities": capabilities},
        dependencies=(),
        core_compatibility={"min_version": "0.1.0", "max_version": "0.x"},
        config_schema={},
        data_migration_version=0,
        cost_limits={"max_runtime_ms": 5000, "max_output_bytes": 1_000_000},
        user_visible_description=description,
        security_url="about:blank",
        terms_url="about:blank",
    )


def career_kb_local(payload: dict[str, Any], context: PluginContext) -> dict[str, Any]:
    context.cancellation.raise_if_cancelled()
    query = str(payload.get("query", "")).strip()
    return {
        "query": query,
        "items": [],
        "read_only": True,
        "evidence_refs": [],
        "message": "local knowledge index is empty" if not query else "no local matches",
    }


class PluginRegistry:
    def __init__(self, registrations: tuple[RegisteredPlugin, ...] | None = None) -> None:
        defaults = registrations or (
            RegisteredPlugin(
                _builtin_manifest(
                    plugin_id="echo-fixture",
                    name="Echo Fixture",
                    capabilities=("fixture.echo", "health"),
                    description="Deterministic offline worker fixture for plugin contracts.",
                ),
                echo_worker,
            ),
            RegisteredPlugin(
                _builtin_manifest(
                    plugin_id="career-kb-local",
                    name="Career Knowledge / Local",
                    capabilities=("knowledge.search", "health"),
                    description="Read-only local knowledge adapter; it cannot change Core truth.",
                ),
                career_kb_local,
            ),
        )
        self._plugins = {item.manifest.id: item for item in defaults}

    def register(self, manifest: PluginManifest, handler: PluginHandler) -> None:
        existing = self._plugins.get(manifest.id)
        if existing is not None:
            if existing.manifest.content_hash() != manifest.content_hash():
                raise ValueError(f"plugin id already registered: {manifest.id}")
            return
        self._plugins[manifest.id] = RegisteredPlugin(manifest, handler)

    def get(self, plugin_id: str) -> RegisteredPlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise PluginNotFound(plugin_id) from exc

    def list(self) -> tuple[RegisteredPlugin, ...]:
        return tuple(self._plugins.values())


class PermissionGate:
    def check(
        self,
        manifest: PluginManifest,
        *,
        capability: str,
        requested_permissions: tuple[str, ...] = (),
    ) -> None:
        if capability not in manifest.capabilities:
            raise PluginPermissionDenied(f"capability not declared: {capability}")
        declared = set(manifest.permissions.scope)
        declared.update(f"network:{item}" for item in manifest.permissions.network)
        declared.update(f"filesystem:{item}" for item in manifest.permissions.filesystem)
        declared.update(f"secret:{item}" for item in manifest.permissions.secrets)
        if manifest.permissions.external_write:
            declared.add("external_write")
        for permission in requested_permissions:
            if permission == "external_write" and not manifest.permissions.external_write:
                raise PluginPermissionDenied("external_write is denied by manifest")
            if permission not in declared:
                raise PluginPermissionDenied(f"permission not declared: {permission}")


def _scoped_read_model(
    engine: Engine,
    name: str,
    identifier: str,
) -> dict[str, Any] | None:
    allowed = {
        "evidence_ref": (
            "SELECT evidence_ref_id AS id FROM evidence_ref "
            "WHERE evidence_ref_id = :id"
        ),
        "plugin": (
            "SELECT plugin_id AS id FROM plugin_packages WHERE plugin_id = :id"
        ),
    }
    query = allowed.get(name)
    if query is None:
        raise ValueError("read model is outside plugin scope")
    with engine.connect() as connection:
        row = connection.execute(text(query), {"id": identifier}).mappings().first()
    return dict(row) if row is not None else None


class ScopedCoreReadClient:
    """A scoped read facade; the plugin cannot access an Engine or Connection."""

    __slots__ = ("_reader",)

    def __init__(self, engine: Engine) -> None:
        def reader(name: str, identifier: str) -> dict[str, Any] | None:
            return _scoped_read_model(engine, name, identifier)

        self._reader = reader

    def get_read_model(self, name: str, identifier: str) -> dict[str, Any] | None:
        return self._reader(name, identifier)


class PluginRunner:
    def __init__(self, permission_gate: PermissionGate | None = None) -> None:
        self.permission_gate = permission_gate or PermissionGate()

    def invoke(
        self,
        registration: RegisteredPlugin,
        *,
        request_id: str,
        capability: str,
        payload: dict[str, Any],
        context: PluginContext,
        requested_permissions: tuple[str, ...] = (),
        timeout_ms: int | None = None,
    ) -> PluginEnvelope:
        started_at = datetime.now(UTC)
        input_hash = stable_payload_hash(payload)
        manifest = registration.manifest
        try:
            self.permission_gate.check(
                manifest,
                capability=capability,
                requested_permissions=requested_permissions,
            )
            context.cancellation.raise_if_cancelled()
        except (PluginPermissionDenied, PluginCancelled) as exc:
            code = "permission_denied" if isinstance(exc, PluginPermissionDenied) else "cancelled"
            return PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=manifest.id,
                plugin_version=manifest.version,
                capability=capability,
                input_hash=input_hash,
                started_at=started_at,
                error=PluginError(code=code, message=str(exc)),
            )

        limit = timeout_ms or manifest.cost_limits.max_runtime_ms
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"plugin-{manifest.id}")
        future = executor.submit(registration.handler, payload, context)
        try:
            result = future.result(timeout=limit / 1000)
            if not isinstance(result, dict):
                raise TypeError("plugin handler must return an object")
            context.cancellation.raise_if_cancelled()
            evidence_refs = tuple(str(item) for item in result.pop("evidence_refs", ()))
            for evidence_ref in evidence_refs:
                if (
                    context.core is not None
                    and context.core.get_read_model("evidence_ref", evidence_ref) is None
                ):
                    raise ValueError(f"dangling evidence reference: {evidence_ref}")
            status = PluginEnvelopeStatus(str(result.pop("status", "ok")))
            if (
                len(json.dumps(result, sort_keys=True, default=str).encode("utf-8"))
                > manifest.cost_limits.max_output_bytes
            ):
                raise ValueError("plugin output exceeds declared max_output_bytes")
            output_hash = stable_payload_hash(result)
            return PluginEnvelope(
                request_id=request_id,
                plugin_id=manifest.id,
                plugin_version=manifest.version,
                capability=capability,
                status=status,
                data=result,
                evidence_refs=evidence_refs,
                input_hash=input_hash,
                output_hash=output_hash,
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        except FutureTimeoutError:
            context.cancellation.cancel()
            return PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=manifest.id,
                plugin_version=manifest.version,
                capability=capability,
                input_hash=input_hash,
                started_at=started_at,
                error=PluginError(
                    code="timeout",
                    message=f"plugin exceeded {limit}ms",
                    retryable=True,
                ),
            )
        except PluginCancelled as exc:
            return PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=manifest.id,
                plugin_version=manifest.version,
                capability=capability,
                input_hash=input_hash,
                started_at=started_at,
                error=PluginError(code="cancelled", message=str(exc), retryable=True),
            )
        except PluginPermissionDenied as exc:
            return PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=manifest.id,
                plugin_version=manifest.version,
                capability=capability,
                input_hash=input_hash,
                started_at=started_at,
                error=PluginError(code="permission_denied", message=str(exc)),
            )
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("career_harness.plugin").exception(
                "plugin invocation failed"
            )
            return PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=manifest.id,
                plugin_version=manifest.version,
                capability=capability,
                input_hash=input_hash,
                started_at=started_at,
                error=PluginError(code="plugin_error", message=str(exc)),
            )
        finally:
            if not future.done():
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)


class PluginLifecycleManager:
    def __init__(
        self,
        engine: Engine,
        registry: PluginRegistry | None = None,
        runner: PluginRunner | None = None,
    ) -> None:
        self.engine = engine
        self.registry = registry or PluginRegistry()
        self.runner = runner or PluginRunner()

    def _registered(self, plugin_id: str) -> RegisteredPlugin:
        return self.registry.get(plugin_id)

    def _audit(
        self,
        plugin_id: str,
        action: str,
        actor: str,
        payload: dict[str, Any],
        key: str | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            if key is not None:
                exists = connection.execute(
                    text(
                        "SELECT audit_id FROM plugin_audit_events "
                        "WHERE plugin_id=:plugin_id AND action=:action "
                        "AND idempotency_key=:key"
                    ),
                    {"plugin_id": plugin_id, "action": action, "key": key},
                ).first()
                if exists is not None:
                    return
            audit_id = f"audit_{uuid.uuid4().hex}"
            event_id = f"event_plugin_{uuid.uuid4().hex}"
            event_payload = {"plugin_id": plugin_id, "action": action, **payload}
            connection.execute(
                text(
                    "INSERT INTO plugin_audit_events "
                    "(audit_id, plugin_id, action, actor, idempotency_key, payload, occurred_at) "
                    "VALUES (:id, :plugin_id, :action, :actor, :key, :payload, :occurred_at)"
                ),
                {
                    "id": audit_id,
                    "plugin_id": plugin_id,
                    "action": action,
                    "actor": actor,
                    "key": key,
                    "payload": json.dumps(payload),
                    "occurred_at": datetime.now(UTC),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO domain_event "
                    "(event_id, event_type, entity_id, entity_revision, "
                    "command_id, payload, occurred_at) "
                    "VALUES (:event_id, :event_type, :entity_id, 1, "
                    ":command_id, :payload, :occurred_at)"
                ),
                {
                    "event_id": event_id,
                    "event_type": f"plugin.{action}",
                    "entity_id": plugin_id,
                    "command_id": f"plugin_{action}_{uuid.uuid4().hex}",
                    "payload": json.dumps({"audit_id": audit_id, **event_payload}),
                    "occurred_at": datetime.now(UTC),
                },
            )

    def catalog(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            installed = {
                row.plugin_id: dict(row._mapping)
                for row in connection.execute(text("SELECT * FROM plugin_installations"))
            }
        for row in installed.values():
            if isinstance(row.get("config"), str):
                row["config"] = json.loads(row["config"])
        result = []
        for item in self.registry.list():
            result.append(
                {
                    "manifest": item.manifest.model_dump(mode="json"),
                    "installed": item.manifest.id in installed,
                    "installation": installed.get(item.manifest.id),
                }
            )
        return result

    def install_preview(self, manifest: PluginManifest) -> dict[str, Any]:
        registered = self._registered(manifest.id)
        if registered.manifest.content_hash() != manifest.content_hash():
            raise PluginStateError("manifest does not match registered plugin")
        return {
            "plugin_id": manifest.id,
            "version": manifest.version,
            "content_hash": manifest.content_hash(),
            "permissions": manifest.permissions.model_dump(mode="json"),
            "external_write_blocked": not manifest.permissions.external_write,
            "requires_user_approval": manifest.permissions.external_write,
            "safe_to_install": manifest.type
            in {PluginType.BUILTIN_ADAPTER, PluginType.WORKER_PLUGIN},
        }

    def install(
        self,
        manifest: PluginManifest,
        *,
        actor: str = "user",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        preview = self.install_preview(manifest)
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            existing = connection.execute(
                text(
                    "SELECT plugin_id, current_version, status "
                    "FROM plugin_installations WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": manifest.id},
            ).mappings().first()
            if existing is not None:
                if existing["current_version"] == manifest.version:
                    self._audit(manifest.id, "install", actor, preview, idempotency_key)
                    return {
                        **preview,
                        "status": existing["status"],
                        "idempotent": True,
                    }
                previous = existing["current_version"]
                connection.execute(
                    text(
                        "INSERT OR REPLACE INTO plugin_releases "
                        "(plugin_id, version, release_commit, dependencies, "
                        "compatibility, scan_report, "
                        "content_hash, created_at) VALUES "
                        "(:plugin_id, :version, :commit, :dependencies, :compatibility, "
                        ":scan_report, :content_hash, :created_at)"
                    ),
                    self._release_values(manifest, now),
                )
                connection.execute(
                    text(
                        "UPDATE plugin_installations SET previous_version=:previous, "
                        "current_version=:version, pinned_release=:version, status='disabled', "
                        "enabled=0, updated_at=:now WHERE plugin_id=:plugin_id"
                    ),
                    {
                        "previous": previous,
                        "version": manifest.version,
                        "now": now,
                        "plugin_id": manifest.id,
                    },
                )
            else:
                connection.execute(
                    text(
                        "INSERT INTO plugin_packages "
                        "(plugin_id, manifest, source_repo, source_ref, source_commit, license, "
                        "trust, content_hash, created_at, updated_at) VALUES "
                        "(:plugin_id, :manifest, :repo, :ref, :commit, :license, :trust, "
                        ":hash, :now, :now)"
                    ),
                    self._package_values(manifest, now),
                )
                connection.execute(
                    text(
                        "INSERT INTO plugin_releases "
                        "(plugin_id, version, release_commit, dependencies, "
                        "compatibility, scan_report, "
                        "content_hash, created_at) VALUES "
                        "(:plugin_id, :version, :commit, :dependencies, :compatibility, "
                        ":scan_report, :content_hash, :created_at)"
                    ),
                    self._release_values(manifest, now),
                )
                connection.execute(
                    text(
                        "INSERT INTO plugin_installations "
                        "(plugin_id, current_version, previous_version, status, config, enabled, "
                        "pinned_release, installed_at, updated_at) VALUES "
                        "(:plugin_id, :version, NULL, 'installed', '{}', 0, :version, :now, :now)"
                    ),
                    {
                        "plugin_id": manifest.id,
                        "version": manifest.version,
                        "now": now,
                    },
                )
                for kind, scope, allowed in self._permissions(manifest):
                    connection.execute(
                        text(
                            "INSERT INTO plugin_permissions "
                            "(plugin_id, permission_kind, scope, allowed, created_at) "
                            "VALUES (:plugin_id, :kind, :scope, :allowed, :now)"
                        ),
                        {
                            "plugin_id": manifest.id,
                            "kind": kind,
                            "scope": scope,
                            "allowed": allowed,
                            "now": now,
                        },
                    )
        self._audit(manifest.id, "install", actor, preview, idempotency_key)
        return {**preview, "status": "installed", "idempotent": False}

    @staticmethod
    def _package_values(manifest: PluginManifest, now: datetime) -> dict[str, Any]:
        return {
            "plugin_id": manifest.id,
            "manifest": json.dumps(manifest.model_dump(mode="json")),
            "repo": manifest.source.repo,
            "ref": manifest.source.ref,
            "commit": manifest.source.commit,
            "license": manifest.source.license,
            "trust": (
                "trusted"
                if manifest.type is PluginType.BUILTIN_ADAPTER
                else "unverified"
            ),
            "hash": manifest.content_hash(),
            "now": now,
        }

    @staticmethod
    def _release_values(
        manifest: PluginManifest,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "plugin_id": manifest.id,
            "version": manifest.version,
            "commit": manifest.source.commit,
            "dependencies": json.dumps(list(manifest.dependencies)),
            "compatibility": json.dumps(
                manifest.core_compatibility.model_dump(mode="json")
            ),
            "scan_report": json.dumps(
                {"offline_fixture": manifest.type is PluginType.BUILTIN_ADAPTER}
            ),
            "content_hash": manifest.content_hash(),
            "created_at": now,
        }

    @staticmethod
    def _permissions(manifest: PluginManifest) -> list[tuple[str, str, bool]]:
        values = [("network", item, True) for item in manifest.permissions.network]
        values += [("filesystem", item, True) for item in manifest.permissions.filesystem]
        values += [("secret", item, True) for item in manifest.permissions.secrets]
        values += [("scope", item, True) for item in manifest.permissions.scope]
        values.append(
            ("external_write", "external_write", manifest.permissions.external_write)
        )
        return values

    def _set_enabled(
        self,
        plugin_id: str,
        enabled: bool,
        actor: str,
        action: str,
    ) -> dict[str, Any]:
        self._registered(plugin_id)
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT current_version, status FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
            if row is None:
                raise PluginStateError("plugin is not installed")
            status = "enabled" if enabled else "disabled"
            connection.execute(
                text(
                    "UPDATE plugin_installations SET enabled=:enabled, status=:status, "
                    "updated_at=:now WHERE plugin_id=:plugin_id"
                ),
                {
                    "enabled": enabled,
                    "status": status,
                    "now": datetime.now(UTC),
                    "plugin_id": plugin_id,
                },
            )
        self._audit(plugin_id, action, actor, {"enabled": enabled})
        return {
            "plugin_id": plugin_id,
            "enabled": enabled,
            "status": status,
            "version": row["current_version"],
        }

    def enable(self, plugin_id: str, *, actor: str = "user") -> dict[str, Any]:
        return self._set_enabled(plugin_id, True, actor, "enable")

    def disable(self, plugin_id: str, *, actor: str = "user") -> dict[str, Any]:
        return self._set_enabled(plugin_id, False, actor, "disable")

    def healthcheck(self, plugin_id: str, *, actor: str = "user") -> PluginEnvelope:
        registration = self._registered(plugin_id)
        result = self.runner.invoke(
            registration,
            request_id=f"health_{uuid.uuid4().hex}",
            capability="health",
            payload={},
            context=PluginContext(),
            timeout_ms=registration.manifest.healthcheck.timeout_ms,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE plugin_installations SET last_health_at=:now, "
                    "last_health_status=:status, updated_at=:now "
                    "WHERE plugin_id=:plugin_id"
                ),
                {
                    "now": datetime.now(UTC),
                    "status": "ok"
                    if result.status is PluginEnvelopeStatus.OK
                    else "error",
                    "plugin_id": plugin_id,
                },
            )
        self._audit(plugin_id, "healthcheck", actor, result.model_dump(mode="json"))
        return result

    def invoke(
        self,
        plugin_id: str,
        *,
        request_id: str,
        capability: str,
        payload: dict[str, Any],
        requested_permissions: tuple[str, ...] = (),
        timeout_ms: int | None = None,
        actor: str = "user",
        cancellation: CancellationToken | None = None,
    ) -> PluginEnvelope:
        registration = self._registered(plugin_id)
        input_hash = stable_payload_hash(payload)
        with self.engine.connect() as connection:
            previous_run = connection.execute(
                text("SELECT * FROM plugin_runs WHERE request_id=:request_id"),
                {"request_id": request_id},
            ).mappings().first()
        if previous_run is not None:
            if previous_run["input_hash"] != input_hash:
                return PluginEnvelope.error_envelope(
                    request_id=request_id,
                    plugin_id=plugin_id,
                    plugin_version=registration.manifest.version,
                    capability=capability,
                    input_hash=input_hash,
                    started_at=datetime.now(UTC),
                    error=PluginError(
                        code="idempotency_conflict",
                        message="request_id was reused with different input",
                    ),
                )
            return PluginEnvelope(
                request_id=previous_run["request_id"],
                plugin_id=previous_run["plugin_id"],
                plugin_version=previous_run["plugin_version"],
                capability=previous_run["capability"],
                status=previous_run["status"],
                data=json.loads(previous_run["trace"]).get("data", {}),
                evidence_refs=tuple(json.loads(previous_run["evidence_refs"])),
                input_hash=previous_run["input_hash"],
                output_hash=previous_run["output_hash"],
                started_at=previous_run["started_at"],
                finished_at=previous_run["finished_at"],
                error=(
                    PluginError(
                        code=previous_run["error_code"],
                        message=previous_run["error_message"],
                    )
                    if previous_run["error_code"]
                    else None
                ),
            )
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT enabled, current_version FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
        if row is None or not row["enabled"]:
            result = PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=plugin_id,
                plugin_version=registration.manifest.version,
                capability=capability,
                input_hash=stable_payload_hash(payload),
                started_at=datetime.now(UTC),
                error=PluginError(
                    code="plugin_disabled",
                    message="plugin is not enabled",
                ),
            )
        else:
            token = cancellation or CancellationToken(Event())
            context = PluginContext(
                core=ScopedCoreReadClient(self.engine),
                cancellation=token,
            )
            result = self.runner.invoke(
                registration,
                request_id=request_id,
                capability=capability,
                payload=payload,
                context=context,
                requested_permissions=requested_permissions,
                timeout_ms=timeout_ms,
            )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO plugin_runs "
                    "(run_id, request_id, plugin_id, plugin_version, capability, input_hash, "
                    "output_hash, status, cost, evidence_refs, trace, error_code, "
                    "error_message, started_at, finished_at) VALUES "
                    "(:run_id, :request_id, :plugin_id, :version, :capability, :input_hash, "
                    ":output_hash, :status, :cost, :evidence_refs, :trace, :error_code, "
                    ":error_message, :started_at, :finished_at)"
                ),
                {
                    "run_id": f"run_{uuid.uuid4().hex}",
                    "request_id": result.request_id,
                    "plugin_id": result.plugin_id,
                    "version": result.plugin_version,
                    "capability": result.capability,
                    "input_hash": result.input_hash,
                    "output_hash": result.output_hash,
                    "status": result.status.value,
                    "cost": json.dumps({}),
                    "evidence_refs": json.dumps(list(result.evidence_refs)),
                    "trace": json.dumps({"actor": actor, "data": result.data}),
                    "error_code": result.error.code if result.error else None,
                    "error_message": result.error.message if result.error else None,
                    "started_at": result.started_at,
                    "finished_at": result.finished_at,
                },
            )
        return result

    def update_preview(self, plugin_id: str) -> dict[str, Any]:
        registration = self._registered(plugin_id)
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_version FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
        current = row["current_version"] if row else None
        preview = {
            "plugin_id": plugin_id,
            "current_version": current,
            "candidate_version": registration.manifest.version,
            "available": current is None or current != registration.manifest.version,
            "tests": {"fixture": "pending"},
            "approval": "pending",
        }
        if current is not None:
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO plugin_update_plans "
                        "(plan_id, plugin_id, current_version, candidate_version, tests, "
                        "migration, approval, rollback_snapshot, created_at) VALUES "
                        "(:plan_id, :plugin_id, :current_version, :candidate_version, "
                        ":tests, :migration, 'pending', :rollback_snapshot, :created_at)"
                    ),
                    {
                        "plan_id": f"plan_{uuid.uuid4().hex}",
                        "plugin_id": plugin_id,
                        "current_version": current,
                        "candidate_version": registration.manifest.version,
                        "tests": json.dumps(preview["tests"]),
                        "migration": json.dumps({}),
                        "rollback_snapshot": json.dumps(
                            {"current_version": current}
                        ),
                        "created_at": datetime.now(UTC),
                    },
                )
        return preview

    def switch(
        self,
        plugin_id: str,
        *,
        version: str | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        registration = self._registered(plugin_id)
        candidate = version or registration.manifest.version
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT current_version, enabled FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
            if row is None:
                raise PluginStateError("plugin is not installed")
            release = connection.execute(
                text(
                    "SELECT version FROM plugin_releases "
                    "WHERE plugin_id=:plugin_id AND version=:version"
                ),
                {"plugin_id": plugin_id, "version": candidate},
            ).first()
            if release is None:
                raise PluginStateError("candidate release is not installed")
            connection.execute(
                text(
                    "UPDATE plugin_installations SET previous_version=:previous, "
                    "current_version=:candidate, pinned_release=:candidate, "
                    "updated_at=:now WHERE plugin_id=:plugin_id"
                ),
                {
                    "previous": row["current_version"],
                    "candidate": candidate,
                    "now": datetime.now(UTC),
                    "plugin_id": plugin_id,
                },
            )
        result = {
            "plugin_id": plugin_id,
            "previous_version": row["current_version"],
            "current_version": candidate,
            "enabled": bool(row["enabled"]),
        }
        self._audit(plugin_id, "switch", actor, result)
        return result

    def rollback(self, plugin_id: str, *, actor: str = "user") -> dict[str, Any]:
        self._registered(plugin_id)
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT current_version, previous_version FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
            if row is None:
                raise PluginStateError("plugin is not installed")
            target = row["previous_version"] or row["current_version"]
            connection.execute(
                text(
                    "UPDATE plugin_installations SET current_version=:target, "
                    "pinned_release=:target, status='rolled_back', enabled=0, "
                    "updated_at=:now WHERE plugin_id=:plugin_id"
                ),
                {
                    "target": target,
                    "now": datetime.now(UTC),
                    "plugin_id": plugin_id,
                },
            )
        result = {"plugin_id": plugin_id, "rolled_back_to": target, "enabled": False}
        self._audit(plugin_id, "rollback", actor, result)
        return result

    def audit(self, plugin_id: str) -> list[dict[str, Any]]:
        self._registered(plugin_id)
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT audit_id, plugin_id, action, actor, idempotency_key, payload, "
                    "occurred_at FROM plugin_audit_events WHERE plugin_id=:plugin_id "
                    "ORDER BY occurred_at, audit_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().all()
        return [
            {
                **dict(row),
                "payload": (
                    json.loads(row["payload"])
                    if isinstance(row["payload"], str)
                    else row["payload"]
                ),
            }
            for row in rows
        ]
