"""Apply versioned production migrations without replacing existing data."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

SCHEMA_REVISION = "0013_annual_program"


def migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    return config


def upgrade_database(engine: Engine) -> None:
    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        if tables and "alembic_version" not in tables:
            raise ValueError("Unversioned nonempty database; explicit import is required")
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Foreign key integrity check failed")
