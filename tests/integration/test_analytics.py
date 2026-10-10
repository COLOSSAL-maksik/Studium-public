"""Fact-derived metrics, explicit denominators, distinct evidence and bulk queries."""

from dataclasses import FrozenInstanceError, asdict
from datetime import UTC, datetime, timedelta, timezone
from time import perf_counter
from types import SimpleNamespace

import pytest
from sqlalchemy import event, text

from studium.application.analytics import calendar_days_late
from studium.application.errors import ApplicationError
from studium.domain import entities as e
from studium.domain.analytics_facts import AttemptItemResult
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, ItemOutcome
from studium.domain.services import StudentWorkProgress
from studium.domain.value_objects import EntityMetadata, LocalDate, UtcInstant
from tests.integration.test_application import runtime as runtime
from tests.unit.test_domain import instant


@pytest.fixture
def analytics_workflow(runtime):
    service = runtime.service
    service._clock = lambda: instant()
    term = service.create_term("Synthetic term", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = service.create_course("Synthetic course")
    group = service.create_group("SYNTHETIC")
    offering = service.create_offering(term.id, course.id, group.id)
    student = service.create_student(offering.id, "Synthetic Student")
    assessment = service.create_assessment(
        offering.id,
        "Synthetic assessment",
        AssessmentType.CONTROL_WORK,
        issued_at=instant(),
        due_at=instant(2),
        max_score=10,
    )
    work = service.get_or_create_work(student.id, assessment.id)
    service._clock = lambda: instant(10)
    return SimpleNamespace(
        s=service,
        term=term,
        course=course,
        group=group,
        offering=offering,
        student=student,
        assessment=assessment,
        work=work,
    )


def new_assessment(w, title="Other", *, due_at=None):
    return w.s.create_assessment(
        w.offering.id,
        title,
        AssessmentType.HOMEWORK,
        issued_at=instant(),
        due_at=due_at,
        max_score=10,
    )


def test_student_zero_completion_and_missing_values_are_distinct(analytics_workflow):
    w = analytics_workflow
    summary = w.s.student_progress(w.student.id, w.offering.id)
    assert summary.assessments_total == 1 and summary.assessments_started == 0
    assert summary.assessments_completed == 0 and summary.completion_rate == 0
    assert summary.first_pass_rate is None and summary.average_attempts_per_started_work is None
    assert summary.on_time_rate is None and summary.average_normalized_score is None
    assert summary.overdue_count == 1 and summary.attendance.attendance_rate is None
    assert summary.questions.average_teacher_response_seconds is None


def test_empty_offering_all_rates_are_not_applicable(analytics_workflow):
    w = analytics_workflow
    other_group = w.s.create_group("EMPTY")
    other = w.s.create_offering(w.term.id, w.course.id, other_group.id)
    result = w.s.group_analytics(other.id)
    assert result.student_count == 0 and result.assessments_total == 0
    assert result.average_completion_rate is None and result.first_pass_rate is None
    assert result.average_attempts is None and result.completion_distribution == ()


def test_student_context_without_enrollment_has_no_invented_assignments(analytics_workflow):
    w = analytics_workflow
    other_group = w.s.create_group("OTHER")
    other_offering = w.s.create_offering(w.term.id, w.course.id, other_group.id)
    outsider = w.s.create_student(other_offering.id, "Synthetic outsider")
    w.s.create_question_case(
        outsider.id, "Question without membership", instant(3), course_offering_id=w.offering.id
    )
    summary = w.s.student_progress(outsider.id, w.offering.id)
    assert summary.assessments_total == summary.overdue_count == summary.attempts_total == 0
    assert summary.completion_rate is None and summary.first_pass_rate is None
    assert summary.attendance.lessons_total == 0
    assert summary.questions.question_cases_count == 1


def test_student_cutoff_before_enrollment_does_not_invent_overdue_work(analytics_workflow):
    w = analytics_workflow
    w.s._clock = lambda: instant(5)
    student = w.s.create_student(w.offering.id, "Synthetic later enrollment")
    before = w.s.student_progress(student.id, w.offering.id, as_of=instant(3))
    after = w.s.student_progress(student.id, w.offering.id, as_of=instant(6))
    assert before.assessments_total == before.overdue_count == 0
    assert before.completion_rate is None
    assert after.assessments_total == after.overdue_count == 1


def test_student_former_enrollment_preserves_personal_progress(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    enrollment = w.s.list_students_for_offering(w.offering.id)[0].enrollment
    w.s.withdraw_student(enrollment)
    assert w.s.group_analytics(w.offering.id).student_count == 0
    summary = w.s.student_progress(w.student.id, w.offering.id)
    assert summary.assessments_total == summary.assessments_completed == 1
    assert summary.completion_rate == 1


def test_completion_projection_average_attempts_and_no_score_inference(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.NEEDS_REVISION, score=3, max_score=10)
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.ACCEPTED, score=7, max_score=10)
    w.s.add_attempt(w.work.id, instant(4), AttemptResult.COMMENT_ONLY, score=0, max_score=10)
    other = new_assessment(w)
    other_work = w.s.get_or_create_work(w.student.id, other.id)
    w.s.add_attempt(other_work.id, instant(3), AttemptResult.SCORED, score=1, max_score=2)
    summary = w.s.student_progress(w.student.id, w.offering.id)
    assert summary.assessments_started == 2 and summary.assessments_completed == 1
    assert summary.completion_rate == 0.5 and summary.passed_count == 1
    assert summary.attempts_total == 4 and summary.average_attempts_per_started_work == 2
    assert summary.first_pass_count == 0 and summary.first_pass_rate == 0
    assert summary.average_normalized_score == pytest.approx(0.6)
    assert w.s.history(w.work.id).progress == StudentWorkProgress.from_history(
        w.work.id, [entry.attempt for entry in w.s.history(w.work.id).entries]
    )


@pytest.mark.parametrize("neutral", [AttemptResult.COMMENT_ONLY, AttemptResult.REJECTED])
def test_comment_is_annotation_but_rejected_breaks_first_pass(analytics_workflow, neutral):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), neutral)
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.ACCEPTED)
    result = w.s.student_progress(w.student.id, w.offering.id)
    assert result.first_pass_count == (neutral == AttemptResult.COMMENT_ONLY)
    assert result.attempts_total == 2 and result.average_attempts_per_started_work == 2
    assert result.on_time_count == (neutral == AttemptResult.REJECTED)
    assert result.late_count == (neutral == AttemptResult.COMMENT_ONLY)


