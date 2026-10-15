"""Annual drafts, import provenance and independent lesson planning; no backfill."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0013_annual_program"
down_revision = "0012_frozen_taxonomy"
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
        raise ValueError("Incomplete annual program SQL")


def downgrade():
    raise RuntimeError("Annual program history must be preserved")
