"""Prepared semester journal: planned cells plus bulk-loaded recorded facts."""

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, timedelta, timezone

from studium.domain.enums import AssessmentType, AttendanceStatus, ItemOutcome, StudentWorkStatus


@dataclass(frozen=True)
class JournalColumn:
    title: str
    kind: str
    module_title: str
    module_id: object = None
    week: int | None = None
    assessment: object = None
    program_work: object = None
    lessons: tuple = ()
    full_title: str = ""


def work_label(assessment_type, number, ordinal=1):
    prefix = {
        AssessmentType.HOMEWORK: "ДЗ",
        AssessmentType.CONTROL_WORK: "РК",
        AssessmentType.EXAM: "Экзамен",
    }.get(assessment_type, "Работа")
    match = re.search(r"\d+", number or "")
    return f"{prefix} №{match.group() if match else ordinal}"


@dataclass(frozen=True)
class JournalSnapshot:
    matrix: object
    program: object
    modules: tuple
    columns: tuple[JournalColumn, ...]
    values: dict
    tooltips: dict
    empty_sections: tuple = ()


def compact_progress(progress):
    if progress is None or progress.status == StudentWorkStatus.NOT_STARTED:
        return "—"
    if progress.status == StudentWorkStatus.ACCEPTED:
        return "✓" + (
            str(progress.attempt_count).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
            if progress.attempt_count > 1
            else ""
        )
    return "⚠" if progress.status == StudentWorkStatus.REVISION_REQUIRED else "○"


