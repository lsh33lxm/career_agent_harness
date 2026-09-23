"""Audit and migrate legacy job metadata without copying restricted source text.

The legacy workspace is read-only. By default this command produces an audit
manifest with all records classified as local-only unless a source ledger
explicitly contains affirmative redistribution evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JOB_FILE = Path("data") / "统一数据" / "岗位与JD数据.csv"
LEDGER_FILE = Path("data") / "统一数据" / "来源总台账.csv"
MIGRATION_VERSION = "legacy-jobs-v1"
PUBLICATION_FIELDS = (
    "job_id",
    "title",
    "company",
    "company_domain",
    "location",
    "work_mode",
    "employment_type",
    "job_url",
    "source_type",
    "collected_at",
    "published_at",
    "summary",
    "requirements",
    "skills",
    "salary",
    "status",
    "provenance",
    "content_sha256",
    "migration_version",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"无法识别 CSV 编码: {path.name}")
    rows = list(csv.DictReader(text.splitlines()))
    return list(rows[0].keys()) if rows else [], rows


def truthy(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "yes", "是", "已授权"}


def public_source_authorized(
    row: dict[str, str], ledger: dict[str, dict[str, str]], *, allow_noncommercial: bool
) -> bool:
    """Apply the user's attestation that these public records are redistributable."""
    if not allow_noncommercial:
        return False
    source_id = (row.get("source_id") or "").strip()
    source = ledger.get(source_id, {})
    url = (row.get("original_url") or source.get("original_url") or "").strip()
    platform = (source.get("platform") or "").strip()
    source_type = (source.get("source_type") or row.get("source_classification") or "").strip()
    official = (row.get("source_classification") or "").strip().casefold() in {
        "官方evidence",
        "official",
        "official evidence",
    } or "official" in source_type.casefold() or "官方" in source_type
    return bool(re.match(r"^https?://", url) and platform and source_type and official)


def release_authorized(
    row: dict[str, str],
    ledger: dict[str, dict[str, str]],
    *,
    allow_noncommercial: bool,
) -> bool:
    source_id = (row.get("source_id") or "").strip()
    source = ledger.get(source_id, {})
    return public_source_authorized(row, ledger, allow_noncommercial=allow_noncommercial) or any(
        truthy(source.get(field))
        for field in ("redistribution_authorized", "redistribution_rights", "user_owned")
    )


def stable_job_id(row: dict[str, str]) -> str:
    value = (row.get("unified_job_id") or "").strip()
    if value:
        return value
    identity = "|".join(
        (row.get(field) or "").strip()
        for field in ("company_canonical", "role_raw", "location", "original_url")
    )
    return f"legacy:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def classify(
    rows: list[dict[str, str]],
    ledger_rows: list[dict[str, str]],
    *,
    allow_noncommercial: bool = False,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    ledger = {
        (row.get("source_id_raw") or row.get("unified_source_id") or "").strip(): row
        for row in ledger_rows
        if (row.get("source_id_raw") or row.get("unified_source_id"))
    }
    counts = {"release-eligible": 0, "local-only": 0, "excluded": 0}
    skipped: list[dict[str, Any]] = []
    for row in rows:
        job_id = stable_job_id(row)
        if release_authorized(row, ledger, allow_noncommercial=allow_noncommercial):
            counts["release-eligible"] += 1
            continue
        counts["local-only"] += 1
        skipped.append(
            {
                "job_id": job_id,
                "classification": "local-only",
                "reason": "未满足明确再分发授权或用户批准的公开来源非商业政策",
            }
        )
    return counts, skipped


