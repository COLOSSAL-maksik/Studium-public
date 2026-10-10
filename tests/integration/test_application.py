from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier, Lock

import pytest
from sqlalchemy import event

from studium.application.services import ApplicationError, GradeInput
from studium.composition import create_runtime
from studium.domain.entities import Attempt, StudentWork
from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    EnrollmentStatus,
    GradeKind,
    StudentWorkStatus,
)
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityMetadata, LocalDate, UtcInstant
from studium.infrastructure.database.repositories import SqlAlchemyEnrollmentRepository


@pytest.fixture
def runtime(tmp_path):
    value = create_runtime(tmp_path)
    yield value
    value.close()


@pytest.fixture
def workflow(runtime):
    s = runtime.service
    term = s.create_term("Осень 2026", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Тестовая дисциплина", "Тест", "Синтетические данные")
    group = s.create_group("ТЕСТ-01", "Учебная кафедра", "Тест")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Тестовый Студент", "Характеристика")
    assessment = s.create_assessment(offering.id, "ДЗ №1", AssessmentType.HOMEWORK, max_score=10)
    work = s.get_or_create_work(student.id, assessment.id)
    return s, term, course, group, offering, student, assessment, work


def test_complete_workflow_and_idempotent_work(workflow):
    s, term, course, group, offering, student, assessment, work = workflow
    assert s.active_term() == term
    assert s.list_courses() == [course]
    assert s.groups(term.id)[0].student_count == 1
    assert s.create_offering(term.id, course.id, group.id) == offering
    assert s.get_or_create_work(student.id, assessment.id) == work
    roster = s.list_students_for_offering(offering.id)
    assert roster[0].student == student
    assert roster[0].enrollment.status == EnrollmentStatus.ACTIVE
    first = s.add_attempt(
        work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION, comment="Исправить знак"
    )
    second = s.add_attempt(
        work.id,
        UtcInstant.now(),
        AttemptResult.ACCEPTED,
        grade=GradeInput(GradeKind.PASS_FAIL, passed=True),
    )
    history = s.history(work.id)
    assert [row.attempt for row in history.entries] == [first, second]
    assert history.entries[0].attempt.comment == "Исправить знак"
    assert history.entries[1].grade.passed is True
    assert history.progress.status == StudentWorkStatus.ACCEPTED
    assert history.progress.attempt_count == 2
    matrix = s.matrix(offering.id)
    assert matrix.cells[student.id, assessment.id].progress == history.progress


def test_updates_revision_and_stale_edit(workflow):
    s, term, course, group, _, student, assessment, _ = workflow
    for original, update, fields in (
        (term, s.update_term, {"name": "Новый период"}),
        (course, s.update_course, {"name": "Новая дисциплина"}),
        (group, s.update_group, {"number": "ТЕСТ-02"}),
        (student, s.update_student, {"notes": "Новая характеристика"}),
        (assessment, s.update_assessment, {"title": "ДЗ №2", "issued_at": None}),
    ):
        changed = update(original, **fields)
        assert changed.id == original.id and changed.revision == 2
        with pytest.raises(RepositoryError) as error:
            update(original, **fields)
        assert error.value.failure == RepositoryFailure.REVISION_CONFLICT


def test_withdraw_preserves_history_and_allows_reenrollment(workflow):
    s, _, _, _, offering, student, _, work = workflow
    attempt = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    en = s.list_students_for_offering(offering.id)[0].enrollment
    s.withdraw_student(en)
    assert s.list_students_for_offering(offering.id) == []
    assert s.list_students_for_offering(offering.id, include_ended=True)[0].enrollment.ended_at
    assert s.history(work.id).entries[0].attempt == attempt
    with pytest.raises(ApplicationError, match="active_enrollment_required"):
        s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    s.enroll_student(offering.id, student.id)
    assert len(s.list_students_for_offering(offering.id, include_ended=True)) == 1


def test_duplicate_enrollment_does_not_create_orphan_student(workflow):
    s, _, _, _, offering, student, _, _ = workflow
    with pytest.raises(RepositoryError) as error:
        s.enroll_student(offering.id, student.id)
    assert error.value.failure == RepositoryFailure.DUPLICATE
    missing = replace(offering.id, value="00000000-0000-4000-8000-000000000000")
    with pytest.raises(RepositoryError):
        s.create_student(missing, "Другой тестовый студент")
    assert s.list_students() == [student]


def test_group_count_deduplicates_students_across_courses(workflow):
    s, term, _, group, _, student, _, _ = workflow
    course = s.create_course("Вторая дисциплина")
    other = s.create_offering(term.id, course.id, group.id)
    s.enroll_student(other.id, student.id)
    assert s.groups(term.id)[0].student_count == 1


@pytest.mark.parametrize(
    "kind,result,fields,spec",
    [
        (
            GradeKind.NUMERIC,
            AttemptResult.SCORED,
            {"score": 8, "max_score": 10},
            GradeInput(GradeKind.NUMERIC),
        ),
        (
            GradeKind.TRADITIONAL,
            AttemptResult.ACCEPTED,
            {},
            GradeInput(GradeKind.TRADITIONAL, label="Хорошо"),
        ),
        (
            GradeKind.PASS_FAIL,
            AttemptResult.REJECTED,
            {},
            GradeInput(GradeKind.PASS_FAIL, passed=False),
        ),
    ],
)
def test_grade_variants(workflow, kind, result, fields, spec):
    s, _, _, _, _, _, assessment, work = workflow
    if result == AttemptResult.REJECTED:
        s.update_assessment(assessment, type=AssessmentType.CONTROL_WORK)
    s.add_attempt(work.id, UtcInstant.now(), result, grade=spec, **fields)
    assert s.history(work.id).entries[0].grade.kind == kind


def test_invalid_grade_rolls_back_attempt(workflow):
    s, *_, work = workflow
    with pytest.raises(ApplicationError, match="grade_result_mismatch"):
        s.add_attempt(
            work.id,
            UtcInstant.now(),
            AttemptResult.PRESENTED,
            grade=GradeInput(GradeKind.PASS_FAIL, passed=True),
        )
    assert s.history(work.id).entries == ()


def test_next_attempt_number_includes_deleted_facts(workflow):
    s, *_, work = workflow
    first = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.PRESENTED)
    s._r.attempts.soft_delete(first.id, expected_revision=first.revision, at=UtcInstant.now())
    assert s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED).attempt_no == 2


