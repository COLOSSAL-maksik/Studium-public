from datetime import UTC, datetime, timedelta
from time import perf_counter

import pytest
from sqlalchemy import event, text

from studium.application.errors import ApplicationError
from studium.domain.content import GenerationCriteria, MaterialFileRole
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, LessonType
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import AcademicWeekNumber, LocalDate, UtcInstant
from tests.integration.test_application import runtime as runtime


@pytest.fixture
def content(runtime):
    s = runtime.service
    s._clock = lambda: UtcInstant(datetime(2026, 9, 1, tzinfo=UTC))
    term = s.create_term("Synthetic", LocalDate(2026, 9, 1), LocalDate(2027, 1, 1))
    course = s.create_course("Synthetic course")
    group = s.create_group("TEST")
    offering = s.create_offering(term.id, course.id, group.id)
    students = [s.create_student(offering.id, f"Synthetic student {i:02}") for i in range(20)]
    return s, term, course, offering, students


@pytest.mark.parametrize("kind", ["homework", "problems", "seminars", "literature"])
def test_library_create_edit_tags_search_archive_files_and_reopen(content, tmp_path, kind):
    s, _, course, _, _ = content
    material = s.create_material(
        kind, course_id=course.id, title="Synthetic балки", tags=["Балки", "балки", "тест"]
    )
    assert material.tags == ("Балки", "тест")
    assert s.list_materials(kind, search="БАЛКИ", tags=["балки"]) == (material,)
    source = tmp_path / "synthetic.txt"
    source.write_text("Synthetic placeholder", encoding="utf8")
    link = s.import_file_for_material(kind, material.id, source)
    assert s.list_material_files(kind, material.id)[0].asset.id == link.file_asset_id
    assert s.accessible_file_path(link.file_asset_id).read_text("utf8") == "Synthetic placeholder"
    updated = s.update_material(kind, material, title="Edited", tags=["рамы"])
    assert s.get_material(kind, material.id) == updated
    with pytest.raises(RepositoryError):
        s.update_material(kind, material, title="Stale")
    with pytest.raises(ApplicationError, match="file_asset_in_use"):
        s.archive_file_asset(link.file_asset_id, expected_revision=1)
    s.archive_material(kind, updated)
    assert s.list_materials(kind) == ()
    assert s.list_material_files(kind, material.id)


def test_homework_assessment_is_independent_historical_fact(content):
    s, _, course, offering, students = content
    definition = s.create_material(
        "homework", course_id=course.id, title="ДЗ №3", description="Original statement"
    )
    assessment = s.create_assessment(
        offering.id,
        definition.title,
        AssessmentType.HOMEWORK,
        description=definition.description,
        homework_definition_id=definition.id,
        planned_issue_week=AcademicWeekNumber(1),
        planned_due_week=AcademicWeekNumber(3),
    )
    s.update_material("homework", definition, title="Edited", description="Edited")
    s.record_attempt(
        students[0].id, assessment.id, occurred_at=s._clock(), result=AttemptResult.PRESENTED
    )
    assert s.list_assessments(offering.id)[0].description == "Original statement"
    assert assessment.planned_due_week.value == 3
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        s.update_assessment(assessment, homework_definition_id=None)


@pytest.mark.parametrize(
    "actual_week,expected", [(1, "on_time_count"), (2, "on_time_count"), (3, "late_count")]
)
def test_first_submission_by_week(content, actual_week, expected):
    s, _, _, offering, students = content
    assessment = s.create_assessment(
        offering.id, "Week due", AssessmentType.HOMEWORK, planned_due_week=AcademicWeekNumber(2)
    )
    at = UtcInstant(datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=(actual_week - 1) * 7))
    s.record_attempt(students[0].id, assessment.id, occurred_at=at, result=AttemptResult.PRESENTED)
    summary = s.student_progress(students[0].id, offering.id, as_of=at)
    assert getattr(summary, expected) == 1 and summary.deadline_assessments_total == 1


def test_week_overdue_only_after_last_day_and_exact_deadline_priority(content):
    s, _, _, offering, students = content
    assessment = s.create_assessment(
        offering.id, "Week due", AssessmentType.HOMEWORK, planned_due_week=AcademicWeekNumber(2)
    )
    before = UtcInstant(datetime(2026, 9, 14, 20, 59, 59, tzinfo=UTC))
    after = UtcInstant(datetime(2026, 9, 14, 21, tzinfo=UTC))
    assert s.student_progress(students[0].id, offering.id, as_of=before).overdue_count == 0
    assert s.student_progress(students[0].id, offering.id, as_of=after).overdue_count == 1
    s.update_assessment(assessment, due_at=UtcInstant(datetime(2026, 10, 1, tzinfo=UTC)))
    assert s.student_progress(students[0].id, offering.id, as_of=after).overdue_count == 0


