from __future__ import annotations

import re
from collections import defaultdict
from pathlib import PurePosixPath

from importers.agent_radar.models import LegacyImportManifest, StrictModel


class ReconciliationGroup(StrictModel):
    key: str
    members: tuple[str, ...]
    hashes: tuple[str, ...]
    authority: str = "unresolved_candidate"


class ReconciliationSummary(StrictModel):
    same_key_same_hash: tuple[ReconciliationGroup, ...]
    same_key_different_hash: tuple[ReconciliationGroup, ...]
    cross_path_hash_duplicates: tuple[ReconciliationGroup, ...]
    snapshot_candidates: tuple[str, ...]
    version_family_candidates: tuple[ReconciliationGroup, ...]
    inspected_archive_member_duplicates: tuple[ReconciliationGroup, ...] = ()
    archive_member_inspection: str = "not_performed"


def reconcile_summary(manifest: LegacyImportManifest) -> ReconciliationSummary:
    """Group candidates without choosing winners or asserting derived-copy identity."""
    by_key: dict[str, list[tuple[str, str]]] = defaultdict(list)
    by_hash: dict[str, list[tuple[str, str]]] = defaultdict(list)
    by_family: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for source in manifest.source_files:
        item = (source.relative_path, source.sha256)
        by_key[source.legacy_key].append(item)
        by_hash[source.sha256].append(item)
        filename = PurePosixPath(source.relative_path).name.casefold()
        # This is a heuristic grouping, explicitly not source identity resolution.
        family = re.sub(
            r"(?:[-_ ](?:v\d+(?:\.\d+)*|\d{4}[-_]?\d{2}[-_]?\d{2}|copy\d*))", "", filename
        )
        by_family[family].append(item)

    def group(key: str, items: list[tuple[str, str]]) -> ReconciliationGroup:
        return ReconciliationGroup(
            key=key,
            members=tuple(sorted(path for path, _ in items)),
            hashes=tuple(sorted({sha for _, sha in items})),
        )

    same: list[ReconciliationGroup] = []
    conflict: list[ReconciliationGroup] = []
    for key, items in sorted(by_key.items()):
        if len(items) > 1:
            if len({sha for _, sha in items}) > 1:
                conflict.append(group(key, items))
            # Record identical subsets even when a key also has conflicting versions.
            for sha in sorted({sha for _, sha in items}):
                subset = [item for item in items if item[1] == sha]
                if len(subset) > 1:
                    same.append(group(key, subset))
    return ReconciliationSummary(
        same_key_same_hash=tuple(same),
        same_key_different_hash=tuple(conflict),
        cross_path_hash_duplicates=tuple(
            group(key, items) for key, items in sorted(by_hash.items()) if len(items) > 1
        ),
        snapshot_candidates=tuple(sorted(manifest.snapshot_candidates)),
        version_family_candidates=tuple(
            group(key, items) for key, items in sorted(by_family.items()) if len(items) > 1
        ),
    )
