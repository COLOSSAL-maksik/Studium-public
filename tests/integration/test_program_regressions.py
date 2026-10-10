from datetime import UTC, datetime
from time import perf_counter

import pytest
from sqlalchemy import event

from studium.application.errors import ApplicationError
from studium.domain.content import GenerationCriteria
from studium.domain.enums import AssessmentType, AttemptResult, ItemOutcome
from studium.domain.value_objects import AcademicWeekNumber, UtcInstant
from tests.integration.test_application import runtime as runtime
from tests.integration.test_content_workflow import content as content


def test_knowledge_manual_generalization_many_sources_and_scope(content):
    s, _, course, offering, students = content
    at = s._clock()
    case = s.create_question_case(
        students[0].id, "Original private question", at, course_offering_id=offering.id
    )
    other = s.create_question_case(
        students[1].id, "Another original question", at, course_offering_id=offering.id
    )
    entry = s.create_knowledge_from_case(
        case.id, "General question", answer="Manual generalized answer"
    )
    assert entry.draft and all(v.full_name not in entry.title + entry.answer for v in students)
    s.link_knowledge_case(entry.id, other.id)
    s.link_knowledge_case(entry.id, other.id)
    assert s.knowledge_occurrences(entry.id).count == 2
    assert s._r.messages.for_case(case.id)[0].body == "Original private question"
    foreign = s.create_course("Foreign")
    group = s.create_group("FOREIGN")
    foreign_offering = s.create_offering(offering.term_id, foreign.id, group.id)
    foreign_case = s.create_question_case(
        students[0].id, "Foreign question", at, course_offering_id=foreign_offering.id
    )
    with pytest.raises(ApplicationError):
        s.link_knowledge_case(entry.id, foreign_case.id)
    material = s.create_material("methodical", course_id=course.id, title="Methodical note")
    s.set_content_links("knowledge_materials", entry.id, (material.id,))
    assert s.content_targets("knowledge_materials", entry.id) == (material,)


def test_module_progress_radial_weekly_same_metric_and_as_of(content):
    s, _, course, offering, students = content
    program = s.program_for_offering(offering.id)
    first = s.create_program_module(program.id, "First", 1, 6)
    second = s.create_program_module(program.id, "Second", 7, 12)
    links = []
    for module, week in ((first, 2), (second, 7)):
        definition = s.create_work_definition(course.id, module.title)
        links.append(
            s.add_program_work(
                program.id,
                definition.id,
                module_id=module.id,
                planned_issue_week=AcademicWeekNumber(1),
                planned_due_week=AcademicWeekNumber(week),
            )
        )
    assessments = [s.issue_program_work(offering.id, link.id) for link in links]
    s._clock = lambda: UtcInstant(datetime(2026, 9, 12, tzinfo=UTC))
    s.record_attempt(
        students[0].id, assessments[0].id, occurred_at=s._clock(), result=AttemptResult.ACCEPTED
    )
    data = s.progress_chart_data(offering.id, module_id=first.id)
    assert len(data.students) == 20 and len(data.weeks) == 17
    assert data.students[0].progress == 1 and data.average == 0.05
    assert data.weeks[0].progress == 0 and data.weeks[1].progress == 0.05
    assert all(point.progress is None for point in data.weeks[2:])
    assert s.group_analytics(offering.id, module_id=second.id).assessments_completed == 0
    assert (
        s.progress_chart_data(
            offering.id, module_id=first.id, as_of=UtcInstant(datetime(2026, 9, 5, tzinfo=UTC))
        ).average
        == 0
    )


def test_problem_taxonomy_filter_and_unlink(content):
    s, _, course, _, _ = content
    topic = s.create_topic(course.id, "Topic")
    skill = s.create_skill(course.id, "Skill")
    problem = s.create_material(
        "problems", course_id=course.id, title="Bank item", identifier="RK-001"
    )
    s.set_content_links("problem_topics", problem.id, (topic.id,))
    s.set_content_links("problem_skills", problem.id, (skill.id,))
    assert s.list_materials("problems", search="rk-001", topic_id=topic.id, skill_id=skill.id) == (
        problem,
    )
    s.set_content_links("problem_skills", problem.id, ())
    assert s.list_materials("problems", skill_id=skill.id) == ()
    s.set_content_links("problem_skills", problem.id, (skill.id,))
    assert s.content_targets("problem_skills", problem.id) == (skill,)


