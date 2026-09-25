from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from career_harness.core.job import JobRequirementStatus
from career_harness.db.job_repository import JobRepository
from career_harness.db.migrations import upgrade_to_head
from career_harness.db.models import (
    CapabilityGraphVersionRow,
    CapabilityIdentityRow,
    CapabilityNodeRow,
    JobIdentityRow,
    JobRequirementEvidenceRefRow,
    JobRequirementIdentityRow,
    JobRequirementRevisionRow,
    JobRequirementScopeRow,
    JobRevisionEvidenceRefRow,
    JobRevisionRow,
)
from career_harness.db.session import create_sqlite_engine, sqlite_url
from tests.support.job_data import seed_job_revision


def _seed_official_capability(engine) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            CapabilityIdentityRow.__table__.insert(),
            {"capability_id": "capability_agents"},
        )
        connection.execute(
            CapabilityNodeRow.__table__.insert(),
            {
                "capability_id": "capability_agents",
                "graph_version_id": "graph_version_jobs",
                "canonical_name": "Agent Engineering",
                "description": "Build and evaluate agent systems.",
                "layer": "track",
                "lifecycle_status": "active",
            },
        )
        connection.execute(
            CapabilityGraphVersionRow.__table__.insert(),
            {
                "graph_version_id": "graph_version_jobs",
                "version_label": "jobs-1",
                "change_note": "Job requirement fixture graph.",
                "released_at": now,
                "released_by": "test-policy",
                "released_by_kind": "rule",
            },
        )


def _insert_requirement(
    connection,  # type: ignore[no-untyped-def]
    *,
    requirement_id: str,
    revision: int,
    status: str,
    job_revision: int = 1,
    graph_version_id: str | None = None,
) -> None:
    connection.execute(
        JobRequirementIdentityRow.__table__.insert().prefix_with("OR IGNORE"),
        {"requirement_id": requirement_id, "job_id": "job_001"},
    )
    connection.execute(
        JobRequirementScopeRow.__table__.insert(),
        {
            "requirement_id": requirement_id,
            "requirement_revision": revision,
            "ordinal": 0,
            "scope": "apply",
        },
    )
    connection.execute(
        JobRequirementEvidenceRefRow.__table__.insert(),
        {
            "requirement_id": requirement_id,
            "requirement_revision": revision,
            "ordinal": 0,
            "evidence_ref_id": f"evidence_job_001_{job_revision}",
        },
    )
    reviewed = status != "proposed"
    connection.execute(
        JobRequirementRevisionRow.__table__.insert(),
        {
            "requirement_id": requirement_id,
            "revision": revision,
            "schema_version": 1,
            "job_id": "job_001",
            "job_revision": job_revision,
            "requirement_text": "Build reliable agent workflows.",
            "importance": "required",
            "capability_id": "capability_agents" if status == "accepted" else None,
            "graph_version_id": (
                graph_version_id or "graph_version_jobs" if status == "accepted" else None
            ),
            "required_scope_count": 1,
            "source_evidence_count": 1,
            "status": status,
            "proposed_by": "extractor:test",
            "proposed_by_kind": "agent",
            "proposed_at": datetime.now(UTC),
            "reviewed_by": "user" if reviewed else None,
            "reviewed_by_kind": "user" if reviewed else None,
            "review_reason": "Reviewed against the source." if reviewed else None,
            "reviewed_at": datetime.now(UTC) if reviewed else None,
        },
    )


def _repository(tmp_path: Path):  # type: ignore[no-untyped-def]
    database_url = sqlite_url(tmp_path / "job-repository.db")
    upgrade_to_head(database_url)
    engine = create_sqlite_engine(database_url)
    seed_job_revision(engine, "job_001", 1)
    seed_job_revision(engine, "job_001", 2)
    _seed_official_capability(engine)
    return engine, JobRepository(engine)


def test_job_repository_reads_exact_latest_and_latest_then_status(tmp_path: Path) -> None:
    engine, repository = _repository(tmp_path)
    with engine.begin() as connection:
        _insert_requirement(
            connection, requirement_id="requirement_a", revision=1, status="accepted"
        )
        _insert_requirement(
            connection, requirement_id="requirement_a", revision=2, status="rejected"
        )
        _insert_requirement(
            connection, requirement_id="requirement_b", revision=1, status="accepted"
        )
        _insert_requirement(
            connection,
            requirement_id="requirement_c",
            revision=1,
            status="proposed",
            job_revision=2,
        )

    assert repository.get_job("job_001", 1).revision == 1  # type: ignore[union-attr]
    assert repository.get_job("job_001").revision == 2  # type: ignore[union-attr]
    assert repository.get_job("job_missing") is None
    assert repository.get_requirement("requirement_a", 1).status is JobRequirementStatus.ACCEPTED  # type: ignore[union-attr]
    assert repository.get_requirement("requirement_a").status is JobRequirementStatus.REJECTED  # type: ignore[union-attr]
    accepted = repository.list_requirements_for_job(
        "job_001", 1, status=JobRequirementStatus.ACCEPTED
    )
    assert [item.requirement_id for item in accepted] == ["requirement_b"]
    assert [item.requirement_id for item in repository.list_requirements_for_job("job_001", 1)] == [
        "requirement_a",
        "requirement_b",
    ]
    assert [
        item.requirement_id
        for item in repository.list_requirements_for_job(
            "job_001", 1, latest_only=False, status=JobRequirementStatus.ACCEPTED
        )
    ] == ["requirement_a", "requirement_b"]


