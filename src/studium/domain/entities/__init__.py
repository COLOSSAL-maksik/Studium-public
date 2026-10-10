"""Immutable domain values. A new presentation always creates a new Attempt."""

import json
import re
from dataclasses import dataclass

from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    AttendanceStatus,
    EnrollmentStatus,
    GradeKind,
    LessonType,
)
from studium.domain.file_contract import validate_filename, validate_storage_key
from studium.domain.value_objects import (
    AcademicWeekNumber,
    EntityId,
    EntityMetadata,
    LocalDate,
    UtcInstant,
    require_text,
    validate_score,
)


@dataclass(frozen=True, kw_only=True)
class StudiumEntity:
    metadata: EntityMetadata

    @property
    def id(self) -> EntityId:
        return self.metadata.id

    @property
    def revision(self) -> int:
        return self.metadata.revision

    @property
    def created_at(self) -> UtcInstant:
        return self.metadata.created_at

    @property
    def updated_at(self) -> UtcInstant:
        return self.metadata.updated_at

    @property
    def deleted_at(self) -> UtcInstant | None:
        return self.metadata.deleted_at


@dataclass(frozen=True, kw_only=True)
class AcademicTerm(StudiumEntity):
    name: str
    starts_on: LocalDate
    ends_on: LocalDate
    archived: bool = False
    week_utc_offset_minutes: int = 180

    def __post_init__(self) -> None:
        require_text(self.name, "name")
        if self.ends_on < self.starts_on:
            raise ValueError("AcademicTerm ends before it starts")
        if (
            type(self.week_utc_offset_minutes) is not int
            or not -840 <= self.week_utc_offset_minutes <= 840
        ):
            raise ValueError("Invalid academic calendar UTC offset")


@dataclass(frozen=True, kw_only=True)
class Course(StudiumEntity):
    name: str
    short_name: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        require_text(self.name, "name")


@dataclass(frozen=True, kw_only=True)
class StudentGroup(StudiumEntity):
    number: str
    department: str = ""
    faculty: str = ""
    faculty_short: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        require_text(self.number, "number")


@dataclass(frozen=True, kw_only=True)
class CourseOffering(StudiumEntity):
    term_id: EntityId
    course_id: EntityId
    group_id: EntityId
    work_program_id: EntityId | None = None


@dataclass(frozen=True, kw_only=True)
class Student(StudiumEntity):
    full_name: str
    preferred_name: str | None = None
    notes: str = ""
    active: bool = True

    def __post_init__(self) -> None:
        require_text(self.full_name, "full_name")
        if self.preferred_name is not None:
            require_text(self.preferred_name, "preferred_name")


@dataclass(frozen=True, kw_only=True)
class Enrollment(StudiumEntity):
    student_id: EntityId
    offering_id: EntityId
    enrolled_at: UtcInstant
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    ended_at: UtcInstant | None = None

    def __post_init__(self) -> None:
        if (self.status == EnrollmentStatus.ACTIVE) != (self.ended_at is None):
            raise ValueError("Only ACTIVE enrollment has no ended_at")
        if self.ended_at is not None and self.ended_at < self.enrolled_at:
            raise ValueError("Enrollment ends before it starts")


@dataclass(frozen=True, kw_only=True)
class Assessment(StudiumEntity):
    offering_id: EntityId
    type: AssessmentType
    title: str
    issued_at: UtcInstant
    number: str | None = None
    description: str = ""
    due_at: UtcInstant | None = None
    max_score: float | None = None
    planned_issue_week: AcademicWeekNumber | None = None
    planned_due_week: AcademicWeekNumber | None = None
    homework_definition_id: EntityId | None = None
    program_work_id: EntityId | None = None

    def __post_init__(self) -> None:
        require_text(self.title, "title")
        validate_score(None, self.max_score)
        for week in (self.planned_issue_week, self.planned_due_week):
            if week is not None and not isinstance(week, AcademicWeekNumber):
                raise ValueError("Expected an academic week")
        if (
            self.planned_issue_week
            and self.planned_due_week
            and self.planned_due_week < self.planned_issue_week
        ):
            raise ValueError("Due week precedes issue week")
        if self.due_at is not None and self.due_at < self.issued_at:
            raise ValueError("due_at precedes issued_at")


@dataclass(frozen=True, kw_only=True)
class StudentWork(StudiumEntity):
    assessment_id: EntityId
    student_id: EntityId


@dataclass(frozen=True, kw_only=True)
class Attempt(StudiumEntity):
    student_work_id: EntityId
    attempt_no: int
    occurred_at: UtcInstant
    result: AttemptResult
    comment: str = ""
    score: float | None = None
    max_score: float | None = None

    def __post_init__(self) -> None:
        if type(self.attempt_no) is not int or self.attempt_no < 1:
            raise ValueError("attempt_no must be a positive integer")
        validate_score(self.score, self.max_score)
        if self.result == AttemptResult.SCORED and self.score is None:
            raise ValueError("SCORED requires a numeric score")