def test_planned_issue_and_legacy_without_weeks(content):
    s, _, _, offering, students = content
    s.create_assessment(
        offering.id, "Future", AssessmentType.HOMEWORK, planned_issue_week=AcademicWeekNumber(5)
    )
    legacy = s.create_assessment(offering.id, "Legacy", AssessmentType.HOMEWORK)
    summary = s.student_progress(students[0].id, offering.id)
    assert summary.assessments_total == 1 and summary.deadline_assessments_total == 0
    assert legacy.planned_due_week is None


@pytest.mark.parametrize("type", list(LessonType))
def test_seminar_and_lecture_attendance_same_mechanism(content, type):
    s, _, _, offering, students = content
    lesson = s.create_lesson(offering.id, LocalDate(2026, 9, 1), type=type)
    en = s.list_students_for_offering(offering.id)[0].enrollment
    s.mark_attendance(lesson.id, en.id, AttendanceStatus.PRESENT)
    result = s.workflow_analytics(offering.id, student_id=students[0].id)
    own = result.lectures if type == LessonType.LECTURE else result.seminars
    other = result.seminars if type == LessonType.LECTURE else result.lectures
    assert own.present == 1 and own.attendance_rate == 1 and other.attendance_rate is None
    assert s.student_progress(students[0].id, offering.id).attendance.present == 1


def test_seminar_topics_plans_week_and_filters(content):
    s, _, course, _, _ = content
    topic = s.create_topic(course.id, "Synthetic topic")
    material = s.create_material(
        "seminars",
        course_id=course.id,
        title="Plan",
        planned_week=AcademicWeekNumber(5),
        plan_text="Plan text",
        full_text="Markdown text",
        topic_ids=[topic.id],
    )
    assert s.seminar_topic_ids(material.id) == (topic.id,)
    assert s.list_materials("seminars", topic_id=topic.id, week=AcademicWeekNumber(5)) == (
        material,
    )
    material = s.update_material("seminars", material, topic_ids=[])
    s.update_material("seminars", material, topic_ids=[topic.id])
    assert s.seminar_topic_ids(material.id) == (topic.id,)


def test_problem_collections_many_to_many_and_course_guard(content):
    s, _, course, _, _ = content
    problem = s.create_material(
        "problems", course_id=course.id, title="Synthetic", correct_answer="Answer", tags=["балки"]
    )
    one = s.create_problem_collection(course.id, "как в ДЗ")
    two = s.create_problem_collection(course.id, "РК1")
    for collection in (one, two):
        s.set_problem_collection(collection.id, problem.id)
    assert set(s.problem_collection_ids(problem.id)) == {one.id, two.id}
    s.set_problem_collection(one.id, problem.id, included=False)
    s.set_problem_collection(one.id, problem.id)
    assert s.list_materials("problems", collection_id=one.id, tags=["балки"]) == (problem,)
    other = s.create_course("Other")
    invalid = s.create_problem_collection(other.id, "Other")
    with pytest.raises(ApplicationError, match="learning_course_mismatch"):
        s.set_problem_collection(invalid.id, problem.id)


@pytest.fixture
def pool(content):
    s, _, course, _, _ = content
    collection = s.create_problem_collection(course.id, "как в ДЗ")
    problems = []
    for i in range(25):
        p = s.create_material(
            "problems",
            course_id=course.id,
            title=f"Балки {i}",
            statement=f"Statement {i}",
            correct_answer="Teacher secret",
            solution="Solution secret",
            tags=["балки"],
        )
        s.set_problem_collection(collection.id, p.id)
        problems.append(p)
    return collection, problems


def test_twenty_variants_assign_replace_snapshot_and_no_answer_leak(content, pool, tmp_path):
    s, _, course, offering, students = content
    collection, problems = pool
    source = tmp_path / "diagram.txt"
    source.write_text("Synthetic diagram", encoding="utf8")
    reference = s.import_file_for_material(
        "problems", problems[0].id, source, role=MaterialFileRole.REFERENCE
    )
    statement = s.import_file_for_material("problems", problems[0].id, source)
    criteria = GenerationCriteria(course.id, 20, 1, ("балки",), collection.id, 7)
    draft = s.generate_ticket_draft(criteria)
    assert draft == s.generate_ticket_draft(criteria)
    used = {p.id for v in draft.variants for p in v}
    replacement = next(p for p in problems if p.id not in used)
    draft = s.replace_draft_problem(draft, 0, 0, replacement.id)
    saved = s.save_ticket_set(offering.id, draft, assign_students=True)
    before = s.ticket_set_details(saved.id)
    assert len(before) == 20 and sum(len(v.assignments) for v in before) == 20
    for p in problems:
        s.update_material("problems", p, statement="Edited", correct_answer="Edited answer")
    assert s.ticket_set_details(saved.id) == before
    for view in before:
        output = s.student_ticket_content(view.ticket.id)
        assert not hasattr(output[0], "correct_answer")
        assert "secret" not in str(output)
        if view.problems[0].problem_id == problems[0].id:
            assert reference.file_asset_id not in output[0].file_asset_ids
            assert statement.file_asset_id in output[0].file_asset_ids
    first = before[0].assignments[0]
    changed = s.assign_ticket(saved.id, first.enrollment_id, before[1].ticket.id, original=first)
    assert changed.ticket_id == before[1].ticket.id
    s.unassign_ticket(changed)
    archived = s._r.ticket_assignments.find_pair(saved.id, changed.enrollment_id)
    assert (
        s.assign_ticket(
            saved.id, changed.enrollment_id, before[2].ticket.id, original=archived
        ).deleted_at
        is None
    )


