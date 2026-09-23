"""Read-only audit for a local job database or export.

This tool never writes to the source path. It emits a small Markdown report
containing schema, counts, date hints, and a conservative publication decision.
It intentionally does not export row contents.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
from pathlib import Path

SENSITIVE_TERMS = {
    "name": "需脱敏",
    "email": "不可公开",
    "phone": "不可公开",
    "cookie": "不可公开",
    "token": "不可公开",
    "address": "需脱敏",
    "url": "需脱敏",
    "contact": "不可公开",
    "resume": "不可公开",
    "jd": "需人工审阅",
    "description": "需人工审阅",
}


def _decision(name: str) -> str:
    lowered = name.casefold()
    for term, decision in SENSITIVE_TERMS.items():
        if term in lowered:
            return decision
    return "可公开（仍需来源许可）"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(path: Path) -> str:
    if str(path) == "<JOB_DB_PATH>" or not path.exists():
        raise FileNotFoundError(
            "岗位数据库路径不可用；请提供真实本地路径，不能使用 <JOB_DB_PATH> 占位符。"
        )
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file())
        listing = "".join(f"{p.relative_to(path)}:{p.stat().st_size}" for p in files)
        listing_hash = hashlib.sha256(listing.encode()).hexdigest()
        return "\n".join(
            [
                "# 原始岗位数据审计",
                f"\n- 类型：目录（只读）\n- 文件数：{len(files)}",
                f"- 路径 SHA-256（目录清单）：{listing_hash}",
                "- 公开结论：在逐字段和来源许可审阅前，不发布完整原文、联系人或原始 URL。",
            ]
        )
    if path.suffix.casefold() in {".csv", ".tsv"}:
        delimiter = "\t" if path.suffix.casefold() == ".tsv" else ","
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            fields = reader.fieldnames or []
            rows = sum(1 for _ in reader)
        lines = [
            "# 原始岗位数据审计",
            f"\n- 类型：{path.suffix[1:].upper()}",
            f"- 行数：{rows}",
            f"- SHA-256：{_sha256(path)}",
            "",
            "| 字段 | 发布结论 |",
            "| --- | --- |",
        ]
        lines.extend(f"| `{field}` | {_decision(field)} |" for field in fields)
        return "\n".join(lines)
    if path.suffix.casefold() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("仅支持 SQLite、CSV 或 TSV 审计。")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        lines = [
            "# 原始岗位数据库审计",
            "",
            "- 类型：SQLite（只读连接）",
            f"- SHA-256：{_sha256(path)}",
            "",
            "| 表 | 行数 | 字段 | 发布结论 |",
            "| --- | ---: | --- | --- |",
        ]
        for table in tables:
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            decisions = "; ".join(f"{column}: {_decision(column)}" for column in columns)
            lines.append(f"| `{table}` | {count} | {', '.join(columns)} | {decisions} |")
        lines += [
            "",
            "公开结论：完整职位原文、联系人、精确 URL 参数和可还原原库的组合字段，"
            "需在来源许可明确后再发布。",
        ]
        return "\n".join(lines)
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="只读审计岗位数据库或导出")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/data-audit.md"))
    args = parser.parse_args()
    report = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(f"已生成只读审计：{args.output}")


if __name__ == "__main__":
    main()
