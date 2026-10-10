"""Immutable query results containing domain values, never ORM objects."""

from collections.abc import Mapping
from dataclasses import dataclass

from studium.domain.entities import (
    AcademicTerm,
    Assessment,
    Attempt,
    Course,
    CourseOffering,
    Enrollment,
    Grade,
    Student,
    StudentGroup,
    StudentWork,
)
from studium.domain.enums import AttemptResult
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import EntityId, UtcInstant


@dataclass(frozen=True)
class OfferingContext:
    offering: CourseOffering
    term: AcademicTerm
    course: Course
    group: StudentGroup


@dataclass(frozen=True)
class RosterEntry:
    student: Student
    enrollment: Enrollment


@dataclass(frozen=True)
class GroupSummary:
    group: StudentGroup
    student_count: int


@dataclass(frozen=True)
class WorkCell:
    student_id: EntityId
    assessment_id: EntityId
    work: StudentWork | None
    progress: StudentWorkProgress | None


@dataclass(frozen=True)
class ProgressMatrix:
    context: OfferingContext
    roster: tuple[RosterEntry, ...]
    assessments: tuple[Assessment, ...]
    cells: Mapping[tuple[EntityId, EntityId], WorkCell]


@dataclass(frozen=True)
class HistoryEntry:
    attempt: Attempt
    grade: Grade | None


@dataclass(frozen=True)
class WorkHistory:
    work: StudentWork
    student: Student
    assessment: Assessment
    context: OfferingContext
    entries: tuple[HistoryEntry, ...]
    progress: StudentWorkProgress


@dataclass(frozen=True)
class Diagnostics:
    database_path: str
    data_directory: str
    app_version: str
    schema_version: str
    python_version: str
    qt_version: str


@dataclass(frozen=True)
class ActivityEntry:
    kind: str
    occurred_at: UtcInstant
    title: str
    result: AttemptResult | None = None
