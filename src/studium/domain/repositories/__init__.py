"""Synchronous local contracts; storage exceptions do not escape these boundaries."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Protocol, TypeVar

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
    StudiumEntity,
)
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import EntityId, UtcInstant

T_co = TypeVar("T_co", bound=StudiumEntity, covariant=True)
T = TypeVar("T", bound=StudiumEntity)


class RepositoryFailure(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE = "DUPLICATE"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    IMMUTABLE_FACT = "IMMUTABLE_FACT"
    INVALID_DATA = "INVALID_DATA"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


class RepositoryError(Exception):
    def __init__(self, failure: RepositoryFailure, message: str) -> None:
        super().__init__(message)
        self.failure = failure


class ReadRepository(Protocol[T_co]):
    def find_by_id(self, id: EntityId, *, include_deleted: bool = False) -> T_co | None: ...
    def list(self, *, include_deleted: bool = False) -> list[T_co]: ...
    def find_by_ids(self, ids: Iterable[EntityId]) -> list[T_co]: ...


class SoftDeleteRepository(ReadRepository[T_co], Protocol[T_co]):
    def soft_delete(self, id: EntityId, *, expected_revision: int, at: UtcInstant) -> None: ...


class MutableRepository(SoftDeleteRepository[T], Protocol[T]):
    def insert(self, entity: T) -> None: ...
    def update(self, entity: T, *, expected_revision: int) -> None: ...


class AcademicTermRepository(MutableRepository[AcademicTerm], Protocol): ...


class CourseRepository(MutableRepository[Course], Protocol): ...


class StudentGroupRepository(MutableRepository[StudentGroup], Protocol): ...


class StudentRepository(MutableRepository[Student], Protocol): ...


class CourseOfferingRepository(MutableRepository[CourseOffering], Protocol):
    def for_group(self, group_id: EntityId) -> list[CourseOffering]: ...


class AssessmentRepository(MutableRepository[Assessment], Protocol):
    def for_offering(self, offering_id: EntityId) -> list[Assessment]: ...


class EnrollmentRepository(MutableRepository[Enrollment], Protocol):
    def for_student(self, student_id: EntityId) -> list[Enrollment]: ...
    def for_offering(self, offering_id: EntityId) -> list[Enrollment]: ...


class StudentWorkRepository(SoftDeleteRepository[StudentWork], Protocol):
    def restore(self, id: EntityId, *, expected_revision: int, at: UtcInstant) -> None: ...
    def insert(self, entity: StudentWork) -> None: ...
    def progress(self, id: EntityId) -> StudentWorkProgress: ...
    def for_assessments(self, ids: Iterable[EntityId]) -> list[StudentWork]: ...
    def find_for_student(
        self, student_id: EntityId, assessment_id: EntityId, *, include_deleted: bool = False
    ) -> StudentWork | None: ...


class AttemptRepository(SoftDeleteRepository[Attempt], Protocol):
    def append(self, attempt: Attempt, *, grade: Grade | None = None) -> None: ...
    def history(
        self, student_work_id: EntityId, *, include_deleted: bool = False
    ) -> list[Attempt]: ...
    def for_works(self, ids: Iterable[EntityId]) -> list[Attempt]: ...


class GradeRepository(ReadRepository[Grade], Protocol):
    def for_attempt(
        self, attempt_id: EntityId, *, include_deleted: bool = False
    ) -> Grade | None: ...