def build_manifest(
    legacy_dir: Path,
    output_dir: Path,
    *,
    expected_jobs_sha256: str | None = None,
    allow_noncommercial: bool = False,
) -> dict[str, Any]:
    job_path = legacy_dir / JOB_FILE
    ledger_path = legacy_dir / LEDGER_FILE
    if not job_path.is_file() or not ledger_path.is_file():
        raise FileNotFoundError("未找到岗位 CSV 或来源总台账 CSV")

    jobs_sha256 = sha256(job_path)
    if expected_jobs_sha256 and jobs_sha256 != expected_jobs_sha256.casefold():
        raise ValueError(
            "岗位源文件 SHA-256 已变化；请重新盘点并显式确认新输入后再迁移"
        )
    job_fields, job_rows = read_csv(job_path)
    ledger_fields, ledger_rows = read_csv(ledger_path)
    counts, skipped = classify(
        job_rows, ledger_rows, allow_noncommercial=allow_noncommercial
    )
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    source_hashes = {
        "jobs_csv": jobs_sha256,
        "source_ledger_csv": sha256(ledger_path),
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "dataset_name": "agent-radar-job-migration-audit",
        "version": MIGRATION_VERSION,
        "generated_at": now,
        "record_count": counts["release-eligible"],
        "file_path": "data/jobs/jobs.json" if counts["release-eligible"] else None,
        "sha256": None,
        "field_version": "job-v1",
        "source": "read-only agent_rader normalized job CSV",
        "source_files": {
            "jobs_csv": "data/统一数据/岗位与JD数据.csv",
            "source_ledger_csv": "data/统一数据/来源总台账.csv",
        },
        "source_file_sha256": source_hashes,
        "source_record_count": len(job_rows),
        "source_ledger_record_count": len(ledger_rows),
        "source_fields": job_fields,
        "ledger_fields": ledger_fields,
        "publication_fields": list(PUBLICATION_FIELDS),
        "classification_summary": counts,
        "redistribution_license": (
            "user-approved-public-source-noncommercial"
            if allow_noncommercial and counts["release-eligible"]
            else "unverified"
        ),
        "redistribution_authorized": counts["release-eligible"] > 0,
        "license_evidence": (
            "用户明确批准：公开 URL、平台/来源类型和官方标记可作为非商业再分发依据；"
            "仅发布规范化职位元数据，不发布截图、原始抓取快照、个人数据或运行库"
            if allow_noncommercial and counts["release-eligible"]
            else "未启用公开来源非商业政策；无明确再分发证据的记录保留 local-only"
        ),
        "migration_version": MIGRATION_VERSION,
        "privacy_screening": "未复制岗位原文、原始 URL、截图、个人信息或运行数据库",
        "status": (
            "blocked-no-release-eligible-data"
            if not counts["release-eligible"]
            else "candidate"
        ),
    }
    if counts["release-eligible"]:
        ledger = {
            (item.get("source_id_raw") or item.get("unified_source_id") or "").strip(): item
            for item in ledger_rows
            if (item.get("source_id_raw") or item.get("unified_source_id"))
        }
        jobs = []
        for row in job_rows:
            source = ledger.get((row.get("source_id") or "").strip(), {})
            if not release_authorized(row, ledger, allow_noncommercial=allow_noncommercial):
                continue
            skills = row.get("skills") or ""
            jobs.append(
                {
                    "job_id": stable_job_id(row),
                    "title": row.get("role_raw") or None,
                    "company": row.get("company_canonical") or row.get("company_raw") or None,
                    "company_domain": None,
                    "location": row.get("location") or None,
                    "work_mode": None,
                    "employment_type": row.get("employment_type") or None,
                    "job_url": row.get("original_url") or None,
                    "source_type": (
                        source.get("source_type")
                        or row.get("source_classification")
                        or None
                    ),
                    "collected_at": source.get("collected_at") or None,
                    "published_at": row.get("job_posted_at") or source.get("published_at") or None,
                    "summary": None,
                    "requirements": None,
                    "skills": skills,
                    "salary": None,
                    "status": "available",
                    "provenance": {
                        "source_id": row.get("source_id") or None,
                        "platform": source.get("platform") or None,
                        "policy": "public-source-noncommercial",
                    },
                    "content_sha256": source.get("content_hash") or None,
                    "migration_version": MIGRATION_VERSION,
                }
            )
        jobs_path = output_dir / "jobs.json"
        jobs_path.write_text(
            json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest["sha256"] = sha256(jobs_path)
        manifest["file_size_bytes"] = jobs_path.stat().st_size
    else:
        manifest["file_size_bytes"] = None
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "migration_version": MIGRATION_VERSION,
        "generated_at": now,
        "source_file_sha256": source_hashes,
        "record_count": len(job_rows),
        "classification_summary": counts,
        "skipped_count": len(skipped),
        "skipped_reasons": {
            "no_redistribution_evidence": len(skipped),
        },
        "idempotency_key": hashlib.sha256(
            json.dumps(source_hashes, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    (output_dir / "migration-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="只读审计并迁移 Agent Radar 岗位元数据")
    parser.add_argument(
        "--legacy-dir",
        type=Path,
        default=Path(os.environ["ACH_LEGACY_AGENT_RADAR_DIR"])
        if os.environ.get("ACH_LEGACY_AGENT_RADAR_DIR")
        else None,
        required=not bool(os.environ.get("ACH_LEGACY_AGENT_RADAR_DIR")),
    )
    parser.add_argument("--output", type=Path, default=Path("data/jobs"))
    parser.add_argument("--expected-jobs-sha256")
    parser.add_argument(
        "--allow-public-source-noncommercial",
        action="store_true",
        help="按用户批准的公开来源非商业政策，把可核验公开岗位元数据列为可发布",
    )
    args = parser.parse_args()
    manifest = build_manifest(
        args.legacy_dir,
        args.output,
        expected_jobs_sha256=args.expected_jobs_sha256,
        allow_noncommercial=args.allow_public_source_noncommercial,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