def test_rejected_only_is_started_without_rewriting_progress(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.REJECTED)
    result = w.s.assessment_analytics(w.assessment.id)
    assert result.started == 1 and result.in_progress == 1 and result.not_started == 0
    assert w.s.history(w.work.id).progress.status.value == "NOT_STARTED"


def test_deadline_min_timestamp_not_attempt_number_and_denominator(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.NEEDS_REVISION)
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    late = new_assessment(w, "Late", due_at=instant(2))
    w.s.add_attempt(
        w.s.get_or_create_work(w.student.id, late.id).id, instant(3), AttemptResult.ACCEPTED
    )
    new_assessment(w, "Overdue", due_at=instant(2))
    new_assessment(w, "Future", due_at=instant(20))
    no_deadline = new_assessment(w)
    w.s.add_attempt(
        w.s.get_or_create_work(w.student.id, no_deadline.id).id, instant(8), AttemptResult.ACCEPTED
    )
    result = w.s.student_progress(w.student.id, w.offering.id)
    assert (result.on_time_count, result.late_count, result.overdue_count) == (1, 1, 1)
    assert result.on_time_rate == 0.5


def test_exact_deadline_is_timely_and_exact_now_not_overdue(analytics_workflow):
    w = analytics_workflow
    assert w.s.student_progress(w.student.id, w.offering.id, as_of=instant(2)).overdue_count == 0
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.PRESENTED)
    assert w.s.student_progress(w.student.id, w.offering.id).on_time_count == 1


def test_no_deadline_is_not_applicable_but_future_deadline_has_missing_data(analytics_workflow):
    w = analytics_workflow
    without_due = new_assessment(w, "No deadline")
    future_due = new_assessment(w, "Future deadline", due_at=instant(20))
    no_due = w.s.assessment_analytics(without_due.id)
    future = w.s.assessment_analytics(future_due.id)
    assert no_due.deadline_assessments_total == 0 and no_due.on_time_rate is None
    assert future.deadline_assessments_total == 1 and future.on_time_rate is None
    assert future.overdue_count == 0
    assert w.s.student_progress(w.student.id, w.offering.id).deadline_assessments_total == 2
    assert w.s.group_analytics(w.offering.id).deadline_assessments_total == 2


