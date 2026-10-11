"""Protect frozen taxonomy dependencies without rewriting published payloads."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0012_frozen_taxonomy"
down_revision = "0011_qa_review_fixes"
branch_labels = None
depends_on = None


def upgrade():
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete frozen taxonomy SQL")


def downgrade():
    raise RuntimeError("Frozen classification dependencies must remain protected")
