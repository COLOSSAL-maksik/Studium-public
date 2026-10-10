"""Factual completion, equal student sectors and the same weekly metric."""

from dataclasses import dataclass
from datetime import UTC, timedelta
from statistics import mean

from studium.application.analytics import _View
from studium.domain.value_objects import UtcInstant


@dataclass(frozen=True)
class StudentSector:
    student_id: object
    label: str
    completed: int
    total: int
    progress: float | None


@dataclass(frozen=True)
class WeeklyProgress:
    week: int
    progress: float | None
    total: int


@dataclass(frozen=True)
class ProgressChartData:
    students: tuple[StudentSector, ...]
    weeks: tuple[WeeklyProgress, ...]
    average: float | None
    metric: str = "Доля зачтённых работ среди назначенных на выбранный момент"


class ProgressChartsService:
    def progress_chart_data(self, offering_id, *, module_id=None, student_id=None, as_of=None):
        view = self._module_view(offering_id, as_of, module_id)
        offering = view.offering(offering_id)
        students = sorted(
            view.roster(offering_id), key=lambda id: (view.students[id].full_name, str(id))
        )
        if student_id is not None:
            students = [id for id in students if id == student_id]

        def sectors(current):
            assessments = current.assessments_for(offering_id)
            total = len(assessments)
            result = []
            for id in students:
                completed = sum(
                    current.work_facts(id, assessment)["completed"] for assessment in assessments
                )
                result.append(
                    StudentSector(
                        id,
                        view.students[id].full_name,
                        completed,
                        total,
                        completed / total if total else None,
                    )
                )
            return tuple(result)

        now = sectors(view)
        program = view.programs.get(offering.work_program_id)
        term = view.terms[offering.term_id]
        first = program.first_week_start if program else term.starts_on
        length = program.weeks if program else 17
        offset = program.week_utc_offset_minutes if program else term.week_utc_offset_minutes
        from datetime import datetime, timezone

        start = datetime(
            first.year, first.month, first.day, tzinfo=timezone(timedelta(minutes=offset))
        )
        weeks = []
        for week in range(1, length + 1):
            cutoff = UtcInstant((start + timedelta(days=week * 7, microseconds=-1)).astimezone(UTC))
            if cutoff > view.as_of:
                week_start = UtcInstant((start + timedelta(days=(week - 1) * 7)).astimezone(UTC))
                current = now if week_start <= view.as_of else ()
            else:
                current = sectors(_View(view.data, cutoff))
            values = [s.progress for s in current if s.progress is not None]
            weeks.append(
                WeeklyProgress(
                    week, mean(values) if values else None, current[0].total if current else 0
                )
            )
        values = [s.progress for s in now if s.progress is not None]
        return ProgressChartData(now, tuple(weeks), mean(values) if values else None)
