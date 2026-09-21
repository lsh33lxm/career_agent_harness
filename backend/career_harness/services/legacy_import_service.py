from __future__ import annotations

import csv
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from sqlalchemy import Engine, text

from career_harness.core.common import FrozenModel
from career_harness.core.evidence.models import ArtifactClass
from career_harness.core.job_source import (
    JobSourceHealth,
    JobSourceTerms,
    JobSourceTermsStatus,
    NormalizedJobRecord,
    RawJobRecord,
)
from career_harness.services.opportunity_radar_service import OpportunityRadarService
from career_harness.storage import ArtifactStore
from importers.agent_radar.inventory import (
    read_source_bytes,
    sha256_file,
    source_metadata_signature,
)

IMPORTER_VERSION = "legacy-structured-v1"


@dataclass(frozen=True, slots=True)
class _SourceSpec:
    relative_path: str
    record_kind: Literal["job", "interview", "question", "coding", "source"]
    source_class: str
    artifact_class: ArtifactClass


SOURCE_SPECS = (
    _SourceSpec("data/统一数据/岗位与JD数据.csv", "job", "unified_job", ArtifactClass.SENSITIVE),
    _SourceSpec(
        "data/统一数据/面试事件数据.csv", "interview", "unified_interview", ArtifactClass.SENSITIVE
    ),
    _SourceSpec(
        "data/统一数据/问题明细.csv", "question", "unified_question", ArtifactClass.SENSITIVE
    ),
    _SourceSpec(
        "data/统一数据/来源总台账.csv", "source", "unified_source", ArtifactClass.SENSITIVE
    ),
    _SourceSpec(
        "data/统一数据/个人刷题记录.csv", "coding", "personal_coding", ArtifactClass.PERSONAL
    ),
    _SourceSpec(
        "data/cn/normalized/jd_events.jsonl", "job", "cn_jd_event", ArtifactClass.SENSITIVE
    ),
    _SourceSpec(
        "data/cn/normalized/interview_events.jsonl",
        "interview",
        "cn_interview_event",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "data/cn/normalized/question_occurrences.jsonl",
        "question",
        "cn_question_occurrence",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "data/cn/normalized/coding_occurrences.jsonl",
        "coding",
        "cn_coding_occurrence",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "data/overseas/normalized/overseas_jd_events.jsonl",
        "job",
        "overseas_jd_event",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "data/候选数据/9.16补采/PlatformJobObservation_candidate_platform.csv",
        "job",
        "candidate_platform",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "data/候选数据/9.16补采/OfficialJD_candidate_official.csv",
        "job",
        "candidate_official",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "data/候选数据/9.16补采/CanonicalJobPosting_candidate_platform.csv",
        "job",
        "candidate_canonical",
        ArtifactClass.SENSITIVE,
    ),
    _SourceSpec(
        "codex/data/snapshots/2026-09-15/overseas/normalized/job_postings.jsonl",
        "job",
        "overseas_job_snapshot",
        ArtifactClass.SENSITIVE,
    ),
)


