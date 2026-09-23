from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.evidence.models import ArtifactClass
from career_harness.core.job_source import (
    JobResumeProposalSeed,
    JobSource,
    JobSourcePolicy,
    JobStagingRecord,
    JobStagingStatus,
    NormalizedJobRecord,
    RawJobRecord,
)
from career_harness.core.opportunity import JobRef
from career_harness.db.job_repository import JobRepository
from career_harness.db.job_staging_repository import JobStagingRepository, _json
from career_harness.services.command_service import CommandService
from career_harness.services.job_service import JobService
from career_harness.services.opportunity_service import (
    OpportunityAdmissionCommit,
    OpportunityService,
)
from career_harness.storage import ArtifactStore


def _digest(value: str | bytes) -> str:
    content = value.encode() if isinstance(value, str) else value
    return hashlib.sha256(content).hexdigest()


def _slug_url(value: str) -> str:
    return re.sub(r"[#?].*$", "", value.strip().lower()).rstrip("/")


RANKING_POLICY_VERSION = "v1.1"


class OpportunityRadarService:
    def __init__(self, engine: Engine, artifact_store: ArtifactStore) -> None:
        self.engine = engine
        self.artifact_store = artifact_store
        self.repository = JobStagingRepository(engine)
        commands = CommandService(engine)
        self.jobs = JobService(commands, JobRepository(engine))
        self.opportunities = OpportunityService(commands)

    def collect(
        self,
        source: JobSource,
        *,
        query: str,
        desired_terms: tuple[str, ...] = (),
        excluded_terms: tuple[str, ...] = (),
        preferred_locations: tuple[str, ...] = (),
        minimum_salary: float | None = None,
    ) -> tuple[JobStagingRecord, ...]:
        policy = self.repository.ensure_source_policy(source.source_id)
        if policy.disabled:
            raise ValueError(f"job source is disabled after repeated failures: {source.source_id}")
        health = source.health()
        terms = source.terms()
        if health.status != "ok" or terms.status.value == "blocked":
            raise ValueError(f"job source is blocked: {health.message}")
        raw_records: tuple[RawJobRecord, ...] | None = None
        last_error: Exception | None = None
        for attempt in range(policy.max_retries + 1):
            if policy.rate_limit_ms:
                time.sleep(policy.rate_limit_ms / 1000)
            try:
                raw_records = source.search(query)
                self.repository.record_source_success(source.source_id)
                break
            except Exception as error:  # noqa: BLE001
                last_error = error
                policy = self.repository.record_source_failure(source.source_id, str(error))
                if attempt >= policy.max_retries or policy.disabled:
                    break
        if raw_records is None:
            if last_error is None:
                raise RuntimeError("job source failed without an error")
            raise last_error
        now = datetime.now(UTC)
        ranking_inputs = self._ranking_inputs(
            query=query,
            desired_terms=desired_terms,
            excluded_terms=excluded_terms,
            preferred_locations=preferred_locations,
            minimum_salary=minimum_salary,
        )
        run_seed = json.dumps(
            {
                "source_id": source.source_id,
                "query": query,
                "raw_sha256": [_digest(item.raw_text) for item in raw_records],
                "ranking_inputs": ranking_inputs,
                "policy_version": RANKING_POLICY_VERSION,
                "started_at": now.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        run_id = f"source_run_{_digest(run_seed)[:32]}"
        try:
            normalized_records = tuple((raw, source.normalize(raw)) for raw in raw_records)
            results: list[JobStagingRecord] = []
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO job_source_run "
                        "(source_run_id, source_id, query, terms_status, status, record_count, "
                        "terms_note, terms_checked_at, started_at, finished_at, "
                        "ranking_inputs, ranking_policy_version) "
                        "VALUES (:id, :source_id, :query, :terms, 'completed', :count, "
                        ":terms_note, :terms_checked_at, :now, :now, "
                        ":ranking_inputs, :policy_version)"
                    ),
                    {
                        "id": run_id,
                        "source_id": source.source_id,
                        "query": query,
                        "terms": terms.status.value,
                        "terms_note": terms.note,
                        "terms_checked_at": terms.checked_at,
                        "count": len(raw_records),
                        "now": now,
                        "ranking_inputs": _json(ranking_inputs),
                        "policy_version": RANKING_POLICY_VERSION,
                    },
                )
                for raw, normalized in normalized_records:
                    results.append(
                        self._stage(
                            source,
                            run_id,
                            raw,
                            desired_terms=desired_terms,
                            excluded_terms=excluded_terms,
                            preferred_locations=preferred_locations,
                            minimum_salary=minimum_salary,
                            normalized=normalized,
                            ranking_inputs=ranking_inputs,
                            evaluated_at=now,
                            connection=connection,
                        )
                    )
            return tuple(results)
        except Exception:
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT OR IGNORE INTO job_source_run "
                        "(source_run_id, source_id, query, terms_status, status, record_count, "
                        "terms_note, terms_checked_at, started_at, finished_at, "
                        "ranking_inputs, ranking_policy_version) "
                        "VALUES (:id, :source_id, :query, :terms, 'failed', :count, "
                        ":terms_note, :terms_checked_at, :now, :now, "
                        ":ranking_inputs, :policy_version)"
                    ),
                    {
                        "id": run_id,
                        "source_id": source.source_id,
                        "query": query,
                        "terms": terms.status.value,
                        "terms_note": terms.note,
                        "terms_checked_at": terms.checked_at,
                        "count": len(raw_records),
                        "now": now,
                        "ranking_inputs": _json(ranking_inputs),
                        "policy_version": RANKING_POLICY_VERSION,
                    },
                )
            raise

    @staticmethod
    def _ranking_inputs(
        *,
        query: str,
        desired_terms: tuple[str, ...],
        excluded_terms: tuple[str, ...],
        preferred_locations: tuple[str, ...],
        minimum_salary: float | None,
    ) -> dict[str, object]:
        return {
            "query": query,
            "desired_terms": list(desired_terms),
            "excluded_terms": list(excluded_terms),
            "preferred_locations": list(preferred_locations),
            "minimum_salary": minimum_salary,
        }

    def _stage(
        self,
        source: JobSource,
        run_id: str,
        raw: RawJobRecord,
        *,
        desired_terms: tuple[str, ...],
        excluded_terms: tuple[str, ...],
        preferred_locations: tuple[str, ...],
        minimum_salary: float | None,
        normalized: NormalizedJobRecord | None = None,
        ranking_inputs: dict[str, object] | None = None,
        evaluated_at: datetime | None = None,
        connection: Connection | None = None,
    ) -> JobStagingRecord:
        normalized = normalized or source.normalize(raw)
        ranking_inputs = ranking_inputs or self._ranking_inputs(
            query="",
            desired_terms=desired_terms,
            excluded_terms=excluded_terms,
            preferred_locations=preferred_locations,
            minimum_salary=minimum_salary,
        )
        evaluated_at = evaluated_at or datetime.now(UTC)
        raw_bytes = raw.raw_text.encode("utf-8")
        raw_sha = _digest(raw_bytes)
        url_fingerprint = _digest(_slug_url(normalized.source_url or raw.source_ref))
        normalized_json = normalized.model_dump(mode="json")
        content_fingerprint = _digest(_json(normalized_json))
        duplicate_of = self.repository.find_duplicate(
            url_fingerprint,
            content_fingerprint,
            connection=connection,
        )
        staging_seed = json.dumps(
            {
                "source_id": source.source_id,
                "source_ref": raw.source_ref,
                "raw_sha256": raw_sha,
                "ranking_inputs": ranking_inputs,
                "policy_version": RANKING_POLICY_VERSION,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        staging_id = f"staging_{_digest(staging_seed)[:32]}"
        existing = self.repository.get(staging_id, connection=connection)
        if existing is not None:
            return existing
        artifact = self.artifact_store.put(raw_bytes, ArtifactClass.PUBLIC_SOURCE)
        artifact_id = f"artifact_job_staging_{raw_sha[:32]}"
        source_id = f"source_job_staging_{_digest(source.source_id + raw.source_ref)[:32]}"
        snapshot_id = f"snapshot_job_staging_{_digest(staging_id + raw_sha)[:32]}"
        evidence_ref_id = f"evidence_job_staging_{_digest(staging_id + raw_sha)[:32]}"
        score, reasons, gaps, score_breakdown = self._rank(
            normalized,
            normalized.requirements,
            desired_terms,
            excluded_terms,
            captured_at=raw.captured_at,
            preferred_locations=preferred_locations,
            minimum_salary=minimum_salary,
            evaluated_at=evaluated_at,
        )
        status = JobStagingStatus.DUPLICATE if duplicate_of else JobStagingStatus.STAGED
        now = raw.captured_at

        def persist(target: Connection) -> None:
            target.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_artifact "
                    "(artifact_id, sha256, media_type, artifact_class, byte_length) "
                    "VALUES (:id, :sha, 'application/json', 'public_source', :length)"
                ),
                {"id": artifact_id, "sha": artifact.sha256, "length": artifact.byte_length},
            )
            target.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_source (source_id, source_type, locator) "
                    "VALUES (:id, :type, :locator)"
                ),
                {"id": source_id, "type": source.source_id, "locator": raw.source_ref},
            )
            target.execute(
                text(
                    "INSERT OR IGNORE INTO source_snapshot "
                    "(snapshot_id, source_id, captured_at, artifact_id) "
                    "VALUES (:id, :source_id, :captured_at, :artifact_id)"
                ),
                {
                    "id": snapshot_id,
                    "source_id": source_id,
                    "captured_at": now,
                    "artifact_id": artifact_id,
                },
            )
            target.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_ref "
                    "(evidence_ref_id, snapshot_id, artifact_id, selector) "
                    "VALUES (:id, :snapshot_id, :artifact_id, NULL)"
                ),
                {"id": evidence_ref_id, "snapshot_id": snapshot_id, "artifact_id": artifact_id},
            )
            target.execute(
                text(
                    "INSERT INTO job_staging_record "
                    "(staging_id, source_run_id, source_id, source_ref, raw_artifact_id, "
                    "raw_sha256, url_fingerprint, content_fingerprint, normalized, terms_status, "
                    "status, duplicate_of, suggested_score, suggested_reasons, gaps, "
                    "score_breakdown, ranking_inputs, ranking_policy_version, evaluated_at, "
                    "admitted_job_id, admitted_opportunity_id, created_at) VALUES "
                    "(:id, :run_id, :source_id, :source_ref, :artifact_id, :raw_sha, :url_fp, "
                    ":content_fp, :normalized, :terms, :status, :duplicate_of, :score, :reasons, "
                    ":gaps, :score_breakdown, :ranking_inputs, :policy_version, :evaluated_at, "
                    "NULL, NULL, :created_at)"
                ),
                {
                    "id": staging_id,
                    "run_id": run_id,
                    "source_id": source.source_id,
                    "source_ref": raw.source_ref,
                    "artifact_id": artifact_id,
                    "raw_sha": raw_sha,
                    "url_fp": url_fingerprint,
                    "content_fp": content_fingerprint,
                    "normalized": _json(normalized_json),
                    "terms": source.terms().status.value,
                    "status": status.value,
                    "duplicate_of": duplicate_of,
                    "score": score,
                    "reasons": _json(list(reasons)),
                    "gaps": _json(list(gaps)),
                    "score_breakdown": _json(score_breakdown),
                    "ranking_inputs": _json(ranking_inputs),
                    "policy_version": RANKING_POLICY_VERSION,
                    "evaluated_at": evaluated_at,
                    "created_at": now,
                },
            )
        if connection is None:
            with self.engine.begin() as owned_connection:
                persist(owned_connection)
        else:
            persist(connection)
        if connection is not None:
            return JobStagingRecord(
                staging_id=staging_id,
                source_id=source.source_id,
                source_ref=raw.source_ref,
                raw_artifact_id=artifact_id,
                raw_sha256=raw_sha,
                url_fingerprint=url_fingerprint,
                content_fingerprint=content_fingerprint,
                normalized=normalized,
                terms_status=source.terms().status,
                status=status,
                duplicate_of=duplicate_of,
                suggested_score=score,
                suggested_reasons=reasons,
                gaps=gaps,
                score_breakdown=score_breakdown,
                ranking_inputs=ranking_inputs,
                ranking_policy_version=RANKING_POLICY_VERSION,
                evaluated_at=evaluated_at,
                created_at=now,
            )
        result = self.repository.get(staging_id)
        if result is None:
            raise RuntimeError("job staging record was not persisted")
        return result

    def source_policies(self) -> tuple[JobSourcePolicy, ...]:
        return self.repository.list_source_policies()

    def update_source_policy(
        self,
        source_id: str,
        *,
        rate_limit_ms: int | None = None,
        max_retries: int | None = None,
        failure_threshold: int | None = None,
        enabled: bool | None = None,
        reset_failures: bool = False,
    ) -> JobSourcePolicy:
        return self.repository.update_source_policy(
            source_id,
            rate_limit_ms=rate_limit_ms,
            max_retries=max_retries,
            failure_threshold=failure_threshold,
            enabled=enabled,
            reset_failures=reset_failures,
        )

    def admit(self, staging_id: str, *, actor: str | None = None) -> OpportunityAdmissionCommit:
        if actor != "user":
            raise ValueError("only the user may admit a staged job")
        record = self.repository.get(staging_id)
        if record is None:
            raise KeyError("job staging record not found")
        if record.status is not JobStagingStatus.STAGED:
            raise ValueError(f"only staged records can be admitted (status={record.status.value})")
        digest = _digest(staging_id)
        job_id = f"job_{digest[:32]}"
        opportunity_id = f"opportunity_{digest[:32]}"
        decision_id = f"decision_{digest[:32]}"
        evidence_ref_id = f"evidence_job_staging_{_digest(staging_id + record.raw_sha256)[:32]}"
        job_command = self._command(
            f"command_job_{digest[:32]}", EntityKind.JOB, job_id, "radar-job"
        )
        opportunity_command = self._command(
            f"command_opportunity_{digest[:32]}",
            EntityKind.OPPORTUNITY,
            opportunity_id,
            "radar-opportunity",
        )
        with Session(self.engine) as session, session.begin():
            job_commit = self.jobs.record_revision(
                job_command,
                content_sha256=record.raw_sha256,
                source_evidence_refs=(evidence_ref_id,),
                session=session,
            )
            admitted = self.opportunities.admit_manually(
                opportunity_command,
                JobRef(job_id=job_id, revision=job_commit.job.revision),
                opportunity_id=opportunity_id,
                decision_id=decision_id,
                reason=f"User admitted staging record {staging_id}",
                session=session,
            )
            session.execute(
                text(
                    "UPDATE job_staging_record SET status='admitted', admitted_job_id=:job_id, "
                    "admitted_opportunity_id=:opportunity_id WHERE staging_id=:id "
                    "AND status='staged'"
                ),
                {"job_id": job_id, "opportunity_id": opportunity_id, "id": staging_id},
            )
        return admitted

    def resume_proposal_seed(self, staging_id: str) -> JobResumeProposalSeed:
        record = self.repository.get(staging_id)
        if record is None:
            raise KeyError("job staging record not found")
        if record.status is not JobStagingStatus.ADMITTED or record.admitted_opportunity_id is None:
            raise ValueError("resume proposal seed requires a user-admitted staging record")
        return JobResumeProposalSeed(
            staging_id=record.staging_id,
            opportunity_id=record.admitted_opportunity_id,
            title=record.normalized.title,
            company=record.normalized.company,
            requirement_texts=record.normalized.requirements,
            keyword_gaps=record.gaps,
            evidence_ref_id=(
                f"evidence_job_staging_{_digest(record.staging_id + record.raw_sha256)[:32]}"
            ),
        )

    @staticmethod
    def _rank(
        normalized: NormalizedJobRecord,
        requirements: tuple[str, ...],
        desired_terms: tuple[str, ...],
        excluded_terms: tuple[str, ...],
        *,
        captured_at: datetime,
        preferred_locations: tuple[str, ...],
        minimum_salary: float | None,
        evaluated_at: datetime,
    ) -> tuple[float, tuple[str, ...], tuple[str, ...], dict[str, float]]:
        fields = (
            normalized.title,
            normalized.company,
            normalized.location or "",
            "remote" if normalized.remote else "",
            normalized.salary or "",
            *requirements,
        )
        haystack = " ".join(fields).lower()
        matched = tuple(term for term in desired_terms if term.lower() in haystack)
        gaps = tuple(term for term in desired_terms if term.lower() not in haystack)
        deal_breakers = tuple(term for term in excluded_terms if term.lower() in haystack)
        deal_breaker_score = 0.0 if deal_breakers else 1.0
        capability_score = 0.5 if not desired_terms else len(matched) / len(desired_terms)
        location_score = 0.5
        if preferred_locations:
            location_score = (
                1.0
                if normalized.location
                and any(term.lower() in normalized.location.lower() for term in preferred_locations)
                else 0.0
            )
        salary_score = 0.5 if not normalized.salary else 1.0
        if minimum_salary is not None:
            amounts = [
                float(value.replace(",", ""))
                for value in re.findall(r"\d[\d,]*(?:\.\d+)?", normalized.salary or "")
            ]
            salary_score = (
                min(1.0, min(amounts, default=0.0) / minimum_salary)
                if minimum_salary > 0
                else 0.0
            )
        deadline_score = 0.5
        if normalized.deadline_at is not None:
            days = (normalized.deadline_at - captured_at).total_seconds() / 86400
            deadline_score = 0.0 if days < 0 else max(0.0, min(1.0, 1 / (1 + days / 7)))
        age_days = max(0.0, (evaluated_at - captured_at).total_seconds() / 86400)
        freshness_score = max(0.0, min(1.0, 1 - age_days / 30))
        breakdown = {
            "deal_breaker": round(deal_breaker_score, 3),
            "capability_match": round(capability_score, 3),
            "evidence_coverage": 0.0,
            "interest_priority": 0.5,
            "location": round(location_score, 3),
            "salary": round(salary_score, 3),
            "deadline": round(deadline_score, 3),
            "freshness": round(freshness_score, 3),
        }
        weighted = (
            0.45 * breakdown["capability_match"]
            + 0.15 * breakdown["evidence_coverage"]
            + 0.10 * breakdown["interest_priority"]
            + 0.10 * breakdown["location"]
            + 0.10 * breakdown["salary"]
            + 0.05 * breakdown["deadline"]
            + 0.05 * breakdown["freshness"]
        )
        score = round(deal_breaker_score * weighted, 3)
        reasons = []
        if deal_breakers:
            reasons.append(f"deal-breaker: {', '.join(deal_breakers)}")
        elif matched:
            reasons.append(f"matched: {', '.join(matched)}")
        else:
            reasons.append("no verified preference match")
        reasons.append("evidence coverage: 0; no personal evidence supplied")
        if preferred_locations:
            reasons.append(f"location score: {breakdown['location']:.3f}")
        if minimum_salary is not None:
            reasons.append(f"salary score: {breakdown['salary']:.3f}")
        return score, tuple(reasons), gaps, breakdown

    @staticmethod
    def _command(command_id: str, kind: EntityKind, entity_id: str, key: str) -> Command:
        return Command(
            command_id=command_id,
            command_type=f"{kind.value}.radar_admission",
            target=EntityRef(entity_id=entity_id, kind=kind),
            expected_revision=0,
            idempotency_key=f"{key}-{uuid.uuid5(uuid.NAMESPACE_URL, command_id).hex}",
            actor="user",
        )
