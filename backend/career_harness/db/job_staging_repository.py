from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.job_source import (
    JobSourcePolicy,
    JobSourceTermsStatus,
    JobStagingRecord,
    JobStagingStatus,
    NormalizedJobRecord,
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(value: Any, default: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value if value is not None else default


class JobStagingRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, staging_id: str) -> JobStagingRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM job_staging_record WHERE staging_id=:id"),
                {"id": staging_id},
            ).mappings().first()
        return self._record(row) if row else None

    def list(self, *, status: JobStagingStatus | None = None) -> tuple[JobStagingRecord, ...]:
        query = "SELECT * FROM job_staging_record"
        params: dict[str, Any] = {}
        if status is not None:
            query += " WHERE status=:status"
            params["status"] = status.value
        query += " ORDER BY suggested_score DESC, staging_id"
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), params).mappings().all()
        return tuple(self._record(row) for row in rows)

    def list_source_policies(self) -> tuple[JobSourcePolicy, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT * FROM job_source_policy ORDER BY source_id")
            ).mappings().all()
        return tuple(self._policy(row) for row in rows)

    def find_duplicate(self, url_fingerprint: str, content_fingerprint: str) -> str | None:
        with self.engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT staging_id FROM job_staging_record WHERE "
                    "url_fingerprint=:url OR content_fingerprint=:content "
                    "ORDER BY created_at LIMIT 1"
                ),
                {"url": url_fingerprint, "content": content_fingerprint},
            ).scalar_one_or_none()

    def get_source_policy(self, source_id: str) -> JobSourcePolicy | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT * FROM job_source_policy WHERE source_id=:source_id"),
                {"source_id": source_id},
            ).mappings().first()
        return self._policy(row) if row else None

    def ensure_source_policy(self, source_id: str) -> JobSourcePolicy:
        policy = self.get_source_policy(source_id)
        if policy is not None:
            return policy
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO job_source_policy "
                    "(source_id, rate_limit_ms, max_retries, failure_threshold, "
                    "failure_count, disabled, last_error, updated_at) "
                    "VALUES (:source_id, 0, 2, 3, 0, 0, NULL, CURRENT_TIMESTAMP)"
                ),
                {"source_id": source_id},
            )
        result = self.get_source_policy(source_id)
        if result is None:
            raise RuntimeError("job source policy was not persisted")
        return result

    def record_source_success(self, source_id: str) -> JobSourcePolicy:
        self.ensure_source_policy(source_id)
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE job_source_policy SET failure_count=0, last_error=NULL, "
                    "updated_at=CURRENT_TIMESTAMP WHERE source_id=:source_id"
                ),
                {"source_id": source_id},
            )
        result = self.get_source_policy(source_id)
        if result is None:
            raise RuntimeError("job source policy disappeared")
        return result

    def record_source_failure(self, source_id: str, error: str) -> JobSourcePolicy:
        current = self.ensure_source_policy(source_id)
        failure_count = current.failure_count + 1
        disabled = failure_count >= current.failure_threshold
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE job_source_policy SET failure_count=:failure_count, "
                    "disabled=:disabled, last_error=:last_error, "
                    "updated_at=CURRENT_TIMESTAMP WHERE source_id=:source_id"
                ),
                {
                    "source_id": source_id,
                    "failure_count": failure_count,
                    "disabled": int(disabled),
                    "last_error": error[:2048],
                },
            )
        result = self.get_source_policy(source_id)
        if result is None:
            raise RuntimeError("job source policy disappeared")
        return result

    @staticmethod
    def _record(row: Any) -> JobStagingRecord:
        return JobStagingRecord(
            staging_id=row["staging_id"],
            source_id=row["source_id"],
            source_ref=row["source_ref"],
            raw_artifact_id=row["raw_artifact_id"],
            raw_sha256=row["raw_sha256"],
            url_fingerprint=row["url_fingerprint"],
            content_fingerprint=row["content_fingerprint"],
            normalized=NormalizedJobRecord.model_validate(_loads(row["normalized"], {})),
            terms_status=JobSourceTermsStatus(row["terms_status"]),
            status=JobStagingStatus(row["status"]),
            duplicate_of=row["duplicate_of"],
            suggested_score=row["suggested_score"],
            suggested_reasons=tuple(_loads(row["suggested_reasons"], [])),
            gaps=tuple(_loads(row["gaps"], [])),
            score_breakdown=dict(_loads(row["score_breakdown"], {})),
            admitted_job_id=row["admitted_job_id"],
            admitted_opportunity_id=row["admitted_opportunity_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _policy(row: Any) -> JobSourcePolicy:
        return JobSourcePolicy(
            source_id=row["source_id"],
            rate_limit_ms=row["rate_limit_ms"],
            max_retries=row["max_retries"],
            failure_threshold=row["failure_threshold"],
            failure_count=row["failure_count"],
            disabled=bool(row["disabled"]),
            last_error=row["last_error"],
            updated_at=row["updated_at"],
        )
