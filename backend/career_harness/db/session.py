from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def create_sqlite_engine(database_url: str) -> Engine:
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Foundation database must use a local SQLite URL")
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
