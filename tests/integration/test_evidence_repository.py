from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from career_harness.core.evidence.models import ArtifactClass
from career_harness.db.evidence_repository import EvidenceRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    EvidenceArtifactRow,
    EvidenceRefRow,
    EvidenceSourceRow,
    SourceSnapshotRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url


def _insert_provenance(engine) -> None:  # type: ignore[no-untyped-def]
    captured_at = datetime(2026, 9, 19, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            EvidenceArtifactRow.__table__.insert(),
            {
                "artifact_id": "artifact_job_001",
                "sha256": "a" * 64,
                "media_type": "text/html",
                "artifact_class": "public_source",
                "byte_length": 1024,
            },
        )
        connection.execute(
            EvidenceSourceRow.__table__.insert(),
            {
                "source_id": "source_job_board_001",
                "source_type": "job_board",
                "locator": "https://example.invalid/jobs/001",
            },
        )
        connection.execute(
            SourceSnapshotRow.__table__.insert(),
            {
                "snapshot_id": "snapshot_job_001",
                "source_id": "source_job_board_001",
                "captured_at": captured_at,
                "artifact_id": "artifact_job_001",
            },
        )
        connection.execute(
            EvidenceRefRow.__table__.insert(),
            {
                "evidence_ref_id": "evidence_job_title",
                "snapshot_id": "snapshot_job_001",
                "artifact_id": "artifact_job_001",
                "selector": "main h1",
            },
        )
        connection.execute(
            EvidenceRefRow.__table__.insert(),
            {
                "evidence_ref_id": "evidence_job_requirements",
                "snapshot_id": "snapshot_job_001",
                "artifact_id": "artifact_job_001",
                "selector": "section.requirements",
            },
        )


def test_repository_reconstructs_exact_provenance_and_stable_order(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "evidence-read.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    _insert_provenance(engine)

    repository = EvidenceRepository(engine)
    result = repository.get("evidence_job_title")

    assert result is not None
    assert result.evidence_ref.selector == "main h1"
    assert result.snapshot.source_id == "source_job_board_001"
    assert result.source.source_type == "job_board"
    assert result.artifact.artifact_class is ArtifactClass.PUBLIC_SOURCE
    assert [
        item.evidence_ref.evidence_ref_id
        for item in repository.list_for_snapshot("snapshot_job_001")
    ] == ["evidence_job_requirements", "evidence_job_title"]
    assert repository.get("evidence_missing") is None
    assert repository.list_for_snapshot("snapshot_missing") == ()
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_evidence_ref_must_match_the_snapshot_artifact(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "evidence-integrity.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    _insert_provenance(engine)
    with engine.begin() as connection:
        connection.execute(
            EvidenceArtifactRow.__table__.insert(),
            {
                "artifact_id": "artifact_other",
                "sha256": "b" * 64,
                "media_type": "text/plain",
                "artifact_class": "public_source",
                "byte_length": 8,
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            EvidenceRefRow.__table__.insert(),
            {
                "evidence_ref_id": "evidence_forged",
                "snapshot_id": "snapshot_job_001",
                "artifact_id": "artifact_other",
                "selector": None,
            },
        )


def test_repository_fails_loud_on_a_malformed_snapshot_artifact_link(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "evidence-malformed.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    _insert_provenance(engine)
    with engine.begin() as connection:
        connection.execute(
            EvidenceArtifactRow.__table__.insert(),
            {
                "artifact_id": "artifact_other",
                "sha256": "b" * 64,
                "media_type": "text/plain",
                "artifact_class": "public_source",
                "byte_length": 8,
            },
        )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
        connection.commit()
        connection.execute(
            EvidenceRefRow.__table__.insert(),
            {
                "evidence_ref_id": "evidence_corrupt",
                "snapshot_id": "snapshot_job_001",
                "artifact_id": "artifact_other",
                "selector": None,
            },
        )
        connection.commit()

    repository = EvidenceRepository(engine)
    with pytest.raises(RuntimeError, match="artifact does not match"):
        repository.get("evidence_corrupt")
    with pytest.raises(RuntimeError, match="artifact does not match"):
        repository.list_for_snapshot("snapshot_job_001")


def test_provenance_is_immutable_and_rejects_credential_sessions(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "evidence-immutable.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    _insert_provenance(engine)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            EvidenceRefRow.__table__.update()
            .where(EvidenceRefRow.evidence_ref_id == "evidence_job_title")
            .values(selector="changed")
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            EvidenceSourceRow.__table__.delete().where(
                EvidenceSourceRow.source_id == "source_job_board_001"
            )
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            EvidenceArtifactRow.__table__.insert(),
            {
                "artifact_id": "artifact_session",
                "sha256": "c" * 64,
                "media_type": "application/octet-stream",
                "artifact_class": "credential_session",
                "byte_length": 12,
            },
        )
