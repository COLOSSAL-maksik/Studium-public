"""Work programs, reusable curricula, knowledge entries and factual skill results."""

import sqlite3
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from alembic import op
from sqlalchemy import text

revision = "0007_work_programs"
down_revision = "0006_content_workflow"
branch_labels = None
depends_on = None


def stable_id(kind, id):
    return str(uuid5(NAMESPACE_URL, f"studium:iteration2:{kind}:{id}"))


def upgrade():
    statement = ""
    for line in Path(__file__).with_suffix(".sql").read_text(encoding="utf-8").splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            op.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete program migration SQL")
    connection = op.get_bind()
    metadata_guards = connection.execute(
        text(
            "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND name IN ('course_offerings_metadata_update','assessments_metadata_update')"
        )
    ).all()
    for name, sql in metadata_guards:
        op.execute(f"DROP TRIGGER {name}")
    offerings = (
        connection.execute(
            text(
                "SELECT o.*, t.starts_on, t.name AS term_name, t.week_utc_offset_minutes, c.name AS course_name, g.number AS group_number FROM course_offerings o JOIN academic_terms t ON t.id=o.term_id JOIN courses c ON c.id=o.course_id JOIN student_groups g ON g.id=o.group_id"
            )
        )
        .mappings()
        .all()
    )
    for offering in offerings:
        program_id = stable_id("program", offering["id"])
        assessments = (
            connection.execute(
                text("SELECT * FROM assessments WHERE offering_id=:id"), {"id": offering["id"]}
            )
            .mappings()
            .all()
        )
        weeks = max(
            [
                17,
                *[
                    a[w] or 1
                    for a in assessments
                    for w in ("planned_issue_week", "planned_due_week")
                ],
            ]
        )
        if weeks > 104:
            raise ValueError(
                "Legacy planned week exceeds supported duration; original database is preserved"
            )
        connection.execute(
            text(
                "INSERT INTO work_programs(id,course_id,term_id,title,first_week_start,weeks,version,week_utc_offset_minutes,created_at,updated_at,revision) VALUES (:id,:course,:term,:title,:start,:weeks,:version,:offset,:at,:at,1)"
            ),
            dict(
                id=program_id,
                course=offering["course_id"],
                term=offering["term_id"],
                title=f"{offering['course_name']} · {offering['group_number']} · {offering['term_name']}",
                start=offering["starts_on"],
                weeks=weeks,
                version="Перенесено из Iteration 1",
                offset=offering["week_utc_offset_minutes"],
                at=offering["updated_at"],
            ),
        )
        # New nullable mapping only; every previous value, revision and fact is retained.
        connection.execute(
            text("UPDATE course_offerings SET work_program_id=:program WHERE id=:id"),
            dict(program=program_id, id=offering["id"]),
        )
        reused_definitions = set()
        for assessment in assessments:
            definition_id = stable_id("definition", assessment["id"])
            source_definition = assessment["homework_definition_id"]
            reuse = (
                source_definition
                and assessment["type"] == "HOMEWORK"
                and source_definition not in reused_definitions
            )
            if reuse:
                definition_id = source_definition
                reused_definitions.add(definition_id)
            work_id = stable_id("program-work", assessment["id"])
            if not reuse:
                connection.execute(
                    text(
                        "INSERT INTO homework_definitions(id,course_id,title,label,description,type,created_at,updated_at,revision,deleted_at) VALUES (:id,:course,:title,:label,:description,:type,:created,:updated,1,:deleted)"
                    ),
                    dict(
                        id=definition_id,
                        course=offering["course_id"],
                        title=assessment["title"],
                        label=assessment["number"] or "",
                        description=assessment["description"],
                        type=assessment["type"],
                        created=assessment["created_at"],
                        updated=assessment["updated_at"],
                        deleted=assessment["deleted_at"],
                    ),
                )
            connection.execute(
                text(
                    "INSERT INTO program_works(id,work_program_id,definition_id,planned_issue_week,planned_due_week,created_at,updated_at,revision,deleted_at) VALUES (:id,:program,:definition,:issue,:due,:created,:updated,1,:deleted)"
                ),
                dict(
                    id=work_id,
                    program=program_id,
                    definition=definition_id,
                    issue=assessment["planned_issue_week"],
                    due=assessment["planned_due_week"],
                    created=assessment["created_at"],
                    updated=assessment["updated_at"],
                    deleted=assessment["deleted_at"],
                ),
            )
            connection.execute(
                text("UPDATE assessments SET program_work_id=:work WHERE id=:id"),
                dict(work=work_id, id=assessment["id"]),
            )
    # Restore exact historical SQL before the transaction can become visible.
    for name, sql in metadata_guards:
        op.execute(sql)


def downgrade():
    raise RuntimeError("Deleting program/content/history by downgrade is not supported")
