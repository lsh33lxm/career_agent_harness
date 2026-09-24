from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event
from typing import Any

from sqlalchemy import Engine, text

from career_harness import __version__
from career_harness.adapters.career_kb_weknora import CareerKbWeknoraAdapter
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


KNOWN_SPDX_LICENSES = {
    "APACHE-2.0",
    "BSD-2-CLAUSE",
    "BSD-3-CLAUSE",
    "MIT",
    "MPL-2.0",
    "LGPL-2.1-ONLY",
    "LGPL-3.0-ONLY",
    "GPL-2.0-ONLY",
    "GPL-3.0-ONLY",
}
UNKNOWN_LICENSES = {"", "UNKNOWN", "NOASSERTION", "UNLICENSED"}


def _scan_manifest(manifest: PluginManifest) -> dict[str, Any]:
    license_value = manifest.source.license.strip()
    license_upper = license_value.upper()
    repository_owned = manifest.source.repo.startswith("builtin://")
    license_verified = (
        license_upper not in UNKNOWN_LICENSES
        and license_upper in KNOWN_SPDX_LICENSES
    )
    notice_requirement = "not_applicable" if repository_owned else "manual_review_required"
    manual_review_status = "not_required" if repository_owned else "pending"
    license_report = {
        "spdx": license_value,
        "status": "verified" if license_verified else "unknown",
        "repository": manifest.source.repo,
        "ref": manifest.source.ref,
        "commit": manifest.source.commit,
        "commercial_restriction": license_upper in {"GPL-2.0-ONLY", "GPL-3.0-ONLY"},
        "notice_requirement": notice_requirement,
        "manual_review_status": manual_review_status,
        "network_lookup": False,
    }
    dependencies: list[dict[str, str]] = []
    for dependency in manifest.dependencies:
        name, _, declared_license = dependency.partition(";license=")
        dependency_license = declared_license.strip() or "UNKNOWN"
        dependency_verified = dependency_license.upper() in KNOWN_SPDX_LICENSES
        dependencies.append(
            {
                "name": name,
                "license": dependency_license,
                "status": "verified" if dependency_verified else "unknown",
            }
        )
    dependency_verified = all(item["status"] == "verified" for item in dependencies)
    dependency_report = {
        "status": "verified" if dependency_verified else "unknown",
        "scan_mode": "declared_license_only",
        "vulnerability_scan": "offline_unavailable",
        "network_lookup": False,
        "dependencies": dependencies,
    }
    security_report = {
        "status": "offline_pass" if repository_owned else "offline_review_required",
        "install_scripts_scanned": False,
        "install_scripts_status": "not_applicable" if repository_owned else "not_scanned",
        "network_domains": list(manifest.permissions.network),
        "external_write_declared": manifest.permissions.external_write,
        "network_access": "none" if not manifest.permissions.network else "declared_only",
    }
    overall = (
        "passed"
        if repository_owned and license_verified and dependency_verified
        else "quarantined"
    )
    return {
        "overall": overall,
        "license": license_report,
        "dependencies": dependency_report,
        "security": security_report,
        "permissions": manifest.permissions.model_dump(mode="json"),
    }


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
    options = payload.get("options")
    if context.core is not None:
        result = context.core.search_read_model(
            "knowledge",
            query,
            options if isinstance(options, dict) else None,
        )
        return {**result, "read_only": True}
    return {
        "query": query,
        "items": [],
        "read_only": True,
        "evidence_refs": [],
        "message": "local knowledge index is empty" if not query else "no local matches",
    }


