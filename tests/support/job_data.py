from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.engine import Connection

from career_harness.db.models import (
    EvidenceArtifactRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    JobIdentityRow,
    JobRevisionEvidenceRefRow,
    JobRevisionRow,
    SourceSnapshotRow,
)


def seed_job_revision(engine: Engine, job_id: str, revision: int) -> None:
    with engine.begin() as connection:
        seed_job_revision_rows(connection, job_id, revision)


def seed_job_revision_rows(connection: Connection, job_id: str, revision: int) -> None:
    suffix = f"{job_id}_{revision}"
    artifact_id = f"artifact_{suffix}"
    source_id = f"source_{suffix}"
    snapshot_id = f"snapshot_{suffix}"
    evidence_ref_id = f"evidence_{suffix}"
    now = datetime.now(UTC)
    content_sha256 = hashlib.sha256(suffix.encode()).hexdigest()
    connection.execute(
        JobIdentityRow.__table__.insert().prefix_with("OR IGNORE"),
        {"job_id": job_id},
    )
    connection.execute(
        EvidenceArtifactRow.__table__.insert(),
        {
            "artifact_id": artifact_id,
            "sha256": content_sha256,
            "media_type": "text/plain",
            "artifact_class": "public_source",
            "byte_length": len(suffix),
        },
    )
    connection.execute(
        EvidenceSourceRow.__table__.insert(),
        {
            "source_id": source_id,
            "source_type": "test_fixture",
            "locator": f"test://{suffix}",
        },
    )
    connection.execute(
        SourceSnapshotRow.__table__.insert(),
        {
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "captured_at": now,
            "artifact_id": artifact_id,
        },
    )
    connection.execute(
        EvidenceRefRow.__table__.insert(),
        {
            "evidence_ref_id": evidence_ref_id,
            "snapshot_id": snapshot_id,
            "artifact_id": artifact_id,
            "selector": None,
        },
    )
    connection.execute(
        JobRevisionEvidenceRefRow.__table__.insert(),
        {
            "job_id": job_id,
            "job_revision": revision,
            "ordinal": 0,
            "evidence_ref_id": evidence_ref_id,
        },
    )
    connection.execute(
        JobRevisionRow.__table__.insert(),
        {
            "job_id": job_id,
            "revision": revision,
            "schema_version": 1,
            "content_sha256": content_sha256,
            "observed_at": now,
            "source_evidence_count": 1,
        },
    )
