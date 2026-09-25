from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text


class ModelProviderRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM model_provider_config ORDER BY provider_id")
            ).mappings()
            return [dict(row) for row in rows]

    def get(self, provider_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM model_provider_config WHERE provider_id = :provider_id"),
                    {"provider_id": provider_id},
                )
                .mappings()
                .first()
            )
            return dict(row) if row else None

    def save(self, values: dict[str, Any]) -> dict[str, Any]:
        current = self.get(str(values["provider_id"]))
        revision = int(current["revision"]) + 1 if current else 1
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO model_provider_config (
                        provider_id, provider_kind, base_url, default_model, timeout_seconds,
                        has_secret, connection_status, last_checked_at, last_error_code,
                        revision, updated_at
                    ) VALUES (
                        :provider_id, :provider_kind, :base_url, :default_model, :timeout_seconds,
                        :has_secret, 'not_tested', NULL, NULL, :revision, :updated_at
                    ) ON CONFLICT(provider_id) DO UPDATE SET
                        provider_kind = excluded.provider_kind,
                        base_url = excluded.base_url,
                        default_model = excluded.default_model,
                        timeout_seconds = excluded.timeout_seconds,
                        has_secret = excluded.has_secret,
                        connection_status = 'not_tested',
                        last_checked_at = NULL,
                        last_error_code = NULL,
                        revision = excluded.revision,
                        updated_at = excluded.updated_at
                    """
                ),
                {**values, "revision": revision, "updated_at": now},
            )
        result = self.get(str(values["provider_id"]))
        assert result is not None
        return result

    def record_test(
        self,
        provider_id: str,
        *,
        success: bool,
        status_code: int | None,
        error_code: str | None,
        latency_ms: int,
        audit_id: str,
    ) -> dict[str, Any]:
        checked_at = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """INSERT INTO model_provider_connection_audit (
                        audit_id, provider_id, success, status_code,
                        error_code, latency_ms, checked_at
                    ) VALUES (
                        :audit_id, :provider_id, :success, :status_code,
                        :error_code, :latency_ms, :checked_at
                    )"""
                ),
                {
                    "audit_id": audit_id,
                    "provider_id": provider_id,
                    "success": success,
                    "status_code": status_code,
                    "error_code": error_code,
                    "latency_ms": latency_ms,
                    "checked_at": checked_at,
                },
            )
            connection.execute(
                text(
                    """UPDATE model_provider_config SET connection_status = :status,
                    last_checked_at = :checked_at, last_error_code = :error_code
                    WHERE provider_id = :provider_id"""
                ),
                {
                    "status": "connected" if success else "failed",
                    "checked_at": checked_at,
                    "error_code": error_code,
                    "provider_id": provider_id,
                },
            )
        result = self.get(provider_id)
        assert result is not None
        return result
