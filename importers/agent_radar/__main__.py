from __future__ import annotations

import argparse
from pathlib import Path

from importers.agent_radar.inventory import (
    build_manifest,
    load_manifest,
    manifest_summary,
    source_metadata_signature,
    verify_manifest,
    write_manifest,
)
from importers.agent_radar.reconcile import build_reconciliation, render_reconciliation_report
from importers.agent_radar.structured_import import run_structured_import


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Agent Radar migration inventory")
    commands = parser.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser("inventory")
    inventory.add_argument("--source", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)
    inventory.add_argument("--verify", action="store_true")

    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("--manifest", type=Path, required=True)
    reconcile.add_argument("--output", type=Path, required=True)

    structured = commands.add_parser(
        "structured-import",
        help="将批准范围内的 Legacy 文件单向导入独立 Career Harness 数据目录",
    )
    structured.add_argument("--source", type=Path, required=True)
    structured.add_argument("--data-root", type=Path, required=True)
    structured.add_argument("--report", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "inventory":
        before = source_metadata_signature(args.source)
        manifest = build_manifest(args.source)
        write_manifest(manifest, args.output)
        after = source_metadata_signature(args.source)
        if before != after:
            raise RuntimeError("source metadata changed during inventory")
        if args.verify:
            failures = tuple(verify_manifest(manifest))
            if failures:
                raise RuntimeError(f"manifest verification failed: {failures[:3]}")
        print(manifest_summary(manifest))
        return

    if args.command == "structured-import":
        report = run_structured_import(args.source, args.data_root, report_path=args.report)
        print(report.model_dump_json(indent=2))
        return

    manifest = load_manifest(args.manifest)
    records = build_reconciliation(manifest)
    source_root = Path(manifest.source_workspace).resolve(strict=True)
    output = args.output.resolve()
    if output == source_root or output.is_relative_to(source_root):
        raise ValueError("Reconciliation output must be outside the read-only source workspace")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_reconciliation_report(manifest, records), encoding="utf-8")
    print(f"reconciliation_records={len(records)} status=needs_user_approval")


if __name__ == "__main__":
    main()

