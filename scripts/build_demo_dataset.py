"""Build a small, reviewable demo dataset from a read-only legacy CSV.

The output deliberately excludes URLs, raw JD text, archive paths and contact
fields. It is a projection for product demonstration, not an application source.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", data, 0, 1, "无法识别岗位文件编码")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _skills(value: str) -> list[str]:
    if not value:
        return []
    try:
        parsed: Any = json.loads(value)
        values = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        values = value.replace("；", ",").replace(";", ",").split(",")
    return [str(item).strip() for item in values if str(item).strip()][:8]


def _location(value: str) -> str:
    if not value:
        return "地点待确认"
    try:
        parsed: Any = json.loads(value)
        if isinstance(parsed, list):
            joined = "、".join(str(item).strip() for item in parsed if str(item).strip())
            return joined[:120] or "地点待确认"
    except json.JSONDecodeError:
        pass
    return value.strip()[:120]


def build(
    source: Path, output: Path, *, limit: int = 24, seed: str = "ach-demo-v1"
) -> dict[str, Any]:
    text = _read_text(source)
    rows = list(csv.DictReader(text.splitlines()))
    candidates: list[dict[str, Any]] = []
    for row in rows:
        title = (row.get("role_raw") or row.get("role_family") or "待确认岗位").strip()
        company = (row.get("company_canonical") or row.get("company_raw") or "待确认公司").strip()
        if not title or not company:
            continue
        stable = row.get("unified_job_id") or f"{company}|{title}|{row.get('location', '')}"
        digest = hashlib.sha256(f"{seed}|{stable}".encode()).hexdigest()
        candidates.append(
            {
                "demo_id": f"demo_job_{digest[:16]}",
                "title": title[:160],
                "company": company[:160],
                "location": _location(row.get("location", "")),
                "region": row.get("region") or "未知",
                "skills": _skills(row.get("skills", "")),
                "evidence_grade": row.get("evidence_grade") or "未确认",
                "status": "演示样本 · 历史岗位",
                "source_type": "经脱敏历史岗位样本",
                "review_status": "demo_reviewed",
            }
        )
    candidates.sort(key=lambda item: item["demo_id"])
    selected = candidates[:limit]
    output.mkdir(parents=True, exist_ok=True)
    (output / "jobs.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "demo-v1",
        "generated_by": "scripts/build_demo_dataset.py",
        "source_sha256": _sha256(source),
        "source_row_count": len(rows),
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "seed": seed,
        "excluded_fields": [
            "original_url",
            "responsibilities_raw",
            "requirements_raw",
            "preferred_raw",
            "original_archive_path",
            "source_table",
            "source_id",
        ],
        "disclaimer": "历史岗位脱敏样本，不代表实时职位，不应直接用于投递决策。",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="从只读岗位 CSV 生成脱敏演示数据")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/demo"))
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--seed", default="ach-demo-v1")
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.source, args.output, limit=args.limit, seed=args.seed),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
