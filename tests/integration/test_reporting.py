"""Synthetic reporting facts, isolation, ordering and fixed SQL query budget."""

from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import event

from studium.application.errors import ApplicationError
from studium.application.report_models import ReportKind
from studium.application.services import GradeInput
from studium.domain import entities as e
from studium.domain.analytics_facts import AttemptItemResult
from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    AttendanceStatus,
    GradeKind,
    ItemOutcome,
    StudentWorkStatus,
)
from studium.domain.value_objects import EntityMetadata, LocalDate
from tests.integration.test_analytics import analytics_workflow as analytics_workflow
from tests.integration.test_application import runtime as runtime
from tests.unit.test_domain import instant


def section(report, key):
    return next(t for t in report.tables if t.key == key)


def database_facts(engine):
    """Every raw record and schema entry, including revisions, attachments and assets."""
    with engine.connect() as connection:
        schema = tuple(
            connection.exec_driver_sql(
                "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
            )
        )
        tables = [name for kind, name, *_ in schema if kind == "table"]
        facts = tuple(
            (name, tuple(connection.exec_driver_sql(f'SELECT * FROM "{name}" ORDER BY rowid')))
            for name in tables
        )
    return schema, facts


def test_student_report_facts_grade_provenance_and_neutral_attempts(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(
        w.work.id,
        instant(3),
        AttemptResult.ACCEPTED,
        score=0,
        max_score=10,
        grade=GradeInput(GradeKind.NUMERIC),
    )
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.COMMENT_ONLY)
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    row = section(report, "works").rows[0]
    assert row[0] == w.assessment.title
    assert row[4:7] == (StudentWorkStatus.ACCEPTED, 2, instant(2))
    assert row[7].score == 0 and row[8] == 1 and row[9] == 0
    assert [r[1] for r in section(report, "attempts").rows] == [1, 2]
    assert section(report, "attendance").rows[0][1:] == (0, 0, 0, 0, 0, 0, 0)
    assert ("ФИО", w.student.full_name) in report.metadata
    with pytest.raises(FrozenInstanceError):
        report.title = "changed"


def test_group_and_assessment_missing_facts_do_not_create_work(analytics_workflow):
    w = analytics_workflow
    other = w.s.create_student(w.offering.id, "Альфа Синтетический")
    before = database_facts(w.s._r.works._sessions.kw["bind"])
    group = w.s.build_report(ReportKind.GROUP, w.offering.id)
    assessment = w.s.build_report(
        ReportKind.ASSESSMENT, w.offering.id, assessment_id=w.assessment.id
    )
    assert [row[0] for row in section(group, "students").rows] == [
        w.student.full_name,
        other.full_name,
    ]
    assert all(row[1:4] == (1, 0, 0) for row in section(group, "students").rows)
    assert all(
        row[5:11] == (StudentWorkStatus.NOT_STARTED, 0, None, None, None, None)
        for row in section(assessment, "works").rows
    )
    assert database_facts(w.s._r.works._sessions.kw["bind"]) == before


def test_empty_group_optional_dates_and_ordering(analytics_workflow):
    w = analytics_workflow
    group = w.s.create_group("Synthetic empty")
    offering = w.s.create_offering(w.term.id, w.course.id, group.id)
    empty = w.s.build_report(ReportKind.GROUP, offering.id)
    assert section(empty, "students").rows == section(empty, "works").rows == ()
    w.s.create_assessment(
        w.offering.id, "Я Синтетическая", AssessmentType.HOMEWORK, issued_at=instant()
    )
    w.s.create_assessment(
        w.offering.id, "А Синтетическая", AssessmentType.HOMEWORK, issued_at=instant()
    )
    one = w.s.build_report(
        ReportKind.STUDENT, w.offering.id, student_id=w.student.id, as_of=instant(10)
    )
    two = w.s.build_report(
        ReportKind.STUDENT, w.offering.id, student_id=w.student.id, as_of=instant(10)
    )
    assert one == two
    works = section(one, "works").rows
    assert [r[0] for r in works] == [w.assessment.title, "А Синтетическая", "Я Синтетическая"]
    assert works[1][2:4] == (None, None)