def test_scores_use_current_projection_and_attempt_maximum(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED, score=5, max_score=20)
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.REJECTED, score=0, max_score=10)
    assert w.s.student_progress(w.student.id, w.offering.id).average_normalized_score == 0.25
    w.s.add_attempt(w.work.id, instant(4), AttemptResult.PRESENTED)
    assert w.s.student_progress(w.student.id, w.offering.id).average_normalized_score is None


def test_score_without_recorded_maximum_is_not_normalized(analytics_workflow):
    w = analytics_workflow
    # Application's default maximum is intentionally bypassed to test valid old facts.
    with w.s._transaction() as repositories:
        repositories.attempts.append(
            e.Attempt(
                metadata=w.s._meta(),
                student_work_id=w.work.id,
                attempt_no=1,
                occurred_at=instant(2),
                result=AttemptResult.SCORED,
                score=4,
            )
        )
    assert w.s.student_progress(w.student.id, w.offering.id).average_normalized_score is None


def test_attendance_denominator_unknown_excused_and_unmarked(analytics_workflow):
    w = analytics_workflow
    enrollment = w.s.list_students_for_offering(w.offering.id)[0].enrollment
    for index, status in enumerate(AttendanceStatus):
        lesson = w.s.create_lesson(w.offering.id, LocalDate(2026, 10, index + 1))
        w.s.mark_attendance(lesson.id, enrollment.id, status)
    w.s.create_lesson(w.offering.id, LocalDate(2026, 10, 6))
    result = w.s.student_progress(w.student.id, w.offering.id).attendance
    assert result.lessons_total == 6
    assert (
        result.present,
        result.absent,
        result.late,
        result.excused,
        result.unknown,
        result.unmarked,
    ) == (1, 1, 1, 1, 1, 1)
    assert result.attendance_rate == pytest.approx(2 / 3)


def test_attendance_repeated_membership_not_counted_twice(analytics_workflow):
    w = analytics_workflow
    enrollment = w.s.list_students_for_offering(w.offering.id)[0].enrollment
    lesson = w.s.create_lesson(w.offering.id, LocalDate(2026, 10, 2))
    w.s.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.PRESENT)
    w.s.withdraw_student(enrollment)
    w.s._clock = lambda: instant(11)
    w.s.enroll_student(w.offering.id, w.student.id)
    assert w.s.student_progress(w.student.id, w.offering.id).attendance.present == 1
    assert w.s.group_analytics(w.offering.id).student_count == 1


def test_question_state_message_counts_and_response_episodes(analytics_workflow):
    w = analytics_workflow
    case = w.s.create_question_case(
        w.student.id, "First", instant(2), course_offering_id=w.offering.id
    )
    w.s.add_student_message(case.id, "Clarification", instant(3))
    w.s.add_teacher_message(case.id, "Response", instant(4))
    w.s.add_teacher_message(case.id, "Another response", instant(5))
    w.s.add_student_message(case.id, "Unanswered", instant(6))
    result = w.s.question_analytics(offering_id=w.offering.id)
    assert (
        result.question_cases_count,
        result.open_questions,
        result.questions_waiting_for_teacher,
    ) == (1, 1, 1)
    assert (result.student_message_count, result.teacher_message_count) == (3, 2)
    assert result.completed_response_count == 1 and result.unanswered_episode_count == 1
    assert result.average_teacher_response_seconds == 2 * 86400
    assert result.median_teacher_response_seconds == 2 * 86400


@pytest.mark.parametrize("teacher_first", [False, True])
def test_response_equal_sent_at_excluded_regardless_capture_order(
    analytics_workflow, teacher_first
):
    w = analytics_workflow
    case = w.s.create_question_case(
        w.student.id, "Start", instant(2), course_offering_id=w.offering.id
    )
    if teacher_first:
        w.s.add_teacher_message(case.id, "Teacher", instant(3))
        w.s.add_student_message(case.id, "Student", instant(3))
    else:
        w.s.add_student_message(case.id, "Student", instant(3))
        w.s.add_teacher_message(case.id, "Teacher", instant(3))
    result = w.s.question_analytics(offering_id=w.offering.id)
    assert result.completed_response_count == 0 and result.ambiguous_response_count == 1
    assert result.average_teacher_response_seconds is None


