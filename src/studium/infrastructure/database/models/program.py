"""Explicit additive program/content mappings; DDL frozen in migration 0007."""

from sqlalchemy import CheckConstraint, Column, Index, Integer, Text, UniqueConstraint, text

from studium.domain import program as e
from studium.infrastructure.database.models.base import Base
from studium.infrastructure.database.models.content import attachment, content, prose
from studium.infrastructure.database.models.learning import order, record, reference, title


def day(name):
    return Column(name, Text), CheckConstraint(
        f"{name} IS NULL OR (date({name}, '+0 days') IS NOT NULL AND date({name}, '+0 days') = {name})"
    )


def week(name):
    return Column(name, Integer), CheckConstraint(
        f"{name} IS NULL OR (typeof({name}) = 'integer' AND {name} >= 1)"
    )


class WorkProgramRow(Base):
    __table__ = record(
        "work_programs",
        reference("course_id", "courses"),
        reference("term_id", "academic_terms"),
        *title(),
        Column("first_week_start", Text, nullable=False),
        Column("weeks", Integer, nullable=False, server_default=text("17")),
        prose("direction"),
        prose("faculty"),
        prose("version"),
        prose("notes"),
        Column("semester", Text, nullable=False, server_default=text("'AUTUMN'")),
        Column("week_utc_offset_minutes", Integer, nullable=False, server_default=text("180")),
        CheckConstraint(
            "date(first_week_start, '+0 days') IS NOT NULL AND date(first_week_start, '+0 days') = first_week_start"
        ),
        CheckConstraint("typeof(weeks) = 'integer' AND weeks BETWEEN 1 AND 104"),
        CheckConstraint("semester IN ('AUTUMN','SPRING')"),
        CheckConstraint(
            "typeof(week_utc_offset_minutes) = 'integer' AND week_utc_offset_minutes BETWEEN -840 AND 840"
        ),
    )


class ProgramModuleRow(Base):
    __table__ = record(
        "program_modules",
        reference("work_program_id", "work_programs"),
        *title(),
        *order(),
        Column("start_week", Integer, nullable=False),
        Column("end_week", Integer, nullable=False),
        CheckConstraint(
            "typeof(start_week) = 'integer' AND typeof(end_week) = 'integer' AND start_week >= 1 AND end_week >= start_week"
        ),
    )


class ProgramWorkRow(Base):
    __table__ = record(
        "program_works",
        reference("work_program_id", "work_programs"),
        reference("definition_id", "homework_definitions"),
        reference("module_id", "program_modules", nullable=True),
        *order(),
        *week("planned_issue_week"),
        *week("planned_due_week"),
        *day("issue_date"),
        *day("due_date"),
        UniqueConstraint("work_program_id", "definition_id"),
        CheckConstraint(
            "planned_issue_week IS NULL OR planned_due_week IS NULL OR planned_due_week >= planned_issue_week"
        ),
        CheckConstraint("issue_date IS NULL OR due_date IS NULL OR due_date >= issue_date"),
    )


class HomeworkPackRow(Base):
    __table__ = content("homework_packs", prose("description"))


class MethodicalMaterialRow(Base):
    __table__ = content("methodical_materials", prose("description"))


class KnowledgeEntryRow(Base):
    __table__ = content(
        "knowledge_entries",
        prose("answer"),
        Column("type", Text, nullable=False, server_default=text("'QUESTION'")),
        Column("draft", Integer, nullable=False, server_default=text("1")),
        CheckConstraint("type IN ('QUESTION','ERROR','UNDERSTANDING','ORGANIZATION')"),
        CheckConstraint("draft IN (0,1)"),
    )


class AssessmentProblemRow(Base):
    __table__ = record(
        "assessment_problems",
        reference("assessment_item_id", "assessment_items"),
        reference("problem_id", "problems"),
        Column("source_revision", Integer, nullable=False),
        prose("statement_snapshot"),
        UniqueConstraint("assessment_item_id"),
        CheckConstraint("typeof(source_revision) = 'integer' AND source_revision >= 1"),
    )


class StudentProblemAssignmentRow(Base):
    __table__ = record(
        "student_problem_assignments",
        reference("student_work_id", "student_works"),
        reference("assessment_item_id", "assessment_items"),
        reference("problem_id", "problems"),
        Column("source_revision", Integer, nullable=False),
        prose("title_snapshot"),
        prose("statement_snapshot"),
        Column("teacher_snapshot_json", Text, nullable=False, server_default=text("'{}'")),
        UniqueConstraint("student_work_id", "assessment_item_id"),
        CheckConstraint("typeof(source_revision) = 'integer' AND source_revision >= 1"),
        CheckConstraint(
            "json_valid(teacher_snapshot_json) AND json_type(teacher_snapshot_json) = 'object'"
        ),
    )


class AttemptSkillResultRow(Base):
    __table__ = record(
        "attempt_skill_results",
        reference("attempt_item_result_id", "attempt_item_results"),
        reference("skill_id", "skills"),
        Column("outcome", Text, nullable=False),
        prose("comment"),
        CheckConstraint("outcome IN ('CORRECT','PARTIAL','INCORRECT','NOT_EVALUATED')"),
    )
    __table_args__ = ()


Index(
    "attempt_skill_results_active_pair",
    AttemptSkillResultRow.__table__.c.attempt_item_result_id,
    AttemptSkillResultRow.__table__.c.skill_id,
    unique=True,
    sqlite_where=AttemptSkillResultRow.__table__.c.deleted_at.is_(None),
)