@dataclass(frozen=True, kw_only=True)
class Grade(StudiumEntity):
    attempt_id: EntityId
    kind: GradeKind
    passed: bool | None = None
    score: float | None = None
    max_score: float | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        validate_score(self.score, self.max_score)
        match self.kind:
            case GradeKind.PASS_FAIL:
                valid = (
                    type(self.passed) is bool
                    and self.score is None
                    and self.max_score is None
                    and self.label is None
                )
            case GradeKind.NUMERIC:
                valid = self.score is not None and self.passed is None and self.label is None
            case GradeKind.TRADITIONAL:
                valid = (
                    self.label is not None
                    and self.passed is None
                    and self.score is None
                    and self.max_score is None
                )
                if self.label is not None:
                    require_text(self.label, "label")
            case _:
                valid = False
        if not valid:
            raise ValueError("Grade fields must match its kind")

    @classmethod
    def pass_fail(cls, *, metadata: EntityMetadata, attempt_id: EntityId, passed: bool) -> "Grade":
        return cls(
            metadata=metadata, attempt_id=attempt_id, kind=GradeKind.PASS_FAIL, passed=passed
        )

    @classmethod
    def numeric(
        cls,
        *,
        metadata: EntityMetadata,
        attempt_id: EntityId,
        score: float,
        max_score: float | None = None,
    ) -> "Grade":
        return cls(
            metadata=metadata,
            attempt_id=attempt_id,
            kind=GradeKind.NUMERIC,
            score=score,
            max_score=max_score,
        )

    @classmethod
    def traditional(cls, *, metadata: EntityMetadata, attempt_id: EntityId, label: str) -> "Grade":
        return cls(
            metadata=metadata, attempt_id=attempt_id, kind=GradeKind.TRADITIONAL, label=label
        )


def validate_order(value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("sort_order must be a nonnegative integer")


@dataclass(frozen=True, kw_only=True)
class Topic(StudiumEntity):
    course_id: EntityId
    title: str
    parent_topic_id: EntityId | None = None
    description: str = ""
    sort_order: int = 0

    def __post_init__(self) -> None:
        require_text(self.title, "title")
        validate_order(self.sort_order)
        if self.parent_topic_id == self.id:
            raise ValueError("Topic cannot be its own parent")


@dataclass(frozen=True, kw_only=True)
class Skill(StudiumEntity):
    course_id: EntityId
    title: str
    description: str = ""
    sort_order: int = 0

    def __post_init__(self) -> None:
        require_text(self.title, "title")
        validate_order(self.sort_order)


@dataclass(frozen=True, kw_only=True)
class Lesson(StudiumEntity):
    course_offering_id: EntityId
    lesson_date: LocalDate
    title: str = ""
    notes: str = ""
    type: LessonType = LessonType.SEMINAR
    planned_date: LocalDate | None = None
    planned_week: AcademicWeekNumber | None = None
    module_id: EntityId | None = None
    cancelled: bool = False
    cancellation_reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.lesson_date, LocalDate):
            raise ValueError("Lesson requires a calendar date")
        if not isinstance(self.type, LessonType):
            raise ValueError("Expected a lesson type")


@dataclass(frozen=True, kw_only=True)
class Attendance(StudiumEntity):
    lesson_id: EntityId
    enrollment_id: EntityId
    status: AttendanceStatus
    comment: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, AttendanceStatus):
            raise ValueError("Attendance requires a known status")


@dataclass(frozen=True, kw_only=True)
class AssessmentItem(StudiumEntity):
    assessment_id: EntityId
    title: str
    description: str = ""
    max_score: float | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        require_text(self.title, "title")
        validate_score(None, self.max_score)
        validate_order(self.sort_order)


@dataclass(frozen=True, kw_only=True)
class TopicSkill(StudiumEntity):
    topic_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class LessonTopic(StudiumEntity):
    lesson_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class AssessmentTopic(StudiumEntity):
    assessment_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class AssessmentSkill(StudiumEntity):
    assessment_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class AssessmentItemTopic(StudiumEntity):
    assessment_item_id: EntityId
    topic_id: EntityId


@dataclass(frozen=True, kw_only=True)
class AssessmentItemSkill(StudiumEntity):
    assessment_item_id: EntityId
    skill_id: EntityId


@dataclass(frozen=True, kw_only=True)
class FileAsset(StudiumEntity):
    original_filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        validate_filename(self.original_filename)
        validate_storage_key(self.storage_key)
        if self.storage_key[9:45] != self.id.value or self.storage_key[6:8] != self.id.value[:2]:
            raise ValueError("Storage key must identify its FileAsset")
        require_text(self.mime_type, "mime_type")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ValueError("File size must be a nonnegative integer")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("File SHA-256 must be lowercase hex")


@dataclass(frozen=True, kw_only=True)
class AttemptAttachment(StudiumEntity):
    attempt_id: EntityId
    file_asset_id: EntityId
    caption: str | None = None
    sort_order: int = 0
    details_json: str = "{}"

    def __post_init__(self) -> None:
        validate_order(self.sort_order)
        if not isinstance(json.loads(self.details_json), dict):
            raise ValueError("Attachment details must be a JSON object")