def test_unsaved_problem_change_rejected_atomically(content, pool):
    s, _, course, offering, _ = content
    draft = s.generate_ticket_draft(GenerationCriteria(course.id, 2))
    s.update_material("problems", draft.variants[-1][0], statement="Changed after review")
    with pytest.raises(RepositoryError):
        s.save_ticket_set(offering.id, draft)
    assert s.list_ticket_sets(offering.id) == ()


def test_empty_unassigned_set_and_insufficient_pool(content, pool):
    s, _, course, offering, _ = content
    with pytest.raises(ApplicationError, match="insufficient_problem_pool"):
        s.generate_ticket_draft(GenerationCriteria(course.id, 30, 1))
    draft = s.generate_ticket_draft(GenerationCriteria(course.id, 3, 2))
    saved = s.save_ticket_set(offering.id, draft)
    assert all(not v.assignments for v in s.ticket_set_details(saved.id))
    with pytest.raises(ApplicationError, match="variant_roster_count_mismatch"):
        s.save_ticket_set(offering.id, draft, assign_students=True)


@pytest.mark.parametrize("kind", ["homework", "problems", "seminars", "literature"])
def test_raw_content_constraints_and_revision_identity(content, runtime, kind):
    s, _, course, _, _ = content
    material = s.create_material(kind, course_id=course.id, title="Synthetic")
    table = {
        "homework": "homework_definitions",
        "problems": "problems",
        "seminars": "seminar_materials",
        "literature": "literature_items",
    }[kind]
    for expression in ["title=''", "tags_json='[2]'", "revision=revision+2", "id='bad'"]:
        with pytest.raises(Exception), runtime._engine.begin() as connection:
            connection.execute(
                text(f"UPDATE {table} SET {expression}, updated_at=updated_at+1 WHERE id=:id"),
                {"id": str(material.id)},
            )
    assert s.get_material(kind, material.id) == material


def test_problem_bank_1000_and_30_students_performance(content, runtime):
    s, _, course, offering, _ = content
    for i in range(20, 30):
        s.create_student(offering.id, f"Synthetic student {i}")
    collections = [s.create_problem_collection(course.id, f"Collection {i}") for i in range(3)]
    with s._transaction() as r:
        from studium.domain.content import Problem, ProblemCollectionMember, tag_document

        for i in range(1000):
            p = Problem(
                metadata=s._meta(),
                course_id=course.id,
                title=f"Synthetic problem {i}",
                tags_json=tag_document(["балки" if i % 2 else "рамы", "тест"]),
            )
            r.problems.insert(p)
            for collection in collections[: 1 + i % 3]:
                r.problem_collection_members.insert(
                    ProblemCollectionMember(
                        metadata=s._meta(), collection_id=collection.id, problem_id=p.id
                    )
                )
    selects = []

    def count(_conn, _cursor, statement, *_):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", count)
    start = perf_counter()
    rows = s.list_materials(
        "problems", course_id=course.id, tags=["балки"], collection_id=collections[0].id
    )
    filtered = perf_counter() - start
    filter_selects = len(selects)
    selects.clear()
    start = perf_counter()
    draft = s.generate_ticket_draft(
        GenerationCriteria(course.id, 30, 3, ("балки",), collections[0].id, 23)
    )
    generated = perf_counter() - start
    event.remove(runtime._engine, "before_cursor_execute", count)
    print(
        f"1000 Problems: filter {filtered:.4f}s/{filter_selects} SELECT; generation30 {generated:.4f}s/{len(selects)} SELECT"
    )
    assert len(rows) == 500 and len(draft.variants) == 30
    # Query count checks N+1 independently of competing builds/Windows IO.
    # Wall-clock measurements are reported separately from correctness tests.
    assert filter_selects == 2 and len(selects) == 3
