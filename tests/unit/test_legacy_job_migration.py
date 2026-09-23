from __future__ import annotations

import json
from pathlib import Path

from scripts.migrate_legacy_jobs import build_manifest, classify


def test_classification_requires_explicit_redistribution_evidence() -> None:
    rows = [{"unified_job_id": "job-1", "source_id": "source-1"}]
    ledger = [{"source_id_raw": "source-1", "original_url": "https://example.test"}]
    counts, skipped = classify(rows, ledger)
    assert counts == {"release-eligible": 0, "local-only": 1, "excluded": 0}
    assert skipped[0]["reason"]

    ledger[0]["redistribution_authorized"] = "true"
    counts, _ = classify(rows, ledger)
    assert counts["release-eligible"] == 1


def test_user_approved_public_source_policy_requires_public_official_metadata() -> None:
    rows = [
        {
            "unified_job_id": "job-public",
            "source_id": "source-public",
            "source_classification": "官方Evidence",
            "original_url": "https://jobs.example.test/1",
        }
    ]
    ledger = [
        {
            "source_id_raw": "source-public",
            "platform": "官方招聘页",
            "source_type": "job_posting",
            "original_url": "https://jobs.example.test/1",
        }
    ]
    counts, skipped = classify(rows, ledger)
    assert counts["release-eligible"] == 0
    assert skipped
    counts, skipped = classify(rows, ledger, allow_noncommercial=True)
    assert counts == {"release-eligible": 1, "local-only": 0, "excluded": 0}
    assert skipped == []


def test_user_attested_source_ledger_authorization_admits_linked_record() -> None:
    rows = [{"unified_job_id": "job-attested", "source_id": "source-attested"}]
    ledger = [{"source_id_raw": "source-attested", "notes": "授权已留存于来源台账"}]
    counts, skipped = classify(rows, ledger, attest_source_ledger_authorization=True)
    assert counts == {"release-eligible": 1, "local-only": 0, "excluded": 0}
    assert skipped == []


def test_user_attested_source_ledger_authorization_covers_unlinked_job_row() -> None:
    rows = [{"unified_job_id": "job-without-key", "source_id": "missing-source"}]
    counts, skipped = classify(rows, [], attest_source_ledger_authorization=True)
    assert counts == {"release-eligible": 1, "local-only": 0, "excluded": 0}
    assert skipped == []


def test_manifest_is_repeatable_and_does_not_copy_rows(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    jobs = legacy / "data" / "统一数据"
    jobs.mkdir(parents=True)
    (jobs / "岗位与JD数据.csv").write_text(
        "unified_job_id,company_canonical,role_raw,location,original_url\n"
        "job-1,Example,Engineer,Beijing,https://example.test/job\n",
        encoding="utf-8",
    )
    (jobs / "来源总台账.csv").write_text(
        "source_id_raw,original_url\nsource-1,https://example.test\n", encoding="utf-8"
    )
    output = tmp_path / "out"
    first = build_manifest(legacy, output)
    second = build_manifest(legacy, output)
    assert first["source_file_sha256"] == second["source_file_sha256"]
    assert first["record_count"] == 0
    assert not (output / "jobs.json").exists()
    report = json.loads((output / "migration-report.json").read_text(encoding="utf-8"))
    assert report["skipped_count"] == 1


def test_manifest_rejects_changed_source_hash(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    jobs = legacy / "data" / "统一数据"
    jobs.mkdir(parents=True)
    job_file = jobs / "岗位与JD数据.csv"
    job_file.write_text("unified_job_id\njob-1\n", encoding="utf-8")
    (jobs / "来源总台账.csv").write_text("source_id_raw\nsource-1\n", encoding="utf-8")
    from scripts.migrate_legacy_jobs import sha256

    expected = sha256(job_file)
    job_file.write_text("unified_job_id\njob-2\n", encoding="utf-8")
    try:
        build_manifest(legacy, tmp_path / "out", expected_jobs_sha256=expected)
    except ValueError as error:
        assert "SHA-256" in str(error)
    else:
        raise AssertionError("changed source must be rejected")