def test_response_mean_median_excludes_unanswered_case(analytics_workflow):
    w = analytics_workflow
    for day in (3, 5, 9):
        case = w.s.create_question_case(
            w.student.id, "Question", instant(2), course_offering_id=w.offering.id
        )
        w.s.add_teacher_message(case.id, "Teacher", instant(day))
    w.s.create_question_case(
        w.student.id, "Unanswered", instant(2), course_offering_id=w.offering.id
    )
    result = w.s.question_analytics(offering_id=w.offering.id)
    assert result.completed_response_count == 3 and result.unanswered_episode_count == 1
    assert result.average_teacher_response_seconds == pytest.approx(11 * 86400 / 3)
    assert result.median_teacher_response_seconds == 3 * 86400


def test_student_questions_closed_waiting_answered_and_explicit_context_counts(analytics_workflow):
    w = analytics_workflow
    topic = w.s.create_topic(w.course.id, "Question Topic")
    skill = w.s.create_skill(w.course.id, "Question Skill")
    answered = w.s.create_question_case(
        w.student.id, "Answered", instant(2), course_offering_id=w.offering.id
    )
    w.s.add_teacher_message(answered.id, "Answer", instant(3))
    w.s.attach_question_context(answered.id, "assessment", w.assessment.id)
    w.s.attach_question_context(answered.id, "topic", topic.id)
    w.s.attach_question_context(answered.id, "skill", skill.id)
    waiting = w.s.create_question_case(
        w.student.id, "Waiting", instant(2), course_offering_id=w.offering.id
    )
    closed = w.s.create_question_case(
        w.student.id, "Closed", instant(2), course_offering_id=w.offering.id
    )
    w.s.close_question_case(closed, closed_at=instant(4))
    result = w.s.student_progress(w.student.id, w.offering.id)
    assert result.question_cases_total == 3 and result.open_questions == 2
    assert result.questions_waiting_for_teacher == 1
    assert (
        result.questions.assessment_linked_count
        == result.questions.topic_linked_count
        == result.questions.skill_linked_count
        == 1
    )
    w.s.archive_question_case(waiting)
    assert w.s.student_progress(w.student.id, w.offering.id).question_cases_total == 2


def test_group_aggregation_distribution_cohort_and_no_ranking(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    w.s._clock = lambda: instant()
    other = w.s.create_student(w.offering.id, "Synthetic Other")
    w.s._clock = lambda: instant(10)
    w.s.add_attempt(
        w.s.get_or_create_work(other.id, w.assessment.id).id,
        instant(3),
        AttemptResult.NEEDS_REVISION,
    )
    result = w.s.group_analytics(w.offering.id)
    assert result.student_count == 2 and result.average_completion_rate == 0.5
    assert result.first_pass_rate == 0.5 and result.average_attempts == 1
    assert result.on_time_rate == 0.5
    assert [(b.completed_count, b.student_count) for b in result.completion_distribution] == [
        (0, 1),
        (1, 1),
    ]
    assert not {"ranking", "rank", "student_scores", "students"} & asdict(result).keys()
    enrollment = next(
        en for en in w.s.list_students_for_offering(w.offering.id) if en.student.id == other.id
    ).enrollment
    w.s.create_question_case(other.id, "Question", instant(3), course_offering_id=w.offering.id)
    w.s.withdraw_student(enrollment)
    assert w.s.group_analytics(w.offering.id).questions.question_cases_count == 0
    assert w.s.question_analytics(offering_id=w.offering.id).question_cases_count == 1
    assert w.s.student_progress(other.id, w.offering.id).assessments_started == 1


def test_assessment_status_attempts_and_score_statistics(analytics_workflow):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED, score=8, max_score=10)
    w.s._clock = lambda: instant()
    other = w.s.create_student(w.offering.id, "Synthetic Other")
    unstarted = w.s.create_student(w.offering.id, "Synthetic Empty")
    w.s._clock = lambda: instant(10)
    work = w.s.get_or_create_work(other.id, w.assessment.id)
    w.s.add_attempt(work.id, instant(3), AttemptResult.NEEDS_REVISION, score=2, max_score=10)
    result = w.s.assessment_analytics(w.assessment.id)
    assert result.assigned_students == 3 and unstarted.id != other.id
    assert (result.started, result.not_started, result.passed, result.revision_required) == (
        2,
        1,
        1,
        1,
    )
    assert (
        result.average_attempts == 1
        and result.first_pass_count == 1
        and result.first_pass_rate == 0.5
    )
    assert result.average_normalized_score == 0.5 and result.median_normalized_score == 0.5