def _digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _clean_record(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key is None:
            continue
        if isinstance(item, str):
            item = item.strip()
        if item not in (None, ""):
            result[str(key).strip()] = item
    return result


def _records(relative_path: str, content: bytes) -> list[tuple[int, dict[str, Any]]]:
    decoded = content.decode("utf-8-sig")
    if relative_path.casefold().endswith(".csv"):
        return [
            (index, _clean_record(dict(row)))
            for index, row in enumerate(csv.DictReader(StringIO(decoded)), start=2)
        ]
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {line_number} must be an object")
        rows.append((line_number, _clean_record(value)))
    return rows


def _first(record: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, list):
            value = "、".join(str(item).strip() for item in value if str(item).strip())
        if value not in (None, ""):
            return str(value).strip()
    return None


def _items(record: dict[str, Any], *keys: str) -> tuple[str, ...]:
    result: list[str] = []
    for key in keys:
        value = record.get(key)
        if isinstance(value, list):
            candidates = value
        elif value in (None, ""):
            candidates = []
        else:
            text_value = str(value).replace("\r", "\n")
            candidates = text_value.replace("；", "\n").replace(";", "\n").split("\n")
        for candidate in candidates:
            normalized = str(candidate).strip(" \t,-•")
            if normalized and normalized not in result:
                result.append(normalized)
    return tuple(result[:100])


def _date(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    candidate = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = datetime.strptime(candidate[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _job_key(record: dict[str, Any], row_number: int) -> str:
    return (
        _first(
            record,
            "unified_job_id",
            "observation_id",
            "job_id",
            "jd_id",
            "job_external_id",
            "canonical_id",
            "portal_id",
        )
        or f"row-{row_number}"
    )


def _projection_key(kind: str, record: dict[str, Any], row_number: int) -> str:
    keys = {
        "interview": ("unified_interview_id", "event_id", "interview_id_raw"),
        "question": ("unified_record_id", "occurrence_id", "record_id_raw"),
        "coding": ("occurrence_id", "leetcode_id", "LeetCode 题号"),
        "source": ("unified_source_id", "source_id_raw", "source_id", "original_url"),
    }
    return _first(record, *keys[kind]) or f"row-{row_number}"


def _normalize_job(record: dict[str, Any], *, relative_path: str) -> NormalizedJobRecord:
    title = _first(
        record,
        "role_raw",
        "job_title_canonical",
        "job_title_raw",
        "job_title",
        "title",
        "title_example",
        "raw_title",
        "role_family",
        "role_cluster",
    )
    company = _first(
        record,
        "company_canonical",
        "company_full",
        "company_raw",
        "company",
        "company_id",
        "official_portal_name",
    )
    if not title or not company:
        raise ValueError("岗位缺少公司或岗位名称")
    location = _first(record, "location", "city_canonical", "city_raw", "city", "locations")
    work_mode = (_first(record, "work_mode") or "").casefold()
    remote = True if any(word in work_mode for word in ("remote", "远程")) else None
    requirements = _items(
        record,
        "requirements_raw",
        "requirements",
        "responsibilities_raw",
        "responsibility_raw",
        "responsibilities",
        "skills",
        "skills_raw",
        "skills_raw_excerpt",
        "skills_normalized",
        "preferred_raw",
        "preferred",
        "experience_requirement_raw",
        "education_requirement_raw",
    )
    return NormalizedJobRecord(
        title=title[:512],
        company=company[:512],
        location=location[:512] if location else None,
        remote=remote,
        salary=(_first(record, "salary_raw", "salary") or None),
        published_at=_date(_first(record, "job_posted_at", "published_at", "publication_date_raw")),
        deadline_at=_date(_first(record, "valid_through")),
        requirements=requirements,
        source_url=_first(
            record,
            "original_url",
            "source_url",
            "job_url",
            "url",
            "platform_url",
            "official_url",
        ),
    )


def _captured_at(record: dict[str, Any], modified_at: datetime) -> datetime:
    return (
        _date(
            _first(
                record,
                "collected_at",
                "job_updated_at",
                "latest_updated",
                "effective_event_date",
                "effective_date",
            )
        )
        or modified_at
    )


class _LegacyJobSource:
    def __init__(
        self,
        source_id: str,
        rows: list[tuple[RawJobRecord, NormalizedJobRecord]],
    ) -> None:
        self.source_id = source_id
        self._rows = tuple(rows)
        self._normalized = {raw.source_ref: normalized for raw, normalized in rows}

    def search(self, query: str) -> tuple[RawJobRecord, ...]:
        return tuple(raw for raw, _ in self._rows)

    def fetch_detail(self, ref: str) -> RawJobRecord:
        return next(raw for raw, _ in self._rows if raw.source_ref == ref)

    def normalize(self, raw: RawJobRecord) -> NormalizedJobRecord:
        return self._normalized[raw.source_ref]

    def health(self) -> JobSourceHealth:
        return JobSourceHealth(status="ok", message="Legacy 只读文件可访问")

    def terms(self) -> JobSourceTerms:
        return JobSourceTerms(
            source_id=self.source_id,
            status=JobSourceTermsStatus.UNKNOWN,
            note="历史只读导入；来源条款状态未知，不执行网络采集或外部写入。",
        )


class LegacyImportFileReport(FrozenModel):
    relative_path: str
    source_class: str
    read_count: int = Field(ge=0)
    new_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    failures: tuple[str, ...] = ()
    sample_validation: dict[str, Any] = Field(default_factory=dict)


class LegacyImportReport(FrozenModel):
    batch_id: str
    source_root: str
    source_signature_before: str
    source_signature_after: str
    status: Literal["completed", "failed"]
    started_at: datetime
    finished_at: datetime
    files: tuple[LegacyImportFileReport, ...]
    totals: dict[str, int]
    importer_version: str = IMPORTER_VERSION


class LegacyImportStatus(FrozenModel):
    configured_source_root: str | None
    source_accessible: bool
    latest_report: LegacyImportReport | None


class LegacyJobSummary(FrozenModel):
    staging_id: str
    title: str
    company: str
    location: str | None
    salary: str | None
    source_url: str | None
    status: str
    duplicate_of: str | None
    suggested_score: float
    review_status: str
    source_path: str
    source_class: str
    source_sha256: str
    row_number: int
    imported_at: datetime
    tags: tuple[str, ...]


class LegacyJobDetail(FrozenModel):
    job: LegacyJobSummary
    jd_text: str
    raw_record: dict[str, Any]
    transform: dict[str, Any]
    batch_id: str
    related_interviews: tuple[dict[str, Any], ...]


class LegacyImportService:
    def __init__(
        self,
        engine: Engine,
        artifact_store: ArtifactStore,
        *,
        default_source_root: Path | None = None,
    ) -> None:
        self.engine = engine
        self.artifact_store = artifact_store
        self.radar = OpportunityRadarService(engine, artifact_store)
        self.default_source_root = default_source_root

    def resolve_source_root(self, requested: Path | None = None) -> Path:
        source = requested or self.default_source_root
        if source is None:
            raise ValueError("尚未配置 Legacy Agent Radar 目录")
        root = source.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Legacy Agent Radar 路径不是目录")
        return root

    def status(self) -> LegacyImportStatus:
        configured = str(self.default_source_root) if self.default_source_root else None
        accessible = False
        if self.default_source_root is not None:
            try:
                accessible = self.resolve_source_root().is_dir()
            except (OSError, ValueError):
                accessible = False
        return LegacyImportStatus(
            configured_source_root=configured,
            source_accessible=accessible,
            latest_report=self.latest_report(),
        )

    def run(self, source_root: Path | None = None) -> LegacyImportReport:
        root = self.resolve_source_root(source_root)
        started_at = datetime.now(UTC)
        signature_before = source_metadata_signature(root)
        batch_id = f"legacy_batch_{started_at.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:12]}"
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO legacy_import_batch "
                    "(batch_id, source_root, source_signature_before, source_signature_after, "
                    "status, started_at, finished_at, report) "
                    "VALUES (:id, :root, :signature, NULL, 'running', :started, NULL, '{}')"
                ),
                {
                    "id": batch_id,
                    "root": str(root),
                    "signature": signature_before,
                    "started": started_at,
                },
            )

        reports: list[LegacyImportFileReport] = []
        try:
            for spec in SOURCE_SPECS:
                reports.append(self._import_file(root, batch_id, spec))
            signature_after = source_metadata_signature(root)
            if signature_after != signature_before:
                raise RuntimeError("Legacy source metadata changed during structured import")
            status: Literal["completed", "failed"] = "completed"
        except Exception as error:
            signature_after = source_metadata_signature(root)
            reports.append(
                LegacyImportFileReport(
                    relative_path="__import__",
                    source_class="importer",
                    read_count=0,
                    new_count=0,
                    updated_count=0,
                    unchanged_count=0,
                    duplicate_count=0,
                    failed_count=1,
                    failures=(str(error),),
                )
            )
            status = "failed"

        finished_at = datetime.now(UTC)
        totals = {
            key: sum(getattr(item, key) for item in reports)
            for key in (
                "read_count",
                "new_count",
                "updated_count",
                "unchanged_count",
                "duplicate_count",
                "failed_count",
            )
        }
        report = LegacyImportReport(
            batch_id=batch_id,
            source_root=str(root),
            source_signature_before=signature_before,
            source_signature_after=signature_after,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            files=tuple(reports),
            totals=totals,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE legacy_import_batch SET source_signature_after=:after, "
                    "status=:status, finished_at=:finished, report=:report WHERE batch_id=:id"
                ),
                {
                    "after": signature_after,
                    "status": status,
                    "finished": finished_at,
                    "report": _json(report.model_dump(mode="json")),
                    "id": batch_id,
                },
            )
        if status == "failed":
            raise RuntimeError(reports[-1].failures[0])
        return report

    def _read_file(self, root: Path, spec: _SourceSpec) -> tuple[bytes, str, datetime, int]:
        path = root / Path(spec.relative_path)
        if not path.exists():
            raise FileNotFoundError(f"缺少 Legacy 文件：{spec.relative_path}")
        stat = path.stat(follow_symlinks=False)
        modified_at = datetime.fromtimestamp(stat.st_mtime, UTC)
        digest = sha256_file(path)
        content = read_source_bytes(
            root,
            spec.relative_path,
            expected_size=stat.st_size,
            expected_sha256=digest,
            expected_modified_at=modified_at,
        )
        return content, digest, modified_at, stat.st_size

    def _import_file(self, root: Path, batch_id: str, spec: _SourceSpec) -> LegacyImportFileReport:
        failures: list[str] = []
        try:
            content, digest, modified_at, byte_length = self._read_file(root, spec)
        except (OSError, UnicodeError, ValueError) as error:
            return LegacyImportFileReport(
                relative_path=spec.relative_path,
                source_class=spec.source_class,
                read_count=0,
                new_count=0,
                updated_count=0,
                unchanged_count=0,
                duplicate_count=0,
                failed_count=1,
                failures=(str(error),),
            )
        artifact = self.artifact_store.put(content, spec.artifact_class)
        if artifact.sha256 != digest:
            raise RuntimeError(f"Artifact Store hash mismatch: {spec.relative_path}")
        file_version_id = f"legacy_file_{_digest(spec.relative_path + ':' + digest)[:32]}"
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO legacy_source_file_version "
                    "(file_version_id, relative_path, sha256, byte_length, modified_at, "
                    "source_class, artifact_class, artifact_sha256, created_at) VALUES "
                    "(:id, :path, :sha, :length, :modified, :source_class, :artifact_class, "
                    ":artifact_sha, :created)"
                ),
                {
                    "id": file_version_id,
                    "path": spec.relative_path,
                    "sha": digest,
                    "length": byte_length,
                    "modified": modified_at,
                    "source_class": spec.source_class,
                    "artifact_class": spec.artifact_class.value,
                    "artifact_sha": artifact.sha256,
                    "created": datetime.now(UTC),
                },
            )
        try:
            rows = _records(spec.relative_path, content)
        except (csv.Error, json.JSONDecodeError, UnicodeError, ValueError) as error:
            rows = []
            failures.append(str(error))

        if spec.record_kind == "job":
            counters = self._import_jobs(
                batch_id, file_version_id, spec, rows, modified_at, failures
            )
        else:
            counters = self._import_projections(batch_id, file_version_id, spec, rows, failures)
        sample = {
            "file_sha256": digest,
            "artifact_sha256": artifact.sha256,
            "artifact_hash_matches": artifact.sha256 == digest,
            "sample_rows": [row_number for row_number, _ in rows[:3]],
        }
        report = LegacyImportFileReport(
            relative_path=spec.relative_path,
            source_class=spec.source_class,
            read_count=len(rows),
            new_count=counters["new"],
            updated_count=counters["updated"],
            unchanged_count=counters["unchanged"],
            duplicate_count=counters["duplicate"],
            failed_count=len(failures),
            failures=tuple(failures[:100]),
            sample_validation=sample,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO legacy_import_batch_file "
                    "(batch_id, file_version_id, read_count, new_count, updated_count, "
                    "unchanged_count, duplicate_count, failed_count, failures, sample_validation) "
                    "VALUES (:batch, :file, :read, :new, :updated, :unchanged, :duplicates, "
                    ":failed, :failures, :sample)"
                ),
                {
                    "batch": batch_id,
                    "file": file_version_id,
                    "read": report.read_count,
                    "new": report.new_count,
                    "updated": report.updated_count,
                    "unchanged": report.unchanged_count,
                    "duplicates": report.duplicate_count,
                    "failed": report.failed_count,
                    "failures": _json(list(report.failures)),
                    "sample": _json(report.sample_validation),
                },
            )
        return report

    def _import_jobs(
        self,
        batch_id: str,
        file_version_id: str,
        spec: _SourceSpec,
        rows: list[tuple[int, dict[str, Any]]],
        modified_at: datetime,
        failures: list[str],
    ) -> dict[str, int]:
        prepared: list[tuple[int, str, dict[str, Any], RawJobRecord, NormalizedJobRecord]] = []
        source_only_rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, record in rows:
            try:
                key = _job_key(record, row_number)
                source_ref = f"legacy://{spec.relative_path}#row={row_number}"
                prepared.append(
                    (
                        row_number,
                        key,
                        record,
                        RawJobRecord(
                            source_ref=source_ref,
                            raw_text=_json(record),
                            captured_at=_captured_at(record, modified_at),
                        ),
                        _normalize_job(record, relative_path=spec.relative_path),
                    )
                )
            except (TypeError, ValueError):
                # Official portal inventories may describe a source without a concrete JD.
                # Preserve those rows as historical source projections instead of inventing a Job.
                source_only_rows.append((row_number, record))
        source_id = f"legacy_{_digest(spec.relative_path)[:32]}"
        results = self.radar.collect(
            _LegacyJobSource(source_id, [(item[3], item[4]) for item in prepared]),
            query="Legacy 历史岗位导入",
        )
        counters = {"new": 0, "updated": 0, "unchanged": 0, "duplicate": 0}
        for item, staged in zip(prepared, results, strict=True):
            row_number, key, record, raw, normalized = item
            with self.engine.begin() as connection:
                previous = connection.execute(
                    text(
                        "SELECT p.staging_id FROM job_staging_provenance p "
                        "JOIN legacy_source_file_version f ON f.file_version_id=p.file_version_id "
                        "WHERE f.relative_path=:path AND p.row_number=:row "
                        "ORDER BY p.imported_at LIMIT 1"
                    ),
                    {"path": spec.relative_path, "row": row_number},
                ).scalar_one_or_none()
                review_status = (
                    "duplicate"
                    if staged.status.value == "duplicate"
                    else "needs_review"
                    if previous and previous != staged.staging_id
                    else "historical_unconfirmed"
                )
                transform = {
                    "importer_version": IMPORTER_VERSION,
                    "source_class": spec.source_class,
                    "captured_at": raw.captured_at.isoformat(),
                    "normalized_fields": list(normalized.model_fields_set),
                    "jd_text": "\n\n".join(normalized.requirements),
                    "tags": list(normalized.requirements[:24]),
                }
                inserted = connection.execute(
                    text(
                        "INSERT OR IGNORE INTO job_staging_provenance "
                        "(staging_id, file_version_id, batch_id, row_number, record_key, "
                        "review_status, transform, imported_at) VALUES "
                        "(:staging, :file, :batch, :row, :key, :review, :transform, :now)"
                    ),
                    {
                        "staging": staged.staging_id,
                        "file": file_version_id,
                        "batch": batch_id,
                        "row": row_number,
                        "key": key[:512],
                        "review": review_status,
                        "transform": _json(transform),
                        "now": datetime.now(UTC),
                    },
                ).rowcount
            if not inserted:
                counters["unchanged"] += 1
            elif previous and previous != staged.staging_id:
                counters["updated"] += 1
            else:
                counters["new"] += 1
            if staged.status.value == "duplicate":
                counters["duplicate"] += 1
        if source_only_rows:
            source_spec = _SourceSpec(
                relative_path=spec.relative_path,
                record_kind="source",
                source_class=f"{spec.source_class}_metadata",
                artifact_class=spec.artifact_class,
            )
            source_counters = self._import_projections(
                batch_id,
                file_version_id,
                source_spec,
                source_only_rows,
                failures,
            )
            for key, value in source_counters.items():
                counters[key] += value
        return counters

    def _import_projections(
        self,
        batch_id: str,
        file_version_id: str,
        spec: _SourceSpec,
        rows: list[tuple[int, dict[str, Any]]],
        failures: list[str],
    ) -> dict[str, int]:
        counters = {"new": 0, "updated": 0, "unchanged": 0, "duplicate": 0}
        for row_number, record in rows:
            try:
                business_key = _projection_key(spec.record_kind, record, row_number)
                content_sha = _digest(_json(record))
                identity = f"{spec.relative_path}:{row_number}:{content_sha}"
                record_id = f"legacy_{spec.record_kind}_{_digest(identity)[:32]}"
                with self.engine.begin() as connection:
                    exact_duplicate = connection.execute(
                        text(
                            "SELECT record_id FROM legacy_projection_record "
                            "WHERE record_kind=:kind AND content_sha256=:sha "
                            "ORDER BY created_at LIMIT 1"
                        ),
                        {"kind": spec.record_kind, "sha": content_sha},
                    ).scalar_one_or_none()
                    key_conflict = connection.execute(
                        text(
                            "SELECT record_id FROM legacy_projection_record "
                            "WHERE record_kind=:kind AND business_key=:key "
                            "AND content_sha256<>:sha ORDER BY created_at LIMIT 1"
                        ),
                        {"kind": spec.record_kind, "key": business_key, "sha": content_sha},
                    ).scalar_one_or_none()
                    prior_location = connection.execute(
                        text(
                            "SELECT r.record_id FROM legacy_projection_record r "
                            "JOIN legacy_source_file_version f "
                            "ON f.file_version_id=r.file_version_id "
                            "WHERE f.relative_path=:path AND r.row_number=:row "
                            "ORDER BY r.created_at LIMIT 1"
                        ),
                        {"path": spec.relative_path, "row": row_number},
                    ).scalar_one_or_none()
                    review_status = (
                        "duplicate"
                        if exact_duplicate and exact_duplicate != record_id
                        else "needs_review"
                        if key_conflict or (prior_location and prior_location != record_id)
                        else "historical_unconfirmed"
                    )
                    inserted = connection.execute(
                        text(
                            "INSERT OR IGNORE INTO legacy_projection_record "
                            "(record_id, record_kind, business_key, content, content_sha256, "
                            "file_version_id, batch_id, row_number, review_status, duplicate_of, "
                            "created_at) VALUES (:id, :kind, :key, :content, :sha, :file, :batch, "
                            ":row, :review, :duplicate_of, :created)"
                        ),
                        {
                            "id": record_id,
                            "kind": spec.record_kind,
                            "key": business_key[:512],
                            "content": _json(record),
                            "sha": content_sha,
                            "file": file_version_id,
                            "batch": batch_id,
                            "row": row_number,
                            "review": review_status,
                            "duplicate_of": (
                                exact_duplicate
                                if exact_duplicate and exact_duplicate != record_id
                                else None
                            ),
                            "created": datetime.now(UTC),
                        },
                    ).rowcount
                if not inserted:
                    counters["unchanged"] += 1
                elif prior_location and prior_location != record_id:
                    counters["updated"] += 1
                else:
                    counters["new"] += 1
                if review_status == "duplicate":
                    counters["duplicate"] += 1
            except (TypeError, ValueError) as error:
                failures.append(f"row {row_number}: {error}")
        return counters

    def latest_report(self) -> LegacyImportReport | None:
        with self.engine.connect() as connection:
            report = connection.execute(
                text(
                    "SELECT report FROM legacy_import_batch "
                    "WHERE status IN ('completed', 'failed') "
                    "ORDER BY started_at DESC LIMIT 1"
                )
            ).scalar_one_or_none()
        if report is None:
            return None
        return LegacyImportReport.model_validate(
            json.loads(report) if isinstance(report, str) else report
        )

    def list_jobs(
        self,
        *,
        query: str = "",
        company: str = "",
        location: str = "",
        status: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LegacyJobSummary, ...]:
        clauses = ["1=1"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            clauses.append(
                "(json_extract(s.normalized, '$.title') LIKE :query OR "
                "json_extract(s.normalized, '$.company') LIKE :query OR "
                "json_extract(s.normalized, '$.requirements') LIKE :query)"
            )
            params["query"] = f"%{query}%"
        if company:
            clauses.append("json_extract(s.normalized, '$.company') LIKE :company")
            params["company"] = f"%{company}%"
        if location:
            clauses.append("json_extract(s.normalized, '$.location') LIKE :location")
            params["location"] = f"%{location}%"
        if status:
            clauses.append("s.status=:status")
            params["status"] = status
        statement = (
            "SELECT s.*, p.review_status, p.row_number, p.imported_at, p.transform, "
            "f.relative_path, f.source_class, f.sha256 FROM job_staging_record s "
            "JOIN job_staging_provenance p ON p.staging_id=s.staging_id "
            "JOIN legacy_source_file_version f ON f.file_version_id=p.file_version_id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY s.suggested_score DESC, p.imported_at DESC LIMIT :limit OFFSET :offset"
        )
        with self.engine.connect() as connection:
            rows = connection.execute(text(statement), params).mappings().all()
        return tuple(self._job_summary(row) for row in rows)

    def get_job(self, staging_id: str) -> LegacyJobDetail | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT s.*, p.review_status, p.row_number, p.imported_at, p.transform, "
                        "p.batch_id, f.relative_path, f.source_class, f.sha256 "
                        "FROM job_staging_record s "
                        "JOIN job_staging_provenance p ON p.staging_id=s.staging_id "
                        "JOIN legacy_source_file_version f ON f.file_version_id=p.file_version_id "
                        "WHERE s.staging_id=:id"
                    ),
                    {"id": staging_id},
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            normalized = (
                json.loads(row["normalized"])
                if isinstance(row["normalized"], str)
                else row["normalized"]
            )
            company = normalized.get("company", "")
            title = normalized.get("title", "")
            interviews = (
                connection.execute(
                    text(
                        "SELECT content, review_status, row_number FROM legacy_projection_record "
                        "WHERE record_kind='interview' AND ("
                        "json_extract(content, '$.company_canonical')=:company OR "
                        "json_extract(content, '$.company')=:company OR "
                        "json_extract(content, '$.company_raw')=:company) "
                        "AND (json_extract(content, '$.role_raw')=:title OR "
                        "json_extract(content, '$.role')=:title OR "
                        "json_extract(content, '$.job_title')=:title) "
                        "ORDER BY created_at DESC LIMIT 50"
                    ),
                    {"company": company, "title": title},
                )
                .mappings()
                .all()
            )
        raw_bytes = self.artifact_store.read(row["raw_sha256"])
        raw_record = json.loads(raw_bytes.decode("utf-8"))
        transform = (
            json.loads(row["transform"]) if isinstance(row["transform"], str) else row["transform"]
        )
        related = tuple(
            {
                **(
                    json.loads(item["content"])
                    if isinstance(item["content"], str)
                    else item["content"]
                ),
                "_review_status": item["review_status"],
                "_row_number": item["row_number"],
            }
            for item in interviews
        )
        return LegacyJobDetail(
            job=self._job_summary(row),
            jd_text=transform.get("jd_text", ""),
            raw_record=raw_record,
            transform=transform,
            batch_id=row["batch_id"],
            related_interviews=related,
        )

    @staticmethod
    def _job_summary(row: Any) -> LegacyJobSummary:
        normalized = (
            json.loads(row["normalized"])
            if isinstance(row["normalized"], str)
            else row["normalized"]
        )
        transform = (
            json.loads(row["transform"]) if isinstance(row["transform"], str) else row["transform"]
        )
        return LegacyJobSummary(
            staging_id=row["staging_id"],
            title=normalized["title"],
            company=normalized["company"],
            location=normalized.get("location"),
            salary=normalized.get("salary"),
            source_url=normalized.get("source_url"),
            status=row["status"],
            duplicate_of=row["duplicate_of"],
            suggested_score=row["suggested_score"],
            review_status=row["review_status"],
            source_path=row["relative_path"],
            source_class=row["source_class"],
            source_sha256=row["sha256"],
            row_number=row["row_number"],
            imported_at=row["imported_at"],
            tags=tuple(transform.get("tags", [])),
        )