def test_saved_control_ticket_snapshots_applied_to_task_checking(content):
    s, _, course, offering, students = content
    skill = s.create_skill(course.id, "Shared skill")
    problems = []
    for i in range(20):
        problem = s.create_material(
            "problems", course_id=course.id, title=f"Task {i}", statement=f"Original {i}"
        )
        s.set_content_links("problem_skills", problem.id, (skill.id,))
        problems.append(problem)
    control = s.create_assessment(offering.id, "RK from tickets", AssessmentType.CONTROL_WORK)
    draft = s.generate_ticket_draft(GenerationCriteria(course.id, 20, 1))
    saved = s.save_ticket_set(offering.id, draft, assessment_id=control.id, assign_students=True)
    for problem in problems:
        s.update_material("problems", problem, statement="Changed after issue")
    assignments = s.apply_ticket_set_for_evaluation(saved.id)
    assert len(assignments) == 20
    assert all(v.statement_snapshot.startswith("Original") for v in assignments)
    assert all(s.assignment_skills(v) == (skill,) for v in assignments)
    assert s.apply_ticket_set_for_evaluation(saved.id) == assignments
    item = s.list_assessment_items(control.id)[0]
    attempt = s.record_attempt(
        students[0].id, control.id, occurred_at=s._clock(), result=AttemptResult.PRESENTED
    )
    s.create_attempt_item_result(
        attempt.id,
        item.id,
        outcome=ItemOutcome.CORRECT,
        skill_results=((skill.id, ItemOutcome.INCORRECT, "Factual error"),),
    )
    assert s.skill_outcome_counts(offering.id, students[0].id)[skill.id][ItemOutcome.INCORRECT] == 1


def test_manual_task_file_snapshot_survives_bank_detach_and_history_lock(content, tmp_path):
    s, _, course, offering, students = content
    problem = s.create_material(
        "problems", course_id=course.id, title="Manual task", statement="Original"
    )
    source = tmp_path / "synthetic-statement.txt"
    source.write_text("Immutable statement file", encoding="utf8")
    link = s.import_file_for_material("problems", problem.id, source)
    control = s.create_assessment(offering.id, "Manual RK", AssessmentType.CONTROL_WORK)
    item = s.add_control_problem(control.id, problem.id)
    other = s.create_assessment_item(control.id, "Other task")
    assignment = s.assign_student_problem(students[0].id, item.id, problem.id)
    files = s.assigned_task_files(assignment.id)
    assert len(files) == 1 and files[0].asset.id == link.file_asset_id
    s.detach_material_file("problems", link)
    assert s.assigned_task_files(assignment.id)[0].asset.id == link.file_asset_id
    with pytest.raises(ApplicationError, match="file_asset_in_use"):
        s.archive_file_asset(link.file_asset_id, expected_revision=1)
    s.record_attempt(
        students[0].id, control.id, occurred_at=s._clock(), result=AttemptResult.PRESENTED
    )
    with pytest.raises(ApplicationError, match="problem_assignment_has_snapshot"):
        s.assign_student_problem(students[0].id, other.id, problem.id)
    assert (
        s.accessible_file_path(link.file_asset_id).read_text("utf8") == "Immutable statement file"
    )


def test_journal_30_by_17_and_charts_fixed_query_budget(content, runtime):
    s, _, course, offering, students = content
    for i in range(10):
        students.append(s.create_student(offering.id, f"Synthetic extra {i}"))
    program = s.program_for_offering(offering.id)
    modules = [
        s.create_program_module(program.id, f"Module {i}", start, end, i)
        for i, (start, end) in enumerate(((1, 6), (7, 12), (13, 17)))
    ]
    for i, module in enumerate(modules):
        for type in (AssessmentType.HOMEWORK, AssessmentType.CONTROL_WORK):
            definition = s.create_work_definition(course.id, f"{type.value} {i}", type)
            link = s.add_program_work(
                program.id,
                definition.id,
                module_id=module.id,
                planned_due_week=AcademicWeekNumber(module.end_week),
            )
            assessment = s.issue_program_work(offering.id, link.id)
            item = (
                s.create_assessment_item(assessment.id, "Task")
                if type == AssessmentType.CONTROL_WORK
                else None
            )
            for student in students:
                attempt = s.record_attempt(
                    student.id, assessment.id, occurred_at=s._clock(), result=AttemptResult.ACCEPTED
                )
                if item:
                    s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    selects = []

    def count(c, cur, sql, params, ctx, many):
        if sql.lstrip().upper().startswith("SELECT"):
            selects.append(sql)

    event.listen(runtime._engine, "before_cursor_execute", count)
    try:
        began = perf_counter()
        journal = s.journal(offering.id)
        elapsed = perf_counter() - began
        journal_queries = len(selects)
        selects.clear()
        began = perf_counter()
        data = s.progress_chart_data(offering.id)
        chart_elapsed = perf_counter() - began
    finally:
        event.remove(runtime._engine, "before_cursor_execute", count)
    assert len(journal.matrix.roster) == 30 and len(journal.columns) == 23
    assert len(data.students) == 30 and len(data.weeks) == 17
    assert journal_queries <= 35 and len(selects) <= 25
    assert elapsed < 3 and chart_elapsed < 3
    print(
        f"Journal30x17+6: {elapsed:.4f}s/{journal_queries} SELECT; progress charts: {chart_elapsed:.4f}s/{len(selects)} SELECT"
    )
