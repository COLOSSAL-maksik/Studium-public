"""Domain ↔ ORM mapping, local transactions and optimistic revision checks."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import fields
from enum import Enum

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from studium.domain import content, program
from studium.domain import entities as domain
from studium.domain.analytics_facts import AttemptItemResult
from studium.domain.communication import AuthorRole, CommunicationChannel, Message
from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    AttendanceStatus,
    EnrollmentStatus,
    GradeKind,
    ItemOutcome,
    LessonType,
)
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import (
    AcademicWeekNumber,
    EntityId,
    EntityMetadata,
    LocalDate,
    UtcInstant,
)
from studium.infrastructure.database import models

ENUM_FIELDS = {
    program.WorkProgram: {"semester": program.SemesterType},
    program.KnowledgeEntry: {"type": program.KnowledgeType},
    program.AttemptSkillResult: {"outcome": ItemOutcome},
    content.HomeworkDefinition: {"type": AssessmentType},
    content.SeminarMaterial: {"type": LessonType},
    domain.Lesson: {"type": LessonType},
    content.LiteratureItem: {"type": content.LiteratureType},
    **{
        cls: {"role": content.MaterialFileRole}
        for cls in (
            content.HomeworkAttachment,
            content.ProblemAttachment,
            content.SeminarAttachment,
            content.LiteratureAttachment,
            content.TicketProblemFile,
            program.ProgramAttachment,
            program.HomeworkPackAttachment,
            program.MethodicalAttachment,
            program.AssessmentAttachment,
            program.StudentProblemFile,
        )
    },
    AttemptItemResult: {"outcome": ItemOutcome},
    Message: {"author_role": AuthorRole, "channel": CommunicationChannel},
    domain.Assessment: {"type": AssessmentType},
    domain.Attempt: {"result": AttemptResult},
    domain.Enrollment: {"status": EnrollmentStatus},
    domain.Grade: {"kind": GradeKind},
    domain.Attendance: {"status": AttendanceStatus},
}
BOOLEAN_FIELDS = {"active", "archived", "passed", "cancelled", "draft", "is_family"}
DATE_FIELDS = {
    "starts_on",
    "ends_on",
    "lesson_date",
    "first_week_start",
    "planned_date",
    "issue_date",
    "due_date",
}
TIME_FIELDS = {
    "opened_at",
    "closed_at",
    "sent_at",
    "created_at",
    "updated_at",
    "deleted_at",
    "enrolled_at",
    "ended_at",
    "issued_at",
    "due_at",
    "occurred_at",
}


def storage_value(value):
    if isinstance(value, AcademicWeekNumber):
        return value.value
    if isinstance(value, EntityId):
        return value.value
    if isinstance(value, UtcInstant):
        return value.epoch_microseconds
    if isinstance(value, LocalDate):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def entity_values(entity: domain.StudiumEntity) -> dict:
    values = {
        f.name: storage_value(getattr(entity.metadata, f.name)) for f in fields(EntityMetadata)
    }
    values.update(
        {
            f.name: storage_value(getattr(entity, f.name))
            for f in fields(entity)
            if f.name != "metadata"
        }
    )
    return values


def domain_value[T: domain.StudiumEntity](entity_type: type[T], row: models.Base) -> T:
    def convert(name: str):
        value = getattr(row, name)
        if value is None:
            return None
        if name in {"planned_issue_week", "planned_due_week", "planned_week"}:
            return AcademicWeekNumber(value)
        if name == "id" or (name.endswith("_id") and not name.startswith("external_")):
            return EntityId(value)
        if name in TIME_FIELDS:
            return UtcInstant.from_epoch_microseconds(value)
        if name in DATE_FIELDS:
            return LocalDate.parse(value)
        if name in BOOLEAN_FIELDS:
            return bool(value)
        if enum := ENUM_FIELDS.get(entity_type, {}).get(name):
            return enum(value)
        return value

    metadata = EntityMetadata(**{f.name: convert(f.name) for f in fields(EntityMetadata)})
    values = {f.name: convert(f.name) for f in fields(entity_type) if f.name != "metadata"}
    return entity_type(metadata=metadata, **values)


def translate_error(error: SQLAlchemyError) -> RepositoryError:
    # Do not expose SQL parameters or student data in public errors.
    if not isinstance(error, IntegrityError):
        return RepositoryError(
            RepositoryFailure.STORAGE_UNAVAILABLE, "Local storage operation failed"
        )
    reason = str(error.orig).lower()
    if "immutable" in reason or "must be soft deleted" in reason:
        failure = RepositoryFailure.IMMUTABLE_FACT
    elif "revision" in reason:
        failure = RepositoryFailure.REVISION_CONFLICT
    elif "unique" in reason or "number must increase" in reason or "must not overlap" in reason:
        failure = RepositoryFailure.DUPLICATE
    elif "foreign key" in reason or "requires" in reason:
        failure = RepositoryFailure.INVALID_REFERENCE
    else:
        failure = RepositoryFailure.INVALID_DATA
    return RepositoryError(failure, f"Local data constraint: {failure.value}")


class SqlAlchemyReadRepository[T: domain.StudiumEntity]:
    entity_type: type[T]
    row_type: type[models.Base]

    def __init__(self, sessions: sessionmaker[Session] | Session) -> None:
        self._sessions = sessions

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        try:
            if isinstance(self._sessions, Session):
                yield self._sessions
            else:
                with self._sessions.begin() as session:
                    yield session
        except SQLAlchemyError as error:
            raise translate_error(error) from None

    def find_by_id(self, id: EntityId, *, include_deleted: bool = False) -> T | None:
        with self._transaction() as session:
            row = session.get(self.row_type, id.value)
            if row is None or (row.deleted_at is not None and not include_deleted):
                return None
            return domain_value(self.entity_type, row)

    def list(self, *, include_deleted: bool = False) -> list[T]:
        query = select(self.row_type).order_by(self.row_type.created_at, self.row_type.id)
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]

    def _insert(self, session: Session, entity: T) -> None:
        session.add(self.row_type(**entity_values(entity)))
        session.flush()

    def _matching(self, column, value) -> list[T]:
        with self._transaction() as session:
            rows = session.scalars(
                select(self.row_type)
                .where(column == storage_value(value), self.row_type.deleted_at.is_(None))
                .order_by(self.row_type.created_at, self.row_type.id)
            )
            return [domain_value(self.entity_type, row) for row in rows]

    def _many(self, column, ids: Iterable[EntityId]) -> list[T]:
        values = sorted({id.value for id in ids})
        result = []
        with self._transaction() as session:
            for offset in range(0, len(values), 400):
                rows = session.scalars(
                    select(self.row_type).where(
                        column.in_(values[offset : offset + 400]),
                        self.row_type.deleted_at.is_(None),
                    )
                )
                result.extend(domain_value(self.entity_type, row) for row in rows)
        return result

    def find_by_ids(self, ids: Iterable[EntityId]) -> list[T]:
        return self._many(self.row_type.id, ids)


class SqlAlchemySoftDeleteRepository[T: domain.StudiumEntity](SqlAlchemyReadRepository[T]):
    def _compare_and_swap(self, session: Session, entity: T, expected_revision: int) -> None:
        if entity.revision != expected_revision + 1:
            raise RepositoryError(
                RepositoryFailure.REVISION_CONFLICT, "Expected the next local revision"
            )
        result = session.execute(
            update(self.row_type)
            .where(self.row_type.id == entity.id.value, self.row_type.revision == expected_revision)
            .values(**entity_values(entity))
        )
        if result.rowcount != 1:
            exists = session.get(self.row_type, entity.id.value)
            failure = (
                RepositoryFailure.NOT_FOUND
                if exists is None
                else RepositoryFailure.REVISION_CONFLICT
            )
            raise RepositoryError(failure, "Object missing or changed since it was read")

    def soft_delete(self, id: EntityId, *, expected_revision: int, at: UtcInstant) -> None:
        with self._transaction() as session:
            row = session.get(self.row_type, id.value)
            if row is None:
                raise RepositoryError(RepositoryFailure.NOT_FOUND, "Object not found")
            if row.revision != expected_revision:
                raise RepositoryError(
                    RepositoryFailure.REVISION_CONFLICT, "Object changed since it was read"
                )
            if row.deleted_at is not None:
                return
            metadata = domain_value(self.entity_type, row).metadata.soft_delete(at)
            result = session.execute(
                update(self.row_type)
                .where(self.row_type.id == id.value, self.row_type.revision == expected_revision)
                .values(
                    updated_at=metadata.updated_at.epoch_microseconds,
                    deleted_at=metadata.deleted_at.epoch_microseconds,
                    revision=metadata.revision,
                )
            )
            if result.rowcount != 1:
                raise RepositoryError(
                    RepositoryFailure.REVISION_CONFLICT, "Object changed since it was read"
                )


class SqlAlchemyMutableRepository[T: domain.StudiumEntity](SqlAlchemySoftDeleteRepository[T]):
    def insert(self, entity: T) -> None:
        with self._transaction() as session:
            self._insert(session, entity)

    def update(self, entity: T, *, expected_revision: int) -> None:
        with self._transaction() as session:
            self._compare_and_swap(session, entity, expected_revision)


class SqlAlchemyAcademicTermRepository(SqlAlchemyMutableRepository[domain.AcademicTerm]):
    entity_type, row_type = domain.AcademicTerm, models.AcademicTermRow


class SqlAlchemyCourseRepository(SqlAlchemyMutableRepository[domain.Course]):
    entity_type, row_type = domain.Course, models.CourseRow


class SqlAlchemyStudentGroupRepository(SqlAlchemyMutableRepository[domain.StudentGroup]):
    entity_type, row_type = domain.StudentGroup, models.StudentGroupRow


class SqlAlchemyStudentRepository(SqlAlchemyMutableRepository[domain.Student]):
    entity_type, row_type = domain.Student, models.StudentRow


class SqlAlchemyCourseOfferingRepository(SqlAlchemyMutableRepository[domain.CourseOffering]):
    entity_type, row_type = domain.CourseOffering, models.CourseOfferingRow

    def for_group(self, group_id: EntityId) -> list[domain.CourseOffering]:
        return self._matching(self.row_type.group_id, group_id)


class SqlAlchemyEnrollmentRepository(SqlAlchemyMutableRepository[domain.Enrollment]):
    entity_type, row_type = domain.Enrollment, models.EnrollmentRow

    def for_offering(self, offering_id: EntityId) -> list[domain.Enrollment]:
        return self._matching(self.row_type.offering_id, offering_id)

    def for_student(self, student_id: EntityId) -> list[domain.Enrollment]:
        query = (
            select(self.row_type)
            .where(self.row_type.student_id == student_id.value, self.row_type.deleted_at.is_(None))
            .order_by(self.row_type.enrolled_at, self.row_type.id)
        )
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]


class SqlAlchemyAssessmentRepository(SqlAlchemyMutableRepository[domain.Assessment]):
    entity_type, row_type = domain.Assessment, models.AssessmentRow

    def for_offering(self, offering_id: EntityId) -> list[domain.Assessment]:
        return self._matching(self.row_type.offering_id, offering_id)


class SqlAlchemyStudentWorkRepository(SqlAlchemySoftDeleteRepository[domain.StudentWork]):
    entity_type, row_type = domain.StudentWork, models.StudentWorkRow

    def for_assessments(self, ids: Iterable[EntityId]) -> list[domain.StudentWork]:
        return self._many(self.row_type.assessment_id, ids)

    def find_for_student(
        self, student_id: EntityId, assessment_id: EntityId, *, include_deleted: bool = False
    ) -> domain.StudentWork | None:
        query = select(self.row_type).where(
            self.row_type.student_id == student_id.value,
            self.row_type.assessment_id == assessment_id.value,
        )
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            row = session.scalar(query)
            return domain_value(self.entity_type, row) if row is not None else None

    def insert(self, entity: domain.StudentWork) -> None:
        with self._transaction() as session:
            self._insert(session, entity)

    def progress(self, id: EntityId) -> StudentWorkProgress:
        with self._transaction() as session:
            work = session.get(self.row_type, id.value)
            if work is None or work.deleted_at is not None:
                raise RepositoryError(RepositoryFailure.NOT_FOUND, "Active work not found")
            rows = session.scalars(
                select(models.AttemptRow)
                .where(models.AttemptRow.student_work_id == id.value)
                .order_by(models.AttemptRow.attempt_no)
            )
            return StudentWorkProgress.from_history(
                id, (domain_value(domain.Attempt, row) for row in rows)
            )


class SqlAlchemyAttemptRepository(SqlAlchemySoftDeleteRepository[domain.Attempt]):
    entity_type, row_type = domain.Attempt, models.AttemptRow

    def for_works(self, ids: Iterable[EntityId]) -> list[domain.Attempt]:
        return self._many(self.row_type.student_work_id, ids)

    def append(self, attempt: domain.Attempt, *, grade: domain.Grade | None = None) -> None:
        if grade is not None and grade.attempt_id != attempt.id:
            raise RepositoryError(
                RepositoryFailure.INVALID_REFERENCE, "Grade belongs to another attempt"
            )
        with self._transaction() as session:
            self._insert(session, attempt)
            if grade is not None:
                session.add(models.GradeRow(**entity_values(grade)))
                session.flush()

    def history(
        self, student_work_id: EntityId, *, include_deleted: bool = False
    ) -> list[domain.Attempt]:
        query = (
            select(self.row_type)
            .where(self.row_type.student_work_id == student_work_id.value)
            .order_by(self.row_type.attempt_no)
        )
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]


class SqlAlchemyGradeRepository(SqlAlchemyReadRepository[domain.Grade]):
    entity_type, row_type = domain.Grade, models.GradeRow

    def for_attempt(
        self, attempt_id: EntityId, *, include_deleted: bool = False
    ) -> domain.Grade | None:
        query = select(self.row_type).where(self.row_type.attempt_id == attempt_id.value)
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            row = session.scalar(query)
            return domain_value(self.entity_type, row) if row is not None else None
