from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from career_harness.core.plugin.contracts import PluginManifest


def manifest_schema_path() -> Path:
    return Path(__file__).resolve().parents[4] / "schemas" / "plugin-manifest-v1.json"


def manifest_schema() -> dict[str, Any]:
    return json.loads(manifest_schema_path().read_text(encoding="utf-8"))


def validate_manifest(value: dict[str, Any] | PluginManifest) -> PluginManifest:
    if isinstance(value, PluginManifest):
        return value
    return PluginManifest.model_validate(value)
