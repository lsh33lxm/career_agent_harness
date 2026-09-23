from __future__ import annotations

import json
from datetime import UTC, datetime

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
            requirements=tuple(str(item) for item in data.get("requirements", ())),
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