def test_job_and_requirement_aggregates_are_parent_last_and_sealed(tmp_path: Path) -> None:
    engine, _ = _repository(tmp_path)
    now = datetime.now(UTC)
    with (
        pytest.raises(IntegrityError, match="aggregate is incomplete"),
        engine.begin() as connection,
    ):
        connection.execute(JobIdentityRow.__table__.insert(), {"job_id": "job_incomplete"})
        connection.execute(
            JobRevisionEvidenceRefRow.__table__.insert(),
            {
                "job_id": "job_incomplete",
                "job_revision": 1,
                "ordinal": 1,
                "evidence_ref_id": "evidence_job_001_1",
            },
        )
        connection.execute(
            JobRevisionRow.__table__.insert(),
            {
                "job_id": "job_incomplete",
                "revision": 1,
                "schema_version": 1,
                "content_sha256": "c" * 64,
                "observed_at": now,
                "source_evidence_count": 1,
            },
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(JobIdentityRow.__table__.insert(), {"job_id": "job_missing_evidence"})
        connection.execute(
            JobRevisionEvidenceRefRow.__table__.insert(),
            {
                "job_id": "job_missing_evidence",
                "job_revision": 1,
                "ordinal": 0,
                "evidence_ref_id": "evidence_missing",
            },
        )
    with (
        pytest.raises(IntegrityError, match="aggregate is incomplete"),
        engine.begin() as connection,
    ):
        connection.execute(
            JobRequirementIdentityRow.__table__.insert(),
            {"requirement_id": "requirement_incomplete", "job_id": "job_001"},
        )
        connection.execute(
            JobRequirementRevisionRow.__table__.insert(),
            {
                "requirement_id": "requirement_incomplete",
                "revision": 1,
                "schema_version": 1,
                "job_id": "job_001",
                "job_revision": 1,
                "requirement_text": "Incomplete aggregate.",
                "importance": "preferred",
                "required_scope_count": 1,
                "source_evidence_count": 1,
                "status": "proposed",
                "proposed_by": "agent",
                "proposed_by_kind": "agent",
                "proposed_at": now,
            },
        )

    with engine.begin() as connection:
        _insert_requirement(
            connection, requirement_id="requirement_sealed", revision=1, status="proposed"
        )
    with pytest.raises(IntegrityError, match="aggregate is sealed"), engine.begin() as connection:
        connection.execute(
            JobRequirementScopeRow.__table__.insert(),
            {
                "requirement_id": "requirement_sealed",
                "requirement_revision": 1,
                "ordinal": 1,
                "scope": "evidence",
            },
        )


def test_requirement_rejects_nonexistent_exact_official_node(tmp_path: Path) -> None:
    engine, _ = _repository(tmp_path)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        _insert_requirement(
            connection,
            requirement_id="requirement_wrong_graph",
            revision=1,
            status="accepted",
            graph_version_id="graph_version_missing",
        )


def test_requirement_rejects_missing_job_and_cross_job_identity_drift(tmp_path: Path) -> None:
    engine, _ = _repository(tmp_path)
    now = datetime.now(UTC)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            JobRequirementIdentityRow.__table__.insert(),
            {"requirement_id": "requirement_missing_job", "job_id": "job_001"},
        )
        connection.execute(
            JobRequirementScopeRow.__table__.insert(),
            {
                "requirement_id": "requirement_missing_job",
                "requirement_revision": 1,
                "ordinal": 0,
                "scope": "apply",
            },
        )
        connection.execute(
            JobRequirementEvidenceRefRow.__table__.insert(),
            {
                "requirement_id": "requirement_missing_job",
                "requirement_revision": 1,
                "ordinal": 0,
                "evidence_ref_id": "evidence_job_001_1",
            },
        )
        connection.execute(
            JobRequirementRevisionRow.__table__.insert(),
            {
                "requirement_id": "requirement_missing_job",
                "revision": 1,
                "schema_version": 1,
                "job_id": "job_001",
                "job_revision": 99,
                "requirement_text": "Missing exact Job revision.",
                "importance": "required",
                "required_scope_count": 1,
                "source_evidence_count": 1,
                "status": "proposed",
                "proposed_by": "agent",
                "proposed_by_kind": "agent",
                "proposed_at": now,
            },
        )

    seed_job_revision(engine, "job_002", 1)
    with engine.begin() as connection:
        _insert_requirement(
            connection, requirement_id="requirement_stable", revision=1, status="proposed"
        )
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            JobRequirementScopeRow.__table__.insert(),
            {
                "requirement_id": "requirement_stable",
                "requirement_revision": 2,
                "ordinal": 0,
                "scope": "apply",
            },
        )
        connection.execute(
            JobRequirementEvidenceRefRow.__table__.insert(),
            {
                "requirement_id": "requirement_stable",
                "requirement_revision": 2,
                "ordinal": 0,
                "evidence_ref_id": "evidence_job_002_1",
            },
        )
        connection.execute(
            JobRequirementRevisionRow.__table__.insert(),
            {
                "requirement_id": "requirement_stable",
                "revision": 2,
                "schema_version": 1,
                "job_id": "job_002",
                "job_revision": 1,
                "requirement_text": "Identity cannot move to another Job.",
                "importance": "required",
                "required_scope_count": 1,
                "source_evidence_count": 1,
                "status": "proposed",
                "proposed_by": "agent",
                "proposed_by_kind": "agent",
                "proposed_at": now,
            },
        )
