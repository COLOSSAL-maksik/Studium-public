"""Correct QA assignments without rewriting v10 or inventing old content."""

import json
import sqlite3
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from alembic import op

revision = "0011_qa_review_fixes"
down_revision = "0010_qa_package"
branch_labels = None
depends_on = None


def _backfill(connection):
    plans = {
        r._mapping["id"]: dict(r._mapping)
        for r in connection.exec_driver_sql("SELECT * FROM semester_plans")
    }
    versions = {
        r[0]: json.loads(r[1])
        for r in connection.exec_driver_sql("SELECT id,content_json FROM program_versions")
    }
    histories = list(
        connection.exec_driver_sql(
            "SELECT snapshot_json FROM plan_history ORDER BY plan_revision,created_at,id"
        )
    )
    for table, field in (("plan_modules", "plan_module_id"), ("planned_works", "planned_work_id")):
        for row in connection.exec_driver_sql(f"SELECT * FROM {table}"):
            source = dict(row._mapping)
            plan = plans[source["semester_plan_id"]]
            # Earliest saved binding wins, including previously reassigned plans.
            for history in histories:
                saved = json.loads(history[0])
                if saved["plan"]["id"] == plan["id"] and any(
                    v["id"] == source["id"]
                    for v in saved.get("modules" if field == "plan_module_id" else "works", [])
                ):
                    plan = saved["plan"]
                    break
            version_id = plan.get("program_version_id")
            snapshot = (
                versions.get(version_id, {}) if field == "planned_work_id" else {"module": source}
            )
            values = {
                "id": str(uuid5(NAMESPACE_URL, "studium:qa:v11:source:" + source["id"])),
                "semester_plan_id": source["semester_plan_id"],
                "plan_module_id": source["id"] if field == "plan_module_id" else None,
                "planned_work_id": source["id"] if field == "planned_work_id" else None,
                "program_version_id": version_id,
                "course_semester": plan.get("course_semester"),
                "snapshot_json": json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
                "provenance": "migration_saved_binding" if version_id else "legacy_unknown",
                "created_at": source["created_at"],
                "updated_at": source["updated_at"],
                "revision": 1,
                "deleted_at": None,
            }
            connection.exec_driver_sql(
                "INSERT INTO plan_content_sources ("
                + ",".join(values)
                + ") VALUES ("
                + ",".join("?" for _ in values)
                + ")",
                tuple(values.values()),
            )


def upgrade():
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete QA review SQL")
    _backfill(op.get_bind())


def downgrade():
    raise RuntimeError("Original bindings and late submission history must be preserved")