SPECS = {
    "work_programs": (e.WorkProgram, WorkProgramRow, None, None),
    "program_modules": (e.ProgramModule, ProgramModuleRow, "work_program_id", "id"),
    "program_works": (e.ProgramWork, ProgramWorkRow, "work_program_id", "definition_id"),
    "homework_packs": (e.HomeworkPack, HomeworkPackRow, None, None),
    "methodical_materials": (e.MethodicalMaterial, MethodicalMaterialRow, None, None),
    "knowledge_entries": (e.KnowledgeEntry, KnowledgeEntryRow, None, None),
    "assessment_problems": (
        e.AssessmentProblem,
        AssessmentProblemRow,
        "assessment_item_id",
        "problem_id",
    ),
    "student_problem_assignments": (
        e.StudentProblemAssignment,
        StudentProblemAssignmentRow,
        "student_work_id",
        "assessment_item_id",
    ),
    "attempt_skill_results": (
        e.AttemptSkillResult,
        AttemptSkillResultRow,
        "attempt_item_result_id",
        "skill_id",
    ),
}


def link(name, entity, owner, owner_table, target, target_table, *fields):
    row = type(
        entity.__name__ + "Row",
        (Base,),
        {
            "__table__": record(
                name,
                reference(owner, owner_table),
                reference(target, target_table),
                *fields,
                UniqueConstraint(owner, target),
            )
        },
    )
    SPECS[name] = (entity, row, owner, target)


link("program_topics", e.ProgramTopic, "work_program_id", "work_programs", "topic_id", "topics")
link("program_skills", e.ProgramSkill, "work_program_id", "work_programs", "skill_id", "skills")
link(
    "program_materials",
    e.ProgramMaterial,
    "work_program_id",
    "work_programs",
    "seminar_material_id",
    "seminar_materials",
    reference("module_id", "program_modules", nullable=True),
    *week("planned_week"),
)
link(
    "program_literature",
    e.ProgramLiterature,
    "work_program_id",
    "work_programs",
    "literature_item_id",
    "literature_items",
)
link(
    "homework_pack_works",
    e.HomeworkPackWork,
    "homework_pack_id",
    "homework_packs",
    "definition_id",
    "homework_definitions",
)
link(
    "knowledge_sources",
    e.KnowledgeSource,
    "knowledge_entry_id",
    "knowledge_entries",
    "question_case_id",
    "question_cases",
)
link(
    "knowledge_materials",
    e.KnowledgeMaterial,
    "knowledge_entry_id",
    "knowledge_entries",
    "methodical_material_id",
    "methodical_materials",
)
link(
    "definition_problems",
    e.DefinitionProblem,
    "definition_id",
    "homework_definitions",
    "problem_id",
    "problems",
    *order(),
)
for name, entity, owner, owner_table, target, target_table in (
    (
        "seminar_problems",
        e.SeminarProblem,
        "seminar_material_id",
        "seminar_materials",
        "problem_id",
        "problems",
    ),
    ("module_topics", e.ProgramModuleTopic, "module_id", "program_modules", "topic_id", "topics"),
    ("problem_topics", e.ProblemTopic, "problem_id", "problems", "topic_id", "topics"),
    ("problem_skills", e.ProblemSkill, "problem_id", "problems", "skill_id", "skills"),
    (
        "definition_topics",
        e.DefinitionTopic,
        "definition_id",
        "homework_definitions",
        "topic_id",
        "topics",
    ),
    (
        "definition_skills",
        e.DefinitionSkill,
        "definition_id",
        "homework_definitions",
        "skill_id",
        "skills",
    ),
    (
        "methodical_topics",
        e.MethodicalTopic,
        "methodical_material_id",
        "methodical_materials",
        "topic_id",
        "topics",
    ),
    (
        "methodical_skills",
        e.MethodicalSkill,
        "methodical_material_id",
        "methodical_materials",
        "skill_id",
        "skills",
    ),
    (
        "knowledge_topics",
        e.KnowledgeTopic,
        "knowledge_entry_id",
        "knowledge_entries",
        "topic_id",
        "topics",
    ),
    (
        "knowledge_skills",
        e.KnowledgeSkill,
        "knowledge_entry_id",
        "knowledge_entries",
        "skill_id",
        "skills",
    ),
):
    link(name, entity, owner, owner_table, target, target_table)

for name, entity, owner, owner_table in (
    (
        "student_problem_files",
        e.StudentProblemFile,
        "student_problem_assignment_id",
        "student_problem_assignments",
    ),
    ("program_attachments", e.ProgramAttachment, "work_program_id", "work_programs"),
    ("homework_pack_attachments", e.HomeworkPackAttachment, "homework_pack_id", "homework_packs"),
    (
        "methodical_attachments",
        e.MethodicalAttachment,
        "methodical_material_id",
        "methodical_materials",
    ),
    ("assessment_attachments", e.AssessmentAttachment, "assessment_id", "assessments"),
):
    row = type(
        entity.__name__ + "Row", (Base,), {"__table__": attachment(name, owner, owner_table)}
    )
    SPECS[name] = (entity, row, owner, "file_asset_id")

for entity, row, owner, target in SPECS.values():
    for column in row.__table__.columns:
        if column.foreign_keys:
            Index(row.__table__.name + "_" + column.name, column)
