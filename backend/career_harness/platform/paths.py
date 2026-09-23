from __future__ import annotations

import os
import platform
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    database: Path
    artifacts: Path
    backups: Path
    browser_sessions: Path
    logs: Path

    @classmethod
    def resolve(
        cls,
        environment: Mapping[str, str] | None = None,
        system: str | None = None,
    ) -> AppPaths:
        env = environment if environment is not None else os.environ
        override = env.get("ACH_DATA_DIR")
        if override:
            root = Path(override).expanduser().resolve()
        else:
            active_system = system or platform.system()
            if active_system == "Windows":
                base = Path(env.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                root = base / "AgentCareerHarness"
            elif active_system == "Darwin":
                root = Path.home() / "Library" / "Application Support" / "AgentCareerHarness"
            else:
                base = Path(env.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
                root = base / "agent-career-harness"
            root = root.resolve()

        return cls(
            root=root,
            database=root / "career_harness.db",
            artifacts=root / "artifacts",
            backups=root / "backups",
            browser_sessions=root / "browser-sessions",
            logs=root / "logs",
        )

    def ensure_directories(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in (self.artifacts, self.backups, self.browser_sessions, self.logs):
            directory.mkdir(exist_ok=True)