class JournalService:
    def journal(self, offering_id, *, include_ended=False):
        matrix = self.matrix(offering_id, include_ended=include_ended)
        program = self.program_for_offering(offering_id)
        modules = self.list_program_modules(program.id) if program else ()
        planned = self.planned_works(offering_id)
        with self._transaction() as r:
            lessons = r.lessons.for_offering(offering_id)
            attendance = r.attendance.list()
            enrollments = {v.id: v for v in r.enrollments.for_offering(offering_id)}
            items = r.items.list()
            works = r.works.for_assessments(a.id for a in matrix.assessments)
            attempts = r.attempts.for_works(w.id for w in works)
            results = r.item_results.for_attempts(a.id for a in attempts)
        lesson_weeks = defaultdict(list)
        for lesson in lessons:
            week = lesson.planned_week or (
                program.week_for_date(lesson.planned_date or lesson.lesson_date)
                if program
                else None
            )
            if week:
                lesson_weeks[week.value].append(lesson)
        columns, empty_sections = [], []
        ranges = [(m.id, m.title, range(m.start_week, m.end_week + 1)) for m in modules]
        covered = {week for _, _, weeks in ranges for week in weeks}
        missing = [w for w in range(1, (program.weeks if program else 17) + 1) if w not in covered]
        if missing:
            ranges.append((None, "План семестра" if not modules else "Без модуля", missing))
        assigned = set()
        for module_id, title, weeks in ranges:
            for week in weeks:
                columns.append(
                    JournalColumn(
                        str(week),
                        "attendance",
                        title,
                        module_id,
                        week,
                        lessons=tuple(lesson_weeks[week]),
                    )
                )
            for kind, type in (
                ("homework", AssessmentType.HOMEWORK),
                ("control", AssessmentType.CONTROL_WORK),
            ):
                matches = [
                    w
                    for w in planned
                    if w.definition.type == type
                    and (
                        w.link.module_id == module_id
                        or (
                            w.link.module_id is None
                            and w.link.planned_due_week
                            and w.link.planned_due_week.value in weeks
                        )
                    )
                ]
                for work in matches:
                    if work.link.id in assigned:
                        continue
                    assigned.add(work.link.id)
                    columns.append(
                        JournalColumn(
                            work.definition.label or work.definition.title,
                            kind,
                            title,
                            module_id,
                            assessment=work.assessment,
                            program_work=work.link,
                        )
                    )
                if not matches:
                    empty_sections.append((title, kind))
        for work in planned:
            if work.link.id not in assigned:
                columns.append(
                    JournalColumn(
                        work.definition.label or work.definition.title,
                        "homework"
                        if work.definition.type == AssessmentType.HOMEWORK
                        else "control",
                        "Без модуля",
                        assessment=work.assessment,
                        program_work=work.link,
                    )
                )
        planned_actual = {w.assessment.id for w in planned if w.assessment}
        for assessment in matrix.assessments:
            if assessment.id not in planned_actual:
                columns.append(
                    JournalColumn(
                        assessment.number or assessment.title,
                        "homework" if assessment.type == AssessmentType.HOMEWORK else "control",
                        "Внеплановые работы",
                        assessment=assessment,
                    )
                )
        semantic_columns = []
        ordinals = defaultdict(int)
        definitions = {work.link.id: work.definition for work in planned}
        for column in columns:
            if column.kind != "attendance":
                definition = (
                    definitions.get(column.program_work.id)
                    if column.program_work
                    else column.assessment
                )
                ordinals[definition.type] += 1
                semantic_columns.append(
                    replace(
                        column,
                        title=work_label(
                            definition.type,
                            getattr(definition, "label", None)
                            or getattr(definition, "number", None),
                            ordinals[definition.type],
                        ),
                        full_title=definition.title,
                    )
                )
            else:
                semantic_columns.append(column)
        columns = semantic_columns
        canonical = self.semester_plan(offering_id)
        if canonical:
            program, modules = canonical.plan, canonical.modules
            first = date(
                program.first_week_start.year,
                program.first_week_start.month,
                program.first_week_start.day,
            )

            def week_for(value):
                return (date(value.year, value.month, value.day) - first).days // 7 + 1

            def title_for(week):
                if week is None:
                    return "Без срока"
                if week < 1 or week > program.weeks:
                    return "После семестра" if week > program.weeks else "До семестра"
                return next(
                    (m.title for m in modules if m.start_week <= week <= m.end_week), "Без модуля"
                )

            actual = {a.id: a for a in matrix.assessments}
            issued = {i.planned_work_id: actual.get(i.assessment_id) for i in canonical.issued}
            columns = []
            for lesson in lessons:
                week = week_for(lesson.lesson_date)
                columns.append(
                    JournalColumn(
                        lesson.title,
                        "attendance",
                        title_for(week),
                        week=week,
                        lessons=(lesson,),
                        full_title=f"{lesson.lesson_date} · {lesson.title}",
                    )
                )
            occupied = {c.week for c in columns}
            for week in range(1, program.weeks + 1):
                if week not in occupied:
                    columns.append(
                        JournalColumn(
                            "Занятие —",
                            "attendance",
                            title_for(week),
                            week=week,
                            full_title="Занятие ещё не создано",
                        )
                    )
            for ordinal, work in enumerate(canonical.works, 1):
                due = work.due_date if work.deadline_kind == "DATE_EXCLUSIVE" else None
                if work.deadline_kind == "EXACT_INCLUSIVE" and work.exact_due_at:
                    value = work.exact_due_at.value.astimezone(
                        timezone(timedelta(minutes=program.week_utc_offset_minutes))
                    ).date()
                    from studium.domain.value_objects import LocalDate

                    due = LocalDate(value.year, value.month, value.day)
                week = week_for(due) if due else work.due_week
                columns.append(
                    JournalColumn(
                        work_label(work.type, work.number, ordinal),
                        "homework" if work.type == AssessmentType.HOMEWORK else "control",
                        title_for(week),
                        work.module_id,
                        week,
                        issued.get(work.id),
                        work,
                        full_title=work.title + (" · отменена" if work.cancelled else ""),
                    )
                )
            linked = {i.assessment_id for i in canonical.issued}
            for assessment in matrix.assessments:
                if assessment.id not in linked:
                    week = None
                    if assessment.due_at:
                        value = assessment.due_at.value.astimezone(
                            timezone(timedelta(minutes=program.week_utc_offset_minutes))
                        ).date()
                        week = (value - first).days // 7 + 1
                    columns.append(
                        JournalColumn(
                            work_label(assessment.type, assessment.number),
                            "homework" if assessment.type == AssessmentType.HOMEWORK else "control",
                            title_for(week),
                            week=week,
                            assessment=assessment,
                            full_title=assessment.title,
                        )
                    )
            columns.sort(
                key=lambda c: (c.week is None, c.week or 0, c.kind != "attendance", c.full_title)
            )
            empty_sections = []
        else:
            # Each recorded lesson is a separate factual column, including events
            # sharing a week and lessons outside the original prepared calendar.
            expanded = []
            seen = set()
            for column in columns:
                if column.kind == "attendance" and column.lessons:
                    for lesson in column.lessons:
                        expanded.append(
                            replace(
                                column,
                                title=lesson.title,
                                lessons=(lesson,),
                                full_title=f"{lesson.lesson_date} · {lesson.title}",
                            )
                        )
                        seen.add(lesson.id)
                else:
                    expanded.append(column)
            for lesson in lessons:
                if lesson.id not in seen:
                    expanded.append(
                        JournalColumn(
                            lesson.title,
                            "attendance",
                            "Вне календаря",
                            lessons=(lesson,),
                            full_title=f"{lesson.lesson_date} · {lesson.title}",
                        )
                    )
            columns = expanded
        marks = {
            (v.lesson_id, enrollments[v.enrollment_id].student_id): v
            for v in attendance
            if v.enrollment_id in enrollments
        }
        by_work = defaultdict(list)
        for attempt in attempts:
            by_work[attempt.student_work_id].append(attempt)
        by_attempt = defaultdict(list)
        for result in results:
            by_attempt[result.attempt_id].append(result)
        counts = defaultdict(int)
        for item in items:
            counts[item.assessment_id] += 1
        values, tooltips = {}, {}
        for entry in matrix.roster:
            for index, column in enumerate(columns, 1):
                key = entry.student.id, index
                if column.kind == "attendance":
                    active = [lesson for lesson in column.lessons if not lesson.cancelled]
                    entries = [marks.get((lesson.id, entry.student.id)) for lesson in active]
                    codes = {
                        AttendanceStatus.PRESENT: "•",
                        AttendanceStatus.ABSENT: "×",
                        AttendanceStatus.LATE: "◷",
                        AttendanceStatus.EXCUSED: "У",
                        AttendanceStatus.UNKNOWN: "?",
                    }
                    values[key] = (
                        codes[entries[0].status]
                        if len(entries) == 1 and entries[0]
                        else f"{sum(v is not None and v.status in {AttendanceStatus.PRESENT, AttendanceStatus.LATE} for v in entries)}/{len(entries)}"
                        if len(entries) > 1
                        else "—"
                    )
                    tooltips[key] = (
                        "\n".join(
                            f"{lesson.lesson_date} · {lesson.title}"
                            + (" · отменено" if lesson.cancelled else "")
                            for lesson in column.lessons
                        )
                        or "Плановое занятие. Нажмите, чтобы создать занятие и отметить посещение."
                    )
                elif column.assessment:
                    cell = matrix.cells[entry.student.id, column.assessment.id]
                    values[key] = compact_progress(cell.progress)
                    if column.program_work and getattr(column.program_work, "cancelled", False):
                        values[key] = "Отм."
                    elif cell.progress and cell.progress.final_score is not None:
                        values[key] += " · " + str(cell.progress.final_score).replace(".", ",")
                    if column.kind == "control" and counts[column.assessment.id] and cell.work:
                        latest = max(
                            by_work[cell.work.id], key=lambda a: a.attempt_no, default=None
                        )
                        if latest:
                            values[key] = (
                                f"{sum(v.outcome == ItemOutcome.CORRECT for v in by_attempt[latest.id])}/{counts[column.assessment.id]}"
                            )
                    tooltips[key] = (
                        column.assessment.title
                        + f"\nПопыток: {cell.progress.attempt_count if cell.progress else 0}"
                        + (
                            "\nЗачтено"
                            if cell.progress and cell.progress.status == StudentWorkStatus.ACCEPTED
                            else ""
                        )
                    )
                else:
                    values[key] = (
                        "Отм." if getattr(column.program_work, "cancelled", False) else "План"
                    )
                    tooltips[key] = (
                        "Плановая работа. Нажмите, чтобы открыть попытки."
                        if column.program_work
                        else "Добавьте работу в рабочую программу."
                    )
        return JournalSnapshot(
            matrix, program, modules, tuple(columns), values, tooltips, tuple(empty_sections)
        )
