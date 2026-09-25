from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from career_harness.core.job_source import (
    JobSourceHealth,
    JobSourceTerms,
    JobSourceTermsStatus,
    NormalizedJobRecord,
    RawJobRecord,
)


class ManualJobSource:
    source_id = "job-source-manual"

    def __init__(self, records: tuple[RawJobRecord, ...] = ()) -> None:
        self.records = records

    def search(self, query: str) -> tuple[RawJobRecord, ...]:
        query_lower = query.lower().strip()
        return tuple(
            item for item in self.records if not query_lower or query_lower in item.raw_text.lower()
        )

    def fetch_detail(self, ref: str) -> RawJobRecord:
        for item in self.records:
            if item.source_ref == ref:
                return item
        raise KeyError("manual job source ref not found")

    def normalize(self, raw: RawJobRecord) -> NormalizedJobRecord:
        try:
            data = json.loads(raw.raw_text)
        except json.JSONDecodeError:
            lines = [line.strip() for line in raw.raw_text.splitlines() if line.strip()]
            return NormalizedJobRecord(
                title=lines[0][:512],
                company="Unknown company",
                requirements=tuple(lines[1:]),
                source_url=raw.source_ref if raw.source_ref.startswith("http") else None,
            )
        return NormalizedJobRecord(
            title=str(data["title"]),
            company=str(data.get("company") or "Unknown company"),
            location=data.get("location"),
            remote=data.get("remote"),
            salary=data.get("salary"),
            published_at=data.get("published_at"),
            deadline_at=data.get("deadline_at"),
            requirements=tuple(str(item) for item in (data.get("requirements") or ())),
            source_url=data.get("source_url") or (
                raw.source_ref if raw.source_ref.startswith("http") else None
            ),
        )

    def health(self) -> JobSourceHealth:
        return JobSourceHealth(status="ok", message="manual source is local and ready")

    def terms(self) -> JobSourceTerms:
        return JobSourceTerms(
            source_id=self.source_id,
            status=JobSourceTermsStatus.VERIFIED,
            note="User supplied text or URL; no crawler or automated site access.",
        )


class OfflineFixtureJobSource(ManualJobSource):
    source_id = "job-source-offline-fixture"

    def __init__(self) -> None:
        super().__init__(
            (
                RawJobRecord(
                    source_ref="fixture://jobs/platform-engineer",
                    raw_text=json.dumps(
                        {
                            "title": "Platform Engineer",
                            "company": "Fixture Labs",
                            "location": "Remote",
                            "remote": True,
                            "requirements": ["Python", "SQLite", "Kubernetes"],
                        }
                    ),
                    captured_at=datetime(2026, 9, 21, tzinfo=UTC),
                ),
            )
        )

    def terms(self) -> JobSourceTerms:
        return JobSourceTerms(
            source_id=self.source_id,
            status=JobSourceTermsStatus.VERIFIED,
            note="Repository-owned synthetic fixture; no external terms apply.",
        )


class PackagedJobSeedSource(ManualJobSource):
    """Load the approved, repository-owned normalized seed without legacy paths."""

    source_id = "job-source-packaged-seed"

    def __init__(self, seed_path: Path | None = None) -> None:
        bundled_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        path = seed_path or Path(
            os.getenv(
                "ACH_JOB_SEED_PATH",
                bundled_root / "data" / "jobs" / "jobs.json",
            )
        )
        if not path.is_file():
            raise FileNotFoundError("离线岗位种子数据不可用，请检查安装资源")
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("离线岗位种子格式无效")
        records = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("job_id") or not row.get("title"):
                continue
            payload = dict(row)
            payload["source_url"] = payload.get("job_url")
            records.append(
                RawJobRecord(
                    source_ref=str(row["job_id"]),
                    raw_text=json.dumps(payload, ensure_ascii=False),
                    captured_at=datetime.now(UTC),
                )
            )
        super().__init__(tuple(records))

    def terms(self) -> JobSourceTerms:
        return JobSourceTerms(
            source_id=self.source_id,
            status=JobSourceTermsStatus.VERIFIED,
            note="安装包内置的用户批准公开来源种子；仅离线读取，不访问旧项目或外网。",
        )
