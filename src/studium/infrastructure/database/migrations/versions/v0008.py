"""Add explicit problem purposes and children of a shared problem template."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0008_problem_variants"
down_revision = "0007_work_programs"
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
        raise ValueError("Incomplete problem migration SQL")


def downgrade():
    raise RuntimeError("Problem families and historical snapshots cannot be deleted by downgrade")