def career_kb_weknora(payload: dict[str, Any], _context: PluginContext) -> dict[str, Any]:
    adapter = CareerKbWeknoraAdapter()
    capability = str(payload.get("operation", "search"))
    if capability == "list":
        return adapter.list(str(payload.get("query", "")))
    if capability == "read":
        return adapter.read(str(payload.get("passage_id", "")))
    if capability == "ask":
        return adapter.ask(str(payload.get("question", "")))
    return adapter.search(str(payload.get("query", "")))


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
            RegisteredPlugin(
                PluginManifest(
                    id="career-kb-weknora",
                    name="Career Knowledge / WeKnora",
                    version="0.1.0",
                    api_version="1",
                    type=PluginType.MCP_PLUGIN,
                    source={
                        "repo": "https://github.com/Tencent/WeKnora",
                        "ref": "v0.8.0",
                        "commit": "immutable-sha-v08",
                        "license": "Apache-2.0",
                    },
                    capabilities=(
                        "knowledge.search",
                        "knowledge.read",
                        "knowledge.ask",
                        "knowledge.list",
                        "health",
                    ),
                    permissions={
                        "network": ("configured-weknora-host",),
                        "filesystem": ("artifact-store:read",),
                        "secrets": ("weknora-api-key",),
                    },
                    data_contracts=("EvidenceRef", "KnowledgePassage", "PluginEnvelope"),
                    healthcheck={"command": "health", "timeout_ms": 5000},
                    replacement={
                        "compatible_capabilities": (
                            "knowledge.search",
                            "knowledge.read",
                            "knowledge.list",
                        )
                    },
                    dependencies=(),
                    core_compatibility={"min_version": "0.1.0", "max_version": "0.x"},
                    config_schema={},
                    data_migration_version=0,
                    cost_limits={"max_runtime_ms": 5000, "max_output_bytes": 1_000_000},
                    user_visible_description=(
                        "Read-only WeKnora adapter; blocked until endpoint, credentials "
                        "and terms are verified."
                    ),
                    security_url="https://github.com/Tencent/WeKnora/security",
                    terms_url="https://github.com/Tencent/WeKnora",
                ),
                career_kb_weknora,
            ),
        )
        self._plugins = {(item.manifest.id, item.manifest.version): item for item in defaults}

    def register(self, manifest: PluginManifest, handler: PluginHandler) -> None:
        key = (manifest.id, manifest.version)
        existing = self._plugins.get(key)
        if existing is not None:
            if existing.manifest.content_hash() != manifest.content_hash():
                raise ValueError(f"plugin id already registered: {manifest.id}")
            return
        self._plugins[key] = RegisteredPlugin(manifest, handler)

    def get(self, plugin_id: str, version: str | None = None) -> RegisteredPlugin:
        matches = [item for key, item in self._plugins.items() if key[0] == plugin_id]
        if not matches:
            raise PluginNotFound(plugin_id)
        if version is not None:
            for item in matches:
                if item.manifest.version == version:
                    return item
            raise PluginNotFound(f"{plugin_id}@{version}")
        return max(matches, key=lambda item: _version_key(item.manifest.version))

    def list(self) -> tuple[RegisteredPlugin, ...]:
        plugin_ids = sorted({key[0] for key in self._plugins})
        return tuple(self.get(plugin_id) for plugin_id in plugin_ids)

    def versions(self, plugin_id: str) -> tuple[RegisteredPlugin, ...]:
        matches = [item for key, item in self._plugins.items() if key[0] == plugin_id]
        if not matches:
            raise PluginNotFound(plugin_id)
        return tuple(sorted(matches, key=lambda item: _version_key(item.manifest.version)))


def _version_key(version: str) -> tuple[int, int, int, str]:
    core, _, suffix = version.partition("-")
    numbers = tuple(int(item) for item in core.split("."))
    return numbers[0], numbers[1], numbers[2], suffix


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


def _empty_knowledge_search(
    _query: str, _options: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"items": [], "evidence_sufficient": False}


