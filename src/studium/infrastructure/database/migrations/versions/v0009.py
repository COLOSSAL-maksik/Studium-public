"""Concrete daily-workflow links and explicitly approved legacy DOC support."""

import sqlite3
from pathlib import Path

from alembic import op

revision = "0009_daily_workflow"
down_revision = "0008_problem_variants"
branch_labels = None
depends_on = None


def _extend_file_extensions():
    connection = op.get_bind()
    table_sql = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_schema WHERE type='table' AND name='file_assets'"
    ).scalar_one()
    if "'doc'" in table_sql:
        return
    if table_sql.count("'docx'") != 1:
        raise RuntimeError("Unexpected FileAsset schema; migration stopped without replacing data")
    objects = (
        connection.exec_driver_sql(
            "SELECT sql FROM sqlite_schema WHERE tbl_name='file_assets' "
            "AND type IN ('index','trigger') AND sql IS NOT NULL ORDER BY type,name"
        )
        .scalars()
        .all()
    )
    # Keep FK enforcement enabled. All dependent rows are retained, and the same
    # UUIDs are restored inside this transaction before its deferred FK check.
    connection.exec_driver_sql("PRAGMA defer_foreign_keys=ON")
    connection.exec_driver_sql("CREATE TEMP TABLE iteration4_assets AS SELECT * FROM file_assets")
    before = connection.exec_driver_sql("SELECT count(*) FROM iteration4_assets").scalar_one()
    connection.exec_driver_sql("DROP TABLE file_assets")
    connection.exec_driver_sql(table_sql.replace("'docx'", "'doc','docx'"))
    connection.exec_driver_sql("INSERT INTO file_assets SELECT * FROM iteration4_assets")
    if connection.exec_driver_sql("SELECT count(*) FROM file_assets").scalar_one() != before:
        raise RuntimeError("FileAsset preservation check failed")
    for sql in objects:
        connection.exec_driver_sql(sql)
    connection.exec_driver_sql("DROP TABLE iteration4_assets")
    if connection.exec_driver_sql("PRAGMA foreign_key_check").all():
        raise RuntimeError("FileAsset foreign-key preservation check failed")


def upgrade():
    _extend_file_extensions()
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete daily-workflow SQL")


def downgrade():
    raise RuntimeError("Daily workflow links and imported DOC files must be preserved")
