from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect

from career_harness.adapters.job_sources import ManualJobSource, OfflineFixtureJobSource
from career_harness.core.job_source import (
    JobSourceHealth,
    JobSourceTerms,
    JobSourceTermsStatus,
    JobStagingStatus,
    RawJobRecord,
)
from career_harness.db.migrations import alembic_config
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.services.opportunity_radar_service import OpportunityRadarService
from career_harness.storage import ArtifactStore
from tests.integration.test_fact_service import _engine


def _service(tmp_path: Path) -> OpportunityRadarService:
    return OpportunityRadarService(_engine(tmp_path), ArtifactStore(tmp_path / "artifacts"))


def test_offline_source_stages_ranks_deduplicates_and_user_admits(tmp_path: Path) -> None:
    service = _service(tmp_path)
    records = service.collect(
        OfflineFixtureJobSource(),
        query="platform",
        desired_terms=("Python", "Kubernetes", "Rust"),
    )
    assert len(records) == 1
    staged = records[0]
    assert staged.status is JobStagingStatus.STAGED
    assert staged.suggested_score == pytest.approx(2 / 3, abs=0.001)
    assert staged.gaps == ("Rust",)
    assert service.artifact_store.read(staged.raw_sha256)
    assert staged.normalized.location == "Remote"

    duplicate = service.collect(
        ManualJobSource(
            (
                RawJobRecord(
                    source_ref="fixture://jobs/platform-engineer",
                    raw_text=(
                        '{"title":"Platform Engineer","company":"Fixture Labs",'
                        '"location":"Remote","remote":true,'
                        '"requirements":["Python","SQLite","Kubernetes"]}'
                    ),
                ),
            )
        ),
        query="",
    )[0]
    assert duplicate.status is JobStagingStatus.DUPLICATE
    assert duplicate.duplicate_of == staged.staging_id
    with pytest.raises(ValueError, match="duplicate"):
        service.admit(duplicate.staging_id)

    admitted = service.admit(staged.staging_id)
    assert admitted.admission.opportunity is not None
    persisted = service.repository.get(staged.staging_id)
    assert persisted is not None
    assert persisted.status is JobStagingStatus.ADMITTED
    assert persisted.admitted_job_id == admitted.admission.decision.job.job_id
    assert persisted.admitted_opportunity_id == admitted.admission.opportunity.entity_id
    seed = service.resume_proposal_seed(staged.staging_id)
    assert seed.status == "proposal_only"
    assert seed.opportunity_id == persisted.admitted_opportunity_id
    assert seed.evidence_ref_id.startswith("evidence_job_staging_")


def test_deal_breaker_zeroes_suggested_score_without_changing_user_priority(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    staged = service.collect(
        OfflineFixtureJobSource(),
        query="",
        desired_terms=("Python",),
        excluded_terms=("Remote",),
    )[0]
    assert staged.suggested_score == 0
    assert staged.suggested_reasons == ("deal-breaker: Remote",)
    assert staged.admitted_opportunity_id is None


def test_source_failure_does_not_create_staging_records(tmp_path: Path) -> None:
    class FailedSource(OfflineFixtureJobSource):
        def search(self, query: str) -> tuple[RawJobRecord, ...]:
            raise RuntimeError("offline source failed")

        def health(self) -> JobSourceHealth:
            return JobSourceHealth(status="ok", message="ready before collection")

        def terms(self) -> JobSourceTerms:
            return JobSourceTerms(
                source_id=self.source_id,
                status=JobSourceTermsStatus.VERIFIED,
                note="test fixture",
            )

    service = _service(tmp_path)
    with pytest.raises(RuntimeError, match="offline source failed"):
        service.collect(FailedSource(), query="")
    assert service.repository.list() == ()


def test_opportunity_radar_migration_is_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "radar-migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    assert "job_staging_record" in inspect(engine).get_table_names()
    command.downgrade(config, "0016_resume_studio")
    tables = inspect(engine).get_table_names()
    assert "job_staging_record" not in tables
    assert "resume_render_run" in tables
