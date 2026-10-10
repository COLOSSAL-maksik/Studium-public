"""Initial local core; immutable SQL snapshot, including SQLite triggers."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0001_local_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # complete_statement handles trigger bodies with internal semicolons.
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete initial migration SQL")


def downgrade() -> None:
    raise RuntimeError("Deleting teaching history by downgrading to an empty DB is not supported")
