from dataclasses import replace

import pytest

from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, ItemOutcome
from studium.domain.value_objects import AcademicWeekNumber, LocalDate
from tests.integration.test_application import runtime as runtime
from tests.integration.test_content_workflow import content as content


def test_multiple_programs_exact_context_and_reusable_work(content):
    s, term, course, offering, _ = content
    a = s.program_for_offering(offering.id)
    b = s.create_work_program(
        course.id, term.id, "Other direction", term.starts_on, direction="Э", weeks=17
    )
    group = s.create_group("TEST-B", faculty="Full faculty", faculty_short="МТ")
    other = s.create_offering(term.id, course.id, group.id, b.id)
    assert other.work_program_id == b.id
    assert s._r.groups.find_by_id(group.id).faculty_short == "МТ"
    definition = s.create_work_definition(course.id, "Reusable RK", AssessmentType.CONTROL_WORK)
    first = s.add_program_work(a.id, definition.id, planned_due_week=AcademicWeekNumber(6))
    second = s.add_program_work(b.id, definition.id, planned_due_week=AcademicWeekNumber(12))
    assert first.definition_id == second.definition_id
    assert s.planned_works(offering.id)[0].link.id == first.id
    assert s.planned_works(other.id)[0].link.id == second.id
    foreign = s.create_course("Foreign")
    foreign_work = s.create_work_definition(foreign.id, "Foreign work")
    with pytest.raises(Exception):
        s.add_program_work(a.id, foreign_work.id)
    with pytest.raises(Exception):
        s.create_offering(term.id, foreign.id, group.id, b.id)


def test_module_bounds_overlap_and_work_date(content):
    s, _, course, offering, _ = content
    program = s.program_for_offering(offering.id)
    module = s.create_program_module(program.id, "Module 1", 1, 6)
    with pytest.raises(Exception):
        s.create_program_module(program.id, "Overlap", 6, 12)
    with pytest.raises(ValueError):
        s.create_program_module(program.id, "Overflow", 13, 18)
    work = s.create_work_definition(course.id, "HW")
    link = s.add_program_work(
        program.id,
        work.id,
        module_id=module.id,
        planned_due_week=AcademicWeekNumber(6),
        due_date=LocalDate(2026, 10, 6),
    )
    with pytest.raises(ValueError):
        s.update_program_work(link, planned_due_week=AcademicWeekNumber(5))
    with pytest.raises(Exception):
        s.update_work_program(program, weeks=5)


def test_planned_structure_creates_no_fake_attempts_and_issue_is_idempotent(content):
    s, _, course, offering, students = content
    program = s.program_for_offering(offering.id)
    definition = s.create_work_definition(course.id, "Planned HW")
    link = s.add_program_work(program.id, definition.id, planned_due_week=AcademicWeekNumber(3))
    assert s.planned_works(offering.id)[0].assessment is None
    assert s._r.attempts.list() == []
    assessment = s.issue_program_work(offering.id, link.id)
    assert s.issue_program_work(offering.id, link.id) == assessment
    assert s._r.attempts.list() == []
    for result in (
        AttemptResult.PRESENTED,
        AttemptResult.NEEDS_REVISION,
        AttemptResult.PRESENTED,
        AttemptResult.NEEDS_REVISION,
        AttemptResult.ACCEPTED,
    ):
        s.record_attempt(students[0].id, assessment.id, occurred_at=s._clock(), result=result)
    assert s.matrix(offering.id).cells[students[0].id, assessment.id].progress.attempt_count == 5
    work = s.get_or_create_work(students[0].id, assessment.id)
    assert [a.attempt.attempt_no for a in s.history(work.id).entries] == [1, 2, 3, 4, 5]
    with pytest.raises(Exception):
        s.record_attempt(
            students[0].id, assessment.id, occurred_at=s._clock(), result=AttemptResult.REJECTED
        )
    assert len(s.history(work.id).entries) == 5


def test_shared_homework_pack_keeps_one_asset(content, tmp_path):
    s, _, course, _, _ = content
    pack = s.create_material("packs", course_id=course.id, title="Semester homework")
    source = tmp_path / "synthetic.txt"
    source.write_text("Synthetic shared contents", encoding="utf8")
    attachment = s.import_file_for_material("packs", pack.id, source)
    works = [s.create_work_definition(course.id, f"HW {i}") for i in range(3)]
    s.set_content_links("homework_pack_works", pack.id, [w.id for w in works])
    assert {s.homework_files(w.id)[0].asset.id for w in works} == {attachment.file_asset_id}
    assert len(s._r.file_assets.list()) == 1
    with pytest.raises(Exception):
        s.archive_file_asset(attachment.file_asset_id, expected_revision=1)


def test_cancelled_lesson_excluded_transfer_keeps_planned_date(content):
    s, _, _, offering, students = content
    lesson = s.create_lesson(offering.id, LocalDate(2026, 9, 1), planned_week=AcademicWeekNumber(1))
    s.mark_attendance(
        lesson.id,
        s.list_students_for_offering(offering.id)[0].enrollment.id,
        AttendanceStatus.ABSENT,
    )
    assert s.group_analytics(offering.id).attendance.absent == 1
    lesson = s.cancel_lesson(lesson, "Holiday")
    assert s.group_analytics(offering.id).attendance.lessons_total == 0
    lesson = s.transfer_lesson(lesson, LocalDate(2026, 9, 9))
    assert lesson.planned_date == LocalDate(2026, 9, 1)
    assert lesson.planned_week == AcademicWeekNumber(1)
    assert s.workflow_analytics(offering.id).weeks[1].seminar_attendance.absent == 1
    assert len(s.workflow_analytics(offering.id).weeks) == 17


def test_fresh_reopen_schema_and_metadata_match(content):
    s, *_ = content
    with s._transaction() as r:
        assert len(r.work_programs.list()) == 1


def test_control_bank_links_student_snapshot_and_skill_outcomes(content):
    s, _, course, offering, students = content
    skill = s.create_skill(course.id, "Synthetic skill")
    problem = s.create_material(
        "problems",
        course_id=course.id,
        title="Task",
        identifier="RK-001",
        statement="Original statement",
    )
    s.set_content_links("problem_skills", problem.id, [skill.id])
    assessment = s.create_assessment(offering.id, "RK", AssessmentType.CONTROL_WORK)
    item = s.add_control_problem(assessment.id, problem.id)
    assert s.learning_targets("item_skills", item.id)[0].id == skill.id
    assignment = s.assign_student_problem(students[0].id, item.id, problem.id)
    s.update_material("problems", problem, statement="Edited statement")
    assert (
        s.list_student_problem_assignments(assignment.student_work_id)[0].statement_snapshot
        == "Original statement"
    )
    attempt = s.record_attempt(
        students[0].id, assessment.id, occurred_at=s._clock(), result=AttemptResult.PRESENTED
    )
    result = s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    fact = s.record_item_skill_result(result.id, skill.id, ItemOutcome.INCORRECT)
    assert s.skill_outcome_counts(offering.id)[skill.id][ItemOutcome.INCORRECT] == 1
    with pytest.raises(Exception):
        s._r.attempt_skill_results.update(
            replace(fact, metadata=fact.metadata.touch(s._clock()), outcome=ItemOutcome.CORRECT),
            expected_revision=1,
        )