def evidence_setup(w):
    parent = w.s.create_topic(w.course.id, "Parent")
    child = w.s.create_topic(w.course.id, "Child", parent_topic_id=parent.id)
    skill = w.s.create_skill(w.course.id, "Skill")
    item = w.s.create_assessment_item(w.assessment.id, "Item", max_score=4)
    w.s.attach_item_topic(item.id, parent.id)
    w.s.attach_item_topic(item.id, child.id)
    w.s.attach_item_skill(item.id, skill.id)
    return parent, child, skill, item


@pytest.mark.parametrize(
    "outcome,score,maximum,evaluated",
    [
        (ItemOutcome.CORRECT, None, None, 1),
        (ItemOutcome.PARTIAL, 2, 4, 1),
        (ItemOutcome.INCORRECT, 0, 4, 1),
        (ItemOutcome.NOT_EVALUATED, None, None, 0),
        (None, 1, None, 1),
        (None, 2, 4, 1),
    ],
)
def test_topic_skill_item_outcomes_score_and_not_evaluated(
    analytics_workflow, outcome, score, maximum, evaluated
):
    w = analytics_workflow
    parent, child, skill, item = evidence_setup(w)
    attempt = w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    result = w.s.create_attempt_item_result(
        attempt.id, item.id, outcome=outcome, score=score, max_score=maximum
    )
    topic = w.s.topic_evidence(parent.id)
    skill_summary = w.s.skill_evidence(skill.id)
    for summary in (topic, skill_summary):
        assert summary.item_result_count == 1 and summary.evaluated == evaluated
        assert summary.not_evaluated == 1 - evaluated and summary.students_with_evidence == 1
        assert summary.evidence_count == 1 and summary.evidence_ids == (("item_result", result.id),)
        assert summary.average_normalized_item_score == (
            score / maximum if score is not None and maximum else None
        )
    assert topic.assessments_covering_topic == 1 and topic.assessment_items_covering_topic == 1
    assert w.s.topic_evidence(child.id).item_result_count == 1
    assert w.s.assessment_analytics(w.assessment.id).items[0].result_count == 1


def test_hierarchy_distinct_questions_lessons_attendance_and_results(analytics_workflow):
    w = analytics_workflow
    parent, child, skill, item = evidence_setup(w)
    w.s.attach_assessment_topic(w.assessment.id, parent.id)
    w.s.attach_assessment_topic(w.assessment.id, child.id)
    attempt = w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    w.s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    case = w.s.create_question_case(
        w.student.id, "Question", instant(2), course_offering_id=w.offering.id
    )
    w.s.attach_question_context(case.id, "topic", parent.id)
    w.s.attach_question_context(case.id, "topic", child.id)
    w.s.attach_question_context(case.id, "skill", skill.id)
    w.s.add_student_message(case.id, "Clarification", instant(3))
    lesson = w.s.create_lesson(
        w.offering.id, LocalDate(2026, 10, 2), topic_ids=(parent.id, child.id)
    )
    enrollment = w.s.list_students_for_offering(w.offering.id)[0].enrollment
    w.s.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.LATE)
    summary = w.s.topic_evidence(parent.id)
    assert summary.evidence_count == 5 and len(set(summary.evidence_ids)) == 5
    assert summary.assessment_attempt_count == summary.item_result_count == 1
    assert summary.question_cases_linked == summary.questions_by_students_count == 1
    assert summary.student_message_count == 2 and summary.lesson_exposure_count == 1
    assert summary.attendance.late == 1 and summary.attendance.attendance_rate == 1
    assert w.s.skill_evidence(skill.id).lesson_exposure_count == 0
    assert w.s.skill_evidence(skill.id).question_cases_linked == 1


