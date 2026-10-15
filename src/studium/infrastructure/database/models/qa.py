"""Explicit mappings for additive QA package schema; migration owns production DDL."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Text, UniqueConstraint

from studium.domain import annual_program as annual
from studium.domain import qa as e
from studium.infrastructure.database.models.base import Base
from studium.infrastructure.database.models.learning import record, reference


def prose(name, nullable=False):
    return Column(name, Text, nullable=nullable)


def integer(name, nullable=False):
    return Column(name, Integer, nullable=nullable), CheckConstraint(
        f"{name} IS NULL OR typeof({name})='integer'" if nullable else f"typeof({name})='integer'"
    )


def cents(name):
    return *integer(name, True), CheckConstraint(f"{name} IS NULL OR {name} >= 0")


def document(name, kind="object"):
    return prose(name), CheckConstraint(f"json_valid({name}) AND json_type({name})='{kind}'")


SPECS = {}
IMMUTABLE = set()


def mapping(name, entity, owner, target, *columns, immutable=False):
    row = type(entity.__name__ + "Row", (Base,), {"__table__": record(name, *columns)})
    for column in row.__table__.columns:
        if column.name.endswith("_id"):
            Index(f"{name}_{column.name}_qa_idx", column)
    SPECS[name] = (entity, row, owner, target)
    if immutable:
        IMMUTABLE.add(name)


mapping(
    "plan_content_sources",
    e.PlanContentSource,
    "semester_plan_id",
    "id",
    reference("semester_plan_id", "semester_plans"),
    reference("plan_module_id", "plan_modules", nullable=True),
    reference("planned_work_id", "planned_works", nullable=True),
    reference("program_version_id", "program_versions", nullable=True),
    *integer("course_semester", True),
    *document("snapshot_json"),
    prose("provenance"),
    UniqueConstraint("plan_module_id"),
    UniqueConstraint("planned_work_id"),
    CheckConstraint("(plan_module_id IS NOT NULL)+(planned_work_id IS NOT NULL)=1"),
    CheckConstraint("course_semester IS NULL OR course_semester>=1"),
    immutable=True,
)
mapping(
    "late_work_authorizations",
    e.LateWorkAuthorization,
    "student_work_id",
    "id",
    Column(
        "student_work_id",
        Text,
        ForeignKey("student_works.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        nullable=False,
    ),
    reference("enrollment_id", "enrollments"),
    reference("student_id", "students"),
    reference("assessment_id", "assessments"),
    UniqueConstraint("student_work_id"),
    immutable=True,
)


mapping(
    "directions",
    e.Direction,
    None,
    None,
    prose("code"),
    prose("normalized_key"),
    prose("name"),
    UniqueConstraint("normalized_key"),
    CheckConstraint("length(trim(code))>0"),
)
mapping(
    "course_programs",
    e.CourseProgram,
    None,
    None,
    reference("course_id", "courses"),
    prose("title"),
    prose("notes"),
    CheckConstraint("length(trim(title))>0"),
)
mapping(
    "program_versions",
    e.ProgramVersion,
    "course_program_id",
    "id",
    reference("course_program_id", "course_programs"),
    *integer("version_no"),
    *document("content_json"),
    prose("label"),
    UniqueConstraint("course_program_id", "version_no"),
    CheckConstraint("version_no>=1"),
    immutable=True,
)
mapping(
    "program_directions",
    e.ProgramDirection,
    "program_version_id",
    "direction_id",
    reference("program_version_id", "program_versions"),
    reference("direction_id", "directions"),
    UniqueConstraint("program_version_id", "direction_id"),
    immutable=True,
)
mapping(
    "legacy_program_maps",
    e.LegacyProgramMap,
    "legacy_program_id",
    "program_version_id",
    reference("legacy_program_id", "work_programs"),
    reference("program_version_id", "program_versions"),
    UniqueConstraint("legacy_program_id"),
    immutable=True,
)
mapping(
    "semester_plans",
    e.SemesterPlan,
    "offering_id",
    "id",
    reference("offering_id", "course_offerings"),
    reference("program_version_id", "program_versions", nullable=True),
    prose("first_week_start"),
    *integer("weeks"),
    *integer("course_semester", True),
    *integer("week_utc_offset_minutes"),
    *integer("configured"),
    UniqueConstraint("offering_id"),
    CheckConstraint("weeks BETWEEN 1 AND 104"),
    CheckConstraint("course_semester IS NULL OR course_semester>=1"),
    CheckConstraint("configured IN (0,1)"),
    CheckConstraint("week_utc_offset_minutes BETWEEN -840 AND 840"),
    CheckConstraint(
        "date(first_week_start,'+0 days')=first_week_start AND date(first_week_start,'+0 days') IS NOT NULL"
    ),
)
mapping(
    "plan_modules",
    e.PlanModule,
    "semester_plan_id",
    "id",
    reference("semester_plan_id", "semester_plans"),
    reference("source_module_id", "program_modules", nullable=True),
    prose("title"),
    *integer("start_week"),
    *integer("end_week"),
    *integer("sort_order"),
    UniqueConstraint("semester_plan_id", "source_module_id"),
    CheckConstraint("start_week>=1 AND end_week>=start_week AND sort_order>=0"),
)
mapping(
    "planned_works",
    e.PlannedWork,
    "semester_plan_id",
    "id",
    reference("semester_plan_id", "semester_plans"),
    reference("module_id", "plan_modules", nullable=True),
    reference("definition_id", "homework_definitions", nullable=True),
    reference("source_work_id", "program_works", nullable=True),
    prose("title"),
    prose("type"),
    prose("number"),
    prose("issue_date", True),
    prose("due_date", True),
    *integer("exact_due_at", True),
    prose("deadline_kind"),
    *integer("due_week", True),
    CheckConstraint("deadline_kind IN ('NONE','DATE_EXCLUSIVE','EXACT_INCLUSIVE','WEEK_ONLY')"),
    CheckConstraint("due_week IS NULL OR due_week>=1"),
    *cents("min_cents"),
    *cents("max_cents"),
    *integer("sort_order"),
    *integer("cancelled"),
    UniqueConstraint("semester_plan_id", "source_work_id"),
    CheckConstraint("type IN ('HOMEWORK','TEST','CONTROL_WORK','DEFENSE','LAB','EXAM','OTHER')"),
    CheckConstraint("cancelled IN (0,1) AND sort_order>=0"),
    CheckConstraint(
        "(min_cents IS NULL AND max_cents IS NULL) OR (min_cents IS NOT NULL AND max_cents IS NOT NULL AND min_cents<=max_cents AND max_cents>0)"
    ),
    CheckConstraint(
        "issue_date IS NULL OR (date(issue_date,'+0 days')=issue_date AND date(issue_date,'+0 days') IS NOT NULL)"
    ),
    CheckConstraint(
        "due_date IS NULL OR (date(due_date,'+0 days')=due_date AND date(due_date,'+0 days') IS NOT NULL)"
    ),
    CheckConstraint("issue_date IS NULL OR due_date IS NULL OR issue_date<=due_date"),
)
mapping(
    "plan_history",
    e.PlanHistory,
    "semester_plan_id",
    "id",
    reference("semester_plan_id", "semester_plans"),
    *integer("plan_revision"),
    *document("snapshot_json"),
    prose("reason"),
    prose("provenance"),
    UniqueConstraint("semester_plan_id", "plan_revision"),
    immutable=True,
)
mapping(
    "issued_works",
    e.IssuedWork,
    "planned_work_id",
    "assessment_id",
    reference("planned_work_id", "planned_works"),
    reference("assessment_id", "assessments"),
    *integer("actual_issued_at", True),
    prose("provenance"),
    UniqueConstraint("planned_work_id"),
    UniqueConstraint("assessment_id"),
    immutable=True,
)
mapping(
    "scoring_rules",
    e.ScoringRule,
    "assessment_id",
    "id",
    reference("assessment_id", "assessments"),
    *integer("sequence"),
    *cents("min_cents"),
    *cents("max_cents"),
    UniqueConstraint("assessment_id", "sequence"),
    CheckConstraint(
        "min_cents IS NOT NULL AND max_cents IS NOT NULL AND min_cents<=max_cents AND max_cents>0 AND sequence>=1"
    ),
    immutable=True,
)
mapping(
    "submissions",
    e.Submission,
    "attempt_id",
    "id",
    reference("attempt_id", "attempts"),
    reference("rule_id", "scoring_rules", nullable=True),
    *integer("received_at"),
    *integer("utc_offset_minutes"),
    prose("provenance"),
    UniqueConstraint("attempt_id"),
    CheckConstraint("utc_offset_minutes BETWEEN -840 AND 840"),
    immutable=True,
)
mapping(
    "reviews",
    e.Review,
    "submission_id",
    "id",
    reference("submission_id", "submissions"),
    reference("rule_id", "scoring_rules", nullable=True),
    *integer("review_seq"),
    prose("result"),
    *integer("reviewed_at"),
    *cents("score_cents"),
    *cents("min_cents"),
    *cents("max_cents"),
    prose("comment"),
    UniqueConstraint("submission_id", "review_seq"),
    CheckConstraint("review_seq>=1"),
    CheckConstraint("result IN ('NEEDS_REVISION','ACCEPTED','SCORED','REJECTED','COMMENT_ONLY')"),
    CheckConstraint("result!='SCORED' OR score_cents IS NOT NULL"),
    CheckConstraint(
        "score_cents IS NULL OR (result IN ('SCORED','ACCEPTED') AND rule_id IS NOT NULL AND min_cents IS NOT NULL AND max_cents IS NOT NULL AND min_cents<=score_cents AND score_cents<=max_cents)"
    ),
    immutable=True,
)
mapping(
    "review_grades",
    e.ReviewGrade,
    "review_id",
    "id",
    reference("review_id", "reviews"),
    prose("kind"),
    *cents("score_cents"),
    *cents("max_cents"),
    *integer("passed", True),
    prose("label", True),
    UniqueConstraint("review_id"),
    CheckConstraint(
        "(kind='NUMERIC' AND score_cents IS NOT NULL AND max_cents IS NOT NULL AND passed IS NULL AND label IS NULL) OR (kind='PASS_FAIL' AND passed IS NOT NULL AND passed IN (0,1) AND score_cents IS NULL AND max_cents IS NULL AND label IS NULL) OR (kind='TRADITIONAL' AND label IS NOT NULL AND length(trim(label))>0 AND passed IS NULL AND score_cents IS NULL AND max_cents IS NULL)"
    ),
    immutable=True,
)
mapping(
    "review_files",
    e.ReviewFile,
    "review_id",
    "file_asset_id",
    reference("review_id", "reviews"),
    reference("file_asset_id", "file_assets"),
    prose("caption"),
    *integer("sort_order"),
    UniqueConstraint("review_id", "file_asset_id"),
    immutable=True,
)
mapping(
    "review_returns",
    e.ReviewReturn,
    "review_id",
    "id",
    reference("review_id", "reviews"),
    *integer("returned_at"),
    prose("comment"),
    immutable=True,
)
mapping(
    "required_work_sets",
    e.RequiredWorkSet,
    "module_id",
    "id",
    reference("module_id", "plan_modules"),
    reference("student_id", "students"),
    *integer("sequence"),
    prose("reason"),
    UniqueConstraint("module_id", "student_id", "sequence"),
    CheckConstraint("sequence>=1"),
    immutable=True,
)
mapping(
    "required_work_bindings",
    e.RequiredWorkBinding,
    "required_set_id",
    "student_work_id",
    reference("required_set_id", "required_work_sets"),
    reference("student_work_id", "student_works"),
    UniqueConstraint("required_set_id", "student_work_id"),
    immutable=True,
)
mapping(
    "answer_templates",
    e.AnswerTemplate,
    None,
    None,
    prose("title"),
    *document("schema_json", "array"),
)
mapping(
    "debt_restorations",
    e.DebtRestoration,
    "student_work_id",
    "id",
    reference("student_work_id", "student_works"),
    *document("before_json"),
    prose("reason"),
    immutable=True,
)
mapping(
    "version_references",
    e.VersionReference,
    "program_version_id",
    "id",
    reference("program_version_id", "program_versions"),
    reference("topic_id", "topics", nullable=True),
    reference("skill_id", "skills", nullable=True),
    reference("definition_id", "homework_definitions", nullable=True),
    reference("seminar_material_id", "seminar_materials", nullable=True),
    reference("literature_item_id", "literature_items", nullable=True),
    reference("file_asset_id", "file_assets", nullable=True),
    CheckConstraint(
        "(topic_id IS NOT NULL)+(skill_id IS NOT NULL)+(definition_id IS NOT NULL)+(seminar_material_id IS NOT NULL)+(literature_item_id IS NOT NULL)+(file_asset_id IS NOT NULL)=1"
    ),
    *(
        UniqueConstraint("program_version_id", target)
        for target in (
            "topic_id",
            "skill_id",
            "definition_id",
            "seminar_material_id",
            "literature_item_id",
            "file_asset_id",
        )
    ),
    immutable=True,
)

# Annual content extends the existing immutable version; drafts are separate.

mapping(
    "program_drafts",
    annual.ProgramDraft,
    "course_program_id",
    "id",
    reference("course_program_id", "course_programs"),
    reference("base_version_id", "program_versions", nullable=True),
    *document("content_json"),
)
mapping(
    "program_imports",
    annual.ProgramImport,
    "program_version_id",
    "id",
    reference("program_version_id", "program_versions"),
    prose("origin"),
    prose("content_hash"),
    UniqueConstraint("program_version_id"),
    immutable=True,
)
mapping(
    "plan_lessons",
    annual.PlanLesson,
    "semester_plan_id",
    "id",
    reference("semester_plan_id", "semester_plans"),
    reference("plan_module_id", "plan_modules"),
    reference("program_version_id", "program_versions"),
    reference("lesson_id", "lessons", nullable=True),
    prose("source_key"),
    *document("baseline_json"),
    *document("current_json"),
    UniqueConstraint("semester_plan_id", "program_version_id", "source_key"),
    UniqueConstraint("lesson_id"),
)
