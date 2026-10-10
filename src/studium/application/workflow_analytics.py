"""Additional factual week and lecture/seminar DTOs over analytics snapshots."""

from dataclasses import dataclass
from datetime import date

from studium.application.analytics import PRESENTATIONS
from studium.application.analytics_models import AttendanceSummary
from studium.domain.enums import AttemptResult, LessonType


@dataclass(frozen=True)
class WeekFacts:
    week: int
    attempts: int
    first_submissions: int
    accepted_attempts: int
    planned_due: int
    seminar_attendance: AttendanceSummary
    lecture_attendance: AttendanceSummary


@dataclass(frozen=True)
class WorkflowAnalytics:
    weeks: tuple[WeekFacts, ...]
    seminars: AttendanceSummary
    lectures: AttendanceSummary


class WorkflowAnalyticsService:
    def workflow_analytics(self, offering_id, *, student_id=None, as_of=None, module_id=None):
        view = self._module_view(offering_id, as_of, module_id)
        offering = view.offering(offering_id)
        students = {student_id} if student_id else view.roster(offering_id)
        lessons = {
            id: lesson
            for id, lesson in view.lessons.items()
            if lesson.course_offering_id == offering_id
        }
        histories = [
            history
            for id, history in view.histories.items()
            if view.works[id].student_id in students
            and view.assessments[view.works[id].assessment_id].offering_id == offering_id
        ]
        firsts = [
            min((a.occurred_at for a in h if a.result in PRESENTATIONS), default=None)
            for h in histories
        ]
        attempts = [a for h in histories for a in h]
        term = view.terms[offering.term_id]
        program = view.programs.get(offering.work_program_id)
        first = program.first_week_start if program else term.starts_on
        start = date(first.year, first.month, first.day)

        def lesson_week(lesson):
            day = lesson.lesson_date
            return (date(day.year, day.month, day.day) - start).days // 7 + 1

        end = date(term.ends_on.year, term.ends_on.month, term.ends_on.day)
        length = program.weeks if program else max(1, (end - start).days // 7 + 1)

        def attendance(kind, week=None):
            ids = [
                id
                for id, lesson in lessons.items()
                if lesson.type == kind and (week is None or lesson_week(lesson) == week)
            ]
            return view.attendance_summary(ids, students)

        assessments = view.assessments_for(offering_id)
        weeks = tuple(
            WeekFacts(
                week,
                sum(view.week_at(offering_id, a.occurred_at) == week for a in attempts),
                sum(at is not None and view.week_at(offering_id, at) == week for at in firsts),
                sum(
                    a.result == AttemptResult.ACCEPTED
                    and view.week_at(offering_id, a.occurred_at) == week
                    for a in attempts
                ),
                sum(
                    a.planned_due_week is not None and a.planned_due_week.value == week
                    for a in assessments
                ),
                attendance(LessonType.SEMINAR, week),
                attendance(LessonType.LECTURE, week),
            )
            for week in range(1, length + 1)
        )
        return WorkflowAnalytics(
            weeks, attendance(LessonType.SEMINAR), attendance(LessonType.LECTURE)
        )
