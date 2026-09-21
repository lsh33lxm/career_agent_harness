from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from career_harness.core.commands import Command
from career_harness.core.common import EntityKind, EntityRef
from career_harness.core.evidence.models import ArtifactClass
from career_harness.core.job_source import (
    JobResumeProposalSeed,
    JobSource,
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
    ) -> tuple[JobStagingRecord, ...]:
        health = source.health()
        terms = source.terms()
        if health.status != "ok" or terms.status.value == "blocked":
            raise ValueError(f"job source is blocked: {health.message}")
        raw_records = source.search(query)
        now = datetime.now(UTC)
        run_seed = source.source_id + query + "".join(item.raw_text for item in raw_records)
        run_id = f"source_run_{_digest(run_seed)[:32]}"
        results: list[JobStagingRecord] = []
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO job_source_run "
                    "(source_run_id, source_id, query, terms_status, status, record_count, "
                    "started_at, finished_at) VALUES (:id, :source_id, :query, :terms, "
                    "'completed', :count, :now, :now)"
                ),
                {
                    "id": run_id,
                    "source_id": source.source_id,
                    "query": query,
                    "terms": terms.status.value,
                    "count": len(raw_records),
                    "now": now,
                },
            )
        for raw in raw_records:
            results.append(
                self._stage(
                    source,
                    run_id,
                    raw,
                    desired_terms=desired_terms,
                    excluded_terms=excluded_terms,
                )
            )
        return tuple(results)

    def _stage(
        self,
        source: JobSource,
        run_id: str,
        raw: RawJobRecord,
        *,
        desired_terms: tuple[str, ...],
        excluded_terms: tuple[str, ...],
    ) -> JobStagingRecord:
        normalized = source.normalize(raw)
        raw_bytes = raw.raw_text.encode("utf-8")
        raw_sha = _digest(raw_bytes)
        url_fingerprint = _digest(_slug_url(normalized.source_url or raw.source_ref))
        normalized_json = normalized.model_dump(mode="json")
        content_fingerprint = _digest(_json(normalized_json))
        duplicate_of = self.repository.find_duplicate(url_fingerprint, content_fingerprint)
        staging_id = f"staging_{_digest(source.source_id + raw.source_ref + raw_sha)[:32]}"
        existing = self.repository.get(staging_id)
        if existing is not None:
            return existing
        artifact = self.artifact_store.put(raw_bytes, ArtifactClass.PUBLIC_SOURCE)
        artifact_id = f"artifact_job_staging_{raw_sha[:32]}"
        source_id = f"source_job_staging_{_digest(source.source_id + raw.source_ref)[:32]}"
        snapshot_id = f"snapshot_job_staging_{_digest(staging_id + raw_sha)[:32]}"
        evidence_ref_id = f"evidence_job_staging_{_digest(staging_id + raw_sha)[:32]}"
        score, reasons, gaps = self._rank(
            normalized,
            normalized.requirements,
            desired_terms,
            excluded_terms,
        )
        status = JobStagingStatus.DUPLICATE if duplicate_of else JobStagingStatus.STAGED
        now = raw.captured_at
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_artifact "
                    "(artifact_id, sha256, media_type, artifact_class, byte_length) "
                    "VALUES (:id, :sha, 'application/json', 'public_source', :length)"
                ),
                {"id": artifact_id, "sha": artifact.sha256, "length": artifact.byte_length},
            )
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_source (source_id, source_type, locator) "
                    "VALUES (:id, :type, :locator)"
                ),
                {"id": source_id, "type": source.source_id, "locator": raw.source_ref},
            )
            connection.execute(
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
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO evidence_ref "
                    "(evidence_ref_id, snapshot_id, artifact_id, selector) "
                    "VALUES (:id, :snapshot_id, :artifact_id, NULL)"
                ),
                {"id": evidence_ref_id, "snapshot_id": snapshot_id, "artifact_id": artifact_id},
            )
            connection.execute(
                text(
                    "INSERT INTO job_staging_record "
                    "(staging_id, source_run_id, source_id, source_ref, raw_artifact_id, "
                    "raw_sha256, url_fingerprint, content_fingerprint, normalized, terms_status, "
                    "status, duplicate_of, suggested_score, suggested_reasons, gaps, "
                    "admitted_job_id, admitted_opportunity_id, created_at) VALUES "
                    "(:id, :run_id, :source_id, :source_ref, :artifact_id, :raw_sha, :url_fp, "
                    ":content_fp, :normalized, :terms, :status, :duplicate_of, :score, :reasons, "
                    ":gaps, NULL, NULL, :created_at)"
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
                    "created_at": now,
                },
            )
        result = self.repository.get(staging_id)
        if result is None:
            raise RuntimeError("job staging record was not persisted")
        return result

    def admit(self, staging_id: str, *, actor: str = "user") -> OpportunityAdmissionCommit:
        if actor != "user":
            raise ValueError("only the user may admit a staged job")
        record = self.repository.get(staging_id)
        if record is None:
            raise KeyError("job staging record not found")
        if record.status is JobStagingStatus.DUPLICATE:
            raise ValueError("duplicate staging record cannot be admitted")
        if record.status is JobStagingStatus.ADMITTED:
            raise ValueError("staging record has already been admitted")
        digest = _digest(staging_id)
        job_id = f"job_{digest[:32]}"
        opportunity_id = f"opportunity_{digest[:32]}"
        decision_id = f"decision_{digest[:32]}"
        evidence_ref_id = f"evidence_job_staging_{_digest(staging_id + record.raw_sha256)[:32]}"
        job_command = self._command(
            f"command_job_{digest[:32]}", EntityKind.JOB, job_id, "radar-job"
        )
        job_commit = self.jobs.record_revision(
            job_command,
            content_sha256=record.raw_sha256,
            source_evidence_refs=(evidence_ref_id,),
        )
        opportunity_command = self._command(
            f"command_opportunity_{digest[:32]}",
            EntityKind.OPPORTUNITY,
            opportunity_id,
            "radar-opportunity",
        )
        admitted = self.opportunities.admit_manually(
            opportunity_command,
            JobRef(job_id=job_id, revision=job_commit.job.revision),
            opportunity_id=opportunity_id,
            decision_id=decision_id,
            reason=f"User admitted staging record {staging_id}",
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE job_staging_record SET status='admitted', admitted_job_id=:job_id, "
                    "admitted_opportunity_id=:opportunity_id WHERE staging_id=:id"
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
    ) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
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
        if deal_breakers:
            return 0.0, (f"deal-breaker: {', '.join(deal_breakers)}",), gaps
        score = 0.5 if not desired_terms else round(len(matched) / len(desired_terms), 3)
        reasons = (
            (f"matched: {', '.join(matched)}",) if matched else ("no verified preference match",)
        )
        return score, reasons, gaps

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