def test_exact_period_course_group_student_and_assessment_scope(analytics_workflow):
    w = analytics_workflow
    contexts = []
    for term, course, group in (
        (
            w.s.create_term("Other period", LocalDate(2027, 2, 1), LocalDate(2027, 6, 1)),
            w.course,
            w.group,
        ),
        (w.term, w.s.create_course("Other course"), w.group),
        (w.term, w.course, w.s.create_group("Other group")),
    ):
        context = w.s.create_offering(term.id, course.id, group.id)
        outsider = w.s.create_student(context.id, "Synthetic outsider")
        assessment = w.s.create_assessment(context.id, "Foreign assessment", AssessmentType.TEST)
        contexts.append(context)
    with pytest.raises(ApplicationError):
        w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=outsider.id)
    with pytest.raises(ApplicationError):
        w.s.build_report(ReportKind.ASSESSMENT, w.offering.id, assessment_id=assessment.id)
    report = w.s.build_report(ReportKind.GROUP, w.offering.id)
    assert len(section(report, "students").rows) == len(section(report, "works").rows) == 1
    assert all(c.term.id == w.term.id for c in w.s.report_contexts(w.term.id))
    assert contexts[0].id not in {c.offering.id for c in w.s.report_contexts(w.term.id)}


def test_historical_context_ended_students_and_archived_assessment(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.ACCEPTED)
    enrollment = w.s._r.enrollments.for_offering(w.offering.id)[0]
    w.s.withdraw_student(enrollment)
    assert section(w.s.build_report(ReportKind.GROUP, w.offering.id), "students").rows == ()
    historical = w.s.build_report(
        ReportKind.STUDENT, w.offering.id, student_id=w.student.id, historical=True
    )
    assert section(historical, "works").rows[0][4] == StudentWorkStatus.ACCEPTED
    w.s.hide("assessment", w.assessment)
    w.s.hide("course", w.course)
    assert w.s.report_contexts(w.term.id) == ()
    assert len(w.s.report_contexts(w.term.id, historical=True)) == 1
    historical = w.s.build_report(
        ReportKind.ASSESSMENT, w.offering.id, assessment_id=w.assessment.id, historical=True
    )
    assert section(historical, "works").rows[0][5] == StudentWorkStatus.ACCEPTED
    with pytest.raises(ApplicationError):
        w.s.build_report(ReportKind.GROUP, w.offering.id)


def test_attendance_and_topic_skill_evidence_reuse_existing_facts(analytics_workflow):
    w = analytics_workflow
    topic = w.s.create_topic(w.course.id, "Синтетическая тема")
    skill = w.s.create_skill(w.course.id, "Синтетический навык")
    with w.s._transaction() as r:
        r.assessment_topics.insert(
            e.AssessmentTopic(
                metadata=EntityMetadata.create(instant()),
                assessment_id=w.assessment.id,
                topic_id=topic.id,
            )
        )
        r.assessment_skills.insert(
            e.AssessmentSkill(
                metadata=EntityMetadata.create(instant()),
                assessment_id=w.assessment.id,
                skill_id=skill.id,
            )
        )
        item = e.AssessmentItem(
            metadata=EntityMetadata.create(instant()),
            assessment_id=w.assessment.id,
            title="Синтетическая часть",
        )
        r.items.insert(item)
    attempt = w.s.add_attempt(w.work.id, instant(3), AttemptResult.NEEDS_REVISION)
    with w.s._transaction() as r:
        r.item_results.insert(
            AttemptItemResult(
                metadata=EntityMetadata.create(instant()),
                attempt_id=attempt.id,
                assessment_item_id=item.id,
                outcome=ItemOutcome.PARTIAL,
                score=0,
                max_score=2,
            )
        )
    lesson = w.s.create_lesson(w.offering.id, LocalDate(2026, 9, 1), title="Synthetic lesson")
    enrollment = w.s._r.enrollments.for_offering(w.offering.id)[0]
    with w.s._transaction() as r:
        r.attendance.insert(
            e.Attendance(
                metadata=EntityMetadata.create(instant()),
                lesson_id=lesson.id,
                enrollment_id=enrollment.id,
                status=AttendanceStatus.LATE,
            )
        )
    report = w.s.build_report(ReportKind.STUDENT, w.offering.id, student_id=w.student.id)
    assert section(report, "items").rows[0][4:] == (ItemOutcome.PARTIAL, 0, 2)
    assert section(report, "attendance").rows[0][1:] == (1, 0, 0, 1, 0, 0, 0)
    assert (
        section(report, "topics").rows[0][1]
        == w.s.topic_evidence(
            topic.id, offering_id=w.offering.id, student_id=w.student.id
        ).evidence_count
    )
    assert section(report, "skills").rows[0][1] > 0
    assert attempt.id.value in section(report, "topics").rows[0][-1]


