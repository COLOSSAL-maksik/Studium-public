"""Separate course content/calendars and immutable QA facts; preserve v1–v9 bytes."""

import json
import re
import sqlite3
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from alembic import op

revision = "0010_qa_package"
down_revision = "0009_daily_workflow"
branch_labels = None
depends_on = None


def _id(kind, *keys):
    return str(uuid5(NAMESPACE_URL, "studium:qa:v10:" + kind + ":" + ":".join(keys)))


def _backfill(connection):
    def rows(table):
        return [dict(row._mapping) for row in connection.exec_driver_sql(f"SELECT * FROM {table}")]

    def insert(table, source, kind, keys, **values):
        record = {
            "id": _id(kind, *keys),
            **values,
            **{name: source[name] for name in ("created_at", "updated_at", "deleted_at")},
            "revision": 1,
        }
        columns = ",".join(record)
        parameters = ",".join("?" for _ in record)
        connection.exec_driver_sql(
            f"INSERT INTO {table} ({columns}) VALUES ({parameters})", tuple(record.values())
        )
        return record["id"]

    programs = {p["id"]: p for p in rows("work_programs")}
    definitions = {d["id"]: d for d in rows("homework_definitions")}
    terms = {t["id"]: t for t in rows("academic_terms")}
    modules, works, assessments = (
        rows("program_modules"),
        rows("program_works"),
        rows("assessments"),
    )
    snapshots = {
        name: rows(name)
        for name in (
            "program_topics",
            "program_skills",
            "program_materials",
            "program_literature",
            "program_attachments",
            "module_topics",
            "definition_problems",
            "definition_topics",
            "definition_skills",
        )
    }
    versions = {}
    for pid, p in programs.items():
        cp = insert(
            "course_programs",
            p,
            "content",
            [pid],
            course_id=p["course_id"],
            title=p["title"],
            notes=p["notes"],
        )
        owned_modules = [m for m in modules if m["work_program_id"] == pid]
        owned_works = [w for w in works if w["work_program_id"] == pid]
        mids = {m["id"] for m in owned_modules}
        dids = {w["definition_id"] for w in owned_works}
        content = {
            "legacy_program": p,
            "modules": owned_modules,
            "works": owned_works,
            "definitions": [d for did, d in definitions.items() if did in dids],
            "course_semester": None,
            "provenance": "migration_baseline",
        }
        for name, records in snapshots.items():
            content[name] = [
                r
                for r in records
                if r.get("work_program_id") == pid
                or r.get("module_id") in mids
                or r.get("definition_id") in dids
            ]
        version = insert(
            "program_versions",
            p,
            "version",
            [pid],
            course_program_id=cp,
            version_no=1,
            content_json=json.dumps(content, ensure_ascii=False, sort_keys=True),
            label=p["version"],
        )
        versions[pid] = version
        reference_targets = {
            "topic_id": {r["topic_id"] for r in content["program_topics"]}
            | {r["topic_id"] for r in content["module_topics"]},
            "skill_id": {r["skill_id"] for r in content["program_skills"]},
            "definition_id": dids,
            "seminar_material_id": {r["seminar_material_id"] for r in content["program_materials"]},
            "literature_item_id": {r["literature_item_id"] for r in content["program_literature"]},
            "file_asset_id": {r["file_asset_id"] for r in content["program_attachments"]},
        }
        for field, target_ids in reference_targets.items():
            for target in sorted(target_ids):
                references = {name: None for name in reference_targets}
                references[field] = target
                insert(
                    "version_references",
                    p,
                    "version-reference",
                    [pid, field, target],
                    program_version_id=version,
                    **references,
                )
        insert(
            "legacy_program_maps",
            p,
            "source-map",
            [pid],
            legacy_program_id=pid,
            program_version_id=version,
        )
        code = unicodedata.normalize("NFC", p["direction"].strip())
        if re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{2}", code):
            did = _id("direction", code.casefold())
            if not connection.exec_driver_sql(
                "SELECT 1 FROM directions WHERE id=?", (did,)
            ).first():
                insert(
                    "directions",
                    {**p, "deleted_at": None},
                    "direction",
                    [code.casefold()],
                    code=code,
                    normalized_key=code.casefold(),
                    name="",
                )
            insert(
                "program_directions",
                p,
                "direction-link",
                [pid, did],
                program_version_id=version,
                direction_id=did,
            )

    for offering in rows("course_offerings"):
        oid = offering["id"]
        p = programs.get(offering["work_program_id"])
        term = terms[offering["term_id"]]
        first = p["first_week_start"] if p else term["starts_on"]
        weeks = (
            p["weeks"]
            if p
            else min(
                104,
                max(
                    1,
                    ((date.fromisoformat(term["ends_on"]) - date.fromisoformat(first)).days + 7)
                    // 7,
                ),
            )
        )
        offset = p["week_utc_offset_minutes"] if p else term["week_utc_offset_minutes"]
        plan = insert(
            "semester_plans",
            offering,
            "plan",
            [oid],
            offering_id=oid,
            program_version_id=versions.get(p["id"]) if p else None,
            first_week_start=first,
            weeks=weeks,
            course_semester=None,
            week_utc_offset_minutes=offset,
            configured=int(p is not None),
        )
        module_map, work_map = {}, {}
        if p:
            for m in modules:
                if m["work_program_id"] != p["id"]:
                    continue
                module_map[m["id"]] = insert(
                    "plan_modules",
                    m,
                    "module",
                    [oid, m["id"]],
                    semester_plan_id=plan,
                    source_module_id=m["id"],
                    title=m["title"],
                    start_week=m["start_week"],
                    end_week=m["end_week"],
                    sort_order=m["sort_order"],
                )
            for w in works:
                if w["work_program_id"] != p["id"]:
                    continue
                d = definitions[w["definition_id"]]

                def day(explicit, week, end=False):
                    if explicit:
                        return explicit
                    return (
                        str(
                            date.fromisoformat(first)
                            + timedelta(weeks=week - 1, days=6 if end else 0)
                        )
                        if week
                        else None
                    )

                work_map[w["id"]] = insert(
                    "planned_works",
                    w,
                    "work",
                    [oid, w["id"]],
                    semester_plan_id=plan,
                    source_work_id=w["id"],
                    module_id=module_map.get(w["module_id"]),
                    definition_id=w["definition_id"],
                    title=d["title"],
                    type=d["type"],
                    number=d["label"],
                    issue_date=day(w["issue_date"], w["planned_issue_week"]),
                    due_date=day(w["due_date"], w["planned_due_week"], True),
                    exact_due_at=None,
                    deadline_kind="DATE_EXCLUSIVE"
                    if w["due_date"]
                    else "WEEK_ONLY"
                    if w["planned_due_week"]
                    else "NONE",
                    due_week=w["planned_due_week"],
                    min_cents=None,
                    max_cents=None,
                    sort_order=w["sort_order"],
                    cancelled=0,
                )
        for a in assessments:
            if a["offering_id"] != oid:
                continue
            wid = work_map.get(a["program_work_id"])
            if wid is None:
                wid = insert(
                    "planned_works",
                    a,
                    "assessment-work",
                    [a["id"]],
                    semester_plan_id=plan,
                    source_work_id=None,
                    module_id=None,
                    definition_id=a["homework_definition_id"],
                    title=a["title"],
                    type=a["type"],
                    number=a["number"] or "",
                    issue_date=None,
                    due_date=None,
                    exact_due_at=a["due_at"],
                    deadline_kind="EXACT_INCLUSIVE"
                    if a["due_at"] is not None
                    else "WEEK_ONLY"
                    if a["planned_due_week"]
                    else "NONE",
                    due_week=a["planned_due_week"],
                    min_cents=None,
                    max_cents=None,
                    sort_order=0,
                    cancelled=0,
                )
            elif a["due_at"] is not None:
                # The issued legacy exact deadline has precedence. Keep the raw
                # ProgramWork schedule in immutable source content/baseline too.
                connection.exec_driver_sql(
                    "UPDATE planned_works SET exact_due_at=?,deadline_kind='EXACT_INCLUSIVE',revision=revision+1 WHERE id=?",
                    (a["due_at"], wid),
                )
            insert(
                "issued_works",
                a,
                "issued",
                [a["id"]],
                planned_work_id=wid,
                assessment_id=a["id"],
                actual_issued_at=None,
                provenance="legacy_ambiguous",
            )
        current = {
            "plan": dict(
                connection.exec_driver_sql("SELECT * FROM semester_plans WHERE id=?", (plan,))
                .first()
                ._mapping
            ),
            "modules": [
                dict(r._mapping)
                for r in connection.exec_driver_sql(
                    "SELECT * FROM plan_modules WHERE semester_plan_id=?", (plan,)
                )
            ],
            "works": [
                dict(r._mapping)
                for r in connection.exec_driver_sql(
                    "SELECT * FROM planned_works WHERE semester_plan_id=?", (plan,)
                )
            ],
            "legacy_assessments": [a for a in assessments if a["offering_id"] == oid],
        }
        insert(
            "plan_history",
            offering,
            "history",
            [oid],
            semester_plan_id=plan,
            plan_revision=1,
            snapshot_json=json.dumps(current, ensure_ascii=False, sort_keys=True),
            reason="Впервые зафиксированный план; прежний первоначальный план неизвестен",
            provenance="migration_baseline",
        )


def upgrade():
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete QA package SQL")
    _backfill(op.get_bind())


def downgrade():
    raise RuntimeError("Course plans, exact results and review history must be preserved")
