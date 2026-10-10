"""Immutable local file assets and explicit attempt ownership."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0003_attachments"
down_revision = "0002_learning_model"
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
        raise ValueError("Incomplete attachments migration SQL")


def downgrade() -> None:
    raise RuntimeError("Deleting file ownership history by downgrade is not supported")
