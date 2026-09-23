from __future__ import annotations

import json
from pathlib import Path

from career_harness.db.migrations import upgrade_to_head
from career_harness.db.session import create_sqlite_engine, sqlite_url
from career_harness.platform import AppPaths
from career_harness.services.legacy_import_service import LegacyImportReport, LegacyImportService
from career_harness.storage import ArtifactStore


def run_structured_import(
    source_root: Path,
    data_root: Path,
    *,
    report_path: Path | None = None,
) -> LegacyImportReport:
    source = source_root.expanduser().resolve(strict=True)
    destination = data_root.expanduser().resolve()
    if destination == source or destination.is_relative_to(source):
        raise ValueError("导入数据目录必须位于只读 Legacy 目录之外")
    paths = AppPaths.resolve({"ACH_DATA_DIR": str(destination)})
    paths.ensure_directories()
    upgrade_to_head(sqlite_url(paths.database))
    engine = create_sqlite_engine(sqlite_url(paths.database))
    try:
        report = LegacyImportService(
            engine,
            ArtifactStore(paths.artifacts),
            default_source_root=source,
        ).run()
    finally:
        engine.dispose()
    if report_path is not None:
        output = report_path.expanduser().resolve()
        if output == source or output.is_relative_to(source):
            raise ValueError("导入报告必须写入只读 Legacy 目录之外")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report
