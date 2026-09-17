from __future__ import annotations

from collections import defaultdict

from importers.agent_radar.models import Disposition, LegacyImportManifest, ReconciliationRecord


def build_reconciliation(manifest: LegacyImportManifest) -> tuple[ReconciliationRecord, ...]:
    by_key: dict[str, list] = defaultdict(list)
    for source_file in manifest.source_files:
        by_key[source_file.legacy_key].append(source_file)

    records: list[ReconciliationRecord] = []
    for legacy_key, candidates in sorted(by_key.items()):
        hashes = {candidate.sha256 for candidate in candidates}
        groups = {candidate.source_group for candidate in candidates}
        if len(candidates) < 2 or len(hashes) == 1:
            continue
        for candidate in candidates:
            records.append(
                ReconciliationRecord(
                    source_path=candidate.relative_path,
                    source_hash=candidate.sha256,
                    legacy_key=legacy_key,
                    candidate_core_identity=None,
                    mismatch="same legacy filename has conflicting content hashes",
                    disposition=Disposition.DEFERRED,
                    reason=(
                        "Conflicting candidates exist across source groups "
                        f"{', '.join(sorted(groups))}; canonical authority cannot be inferred."
                    ),
                )
            )
    return tuple(records)


def render_reconciliation_report(
    manifest: LegacyImportManifest, records: tuple[ReconciliationRecord, ...]
) -> str:
    groups: dict[str, int] = defaultdict(int)
    for source_file in manifest.source_files:
        groups[source_file.source_group] += 1

    lines = [
        "# Legacy Reconciliation Report",
        "",
        "**Status:** CANDIDATE - NEEDS USER APPROVAL",
        "",
        "No source group, workbook, snapshot, or generated database is declared canonical.",
        "",
        "## Inventory Summary",
        "",
        f"- Source workspace: `{manifest.source_workspace}`",
        f"- Files hashed: {len(manifest.source_files)}",
        f"- Snapshot candidates: {len(manifest.snapshot_candidates)}",
        f"- Skipped links/reparse entries: {len(manifest.skipped_entries)}",
        "- Approved entities: 0",
        "",
        "## Source Groups",
        "",
        "| Source group | Files |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{group}` | {count} |" for group, count in sorted(groups.items()))
    lines.extend(
        [
            "",
            "## Deferred Mismatches",
            "",
            (
                f"Detected {len(records)} conflicting file candidates. "
                "Every disposition is `deferred`."
            ),
            "",
            "| Legacy key | Source path | Hash prefix | Mismatch | Disposition |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for record in records:
        escaped_path = record.source_path.replace("|", "\\|")
        lines.append(
            f"| `{record.legacy_key}` | `{escaped_path}` | `{record.source_hash[:12]}` | "
            f"{record.mismatch} | `{record.disposition.value}` |"
        )
    if not records:
        lines.append(
            "| - | - | - | No conflicting filename/hash candidates detected | `deferred` |"
        )
    lines.extend(
        [
            "",
            "## Required Approval",
            "",
            "The user must decide source authority and candidate Core identities before any",
            "entity can move from candidate inventory to approved import or canonical cutover.",
            "",
        ]
    )
    return "\n".join(lines)
