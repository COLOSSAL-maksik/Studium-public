"""Explicit database initialization/upgrade; never selects a user DB implicitly."""

import argparse
from pathlib import Path

from studium.infrastructure.database.migrations import SCHEMA_REVISION, upgrade_database
from studium.infrastructure.database.session import create_database_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade an explicitly selected Studium SQLite DB")
    parser.add_argument("--database", type=Path, required=True)
    args = parser.parse_args()
    engine = create_database_engine(args.database)
    try:
        upgrade_database(engine)
        print(f"Database is at Alembic revision {SCHEMA_REVISION}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
