from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def migration_resource_root() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root is not None:
        return Path(bundled_root)
    return Path(__file__).resolve().parents[3]


def alembic_config(database_url: str) -> Config:
    resource_root = migration_resource_root()
    config = Config(str(resource_root / "alembic.ini"))
    config.set_main_option("script_location", str(resource_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")

