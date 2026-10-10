"""Semester plans and reusable content links, independent of persistence/UI."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from studium.domain.content import MaterialAttachment, TeachingContent
from studium.domain.entities import StudiumEntity, validate_order
from studium.domain.enums import ItemOutcome
from studium.domain.value_objects import AcademicWeekNumber, EntityId, LocalDate, require_text


class SemesterType(StrEnum):
    AUTUMN = "AUTUMN"
    SPRING = "SPRING"


@dataclass(frozen=True, kw_only=True)
class WorkProgram(StudiumEntity):
    course_id: EntityId
    term_id: EntityId
    title: str
    first_week_start: LocalDate
    weeks: int = 17
    direction: str = ""
    faculty: str = ""
    version: str = ""
    semester: SemesterType = SemesterType.AUTUMN
    notes: str = ""
    week_utc_offset_minutes: int = 180

    def __post_init__(self):
        require_text(self.title, "title")
        if type(self.weeks) is not int or not 1 <= self.weeks <= 104:
            raise ValueError("Semester duration must be between 1 and 104 weeks")
        if not isinstance(self.first_week_start, LocalDate):
            raise ValueError("Program requires first week calendar date")
        if not isinstance(self.semester, SemesterType):
            raise ValueError("Expected semester type")
        if (
            type(self.week_utc_offset_minutes) is not int
            or not -840 <= self.week_utc_offset_minutes <= 840
        ):
            raise ValueError("Invalid program calendar UTC offset")

    def week_dates(self, week):
        number = week.value if isinstance(week, AcademicWeekNumber) else week
        if type(number) is not int or not 1 <= number <= self.weeks:
            raise ValueError("Week is outside program duration")
        start = date(
            self.first_week_start.year, self.first_week_start.month, self.first_week_start.day
        ) + timedelta(weeks=number - 1)
        return LocalDate.parse(start.isoformat()), LocalDate.parse(
            (start + timedelta(days=6)).isoformat()
        )

    def week_for_date(self, on):
        week = AcademicWeekNumber.for_date(self.first_week_start, on)
        return week if week and week.value <= self.weeks else None

    def validate_week_date(self, week, on):
        if on is None:
            if week is not None:
                self.week_dates(week)
            return
        if week is None:
            raise ValueError("Choose a week before its exact date")
        start, end = self.week_dates(week)
        if not start <= on <= end:
            raise ValueError("Date must lie inside selected academic week")


@dataclass(frozen=True, kw_only=True)
class ProgramModule(StudiumEntity):
    work_program_id: EntityId
    title: str
    start_week: int
    end_week: int
    sort_order: int = 0

    def __post_init__(self):
        require_text(self.title, "title")
        validate_order(self.sort_order)
        if (
            type(self.start_week) is not int
            or type(self.end_week) is not int
            or not 1 <= self.start_week <= self.end_week
        ):
            raise ValueError("Invalid module week range")


@dataclass(frozen=True, kw_only=True)
class ProgramWork(StudiumEntity):
    work_program_id: EntityId
    definition_id: EntityId
    module_id: EntityId | None = None
    sort_order: int = 0
    planned_issue_week: AcademicWeekNumber | None = None
    planned_due_week: AcademicWeekNumber | None = None
    issue_date: LocalDate | None = None
    due_date: LocalDate | None = None

    def __post_init__(self):
        validate_order(self.sort_order)
        for week in (self.planned_issue_week, self.planned_due_week):
            if week is not None and not isinstance(week, AcademicWeekNumber):
                raise ValueError("Expected academic week")
        if (
            self.planned_issue_week
            and self.planned_due_week
            and self.planned_due_week < self.planned_issue_week
        ):
            raise ValueError("Due week precedes issue week")
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            raise ValueError("Due date precedes issue date")


@dataclass(frozen=True, kw_only=True)
class ProgramTopic(StudiumEntity):
    work_program_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class ProgramSkill(StudiumEntity):
    work_program_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class ProgramMaterial(StudiumEntity):
    work_program_id: EntityId
    seminar_material_id: EntityId
    module_id: EntityId | None = None
    planned_week: AcademicWeekNumber | None = None


@dataclass(frozen=True, kw_only=True)
class ProgramLiterature(StudiumEntity):
    work_program_id: EntityId
    literature_item_id: EntityId


@dataclass(frozen=True, kw_only=True)
class ProgramAttachment(MaterialAttachment):
    work_program_id: EntityId


@dataclass(frozen=True, kw_only=True)
class SeminarProblem(StudiumEntity):
    seminar_material_id: EntityId
    problem_id: EntityId


@dataclass(frozen=True, kw_only=True)
class ProgramModuleTopic(StudiumEntity):
    module_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class HomeworkPack(TeachingContent):
    description: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.course_id is None:
            raise ValueError("Homework pack requires discipline")


@dataclass(frozen=True, kw_only=True)
class HomeworkPackWork(StudiumEntity):
    homework_pack_id: EntityId
    definition_id: EntityId


@dataclass(frozen=True, kw_only=True)
class HomeworkPackAttachment(MaterialAttachment):
    homework_pack_id: EntityId


@dataclass(frozen=True, kw_only=True)
class MethodicalMaterial(TeachingContent):
    description: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.course_id is None:
            raise ValueError("Methodical material requires discipline")


@dataclass(frozen=True, kw_only=True)
class MethodicalAttachment(MaterialAttachment):
    methodical_material_id: EntityId


class KnowledgeType(StrEnum):
    QUESTION = "QUESTION"
    ERROR = "ERROR"
    UNDERSTANDING = "UNDERSTANDING"
    ORGANIZATION = "ORGANIZATION"


@dataclass(frozen=True, kw_only=True)
class KnowledgeEntry(TeachingContent):
    answer: str = ""
    type: KnowledgeType = KnowledgeType.QUESTION
    draft: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.course_id is None or not isinstance(self.type, KnowledgeType):
            raise ValueError("Knowledge entry requires discipline and type")


@dataclass(frozen=True, kw_only=True)
class KnowledgeSource(StudiumEntity):
    knowledge_entry_id: EntityId
    question_case_id: EntityId


@dataclass(frozen=True, kw_only=True)
class KnowledgeMaterial(StudiumEntity):
    knowledge_entry_id: EntityId
    methodical_material_id: EntityId


@dataclass(frozen=True, kw_only=True)
class DefinitionProblem(StudiumEntity):
    definition_id: EntityId
    problem_id: EntityId
    sort_order: int = 0

    def __post_init__(self):
        validate_order(self.sort_order)


@dataclass(frozen=True, kw_only=True)
class AssessmentProblem(StudiumEntity):
    assessment_item_id: EntityId
    problem_id: EntityId
    source_revision: int
    statement_snapshot: str


@dataclass(frozen=True, kw_only=True)
class StudentProblemAssignment(StudiumEntity):
    student_work_id: EntityId
    assessment_item_id: EntityId
    problem_id: EntityId
    source_revision: int
    title_snapshot: str
    statement_snapshot: str
    teacher_snapshot_json: str = "{}"


@dataclass(frozen=True, kw_only=True)
class AttemptSkillResult(StudiumEntity):
    attempt_item_result_id: EntityId
    skill_id: EntityId
    outcome: ItemOutcome
    comment: str = ""

    def __post_init__(self):
        if not isinstance(self.outcome, ItemOutcome):
            raise ValueError("Expected factual skill outcome")


@dataclass(frozen=True, kw_only=True)
class StudentProblemFile(MaterialAttachment):
    student_problem_assignment_id: EntityId


@dataclass(frozen=True, kw_only=True)
class AssessmentAttachment(MaterialAttachment):
    assessment_id: EntityId


# Concrete FK links, preserving one discipline-wide Topic/Skill catalogue.
@dataclass(frozen=True, kw_only=True)
class ProblemTopic(StudiumEntity):
    problem_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class ProblemSkill(StudiumEntity):
    problem_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class DefinitionTopic(StudiumEntity):
    definition_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class DefinitionSkill(StudiumEntity):
    definition_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class MethodicalTopic(StudiumEntity):
    methodical_material_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class MethodicalSkill(StudiumEntity):
    methodical_material_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class KnowledgeTopic(StudiumEntity):
    knowledge_entry_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class KnowledgeSkill(StudiumEntity):
    knowledge_entry_id: EntityId
    skill_id: EntityId
