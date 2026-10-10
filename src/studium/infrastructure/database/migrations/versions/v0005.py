"""Item evaluation facts and historical assessment content protection."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0005_analytics_foundation"
down_revision = "0004_communication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete analytics foundation migration SQL")


def downgrade() -> None:
    raise RuntimeError("Deleting item result history by downgrade is not supported")