def test_whole_assessment_tag_does_not_invent_item_outcome(analytics_workflow):
    w = analytics_workflow
    topic = w.s.create_topic(w.course.id, "Whole")
    item = w.s.create_assessment_item(w.assessment.id, "No item tag")
    w.s.attach_assessment_topic(w.assessment.id, topic.id)
    attempt = w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    w.s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    result = w.s.topic_evidence(topic.id)
    assert result.assessment_attempt_count == 1 and result.item_result_count == 0
    assert result.correct == 0 and result.average_normalized_item_score is None


def test_course_evidence_scope_student_filter_and_no_topic_skill_inference(analytics_workflow):
    w = analytics_workflow
    parent, _, skill, item = evidence_setup(w)
    w.s.attach_topic_skill(parent.id, skill.id)
    other_group = w.s.create_group("OTHER")
    other_offering = w.s.create_offering(w.term.id, w.course.id, other_group.id)
    other_student = w.s.create_student(other_offering.id, "Synthetic other context")
    assessment = w.s.create_assessment(
        other_offering.id, "Other", AssessmentType.HOMEWORK, issued_at=instant()
    )
    other_item = w.s.create_assessment_item(assessment.id, "Item")
    w.s.attach_item_topic(other_item.id, parent.id)
    other_attempt = w.s.add_attempt(
        w.s.get_or_create_work(other_student.id, assessment.id).id,
        instant(3),
        AttemptResult.ACCEPTED,
    )
    w.s.create_attempt_item_result(other_attempt.id, other_item.id, outcome=ItemOutcome.INCORRECT)
    attempt = w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)
    w.s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    assert w.s.topic_evidence(parent.id).item_result_count == 2
    assert w.s.topic_evidence(parent.id, offering_id=w.offering.id).item_result_count == 1
    assert w.s.topic_evidence(parent.id, student_id=other_student.id).incorrect == 1
    assert w.s.skill_evidence(skill.id).item_result_count == 1


def test_attempt_history_and_old_item_analytics_remain_separate(analytics_workflow):
    w = analytics_workflow
    parent, _, _, item = evidence_setup(w)
    first = w.s.add_attempt(w.work.id, instant(2), AttemptResult.NEEDS_REVISION)
    old = w.s.create_attempt_item_result(first.id, item.id, outcome=ItemOutcome.INCORRECT)
    before = w.s.topic_evidence(parent.id)
    second = w.s.add_attempt(w.work.id, instant(3), AttemptResult.ACCEPTED)
    w.s.create_attempt_item_result(second.id, item.id, outcome=ItemOutcome.CORRECT)
    after = w.s.topic_evidence(parent.id)
    assert before.incorrect == after.incorrect == 1 and after.correct == 1
    assert w.s.list_attempt_item_results(first.id) == (old,)
    assert after.item_result_count == 2


def test_timeline_cutoffs_use_current_facts_and_one_bulk_load(analytics_workflow, runtime):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.NEEDS_REVISION)
    w.s.add_attempt(w.work.id, instant(3), AttemptResult.ACCEPTED)
    selects = []

    def count_queries(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", count_queries)
    try:
        points = w.s.analytics_timeline(
            w.offering.id, (instant(4), instant(), instant(2), instant(4)), student_id=w.student.id
        )
    finally:
        event.remove(runtime._engine, "before_cursor_execute", count_queries)
    assert [point.assessments_completed for point in points] == [0, 0, 1]
    assert [point.attempts_total for point in points] == [0, 1, 2]
    assert len(selects) <= 25


def test_analytics_reads_are_immutable_and_do_not_change_database(analytics_workflow, runtime):
    w = analytics_workflow
    w.s.add_attempt(w.work.id, instant(2), AttemptResult.ACCEPTED)

    def dump():
        with runtime._engine.connect() as connection:
            tables = (
                connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                )
                .scalars()
                .all()
            )
            return {
                name: connection.exec_driver_sql(
                    f'SELECT * FROM "{name}" ORDER BY rowid'
                ).fetchall()
                for name in tables
            }

    before = dump()
    value = w.s.student_progress(w.student.id, w.offering.id)
    w.s.group_analytics(w.offering.id)
    w.s.assessment_analytics(w.assessment.id)
    w.s.question_analytics()
    assert dump() == before
    with pytest.raises(FrozenInstanceError):
        value.completion_rate = 2
    assert asdict(value)["completion_rate"] == 1


