"""Real multi-group evidence, immutable bytes, read budgets and period debts."""

from datetime import date, timedelta
from hashlib import sha256

from sqlalchemy import event

from studium.domain.enums import AssessmentType, AttemptResult, StudentWorkStatus
from studium.domain.value_objects import LocalDate, UtcInstant
from tests.integration.test_application import runtime as runtime


def test_all_package_two_groups_sixty_students_120_submissions_300_files(runtime, tmp_path):
    s = runtime.service
    first = s.create_term("Synthetic T1", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    second = s.create_term("Synthetic T2", LocalDate(2027, 2, 1), LocalDate(2027, 6, 30))
    course = s.create_course("Synthetic course A")
    other_course = s.create_course("Synthetic course B")
    direction = s.create_direction(" 15.15.03 ", "Synthetic direction")
    version = s.create_course_program(
        course.id,
        "Two-period course",
        direction_ids=[direction.id],
        content={
            "modules": [
                {
                    "key": "M1",
                    "title": "T1 M1",
                    "course_semester": 1,
                    "start_week": 1,
                    "end_week": 6,
                },
                {
                    "key": "M2",
                    "title": "T2 M1",
                    "course_semester": 2,
                    "start_week": 1,
                    "end_week": 6,
                },
            ]
        },
    )
    groups = [s.create_group(f"Synthetic-{i}") for i in range(2)]
    offerings = [
        s.create_offering(
            first.id, course.id, group.id, course_version_id=version.id, course_semester=1
        )
        for group in groups
    ]
    next_offering = s.create_offering(
        second.id, course.id, groups[0].id, course_version_id=version.id, course_semester=2
    )
    s.create_offering(first.id, other_course.id, groups[1].id)
    assert s.semester_plan(next_offering.id).modules[0].title == "T2 M1"
    s.set_fractional_scores_enabled(True)
    assessments, students, modules = {}, {}, {}
    for offering in offerings:
        plan = s.semester_plan(offering.id)
        preview = s.preview_plan_change(offering.id, plan_values={"weeks": 18})
        s.apply_plan_change(preview)
        modules[offering.id] = plan.modules[0]
        works = []
        for index in range(36):
            # Explicit dates cover 18 weeks; no automatic shift of neighbouring work.
            due = date(2026, 9, 1) + timedelta(weeks=index // 2, days=5)
            work = s.add_planned_work(
                offering.id,
                f"Synthetic work {index + 1}",
                AssessmentType.HOMEWORK if index % 2 == 0 else AssessmentType.CONTROL_WORK,
                module_id=plan.modules[0].id if index < 12 else None,
                due_date=LocalDate(due.year, due.month, due.day),
                minimum="18,25",
                maximum="30",
                number=str(index + 1),
            )
            works.append(s.issue_planned_work(work.id))
        assessments[offering.id] = works
        students[offering.id] = [
            s.create_student(offering.id, f"Synthetic student {offering.id.value[:4]} {i:02d}")
            for i in range(30)
        ]
    source = [tmp_path / "original.docx", tmp_path / "original.pdf", tmp_path / "teacher.docx"]
    for i, path in enumerate(source):
        path.write_bytes(f"Synthetic immutable bytes {i}".encode())
    digest = {path: sha256(path.read_bytes()).hexdigest() for path in source}
    now = UtcInstant.now()
    submitted = []
    for offering in offerings:
        for i, student in enumerate(students[offering.id]):
            required = []
            for assessment in assessments[offering.id][:2]:
                submission = s.register_student_submission(
                    student.id,
                    assessment.id,
                    UtcInstant(now.value - timedelta(days=10, minutes=i)),
                    paths=source[:2],
                )
                work = s._r.works.find_for_student(student.id, assessment.id)
                required.append(work.id)
                submitted.append((student, work, submission))
            s.set_required_works(
                modules[offering.id].id, student.id, required, reason="Explicit two-work set"
            )
    for index, (_, _, sub) in enumerate(submitted[:60]):
        s.review_submission(
            sub.id,
            AttemptResult.ACCEPTED if index % 2 == 0 else AttemptResult.SCORED,
            score="24,75",
            reviewed_at=now,
            paths=source[2:],
        )
    assert len(s._r.submissions.list()) == 120
    assert len(s._r.attempts.list()) == 120
    assert len(s._r.reviews.list()) == 60
    assert len(s._r.file_assets.list()) == 300
    queries = []

    def counted(conn, cursor, statement, params, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", counted)
    try:
        queue = s.review_queue(now=now)
        count = len(queries)
        assert count <= 15
        assert len(queue) == 60 and all(row.state == "overdue" for row in queue)
        assert [row.submission.received_at for row in queue] == sorted(
            row.submission.received_at for row in queue
        )
        queries.clear()
        all_rows = s.review_queue(now=now, include_reviewed=True)
        assert len(all_rows) == 120 and len(queries) == count
    finally:
        event.remove(runtime._engine, "before_cursor_execute", counted)
    student, work, sub = submitted[0]
    rows, _ = s.student_package_summary(student.id)
    assert sum(row[3] for row in rows) == 2 and sum(row[4] for row in rows) == 1
    assert s.student_module_results(student.id)[0].state == "open"
    s.enroll_student(next_offering.id, student.id)
    enrollment = next(
        row.enrollment
        for row in s.list_students_for_offering(offerings[0].id)
        if row.student.id == student.id
    )
    s.withdraw_student(enrollment)
    ended = s._r.enrollments.find_by_id(enrollment.id)
    future = UtcInstant(now.value + timedelta(days=400))
    s._clock = lambda: future
    debt = submitted[1][1]
    resub = s.register_submission(debt.id, UtcInstant(future.value - timedelta(days=1)))
    review = s.review_submission(resub.id, AttemptResult.ACCEPTED, score="24,75")
    s.record_review_return(review.id, future)
    assert s.student_module_results(student.id)[0].state == "closed"
    assert s._r.enrollments.find_by_id(enrollment.id) == ended
    assert s._r.assessments.find_by_id(debt.assessment_id).offering_id == offerings[0].id
    s.set_fractional_scores_enabled(False)
    assert s.work_result(debt.id).score == 2475
    assert s.work_result(debt.id).status == StudentWorkStatus.ACCEPTED
    assert all(sha256(path.read_bytes()).hexdigest() == digest[path] for path in source)
    for asset in s._r.file_assets.list():
        assert sha256(s._file_storage.path(asset).read_bytes()).hexdigest() == asset.sha256
    with runtime._engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
