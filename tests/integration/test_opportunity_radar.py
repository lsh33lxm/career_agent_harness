import hashlib
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect, text

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
    # Freshness is evaluated against the current UTC clock, so the fixture's
    # score remains deterministic by components while its final weighted value
    # moves within the expected range as the day advances.
    assert 0.50 <= staged.suggested_score <= 0.526
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
        service.admit(duplicate.staging_id, actor="user")

    admitted = service.admit(staged.staging_id, actor="user")
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
    assert staged.score_breakdown["salary"] == pytest.approx(0.938, abs=0.001)
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
    assert {"terms_note", "terms_checked_at"} <= {
        item["name"] for item in inspect(engine).get_columns("job_source_run")
    }
    command.downgrade(config, "0021_plugin_lifecycle_observability")
    assert not {"terms_note", "terms_checked_at"} & {
        item["name"] for item in inspect(engine).get_columns("job_source_run")
    }
    command.downgrade(config, "0016_resume_studio")
    tables = inspect(engine).get_table_names()
    assert "job_staging_record" not in tables
    assert "job_source_policy" not in tables
    assert "resume_render_run" in tables


def test_terms_provenance_migration_keeps_historical_check_time_unknown(
    tmp_path: Path,
) -> None:
    database_url = sqlite_url(tmp_path / "terms-history.db")
    config = alembic_config(database_url)
    command.upgrade(config, "0021_plugin_lifecycle_observability")
    engine = create_sqlite_engine(database_url)
    historical_time = "2020-01-02 03:04:05"
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO job_source_run "
                "(source_run_id, source_id, query, terms_status, status, record_count, "
                "started_at, finished_at, ranking_inputs, ranking_policy_version) "
                "VALUES ('historical-run', 'manual', 'old query', 'unknown', "
                "'completed', 0, :at, :at, '{}', 'v1')"
            ),
            {"at": historical_time},
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT terms_note, terms_checked_at FROM job_source_run "
                "WHERE source_run_id='historical-run'"
            )
        ).mappings().one()
    assert row["terms_note"] is None
    assert row["terms_checked_at"] is None


def test_ranking_inputs_are_part_of_identity_and_provenance(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source = OfflineFixtureJobSource()
    first = service.collect(source, query="platform", desired_terms=("Python",))[0]
    second = service.collect(
        source,
        query="platform",
        desired_terms=("Rust",),
        excluded_terms=("Remote",),
        preferred_locations=("Shanghai",),
        minimum_salary=160000,
    )[0]
    assert second.staging_id != first.staging_id
    assert first.ranking_inputs["desired_terms"] == ["Python"]
    assert second.ranking_inputs["desired_terms"] == ["Rust"]
    assert second.ranking_inputs["excluded_terms"] == ["Remote"]
    with service.engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT status, ranking_inputs, ranking_policy_version, terms_note, "
                "terms_checked_at "
                "FROM job_source_run ORDER BY started_at"
            )
        ).mappings().all()
    assert len(rows) == 2
    assert all(row["status"] == "completed" for row in rows)
    assert all(row["ranking_policy_version"] == "v1.1" for row in rows)
    assert all("fixture" in row["terms_note"] for row in rows)
    assert all(row["terms_checked_at"] is not None for row in rows)


def test_failed_normalization_is_recorded_as_failed_run(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source = ManualJobSource(
        (RawJobRecord(source_ref="manual://invalid", raw_text='{"company":"Missing"}'),)
    )
    with pytest.raises(KeyError, match="title"):
        service.collect(source, query="")
    with service.engine.connect() as connection:
        statuses = connection.execute(
            text("SELECT status FROM job_source_run")
        ).scalars().all()
    assert statuses == ["failed"]
    assert service.repository.list() == ()


def test_disabled_source_can_be_reenabled_by_user_policy_action(tmp_path: Path) -> None:
    class ToggleSource(OfflineFixtureJobSource):
        available = False

        def search(self, query: str) -> tuple[RawJobRecord, ...]:
            if not self.available:
                raise RuntimeError("temporary fixture outage")
            return super().search(query)

    service = _service(tmp_path)
    source = ToggleSource()
    with pytest.raises(RuntimeError, match="temporary fixture outage"):
        service.collect(source, query="platform")
    assert service.source_policies()[0].disabled is True
    source.available = True
    policy = service.update_source_policy(source.source_id, enabled=True, reset_failures=True)
    assert policy.disabled is False
    assert policy.failure_count == 0
    assert len(service.collect(source, query="platform")) == 1


def test_admission_rolls_back_job_when_opportunity_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path)
    staged = service.collect(OfflineFixtureJobSource(), query="platform")[0]

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("opportunity write failed")

    monkeypatch.setattr(service.opportunities, "admit_manually", fail)
    with pytest.raises(RuntimeError, match="opportunity write failed"):
        service.admit(staged.staging_id, actor="user")
    digest = hashlib.sha256(staged.staging_id.encode()).hexdigest()[:32]
    assert service.jobs.repository.get_job(f"job_{digest}") is None
    persisted = service.repository.get(staged.staging_id)
    assert persisted is not None
    assert persisted.status is JobStagingStatus.STAGED


def test_opportunity_radar_constraints_survive_hardening_migration(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "radar-schema.db")
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_sqlite_engine(database_url)
    with engine.connect() as connection:
        staging_sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='job_staging_record'")
        ).scalar_one()
        source_run_sql = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='job_source_run'")
        ).scalar_one()
    for fragment in (
        "ck_job_staging_terms_status",
        "ck_job_staging_status",
        "ck_job_staging_score",
        "ck_job_staging_normalized",
        "ck_job_staging_suggested_reasons",
        "ck_job_staging_gaps",
        "ck_job_staging_duplicate_ref",
        "ck_job_staging_admission_refs",
        "ck_job_staging_score_breakdown",
        "ck_job_staging_ranking_inputs",
    ):
        assert fragment in staging_sql
    for fragment in (
        "ck_job_source_run_terms_status",
        "ck_job_source_run_status",
        "ck_job_source_run_record_count",
    ):
        assert fragment in source_run_sql
    assert "terms_note" in source_run_sql
    assert "terms_checked_at" in source_run_sql