def test_calendar_days_late_requires_explicit_timezone_at_midnight():
    due = UtcInstant(datetime(2026, 10, 1, 20, 30, tzinfo=UTC))
    presented = UtcInstant(datetime(2026, 10, 1, 21, 30, tzinfo=UTC))
    assert calendar_days_late(presented, due, UTC) == 0
    assert calendar_days_late(presented, due, timezone(timedelta(hours=3))) == 1
    with pytest.raises(ValueError, match="timezone"):
        calendar_days_late(presented, due, None)


def test_invalid_as_of_and_unknown_context_are_explicit(analytics_workflow):
    w = analytics_workflow
    with pytest.raises(ValueError, match="UTC"):
        w.s.group_analytics(w.offering.id, as_of="2026-10-02")
    with pytest.raises(ApplicationError, match="not_found"):
        w.s.group_analytics(w.s._meta().id)


def test_synthetic_group_30_students_20_assessments_has_bounded_queries(
    analytics_workflow, runtime
):
    w = analytics_workflow
    topic = w.s.create_topic(w.course.id, "Synthetic Topic")
    skill = w.s.create_skill(w.course.id, "Synthetic Skill")
    assessments = [w.assessment] + [
        new_assessment(w, f"Synthetic work {n}", due_at=instant(5)) for n in range(19)
    ]
    items = []
    for assessment in assessments:
        item = w.s.create_assessment_item(assessment.id, "Synthetic item")
        w.s.attach_item_topic(item.id, topic.id)
        w.s.attach_item_skill(item.id, skill.id)
        items.append(item)
    students = [w.student]
    with w.s._transaction() as repositories:
        for n in range(29):
            student = e.Student(metadata=w.s._meta(), full_name=f"Synthetic {n:02}")
            repositories.students.insert(student)
            repositories.enrollments.insert(
                e.Enrollment(
                    metadata=w.s._meta(),
                    student_id=student.id,
                    offering_id=w.offering.id,
                    enrolled_at=instant(),
                )
            )
            students.append(student)
        for student in students:
            for assessment, item in zip(assessments, items, strict=True):
                work = repositories.works.find_for_student(student.id, assessment.id)
                if work is None:
                    work = e.StudentWork(
                        metadata=w.s._meta(), assessment_id=assessment.id, student_id=student.id
                    )
                    repositories.works.insert(work)
                for number, result in enumerate(
                    (AttemptResult.PRESENTED, AttemptResult.NEEDS_REVISION, AttemptResult.ACCEPTED),
                    start=1,
                ):
                    attempt = e.Attempt(
                        metadata=EntityMetadata.create(instant(10)),
                        student_work_id=work.id,
                        attempt_no=number,
                        occurred_at=instant(number + 1),
                        result=result,
                        score=number,
                        max_score=3,
                    )
                    repositories.attempts.append(attempt)
                repositories.item_results.insert(
                    AttemptItemResult(
                        metadata=w.s._meta(),
                        attempt_id=attempt.id,
                        assessment_item_id=item.id,
                        outcome=ItemOutcome.CORRECT,
                        score=3,
                        max_score=3,
                    )
                )
    for n in range(10):
        lesson = w.s.create_lesson(w.offering.id, LocalDate(2026, 10, n + 1), topic_ids=(topic.id,))
        enrollment = w.s.list_students_for_offering(w.offering.id)[0].enrollment
        w.s.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.PRESENT)
    for student in students:
        case = w.s.create_question_case(
            student.id, "Synthetic question", instant(2), course_offering_id=w.offering.id
        )
        w.s.attach_question_context(case.id, "topic", topic.id)
        w.s.attach_question_context(case.id, "skill", skill.id)
    selects = []

    def count_queries(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", count_queries)
    try:
        began = perf_counter()
        result = w.s.group_analytics(w.offering.id)
        elapsed = perf_counter() - began
    finally:
        event.remove(runtime._engine, "before_cursor_execute", count_queries)
    assert result.student_count == 30 and result.assessments_total == 20
    assert result.assessments_completed == 600 and result.attempts_total == 1800
    assert result.average_attempts == 3 and result.questions.question_cases_count == 30
    assert w.s.topic_evidence(topic.id).item_result_count == 600
    assert len(selects) <= 25 and elapsed < 5
    print(
        f"Analytics performance: {len(selects)} SELECT, {elapsed:.3f}s; 30 students/20 assessments/1800 attempts/600 item results/10 lessons/30 cases"
    )
