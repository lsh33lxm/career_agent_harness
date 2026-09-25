from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, text

from career_harness.core.job_lifecycle import JobListingLifecycleStatus, JobListingObservation


class JobLifecycleRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list(self, *, source_id: str | None = None) -> tuple[JobListingObservation, ...]:
        query = "SELECT * FROM job_listing_observation"
        params: dict[str, Any] = {}
        if source_id is not None:
            query += " WHERE source_id=:source_id"
            params["source_id"] = source_id
        query += " ORDER BY source_id, query, source_ref"
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), params).mappings().all()
        return tuple(self._model(row) for row in rows)

    def get(
        self, source_id: str, query: str, url_fingerprint: str
    ) -> JobListingObservation | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT * FROM job_listing_observation "
                    "WHERE source_id=:source_id AND query=:query "
                    "AND url_fingerprint=:url_fingerprint"
                ),
                {
                    "source_id": source_id,
                    "query": query,
                    "url_fingerprint": url_fingerprint,
                },
            ).mappings().first()
        return self._model(row) if row else None

    @staticmethod
    def _model(row: Any) -> JobListingObservation:
        return JobListingObservation(
            observation_id=row["observation_id"],
            source_id=row["source_id"],
            query=row["query"],
            source_ref=row["source_ref"],
            url_fingerprint=row["url_fingerprint"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
            last_checked_at=row["last_checked_at"],
            consecutive_missing=row["consecutive_missing"],
            status=JobListingLifecycleStatus(row["status"]),
            last_success_run_id=row["last_success_run_id"],
        )
