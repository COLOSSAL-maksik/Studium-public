"""Semantic port of all 16 checkpoint domain scenarios."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

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
from studium.domain.enums import AssessmentType, AttemptResult, EnrollmentStatus, StudentWorkStatus
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import EntityId, EntityMetadata, LocalDate, UtcInstant


def instant(day: int = 1) -> UtcInstant:
    return UtcInstant(datetime(2026, 10, day, tzinfo=UTC))


def metadata() -> EntityMetadata:
    return EntityMetadata.create(instant())


def attempt(
    work: EntityId,
    number: int,
    result: AttemptResult,
    *,
    day: int | None = None,
    score: float | None = None,
) -> Attempt:
    return Attempt(
        metadata=metadata(),
        student_work_id=work,
        attempt_no=number,
        occurred_at=instant(day or number),
        result=result,
        score=score,
    )


def test_uuid_v4_and_canonical_identity():
    ids = {EntityId.generate() for _ in range(100)}
    assert len(ids) == 100
    assert all(UUID(i.value).version == 4 for i in ids)
    first = next(iter(ids))
    assert EntityId(first.value.upper()) == first
    with pytest.raises(ValueError):
        EntityId("42")


def test_explicit_utc_and_microsecond_roundtrip():
    at = UtcInstant(datetime(2026, 9, 30, 9, 30, 0, 1007, tzinfo=UTC))
    assert UtcInstant.from_epoch_microseconds(at.epoch_microseconds) == at
    with pytest.raises(ValueError):
        UtcInstant(datetime(2026, 9, 30))
    with pytest.raises(ValueError):
        UtcInstant(datetime(2026, 9, 30, tzinfo=timezone(timedelta(hours=3))))
    assert UtcInstant.from_epoch_microseconds(-1).epoch_microseconds == -1


def test_calendar_date_is_not_instant():
    assert str(LocalDate.parse("2026-09-30")) == "2026-09-30"
    assert LocalDate(2024, 2, 29).day == 29
    for invalid in ["2026-02-29", "2026-09-30T00:00:00Z", "0000-01-01", "20260930"]:
        with pytest.raises(ValueError):
            LocalDate.parse(invalid)


def test_term_interval_and_name():
    term = AcademicTerm(
        metadata=metadata(),
        name="Synthetic term",
        starts_on=LocalDate(2026, 9, 1),
        ends_on=LocalDate(2027, 1, 31),
    )
    assert term.revision == 1 and term.deleted_at is None
    for changes in [dict(name=" "), dict(ends_on=LocalDate(2026, 8, 31))]:
        with pytest.raises(ValueError):
            replace(term, **changes)


def test_group_student_course():
    assert StudentGroup(metadata=metadata(), number="TEST-01").number == "TEST-01"
    assert Student(metadata=metadata(), full_name="Synthetic student").active
    assert Course(metadata=metadata(), name="Synthetic course").name
    with pytest.raises(ValueError):
        Student(metadata=metadata(), full_name=" ")


def test_offering_membership_context():
    offering = CourseOffering(
        metadata=metadata(),
        term_id=EntityId.generate(),
        course_id=EntityId.generate(),
        group_id=EntityId.generate(),
    )
    enrollment = Enrollment(
        metadata=metadata(),
        student_id=EntityId.generate(),
        offering_id=offering.id,
        enrolled_at=instant(),
    )
    assert enrollment.offering_id == offering.id
    with pytest.raises(ValueError):
        replace(enrollment, status=EnrollmentStatus.COMPLETED)


def test_assessment_maximum_and_deadline():
    assessment = Assessment(
        metadata=metadata(),
        offering_id=EntityId.generate(),
        type=AssessmentType.HOMEWORK,
        title="Test",
        issued_at=instant(),
        due_at=instant(2),
        max_score=10,
    )
    assert assessment.type.value == "HOMEWORK"
    for changes in [dict(issued_at=instant(3)), dict(max_score=0)]:
        with pytest.raises(ValueError):
            replace(assessment, **changes)


def test_work_is_identity_without_status():
    work = StudentWork(
        metadata=metadata(), student_id=EntityId.generate(), assessment_id=EntityId.generate()
    )
    assert not hasattr(work, "status")
    assert StudentWorkProgress.from_history(work.id, []) == StudentWorkProgress(
        StudentWorkStatus.NOT_STARTED, None, 0
    )


def test_second_attempt_is_separate_immutable_fact():
    work = EntityId.generate()
    first, second = (
        attempt(work, 1, AttemptResult.NEEDS_REVISION),
        attempt(work, 2, AttemptResult.ACCEPTED),
    )
    assert first.id != second.id and first.attempt_no == 1
    assert first.result == AttemptResult.NEEDS_REVISION
    with pytest.raises(FrozenInstanceError):
        first.attempt_no = 2
    assert (
        StudentWorkProgress.from_history(work, [second, first]).status == StudentWorkStatus.ACCEPTED
    )


def test_history_order_by_number_not_date():
    work = EntityId.generate()
    first = attempt(work, 1, AttemptResult.NEEDS_REVISION, day=5)
    second = attempt(work, 2, AttemptResult.ACCEPTED, day=1)
    assert (
        StudentWorkProgress.from_history(work, [second, first]).status == StudentWorkStatus.ACCEPTED
    )


def test_history_rejects_duplicate_and_foreign_attempts():
    work = EntityId.generate()
    first = attempt(work, 1, AttemptResult.PRESENTED)
    for history in [
        [first, first],
        [first, attempt(work, 1, AttemptResult.ACCEPTED)],
        [attempt(EntityId.generate(), 1, AttemptResult.PRESENTED)],
    ]:
        with pytest.raises(ValueError):
            StudentWorkProgress.from_history(work, history)


def test_rejected_comment_preserve_accepted_result():
    work = EntityId.generate()
    history = [
        attempt(work, 1, AttemptResult.ACCEPTED, score=8),
        attempt(work, 2, AttemptResult.REJECTED, score=0),
        attempt(work, 3, AttemptResult.COMMENT_ONLY),
    ]
    assert StudentWorkProgress.from_history(work, history) == StudentWorkProgress(
        StudentWorkStatus.ACCEPTED, 8, 3
    )


def test_scored_does_not_mean_accepted():
    work = EntityId.generate()
    assert (
        StudentWorkProgress.from_history(
            work, [attempt(work, 1, AttemptResult.SCORED, score=10)]
        ).status
        == StudentWorkStatus.SUBMITTED
    )
    with pytest.raises(ValueError):
        attempt(work, 2, AttemptResult.SCORED)


def test_soft_deleted_attempt_excluded_from_projection():
    work = EntityId.generate()
    first = attempt(work, 1, AttemptResult.NEEDS_REVISION)
    second = attempt(work, 2, AttemptResult.ACCEPTED)
    second = replace(second, metadata=second.metadata.soft_delete(instant(8)))
    assert second.result == AttemptResult.ACCEPTED and second.revision == 2
    assert (
        StudentWorkProgress.from_history(work, [first, second]).status
        == StudentWorkStatus.REVISION_REQUIRED
    )


def test_revision_and_monotonic_metadata():
    first = metadata()
    second = first.touch(instant(2))
    assert second.id == first.id and second.revision == 2
    deleted = second.soft_delete(instant(3))
    assert deleted.revision == 3 and deleted.deleted_at == instant(3)
    assert deleted.soft_delete(instant(4)) == deleted
    for mutation in [lambda: second.touch(instant()), lambda: replace(first, revision=0)]:
        with pytest.raises(ValueError):
            mutation()


def test_grade_variants_and_validation():
    id = EntityId.generate()
    assert Grade.pass_fail(metadata=metadata(), attempt_id=id, passed=True).passed
    assert Grade.pass_fail(metadata=metadata(), attempt_id=id, passed=False).passed is False
    assert Grade.numeric(metadata=metadata(), attempt_id=id, score=7).max_score is None
    assert Grade.numeric(metadata=metadata(), attempt_id=id, score=7, max_score=10).max_score == 10
    assert (
        Grade.traditional(metadata=metadata(), attempt_id=id, label="Excellent").label
        == "Excellent"
    )
    for score in [11, float("nan"), float("inf"), -1]:
        with pytest.raises(ValueError):
            Grade.numeric(metadata=metadata(), attempt_id=id, score=score, max_score=10)
    with pytest.raises(ValueError):
        Grade.traditional(metadata=metadata(), attempt_id=id, label=" ")