def test_all_attendance_states_and_unmarked_are_preserved(analytics_workflow):
    w = analytics_workflow
    enrollment = w.s._r.enrollments.for_offering(w.offering.id)[0]
    with w.s._transaction() as r:
        for i, status in enumerate((*AttendanceStatus, None), 1):
            lesson = e.Lesson(
                metadata=EntityMetadata.create(instant()),
                course_offering_id=w.offering.id,
                lesson_date=LocalDate(2026, 9, i),
            )
            r.lessons.insert(lesson)
            if status is not None:
                r.attendance.insert(
                    e.Attendance(
                        metadata=EntityMetadata.create(instant()),
                        lesson_id=lesson.id,
                        enrollment_id=enrollment.id,
                        status=status,
                    )
                )
    report = w.s.build_report(ReportKind.GROUP, w.offering.id)
    assert section(report, "attendance_total").rows == ((6, 1, 1, 1, 1, 1, 1),)


def test_group_query_budget_does_not_grow_with_matrix(runtime):
    s = runtime.service
    s._clock = lambda: instant(20)
    term = s.create_term("Synthetic performance", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course, group = s.create_course("Synthetic course"), s.create_group("Synthetic 30x20")
    offering = s.create_offering(term.id, course.id, group.id)
    queries = []

    def capture(_conn, _cursor, statement, *_):
        queries.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", capture)
    s.build_report(ReportKind.GROUP, offering.id)
    small_count = len(queries)
    event.remove(runtime._engine, "before_cursor_execute", capture)

    def meta():
        return EntityMetadata.create(instant())

    with s._transaction() as r:
        students = [e.Student(metadata=meta(), full_name=f"Synthetic {i:02}") for i in range(30)]
        enrollments = [
            e.Enrollment(
                metadata=meta(),
                student_id=student.id,
                offering_id=offering.id,
                enrolled_at=instant(),
            )
            for student in students
        ]
        assessments = [
            e.Assessment(
                metadata=meta(),
                offering_id=offering.id,
                type=AssessmentType.TEST,
                title=f"Synthetic {i:02}",
                issued_at=instant(),
            )
            for i in range(20)
        ]
        lessons = [
            e.Lesson(
                metadata=meta(),
                course_offering_id=offering.id,
                lesson_date=LocalDate(2026, 9, i + 1),
            )
            for i in range(15)
        ]
        for name, values in (
            ("students", students),
            ("enrollments", enrollments),
            ("assessments", assessments),
            ("lessons", lessons),
        ):
            for value in values:
                getattr(r, name).insert(value)
        for assessment in assessments:
            item = e.AssessmentItem(
                metadata=meta(), assessment_id=assessment.id, title="Synthetic item"
            )
            r.items.insert(item)
            for student in students:
                work = e.StudentWork(
                    metadata=meta(), student_id=student.id, assessment_id=assessment.id
                )
                r.works.insert(work)
                for number, result in enumerate(
                    (AttemptResult.NEEDS_REVISION, AttemptResult.ACCEPTED), 1
                ):
                    attempt = e.Attempt(
                        metadata=meta(),
                        student_work_id=work.id,
                        attempt_no=number,
                        occurred_at=instant(number),
                        result=result,
                    )
                    r.attempts.append(attempt)
                    r.item_results.insert(
                        AttemptItemResult(
                            metadata=meta(),
                            attempt_id=attempt.id,
                            assessment_item_id=item.id,
                            outcome=ItemOutcome.CORRECT,
                        )
                    )
        for lesson in lessons:
            for enrollment in enrollments:
                r.attendance.insert(
                    e.Attendance(
                        metadata=meta(),
                        lesson_id=lesson.id,
                        enrollment_id=enrollment.id,
                        status=AttendanceStatus.PRESENT,
                    )
                )
    queries.clear()
    event.listen(runtime._engine, "before_cursor_execute", capture)
    try:
        report = s.build_report(ReportKind.GROUP, offering.id)
    finally:
        event.remove(runtime._engine, "before_cursor_execute", capture)
    # Six fixed bulk reads cover submission/review, plan and review-grade facts.
    assert len(queries) == small_count <= 34
    assert all(q.lstrip().upper().startswith("SELECT") for q in queries)
    assert len(section(report, "students").rows) == 30
    assert len(section(report, "works").rows) == 600
    assert len(section(report, "items").rows) == 1200
    assert section(report, "attendance_total").rows[0] == (15, 450, 0, 0, 0, 0, 0)
