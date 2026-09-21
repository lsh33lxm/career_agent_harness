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
    assert staged.suggested_score == pytest.approx(0.475, abs=0.001)
    assert staged.gaps == ("Rust",)
    assert staged.score_breakdown["capability_match"] == pytest.approx(2 / 3, abs=0.001)
    assert staged.score_breakdown["evidence_coverage"] == 0
    assert any("evidence coverage: 0" in reason for reason in staged.suggested_reasons)
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
    assert staged.suggested_reasons[0] == "deal-breaker: Remote"
    assert staged.score_breakdown["deal_breaker"] == 0
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


def test_source_policy_retries_then_resets_failure_count(tmp_path: Path) -> None:
    class FlakySource(OfflineFixtureJobSource):
        calls = 0

        def search(self, query: str) -> tuple[RawJobRecord, ...]:
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("temporary fixture outage")
            return super().search(query)

    service = _service(tmp_path)
    source = FlakySource()
    records = service.collect(source, query="platform")
    assert len(records) == 1
    assert source.calls == 3
    policy = service.source_policies()[0]
    assert policy.source_id == source.source_id
    assert policy.failure_count == 0
    assert policy.disabled is False


def test_source_policy_disables_after_retry_budget(tmp_path: Path) -> None:
    class BrokenSource(OfflineFixtureJobSource):
        calls = 0

        def search(self, query: str) -> tuple[RawJobRecord, ...]:
            self.calls += 1
            raise RuntimeError("fixture source unavailable")

    service = _service(tmp_path)
    source = BrokenSource()
    with pytest.raises(RuntimeError, match="fixture source unavailable"):
        service.collect(source, query="platform")
    assert source.calls == 3
    policy = service.source_policies()[0]
    assert policy.failure_count == 3
    assert policy.disabled is True
    with pytest.raises(ValueError, match="disabled"):
        service.collect(source, query="platform")


def test_rank_records_location_salary_deadline_and_freshness_components(tmp_path: Path) -> None:
    service = _service(tmp_path)
    record = RawJobRecord(
        source_ref="manual://ranked",
        raw_text=(
            '{"title":"Platform Engineer","company":"Local Co",'
            '"location":"Remote","salary":"150000-180000",'
            '"deadline_at":"2026-09-28T00:00:00+00:00",'
            '"requirements":["Python"]}'
        ),
    )
    staged = service.collect(
        ManualJobSource((record,)),
        query="",
        desired_terms=("Python",),
        preferred_locations=("Remote",),
        minimum_salary=160000,
    )[0]
    assert staged.score_breakdown["location"] == 1
    assert staged.score_breakdown["salary"] == pytest.approx(1, abs=0.001)
    assert staged.score_breakdown["deadline"] > 0
    assert 0 <= staged.score_breakdown["freshness"] <= 1


def test_opportunity_radar_migration_is_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "radar-migration.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    assert "job_staging_record" in inspect(engine).get_table_names()
    assert "job_source_policy" in inspect(engine).get_table_names()
    assert "score_breakdown" in {
        item["name"] for item in inspect(engine).get_columns("job_staging_record")
    }
    command.downgrade(config, "0016_resume_studio")
    tables = inspect(engine).get_table_names()
    assert "job_staging_record" not in tables
    assert "job_source_policy" not in tables
    assert "resume_render_run" in tables
