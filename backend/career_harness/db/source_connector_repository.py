from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.connectors.models import (
    ConflictPolicy,
    ConnectorStatus,
    DeletePolicy,
    SourceConnector,
    SyncMode,
    SyncRun,
    SyncStats,
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class SourceConnectorRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _event(
        connection: Any, event_type: str, entity_id: str, payload: dict[str, Any], now: datetime
    ) -> None:
        connection.execute(
            text(
                "INSERT INTO domain_event "
                "(event_id,event_type,entity_id,entity_revision,command_id,payload,occurred_at) "
                "VALUES (:event,:type,:entity,1,:command,:payload,:now)"
            ),
            {
                "event": f"event_connector_{uuid.uuid4().hex}",
                "type": event_type,
                "entity": entity_id,
                "command": f"connector_{uuid.uuid4().hex}",
                "payload": _json(payload),
                "now": now,
            },
        )

    def create_local_folder(
        self,
        *,
        display_name: str,
        root_path: str,
        conflict_policy: ConflictPolicy = ConflictPolicy.DEFER,
        delete_policy: DeletePolicy = DeletePolicy.MARK_DELETED,
    ) -> SourceConnector:
        return self._create(
            connector_type="local_folder",
            display_name=display_name,
            config={"root_path": root_path},
            conflict_policy=conflict_policy,
            delete_policy=delete_policy,
        )

    def create_legacy_agent_radar(
        self,
        *,
        display_name: str,
        root_path: str,
    ) -> SourceConnector:
        return self._create(
            connector_type="legacy_agent_radar",
            display_name=display_name,
            config={"root_path": root_path},
            conflict_policy=ConflictPolicy.DEFER,
            delete_policy=DeletePolicy.KEEP,
        )

    def create_github(
        self,
        *,
        display_name: str,
        repository_url: str,
        use_private_token: bool,
    ) -> SourceConnector:
        return self._create(
            connector_type="github",
            display_name=display_name,
            config={
                "repository_url": repository_url,
                "use_private_token": use_private_token,
                "read_only_network_confirmed": True,
            },
            conflict_policy=ConflictPolicy.DEFER,
            delete_policy=DeletePolicy.KEEP,
        )

    def _create(
        self,
        *,
        connector_type: str,
        display_name: str,
        config: dict[str, Any],
        conflict_policy: ConflictPolicy,
        delete_policy: DeletePolicy,
    ) -> SourceConnector:
        connector_id = f"connector_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_connector "
                    "(connector_id,connector_type,display_name,status,config,auth_schema,"
                    "conflict_policy,delete_policy,created_at,updated_at) VALUES "
                    "(:id,:type,:name,'active',:config,'{}',:conflict,:delete,:now,:now)"
                ),
                {
                    "id": connector_id,
                    "type": connector_type,
                    "name": display_name.strip(),
                    "config": _json(config),
                    "conflict": conflict_policy.value,
                    "delete": delete_policy.value,
                    "now": now,
                },
            )
            self._event(
                connection,
                "source.connector.created",
                connector_id,
                {"connector_type": connector_type},
                now,
            )
        return self.get(connector_id)

    def get(self, connector_id: str) -> SourceConnector:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM source_connector WHERE connector_id=:id"),
                    {"id": connector_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError("source connector not found")
        return self._connector(row)

    def list(self) -> tuple[SourceConnector, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM source_connector ORDER BY created_at DESC")
            ).mappings()
        return tuple(self._connector(row) for row in rows)

    def set_status(self, connector_id: str, status: ConnectorStatus) -> SourceConnector:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    "UPDATE source_connector SET status=:status,updated_at=:now "
                    "WHERE connector_id=:id"
                ),
                {"status": status.value, "now": now, "id": connector_id},
            )
            if result.rowcount != 1:
                raise KeyError("source connector not found")
            self._event(
                connection, f"source.connector.{status.value}", connector_id, {}, now
            )
        return self.get(connector_id)

    def start_run(self, connector: SourceConnector, mode: SyncMode) -> SyncRun:
        sync_run_id = f"sync_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_sync_run "
                    "(sync_run_id,connector_id,mode,status,cursor_before,created_count,"
                    "updated_count,skipped_count,deleted_count,failed_count,started_at) VALUES "
                    "(:id,:connector,:mode,'processing',:cursor,0,0,0,0,0,:now)"
                ),
                {
                    "id": sync_run_id,
                    "connector": connector.connector_id,
                    "mode": mode.value,
                    "cursor": _json(connector.sync_cursor) if connector.sync_cursor else None,
                    "now": now,
                },
            )
            self._event(connection, "source.sync.started", sync_run_id, {}, now)
        return self.get_run(sync_run_id)

    def existing_resources(self, connector_id: str) -> dict[str, dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM source_resource WHERE connector_id=:id"),
                {"id": connector_id},
            ).mappings()
        return {str(row["resource_key"]): dict(row) for row in rows}

    def upsert_resource(
        self,
        *,
        connector_id: str,
        resource_key: str,
        fingerprint: str,
        artifact_sha256: str,
        byte_length: int,
        source_modified_ns: int,
        now: datetime,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_resource "
                    "(connector_id,resource_key,status,fingerprint,artifact_sha256,byte_length,"
                    "source_modified_ns,first_seen_at,last_seen_at) VALUES "
                    "(:connector,:key,'active',:fingerprint,:artifact,:length,:mtime,:now,:now) "
                    "ON CONFLICT(connector_id,resource_key) DO UPDATE SET status='active',"
                    "fingerprint=excluded.fingerprint,artifact_sha256=excluded.artifact_sha256,"
                    "byte_length=excluded.byte_length,source_modified_ns=excluded.source_modified_ns,"
                    "last_seen_at=excluded.last_seen_at"
                ),
                {
                    "connector": connector_id,
                    "key": resource_key,
                    "fingerprint": fingerprint,
                    "artifact": artifact_sha256,
                    "length": byte_length,
                    "mtime": source_modified_ns,
                    "now": now,
                },
            )

    def mark_missing(self, connector_id: str, seen: set[str], now: datetime) -> int:
        existing = self.existing_resources(connector_id)
        missing = [
            key
            for key, row in existing.items()
            if key not in seen and row["status"] == "active"
        ]
        if not missing:
            return 0
        with self.engine.begin() as connection:
            for key in missing:
                connection.execute(
                    text(
                        "UPDATE source_resource SET status='source_deleted',last_seen_at=:now "
                        "WHERE connector_id=:connector AND resource_key=:key"
                    ),
                    {"connector": connector_id, "key": key, "now": now},
                )
        return len(missing)

    def complete_run(self, run_id: str, cursor: dict[str, Any], stats: SyncStats) -> SyncRun:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            run = self._run_row(connection, run_id)
            connection.execute(
                text(
                    "UPDATE source_sync_run SET status='completed',cursor_after=:cursor,"
                    "created_count=:created,updated_count=:updated,skipped_count=:skipped,"
                    "deleted_count=:deleted,failed_count=:failed,finished_at=:now "
                    "WHERE sync_run_id=:id"
                ),
                {"id": run_id, "cursor": _json(cursor), "now": now, **stats.model_dump()},
            )
            connection.execute(
                text(
                    "UPDATE source_connector SET sync_cursor=:cursor,updated_at=:now "
                    "WHERE connector_id=:id"
                ),
                {"cursor": _json(cursor), "now": now, "id": run["connector_id"]},
            )
            self._event(
                connection, "source.sync.completed", run_id, stats.model_dump(), now
            )
        return self.get_run(run_id)

    def fail_run(self, run_id: str, error: str) -> SyncRun:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            self._run_row(connection, run_id)
            connection.execute(
                text(
                    "UPDATE source_sync_run SET status='failed',failed_count=1,error=:error,"
                    "finished_at=:now WHERE sync_run_id=:id"
                ),
                {"id": run_id, "error": error[:4000], "now": now},
            )
            self._event(connection, "source.sync.failed", run_id, {}, now)
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> SyncRun:
        with self.engine.connect() as connection:
            row = self._run_row(connection, run_id)
        return self._run(row)

    def list_runs(self, connector_id: str) -> tuple[SyncRun, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT * FROM source_sync_run WHERE connector_id=:id ORDER BY started_at DESC"
                ),
                {"id": connector_id},
            ).mappings()
        return tuple(self._run(row) for row in rows)

    @staticmethod
    def _run_row(connection: Any, run_id: str) -> Any:
        row = connection.execute(
            text("SELECT * FROM source_sync_run WHERE sync_run_id=:id"), {"id": run_id}
        ).mappings().first()
        if row is None:
            raise KeyError("sync run not found")
        return row

    @staticmethod
    def _connector(row: Any) -> SourceConnector:
        values = dict(row)
        values["config"] = _loads(values["config"])
        values["auth_schema"] = _loads(values["auth_schema"])
        values["sync_cursor"] = _loads(values["sync_cursor"]) if values["sync_cursor"] else None
        return SourceConnector(**values)

    @staticmethod
    def _run(row: Any) -> SyncRun:
        return SyncRun(
            sync_run_id=row["sync_run_id"],
            connector_id=row["connector_id"],
            mode=row["mode"],
            status=row["status"],
            cursor_before=_loads(row["cursor_before"]) if row["cursor_before"] else None,
            cursor_after=_loads(row["cursor_after"]) if row["cursor_after"] else None,
            stats=SyncStats(
                created=row["created_count"],
                updated=row["updated_count"],
                skipped=row["skipped_count"],
                deleted=row["deleted_count"],
                failed=row["failed_count"],
            ),
            error=row["error"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
