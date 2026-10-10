"""Development-only SQL snapshot writer; production reads the frozen SQL file."""

from pathlib import Path

from sqlalchemy.dialects.sqlite import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from studium.infrastructure.database.models.program import SPECS


def trigger(name, table, event, condition, message):
    return f"CREATE TRIGGER {name} BEFORE {event} ON {table} WHEN {condition} BEGIN SELECT RAISE(ABORT, '{message}'); END;\n"


def main():
    sql = ["-- Iteration 2 additive snapshot; existing records and v1-v6 resources retained.\n"]
    for name, (entity, row, owner, target) in SPECS.items():
        table = row.__table__
        sql.append(str(CreateTable(table).compile(dialect=dialect())) + ";\n")
        for index in sorted(table.indexes, key=lambda i: i.name):
            sql.append(str(CreateIndex(index).compile(dialect=dialect())) + ";\n")
        sql.append(
            trigger(
                name + "_metadata_update",
                name,
                "UPDATE",
                "NEW.id IS NOT OLD.id OR NEW.created_at IS NOT OLD.created_at OR NEW.revision != OLD.revision + 1 OR NEW.updated_at < OLD.updated_at",
                "immutable identity or invalid revision",
            )
        )
        sql.append(
            f"CREATE TRIGGER {name}_no_delete BEFORE DELETE ON {name} BEGIN SELECT RAISE(ABORT, 'record must be soft deleted'); END;\n"
        )
        fields = [c.name for c in table.columns if c.foreign_keys and c.name != "module_id"]
        if name in {
            "assessment_problems",
            "student_problem_assignments",
            "attempt_skill_results",
            "student_problem_files",
        }:
            fields = [
                c.name
                for c in table.columns
                if c.name not in {"id", "created_at", "updated_at", "revision", "deleted_at"}
            ]
        if fields:
            sql.append(
                trigger(
                    name + "_identity_update",
                    name,
                    "UPDATE",
                    " OR ".join(f"NEW.{f} IS NOT OLD.{f}" for f in fields),
                    "immutable ownership or factual snapshot",
                )
            )
    sql += [
        "ALTER TABLE student_groups ADD COLUMN faculty_short TEXT NOT NULL DEFAULT '';\n",
        "ALTER TABLE course_offerings ADD COLUMN work_program_id TEXT REFERENCES work_programs(id);\n",
        "CREATE INDEX course_offerings_work_program ON course_offerings(work_program_id);\n",
        "ALTER TABLE assessments ADD COLUMN program_work_id TEXT REFERENCES program_works(id);\n",
        "CREATE INDEX assessments_program_work ON assessments(program_work_id);\n",
        "CREATE UNIQUE INDEX assessments_program_work_active ON assessments(offering_id,program_work_id) WHERE deleted_at IS NULL AND program_work_id IS NOT NULL;\n",
        "ALTER TABLE homework_definitions ADD COLUMN type TEXT NOT NULL DEFAULT 'HOMEWORK' CHECK(type IN ('HOMEWORK','CONTROL_WORK','LAB','DEFENSE','EXAM','TEST','OTHER'));\n",
        "ALTER TABLE problems ADD COLUMN identifier TEXT NOT NULL DEFAULT '';\n",
        "CREATE UNIQUE INDEX problems_identifier_active ON problems(course_id,identifier) WHERE deleted_at IS NULL AND identifier != '';\n",
        "ALTER TABLE seminar_materials ADD COLUMN type TEXT NOT NULL DEFAULT 'SEMINAR' CHECK(type IN ('SEMINAR','LECTURE'));\n",
        "ALTER TABLE lessons ADD COLUMN planned_date TEXT CHECK(planned_date IS NULL OR (date(planned_date, '+0 days') IS NOT NULL AND date(planned_date, '+0 days') = planned_date));\n",
        "ALTER TABLE lessons ADD COLUMN planned_week INTEGER CHECK(planned_week IS NULL OR (typeof(planned_week) = 'integer' AND planned_week >= 1));\n",
        "ALTER TABLE lessons ADD COLUMN module_id TEXT REFERENCES program_modules(id);\n",
        "ALTER TABLE lessons ADD COLUMN cancelled INTEGER NOT NULL DEFAULT 0 CHECK(cancelled IN (0,1));\n",
        "ALTER TABLE lessons ADD COLUMN cancellation_reason TEXT NOT NULL DEFAULT '';\n",
    ]
    guards = {
        "course_offerings": "NEW.work_program_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM work_programs p WHERE p.id=NEW.work_program_id AND p.course_id=NEW.course_id AND p.term_id=NEW.term_id)",
        "program_modules": "NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM work_programs p WHERE p.id=NEW.work_program_id AND NEW.end_week<=p.weeks) OR EXISTS(SELECT 1 FROM program_modules m WHERE m.work_program_id=NEW.work_program_id AND m.id!=NEW.id AND m.deleted_at IS NULL AND m.start_week<=NEW.end_week AND m.end_week>=NEW.start_week))",
        "program_works": "NOT EXISTS(SELECT 1 FROM work_programs p JOIN homework_definitions d ON d.course_id=p.course_id WHERE p.id=NEW.work_program_id AND d.id=NEW.definition_id AND (NEW.planned_issue_week IS NULL OR NEW.planned_issue_week<=p.weeks) AND (NEW.planned_due_week IS NULL OR NEW.planned_due_week<=p.weeks) AND (NEW.module_id IS NULL OR EXISTS(SELECT 1 FROM program_modules m WHERE m.id=NEW.module_id AND m.work_program_id=p.id AND (NEW.planned_due_week IS NULL OR NEW.planned_due_week BETWEEN m.start_week AND m.end_week))) AND (NEW.issue_date IS NULL OR (NEW.planned_issue_week IS NOT NULL AND NEW.issue_date BETWEEN date(p.first_week_start, '+' || ((NEW.planned_issue_week-1)*7) || ' days') AND date(p.first_week_start, '+' || (NEW.planned_issue_week*7-1) || ' days'))) AND (NEW.due_date IS NULL OR (NEW.planned_due_week IS NOT NULL AND NEW.due_date BETWEEN date(p.first_week_start, '+' || ((NEW.planned_due_week-1)*7) || ' days') AND date(p.first_week_start, '+' || (NEW.planned_due_week*7-1) || ' days'))))",
        "assessments": "NEW.program_work_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_works w JOIN course_offerings o ON o.work_program_id=w.work_program_id WHERE w.id=NEW.program_work_id AND o.id=NEW.offering_id)",
        "lessons": "(NEW.planned_week IS NOT NULL AND NOT EXISTS(SELECT 1 FROM course_offerings o JOIN work_programs p ON p.id=o.work_program_id WHERE o.id=NEW.course_offering_id AND NEW.planned_week<=p.weeks)) OR (NEW.module_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM program_modules m JOIN course_offerings o ON o.work_program_id=m.work_program_id WHERE m.id=NEW.module_id AND o.id=NEW.course_offering_id AND (NEW.planned_week IS NULL OR NEW.planned_week BETWEEN m.start_week AND m.end_week)))",
        "homework_pack_works": "NOT EXISTS(SELECT 1 FROM homework_packs p JOIN homework_definitions d ON d.course_id=p.course_id WHERE p.id=NEW.homework_pack_id AND d.id=NEW.definition_id AND d.type='HOMEWORK')",
        "definition_problems": "NOT EXISTS(SELECT 1 FROM homework_definitions d JOIN problems p ON p.course_id=d.course_id WHERE d.id=NEW.definition_id AND p.id=NEW.problem_id)",
        "assessment_problems": "NOT EXISTS(SELECT 1 FROM assessment_items i JOIN assessments a ON a.id=i.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN problems p ON p.course_id=o.course_id WHERE i.id=NEW.assessment_item_id AND p.id=NEW.problem_id)",
        "student_problem_assignments": "NOT EXISTS(SELECT 1 FROM student_works w JOIN assessment_items i ON i.assessment_id=w.assessment_id JOIN assessments a ON a.id=w.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN problems p ON p.course_id=o.course_id WHERE w.id=NEW.student_work_id AND i.id=NEW.assessment_item_id AND p.id=NEW.problem_id)",
        "attempt_skill_results": "NOT EXISTS(SELECT 1 FROM attempt_item_results r JOIN attempts t ON t.id=r.attempt_id JOIN student_works w ON w.id=t.student_work_id JOIN assessments a ON a.id=w.assessment_id JOIN course_offerings o ON o.id=a.offering_id JOIN skills s ON s.course_id=o.course_id WHERE r.id=NEW.attempt_item_result_id AND s.id=NEW.skill_id)",
        "knowledge_sources": "NOT EXISTS(SELECT 1 FROM knowledge_entries k JOIN question_cases q ON q.id=NEW.question_case_id JOIN course_offerings o ON o.id=q.course_offering_id WHERE k.id=NEW.knowledge_entry_id AND k.course_id=o.course_id)",
        "knowledge_materials": "NOT EXISTS(SELECT 1 FROM knowledge_entries k JOIN methodical_materials m ON m.course_id=k.course_id WHERE k.id=NEW.knowledge_entry_id AND m.id=NEW.methodical_material_id)",
    }
    for name, (entity, row, owner, target) in SPECS.items():
        if name.endswith(("_topics", "_skills")):
            owner_table = next(iter(row.__table__.c[owner].foreign_keys)).column.table.name
            target_table = next(iter(row.__table__.c[target].foreign_keys)).column.table.name
            guards[name] = (
                f"NOT EXISTS(SELECT 1 FROM {owner_table} a JOIN {target_table} b ON b.course_id=a.course_id WHERE a.id=NEW.{owner} AND b.id=NEW.{target})"
            )
        if name.endswith("_attachments") or name == "student_problem_files":
            owner_table = next(iter(row.__table__.c[owner].foreign_keys)).column.table.name
            guards[name] = (
                f"NEW.deleted_at IS NULL AND (NOT EXISTS(SELECT 1 FROM {owner_table} WHERE id=NEW.{owner} AND deleted_at IS NULL) OR NOT EXISTS(SELECT 1 FROM file_assets WHERE id=NEW.file_asset_id AND deleted_at IS NULL))"
            )
            sql.append(
                trigger(
                    "file_assets_" + name + "_guard",
                    "file_assets",
                    "UPDATE",
                    f"NEW.deleted_at IS NOT NULL AND EXISTS(SELECT 1 FROM {name} WHERE file_asset_id=NEW.id AND deleted_at IS NULL)",
                    "asset requires detached content attachments",
                )
            )
    guards["program_materials"] = (
        "NOT EXISTS(SELECT 1 FROM work_programs p JOIN seminar_materials m ON m.course_id=p.course_id WHERE p.id=NEW.work_program_id AND m.id=NEW.seminar_material_id AND (NEW.planned_week IS NULL OR NEW.planned_week<=p.weeks) AND (NEW.module_id IS NULL OR EXISTS(SELECT 1 FROM program_modules x WHERE x.id=NEW.module_id AND x.work_program_id=p.id)))"
    )
    guards["program_literature"] = (
        "NOT EXISTS(SELECT 1 FROM work_programs p JOIN literature_items l ON l.course_id IS NULL OR l.course_id=p.course_id WHERE p.id=NEW.work_program_id AND l.id=NEW.literature_item_id)"
    )
    for name, condition in guards.items():
        for event in ("INSERT", "UPDATE"):
            sql.append(
                trigger(
                    name + "_program_context_" + event.lower(),
                    name,
                    event,
                    condition,
                    "link requires matching discipline/program/week",
                )
            )
    sql.append(
        trigger(
            "attempts_homework_result",
            "attempts",
            "INSERT",
            "NEW.result='REJECTED' AND EXISTS(SELECT 1 FROM student_works w JOIN assessments a ON a.id=w.assessment_id WHERE w.id=NEW.student_work_id AND a.type='HOMEWORK')",
            "homework requires revision instead of rejection",
        )
    )
    sql.append(
        trigger(
            "student_problem_assignments_history_lock",
            "student_problem_assignments",
            "INSERT",
            "EXISTS(SELECT 1 FROM attempts WHERE student_work_id=NEW.student_work_id)",
            "task assignment requires an unattempted work",
        )
    )
    sql.append(
        trigger(
            "course_offerings_program_lock",
            "course_offerings",
            "UPDATE",
            "OLD.work_program_id IS NOT NULL AND NEW.work_program_id IS NOT OLD.work_program_id AND (EXISTS(SELECT 1 FROM assessments WHERE offering_id=OLD.id) OR EXISTS(SELECT 1 FROM lessons WHERE course_offering_id=OLD.id))",
            "immutable historical program context",
        )
    )
    sql.append(
        trigger(
            "assessments_program_lock",
            "assessments",
            "UPDATE",
            "OLD.program_work_id IS NOT NULL AND NEW.program_work_id IS NOT OLD.program_work_id",
            "immutable issued program work",
        )
    )
    sql.append(
        trigger(
            "work_programs_calendar_lock",
            "work_programs",
            "UPDATE",
            "(NEW.first_week_start IS NOT OLD.first_week_start OR NEW.week_utc_offset_minutes IS NOT OLD.week_utc_offset_minutes) AND EXISTS(SELECT 1 FROM course_offerings o JOIN assessments a ON a.offering_id=o.id JOIN analytics_locked_assessments l ON l.id=a.id WHERE o.work_program_id=OLD.id)",
            "immutable historical program calendar",
        )
    )
    sql.append(
        trigger(
            "work_programs_duration_guard",
            "work_programs",
            "UPDATE",
            "EXISTS(SELECT 1 FROM program_modules WHERE work_program_id=OLD.id AND deleted_at IS NULL AND end_week>NEW.weeks) OR EXISTS(SELECT 1 FROM program_works WHERE work_program_id=OLD.id AND deleted_at IS NULL AND (planned_issue_week>NEW.weeks OR planned_due_week>NEW.weeks))",
            "duration requires retaining planned weeks",
        )
    )
    sql.append(
        trigger(
            "program_modules_work_bounds",
            "program_modules",
            "UPDATE",
            "EXISTS(SELECT 1 FROM program_works WHERE module_id=OLD.id AND deleted_at IS NULL AND planned_due_week IS NOT NULL AND planned_due_week NOT BETWEEN NEW.start_week AND NEW.end_week)",
            "module requires retaining planned work weeks",
        )
    )
    Path("src/studium/infrastructure/database/migrations/versions/v0007.sql").write_text(
        "\n".join(sql), encoding="utf8"
    )


if __name__ == "__main__":
    main()
