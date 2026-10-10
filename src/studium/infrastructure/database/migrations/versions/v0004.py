"""Factual questions, messages and educational context; additive to v3."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0004_communication"
down_revision = "0003_attachments"
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
        raise ValueError("Incomplete communication migration SQL")


def downgrade() -> None:
    raise RuntimeError("Deleting communication history by downgrade is not supported")