def test_concurrent_attempt_number_assignment(workflow, monkeypatch):
    s, *_, work = workflow
    barrier, lock = Barrier(2), Lock()
    read_history = s._r.attempts.history
    calls = 0

    def simultaneous_history(*args, **kwargs):
        nonlocal calls
        history = read_history(*args, **kwargs)
        with lock:
            calls += 1
            synchronize = calls <= 2
        if synchronize:
            barrier.wait(timeout=5)
        return history

    monkeypatch.setattr(s._r.attempts, "history", simultaneous_history)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: s.add_attempt(work.id, UtcInstant.now(), AttemptResult.PRESENTED),
                range(2),
            )
        )
    assert sorted(a.attempt_no for a in results) == [1, 2]
    assert len(s.history(work.id).entries) == 2


def test_student_and_enrollment_rollback_together(workflow, monkeypatch):
    s, _, _, _, offering, student, _, _ = workflow

    def fail_enrollment(_self, _entity):
        raise RepositoryError(RepositoryFailure.INVALID_REFERENCE, "Synthetic insertion failure")

    monkeypatch.setattr(SqlAlchemyEnrollmentRepository, "insert", fail_enrollment)
    with pytest.raises(RepositoryError):
        s.create_student(offering.id, "Студент откатанной транзакции")
    assert s.list_students() == [student]


def test_attempt_retries_are_bounded_and_do_not_overwrite(workflow, monkeypatch):
    s, *_, work = workflow
    calls = 0

    def duplicate(_attempt, *, grade=None):
        nonlocal calls
        calls += 1
        raise RepositoryError(RepositoryFailure.DUPLICATE, "Synthetic conflict")

    monkeypatch.setattr(s._r.attempts, "append", duplicate)
    with pytest.raises(ApplicationError, match="concurrent_attempt"):
        s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    assert calls == 5
    assert s.history(work.id).entries == ()


def test_soft_delete_parent_preserves_history(workflow):
    s, _, _, group, _, _, _, work = workflow
    s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    s.hide("group", group)
    assert s.groups() == []
    assert s.history(work.id).entries[0].attempt.result == AttemptResult.ACCEPTED
    with pytest.raises(RepositoryError):
        s.add_attempt(work.id, UtcInstant.now(), AttemptResult.PRESENTED)


def test_selected_term_and_data_survive_reopen(runtime, workflow, tmp_path):
    s, term, *_, work = workflow
    s.add_attempt(work.id, UtcInstant(datetime(2026, 10, 1, tzinfo=UTC)), AttemptResult.ACCEPTED)
    other = s.create_term("Весна", LocalDate(2027, 2, 1), LocalDate(2027, 6, 30))
    s.select_term(term.id)
    reopened = create_runtime(tmp_path)
    try:
        assert reopened.service.active_term().id == term.id
        assert len(reopened.service.list_terms()) == 2
        assert other.id != term.id
        assert reopened.service.history(work.id).progress.status == StudentWorkStatus.ACCEPTED
    finally:
        reopened.close()


def test_matrix_does_not_issue_query_per_cell(runtime, workflow):
    s, _, _, _, offering, _, _, _ = workflow
    for i in range(24):
        s.create_student(offering.id, f"Синтетический студент {i:02}")
    for i in range(29):
        s.create_assessment(offering.id, f"ДЗ {i:02}", AssessmentType.HOMEWORK)
    initial = s.matrix(offering.id)
    # A full matrix exercises the >400 UUID chunk boundary as well as avoiding N+1.
    with s._transaction() as r:
        for cell in initial.cells.values():
            work = cell.work
            if work is None:
                work = StudentWork(
                    metadata=EntityMetadata.create(UtcInstant.now()),
                    student_id=cell.student_id,
                    assessment_id=cell.assessment_id,
                )
                r.works.insert(work)
            r.attempts.append(
                Attempt(
                    metadata=EntityMetadata.create(UtcInstant.now()),
                    student_work_id=work.id,
                    attempt_no=1,
                    occurred_at=UtcInstant.now(),
                    result=AttemptResult.ACCEPTED,
                )
            )
    queries = []

    def capture(*args):
        queries.append(args[2])

    event.listen(runtime._engine, "before_cursor_execute", capture)
    try:
        matrix = s.matrix(offering.id)
    finally:
        event.remove(runtime._engine, "before_cursor_execute", capture)
    assert len(matrix.cells) == 25 * 30
    assert all(cell.progress.status == StudentWorkStatus.ACCEPTED for cell in matrix.cells.values())
    assert len(queries) <= 10
