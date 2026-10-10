"""Connection policy shared by repositories, migrations and temporary tests."""

from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from studium.infrastructure.user_data import ensure_outside_repository


def create_database_engine(path: Path, *, wal: bool = True) -> Engine:
    path = path.resolve()
    ensure_outside_repository(path)
    engine = create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"autocommit": False, "timeout": 5},
        hide_parameters=True,
    )

    @event.listens_for(engine, "connect")
    def configure_connection(connection, _record) -> None:
        # sqlite3 Python 3.12: PRAGMA foreign_keys needs autocommit, before BEGIN.
        previous = connection.autocommit
        connection.autocommit = True
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys = ON")
                if cursor.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                    raise RuntimeError("SQLite foreign keys are unavailable")
                cursor.execute("PRAGMA busy_timeout = 5000")
                if wal and cursor.execute("PRAGMA journal_mode = WAL").fetchone()[0] != "wal":
                    raise RuntimeError("SQLite WAL is unavailable")
            finally:
                cursor.close()
        finally:
            connection.autocommit = previous

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