def _envelope_metrics(result: PluginEnvelope) -> dict[str, Any]:
    latency_ms = max(
        0.0,
        (result.finished_at - result.started_at).total_seconds() * 1000,
    )
    output_bytes = len(
        json.dumps(result.data, sort_keys=True, default=str).encode("utf-8")
    )
    return {
        "latency_ms": round(latency_ms, 3),
        "provenance_hash": stable_payload_hash(list(result.evidence_refs)),
        "evidence_refs": list(result.evidence_refs),
        "output_hash": result.output_hash,
        "structured_output_hash": stable_payload_hash(result.data),
        "status": result.status.value,
        "error_code": result.error.code if result.error else None,
        "output_bytes": output_bytes,
    }


class ScopedCoreReadClient:
    """A scoped read facade; the plugin cannot access an Engine or Connection."""

    __slots__ = ("_reader", "_knowledge_search")

    def __init__(
        self,
        engine: Engine,
        knowledge_search: Callable[
            [str, dict[str, Any] | None], dict[str, Any]
        ] | None = None,
    ) -> None:
        def reader(name: str, identifier: str) -> dict[str, Any] | None:
            return _scoped_read_model(engine, name, identifier)

        self._reader = reader
        self._knowledge_search = knowledge_search or _empty_knowledge_search

    def get_read_model(self, name: str, identifier: str) -> dict[str, Any] | None:
        return self._reader(name, identifier)

    def search_read_model(
        self, name: str, query: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if name != "knowledge":
            raise ValueError("read model is outside plugin scope")
        return self._knowledge_search(query, options)


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
        knowledge_search: Callable[
            [str, dict[str, Any] | None], dict[str, Any]
        ] | None = None,
    ) -> None:
        self.engine = engine
        self.registry = registry or PluginRegistry()
        self.runner = runner or PluginRunner()
        self.knowledge_search = knowledge_search

    def _registered(self, plugin_id: str, version: str | None = None) -> RegisteredPlugin:
        return self.registry.get(plugin_id, version)

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
            scans = {
                (row["plugin_id"], row["version"]): (
                    json.loads(row["scan_report"])
                    if isinstance(row["scan_report"], str)
                    else row["scan_report"]
                )
                for row in connection.execute(
                    text(
                        "SELECT plugin_id, version, scan_report FROM plugin_releases "
                        "ORDER BY created_at DESC"
                    )
                ).mappings()
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
                    "release_scan": scans.get(
                        (item.manifest.id, item.manifest.version),
                        _scan_manifest(item.manifest),
                    ),
                }
            )
        return result

    def install_preview(self, manifest: PluginManifest) -> dict[str, Any]:
        registered = self._registered(manifest.id, manifest.version)
        if registered.manifest.content_hash() != manifest.content_hash():
            raise PluginStateError("manifest does not match registered plugin")
        scan_report = _scan_manifest(manifest)
        return {
            "plugin_id": manifest.id,
            "version": manifest.version,
            "content_hash": manifest.content_hash(),
            "permissions": manifest.permissions.model_dump(mode="json"),
            "scan_report": scan_report,
            "external_write_blocked": not manifest.permissions.external_write,
            "requires_user_approval": manifest.permissions.external_write,
            "safe_to_install": (
                manifest.type in {PluginType.BUILTIN_ADAPTER, PluginType.WORKER_PLUGIN}
                and scan_report["overall"] == "passed"
            ),
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
        audit_action = "install"
        result: dict[str, Any]
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
                    result = {
                        **preview,
                        "status": existing["status"],
                        "idempotent": True,
                    }
                else:
                    connection.execute(
                        text(
                            "INSERT OR IGNORE INTO plugin_releases "
                            "(plugin_id, version, release_commit, dependencies, "
                            "compatibility, scan_report, "
                            "content_hash, created_at) VALUES "
                            "(:plugin_id, :version, :commit, :dependencies, :compatibility, "
                            ":scan_report, :content_hash, :created_at)"
                        ),
                        self._release_values(manifest, now),
                    )
                    result = {
                        **preview,
                        "status": "candidate_staged",
                        "idempotent": False,
                    }
                    audit_action = "candidate_stage"
            else:
                initial_status = "installed" if preview["safe_to_install"] else "quarantined"
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
                        "(:plugin_id, :version, NULL, :status, :config, 0, :version, :now, :now)"
                    ),
                    {
                        "plugin_id": manifest.id,
                        "version": manifest.version,
                        "status": initial_status,
                        "config": json.dumps({"update_policy": "notify"}),
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
                result = {**preview, "status": initial_status, "idempotent": False}
        self._audit(manifest.id, audit_action, actor, result, idempotency_key)
        return result

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
                {
                    **_scan_manifest(manifest),
                    "offline_fixture": manifest.type is PluginType.BUILTIN_ADAPTER,
                }
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

    def _release_is_executable(
        self,
        connection: Any,
        plugin_id: str,
        version: str,
    ) -> bool:
        row = connection.execute(
            text(
                "SELECT scan_report, content_hash FROM plugin_releases "
                "WHERE plugin_id=:plugin_id AND version=:version"
            ),
            {"plugin_id": plugin_id, "version": version},
        ).mappings().first()
        if row is None:
            return False
        raw_report = row["scan_report"]
        report = json.loads(raw_report) if isinstance(raw_report, str) else raw_report
        try:
            manifest = self.registry.get(plugin_id, version).manifest
        except PluginNotFound:
            return False
        return bool(
            isinstance(report, dict)
            and report.get("overall") == "passed"
            and row["content_hash"] == manifest.content_hash()
            and _scan_manifest(manifest)["overall"] == "passed"
        )

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
            release_is_executable = self._release_is_executable(
                connection, plugin_id, row["current_version"]
            )
            if row["status"] == "quarantined" or not release_is_executable:
                if enabled:
                    raise PluginStateError("quarantined plugin cannot be enabled")
                status = "quarantined"
            else:
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
        with self.engine.connect() as connection:
            installation = connection.execute(
                text(
                    "SELECT current_version, status FROM plugin_installations "
                    "WHERE plugin_id=:id"
                ),
                {"id": plugin_id},
            ).mappings().first()
            release_is_executable = (
                self._release_is_executable(
                    connection, plugin_id, installation["current_version"]
                )
                if installation is not None
                else False
            )
        if installation is None:
            raise PluginStateError("plugin is not installed")
        if installation["status"] == "quarantined" or not release_is_executable:
            raise PluginStateError("quarantined plugin cannot execute healthcheck")
        version = installation["current_version"]
        registration = self._registered(plugin_id, version)
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
        input_hash = stable_payload_hash(payload)
        with self.engine.connect() as connection:
            installation = connection.execute(
                text(
                    "SELECT enabled, current_version, status FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
            release_is_executable = (
                self._release_is_executable(
                    connection, plugin_id, installation["current_version"]
                )
                if installation is not None
                else False
            )
        registration = self._registered(
            plugin_id,
            installation["current_version"] if installation is not None else None,
        )
        if installation is not None and not release_is_executable:
            return PluginEnvelope.error_envelope(
                request_id=request_id,
                plugin_id=plugin_id,
                plugin_version=registration.manifest.version,
                capability=capability,
                input_hash=input_hash,
                started_at=datetime.now(UTC),
                error=PluginError(
                    code="plugin_quarantined",
                    message="plugin release has not passed the frozen scan gate",
                ),
            )
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
        if (
            installation is None
            or not installation["enabled"]
            or installation["status"] == "quarantined"
        ):
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
                core=ScopedCoreReadClient(self.engine, self.knowledge_search),
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
            metrics = _envelope_metrics(result)
            connection.execute(
                text(
                    "INSERT INTO plugin_runs "
                    "(run_id, request_id, plugin_id, plugin_version, capability, input_hash, "
                    "output_hash, status, cost, evidence_refs, provenance_hash, latency_ms, "
                    "trace, error_code, error_message, started_at, finished_at) VALUES "
                    "(:run_id, :request_id, :plugin_id, :version, :capability, :input_hash, "
                    ":output_hash, :status, :cost, :evidence_refs, :provenance_hash, :latency_ms, "
                    ":trace, :error_code, :error_message, :started_at, :finished_at)"
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
                    "cost": json.dumps(
                        {
                            "latency_ms": metrics["latency_ms"],
                            "output_bytes": metrics["output_bytes"],
                        }
                    ),
                    "evidence_refs": json.dumps(list(result.evidence_refs)),
                    "provenance_hash": metrics["provenance_hash"],
                    "latency_ms": metrics["latency_ms"],
                    "trace": json.dumps({"actor": actor, "data": result.data}),
                    "error_code": result.error.code if result.error else None,
                    "error_message": result.error.message if result.error else None,
                    "started_at": result.started_at,
                    "finished_at": result.finished_at,
                },
            )
        return result

    def update_preview(
        self,
        plugin_id: str,
        *,
        capability: str | None = None,
        fixture: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        registration = self._registered(plugin_id)
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_version, config FROM plugin_installations "
                    "WHERE plugin_id=:plugin_id"
                ),
                {"plugin_id": plugin_id},
            ).mappings().first()
        if row is None:
            raise PluginStateError("plugin is not installed")
        current = row["current_version"]
        current_registration = self._registered(plugin_id, current)
        candidate = registration.manifest
        current_manifest = current_registration.manifest
        selected_capability = capability or next(
            (
                item
                for item in candidate.capabilities
                if item != "health" and item in current_manifest.capabilities
            ),
            "health",
        )
        shadow_payload = fixture or {}
        current_result = self.runner.invoke(
            current_registration,
            request_id=f"shadow_current_{uuid.uuid4().hex}",
            capability=selected_capability,
            payload=dict(shadow_payload),
            context=PluginContext(),
        )
        candidate_result = self.runner.invoke(
            registration,
            request_id=f"shadow_candidate_{uuid.uuid4().hex}",
            capability=selected_capability,
            payload=dict(shadow_payload),
            context=PluginContext(),
        )
        current_metrics = _envelope_metrics(current_result)
        candidate_metrics = _envelope_metrics(candidate_result)
        current_permissions = self._permission_set(current_manifest)
        candidate_permissions = self._permission_set(candidate)
        compatibility = self._core_compatible(candidate)
        scan_report = _scan_manifest(candidate)
        license_verified = scan_report["license"]["status"] == "verified"
        capability_compatible = set(current_manifest.replacement.compatible_capabilities) <= set(
            candidate.capabilities
        )
        error_behavior_equal = (
            current_metrics["status"] == candidate_metrics["status"]
            and current_metrics["error_code"] == candidate_metrics["error_code"]
        )
        provenance_equal = current_metrics["provenance_hash"] == candidate_metrics[
            "provenance_hash"
        ]
        structured_output_equal = current_metrics["structured_output_hash"] == candidate_metrics[
            "structured_output_hash"
        ]
        output_equal = current_metrics["output_hash"] == candidate_metrics["output_hash"]
        latency_regression = candidate_metrics["latency_ms"] > max(
            current_metrics["latency_ms"] * 1.5,
            current_metrics["latency_ms"] + 50,
        )
        shadow_passed = all(
            (error_behavior_equal, provenance_equal, structured_output_equal, output_equal)
        )
        permission_escalation = sorted(candidate_permissions - current_permissions)
        rollback_reasons = [
            reason
            for reason, failed in (
                ("shadow_output_mismatch", not output_equal),
                ("structured_output_mismatch", not structured_output_equal),
                ("provenance_mismatch", not provenance_equal),
                ("error_behavior_regression", not error_behavior_equal),
                ("latency_regression", latency_regression),
            )
            if failed
        ]
        safe_to_switch = all(
            (
                compatibility,
                scan_report["overall"] == "passed",
                license_verified,
                capability_compatible,
                shadow_passed,
                not latency_regression,
            )
        ) and not permission_escalation
        tests = {
            "core_compatible": compatibility,
            "license_verified": license_verified,
            "capability_compatible": capability_compatible,
            "shadow_passed": shadow_passed,
            "shadow_capability": selected_capability,
            "current_output_hash": current_result.output_hash,
            "candidate_output_hash": candidate_result.output_hash,
            "current_metrics": current_metrics,
            "candidate_metrics": candidate_metrics,
            "error_behavior_equal": error_behavior_equal,
            "provenance_equal": provenance_equal,
            "structured_output_equal": structured_output_equal,
            "latency_regression": latency_regression,
            "license_scan": scan_report,
            "permission_escalation": permission_escalation,
            "safe_to_switch": safe_to_switch,
        }
        preview = {
            "plugin_id": plugin_id,
            "current_version": current,
            "candidate_version": candidate.version,
            "available": current != candidate.version,
            "tests": tests,
            "permission_diff": {
                "added": permission_escalation,
                "removed": sorted(current_permissions - candidate_permissions),
            },
            "migration": {
                "from": current_manifest.data_migration_version,
                "to": candidate.data_migration_version,
                "required": candidate.data_migration_version
                != current_manifest.data_migration_version,
            },
            "rollback_recommendation": {
                "action": "rollback" if rollback_reasons else "retain",
                "automatic": False,
                "reasons": rollback_reasons,
            },
            "approval": "pending" if safe_to_switch else "rejected",
        }
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO plugin_releases "
                    "(plugin_id, version, release_commit, dependencies, compatibility, "
                    "scan_report, content_hash, created_at) VALUES "
                    "(:plugin_id, :version, :commit, :dependencies, :compatibility, "
                    ":scan_report, :content_hash, :created_at)"
                ),
                self._release_values(candidate, datetime.now(UTC)),
            )
            connection.execute(
                    text(
                        "INSERT INTO plugin_update_plans "
                        "(plan_id, plugin_id, current_version, candidate_version, tests, "
                        "migration, approval, rollback_snapshot, created_at) VALUES "
                        "(:plan_id, :plugin_id, :current_version, :candidate_version, "
                        ":tests, :migration, :approval, :rollback_snapshot, :created_at)"
                    ),
                    {
                        "plan_id": f"plan_{uuid.uuid4().hex}",
                        "plugin_id": plugin_id,
                        "current_version": current,
                        "candidate_version": candidate.version,
                        "tests": json.dumps(tests),
                        "migration": json.dumps(preview["migration"]),
                        "approval": preview["approval"],
                        "rollback_snapshot": json.dumps(
                            {"current_version": current}
                        ),
                        "created_at": datetime.now(UTC),
                    },
                )
        self._audit(plugin_id, "update_preview", "user", preview)
        return preview

    @staticmethod
    def _permission_set(manifest: PluginManifest) -> set[str]:
        values = {f"network:{item}" for item in manifest.permissions.network}
        values.update(f"filesystem:{item}" for item in manifest.permissions.filesystem)
        values.update(f"secret:{item}" for item in manifest.permissions.secrets)
        values.update(f"scope:{item}" for item in manifest.permissions.scope)
        if manifest.permissions.external_write:
            values.add("external_write")
        return values

    @staticmethod
    def _core_compatible(manifest: PluginManifest) -> bool:
        current = _version_key(__version__)[:3]
        minimum = _version_key(manifest.core_compatibility.min_version)[:3]
        maximum_text = manifest.core_compatibility.max_version
        if maximum_text.endswith(".x"):
            prefix = tuple(int(item) for item in maximum_text[:-2].split("."))
            maximum_ok = current[: len(prefix)] == prefix
        else:
            maximum_ok = current <= _version_key(maximum_text)[:3]
        return current >= minimum and maximum_ok

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
            if not self._release_is_executable(connection, plugin_id, candidate):
                raise PluginStateError("candidate release is quarantined")
            plan = connection.execute(
                text(
                    "SELECT plan_id, tests, approval FROM plugin_update_plans "
                    "WHERE plugin_id=:plugin_id AND candidate_version=:version "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"plugin_id": plugin_id, "version": candidate},
            ).mappings().first()
            if candidate != row["current_version"]:
                tests = json.loads(plan["tests"]) if plan is not None else {}
                if plan is None or plan["approval"] != "pending" or not tests.get(
                    "safe_to_switch"
                ):
                    raise PluginStateError("candidate has no approved-safe update preview")
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
            if plan is not None:
                connection.execute(
                    text(
                        "UPDATE plugin_update_plans SET approval='applied' "
                        "WHERE plan_id=:plan_id"
                    ),
                    {"plan_id": plan["plan_id"]},
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
            target_status = (
                "rolled_back"
                if self._release_is_executable(connection, plugin_id, target)
                else "quarantined"
            )
            connection.execute(
                text(
                    "UPDATE plugin_installations SET current_version=:target, "
                    "pinned_release=:target, status=:status, enabled=0, "
                    "updated_at=:now WHERE plugin_id=:plugin_id"
                ),
                {
                    "target": target,
                    "status": target_status,
                    "now": datetime.now(UTC),
                    "plugin_id": plugin_id,
                },
            )
        result = {
            "plugin_id": plugin_id,
            "rolled_back_to": target,
            "enabled": False,
            "status": target_status,
        }
        self._audit(plugin_id, "rollback", actor, result)
        return result

    def set_update_policy(
        self, plugin_id: str, policy: str, *, actor: str = "user"
    ) -> dict[str, Any]:
        if policy not in {"notify", "patch_auto", "manual"}:
            raise ValueError("update policy must be notify, patch_auto or manual")
        self._registered(plugin_id)
        with self.engine.begin() as connection:
            raw = connection.execute(
                text("SELECT config FROM plugin_installations WHERE plugin_id=:id"),
                {"id": plugin_id},
            ).scalar_one_or_none()
            if raw is None:
                raise PluginStateError("plugin is not installed")
            config = json.loads(raw) if isinstance(raw, str) else dict(raw)
            config["update_policy"] = policy
            connection.execute(
                text(
                    "UPDATE plugin_installations SET config=:config, updated_at=:now "
                    "WHERE plugin_id=:id"
                ),
                {"config": json.dumps(config), "now": datetime.now(UTC), "id": plugin_id},
            )
        result = {"plugin_id": plugin_id, "update_policy": policy, "auto_switch": False}
        self._audit(plugin_id, "update_policy", actor, result)
        return result

    def uninstall_preview(self, plugin_id: str) -> dict[str, Any]:
        self._registered(plugin_id)
        with self.engine.connect() as connection:
            installation = connection.execute(
                text("SELECT enabled FROM plugin_installations WHERE plugin_id=:id"),
                {"id": plugin_id},
            ).mappings().first()
            if installation is None:
                raise PluginStateError("plugin is not installed")
            run_count = connection.execute(
                text("SELECT count(*) FROM plugin_runs WHERE plugin_id=:id"),
                {"id": plugin_id},
            ).scalar_one()
        return {
            "plugin_id": plugin_id,
            "enabled": bool(installation["enabled"]),
            "run_count": run_count,
            "core_truth_deleted": False,
            "artifact_bytes_deleted": False,
            "removal_allowed": not bool(installation["enabled"]),
            "retained_records": ("plugin_runs", "plugin_audit_events", "artifacts"),
        }

    def rollback_recommendation(self, plugin_id: str) -> dict[str, Any]:
        self._registered(plugin_id)
        with self.engine.connect() as connection:
            installation = connection.execute(
                text(
                    "SELECT current_version, previous_version FROM plugin_installations "
                    "WHERE plugin_id=:id"
                ),
                {"id": plugin_id},
            ).mappings().first()
            if installation is None:
                raise PluginStateError("plugin is not installed")
            rows = connection.execute(
                text(
                    "SELECT plugin_version, status, error_code, latency_ms, provenance_hash "
                    "FROM plugin_runs WHERE plugin_id=:id AND plugin_version IN "
                    "(:current, :previous)"
                ),
                {
                    "id": plugin_id,
                    "current": installation["current_version"],
                    "previous": installation["previous_version"] or installation["current_version"],
                },
            ).mappings().all()
        current_rows = [
            row for row in rows if row["plugin_version"] == installation["current_version"]
        ]
        previous_rows = [
            row
            for row in rows
            if row["plugin_version"] == installation["previous_version"]
        ]
        if not current_rows or not previous_rows:
            return {
                "plugin_id": plugin_id,
                "action": "retain",
                "automatic": False,
                "reason": "insufficient_observation_window",
                "current_version": installation["current_version"],
                "previous_version": installation["previous_version"],
            }

        def stats(values: list[dict[str, Any]]) -> dict[str, Any]:
            errors = sum(1 for row in values if row["status"] == "error")
            latencies = [float(row["latency_ms"] or 0) for row in values]
            return {
                "run_count": len(values),
                "error_rate": errors / len(values),
                "average_latency_ms": sum(latencies) / len(latencies),
                "provenance_hashes": sorted({row["provenance_hash"] for row in values}),
            }

        current_stats = stats(current_rows)
        previous_stats = stats(previous_rows)
        reasons: list[str] = []
        if current_stats["error_rate"] > previous_stats["error_rate"]:
            reasons.append("error_rate_regression")
        if current_stats["average_latency_ms"] > max(
            previous_stats["average_latency_ms"] * 1.5,
            previous_stats["average_latency_ms"] + 50,
        ):
            reasons.append("latency_regression")
        if set(current_stats["provenance_hashes"]).isdisjoint(
            previous_stats["provenance_hashes"]
        ):
            reasons.append("provenance_mismatch")
        return {
            "plugin_id": plugin_id,
            "action": "rollback" if reasons else "retain",
            "automatic": False,
            "reasons": reasons,
            "current_version": installation["current_version"],
            "previous_version": installation["previous_version"],
            "current": current_stats,
            "previous": previous_stats,
        }

    def audit_summary(self, plugin_id: str) -> dict[str, Any]:
        self._registered(plugin_id)
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT status, cost, trace, latency_ms, provenance_hash, error_code "
                    "FROM plugin_runs WHERE plugin_id=:id "
                    "ORDER BY started_at"
                ),
                {"id": plugin_id},
            ).mappings().all()
            scopes = connection.execute(
                text(
                    "SELECT permission_kind, scope FROM plugin_permissions "
                    "WHERE plugin_id=:id AND allowed=1 ORDER BY permission_kind, scope"
                ),
                {"id": plugin_id},
            ).all()
        errors = sum(1 for row in rows if row["status"] == "error")
        latencies = [float(row["latency_ms"] or 0) for row in rows]
        provenance_hashes = sorted({row["provenance_hash"] for row in rows})
        error_codes = sorted({row["error_code"] for row in rows if row["error_code"]})
        return {
            "plugin_id": plugin_id,
            "run_count": len(rows),
            "error_count": errors,
            "error_rate": 0 if not rows else round(errors / len(rows), 6),
            "latency": {
                "average_ms": 0 if not latencies else round(sum(latencies) / len(latencies), 3),
                "max_ms": 0 if not latencies else round(max(latencies), 3),
            },
            "provenance_hashes": provenance_hashes,
            "error_codes": error_codes,
            "declared_data_scopes": [f"{kind}:{scope}" for kind, scope in scopes],
            "cost": {"recorded_runs": len(rows), "external_cost_known": False},
            "rollback_recommendation": self.rollback_recommendation(plugin_id),
        }

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
