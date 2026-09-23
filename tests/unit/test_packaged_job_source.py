from __future__ import annotations

import json
from pathlib import Path

from career_harness.adapters.job_sources import PackagedJobSeedSource


def test_packaged_seed_source_loads_normalized_jobs_without_legacy_path(tmp_path: Path) -> None:
    seed = tmp_path / "jobs.json"
    seed.write_text(
        json.dumps(
            [
                {
                    "job_id": "job-1",
                    "title": "工程师",
                    "company": "Example",
                    "location": "Remote",
                    "job_url": "https://example.test/jobs/1",
                    "requirements": ["Python"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    source = PackagedJobSeedSource(seed)
    records = source.search("工程师")
    assert len(records) == 1
    normalized = source.normalize(records[0])
    assert normalized.title == "工程师"
    assert normalized.company == "Example"
    assert normalized.source_url == "https://example.test/jobs/1"
