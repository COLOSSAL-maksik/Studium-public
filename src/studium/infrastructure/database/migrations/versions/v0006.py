"""Reusable teaching content, academic weeks, lesson types and ticket snapshots."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0006_content_workflow"
down_revision = "0005_analytics_foundation"
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
        raise ValueError("Incomplete content migration SQL")


def downgrade():
    raise RuntimeError("Deleting teaching content/history by downgrade is not supported")
