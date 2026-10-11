"""Read-only reporting over the existing analytics snapshot and factual semantics."""

from collections import Counter, defaultdict
from decimal import Decimal

from studium.application.analytics import _Snapshot, _View
from studium.application.errors import ApplicationError
from studium.application.report_models import Report, ReportChoices, ReportKind, ReportTable
from studium.application.view_models import OfferingContext
from studium.domain.enums import AttendanceStatus, StudentWorkStatus
from studium.domain.qa import result_from_events, score_text
from studium.domain.value_objects import UtcInstant


class _ReportSnapshot(_Snapshot):
    NAMES = (*_Snapshot.NAMES, "courses", "groups", "grades")

    def __init__(self, repositories, *, historical=False):
        super().__init__(repositories, historical=historical)
        repo = getattr(repositories, "review_grades", None)
        self.review_grades = tuple(repo.list(include_deleted=historical)) if repo else ()


WORK_COLUMNS = (
    ("assessment", "Работа"),
    ("type", "Тип"),
    ("due_at", "Срок"),
    ("due_week", "Неделя срока"),
    ("status", "Текущий статус"),
    ("attempts", "Попыток"),
    ("last_attempt", "Последняя попытка"),
    ("grade", "Последняя оценка"),
    ("grade_attempt", "Попытка оценки"),
    ("score", "Текущий балл"),
)
ATTENDANCE_COLUMNS = (
    ("lessons", "Занятий"),
    *((s.value.lower(), s) for s in AttendanceStatus),
    ("unmarked", "Не отмечено"),
)


def _attendance_row(summary):
    return (
        summary.lessons_total,
        summary.present,
        summary.absent,
        summary.late,
        summary.excused,
        summary.unknown,
        summary.unmarked,
    )


class _Projection:
    def __init__(self, snapshot, at, offering_id, historical):
        self.historical = historical
        self.view = _View(snapshot, at)
        self.context = self._context(snapshot, offering_id)
        self.assessments = tuple(
            sorted(
                self.view.assessments_for(offering_id),
                key=lambda a: (a.type.value, a.number or "", a.title.casefold(), a.id),
            )
        )
        ids = self.view.roster(offering_id)
        if historical:
            ids |= {
                en.student_id
                for en in self.view.enrollments.values()
                if en.offering_id == offering_id and en.enrolled_at <= at
            }
        self.students = tuple(
            sorted(
                (self.view.students[id] for id in ids if id in self.view.students),
                key=lambda s: (s.full_name.casefold(), s.id),
            )
        )
        self.grades = {g.attempt_id: g for g in snapshot.grades if g.created_at <= at}
        self.review_grades = {g.review_id: g for g in snapshot.review_grades if g.created_at <= at}
        self.results = defaultdict(list)
        for result in self.view.results:
            self.results[result.attempt_id].append(result)
        for results in self.results.values():
            results.sort(
                key=lambda r: (
                    self.view.items[r.assessment_item_id].sort_order,
                    r.assessment_item_id,
                )
            )
        self.lessons = {
            lesson.id
            for lesson in self.view.lessons.values()
            if lesson.course_offering_id == offering_id
        }

    @staticmethod
    def _context(snapshot, offering_id):
        offering = next((o for o in snapshot.offerings if o.id == offering_id), None)
        if offering is None:
            raise ApplicationError("not_found")
        values = []
        for entries, id in (
            (snapshot.terms, offering.term_id),
            (snapshot.courses, offering.course_id),
            (snapshot.groups, offering.group_id),
        ):
            value = next((v for v in entries if v.id == id), None)
            if value is None:
                raise ApplicationError("not_found")
            values.append(value)
        return OfferingContext(offering, *values)

    def history(self, student, assessment):
        work = self.view.by_pair.get((student.id, assessment.id))
        return self.view.histories[work.id] if work else ()

    def work_row(self, student, assessment):
        facts = self.view.work_facts(student.id, assessment)
        history = self.history(student, assessment)
        graded = next((a for a in reversed(history) if a.id in self.grades), None)
        submissions = [
            self.view.submissions[a.id] for a in history if a.id in self.view.submissions
        ]
        reviews = [v for sub in submissions for v in self.view.reviews[sub.id]]
        result = result_from_events(history, submissions, reviews)
        numeric = (
            Decimal(result.score) / 100
            if result.exact and result.score is not None
            else result.score
        )
        grade = self.review_grades.get(result.source_id)
        evaluation = (
            score_text(grade.score_cents) + " / " + score_text(grade.max_cents)
            if grade and grade.score_cents is not None
            else "Зачтено"
            if grade and grade.passed is True
            else "Незачтено"
            if grade and grade.passed is False
            else grade.label
            if grade
            else self.grades.get(graded.id)
            if graded
            else None
        )
        plan_work = self.view.plan_deadlines.get(assessment.id)
        deadline = assessment.due_at
        due_week = assessment.planned_due_week.value if assessment.planned_due_week else None
        if plan_work:
            deadline = (
                plan_work.exact_due_at
                if plan_work.deadline_kind == "EXACT_INCLUSIVE"
                else plan_work.due_date
                if plan_work.deadline_kind == "DATE_EXCLUSIVE"
                else None
            )
            due_week = plan_work.due_week if plan_work.deadline_kind == "WEEK_ONLY" else None
        return (
            assessment.title,
            assessment.type,
            deadline,
            due_week,
            facts["status"],
            facts["attempts"],
            history[-1].occurred_at if history else None,
            evaluation,
            graded.attempt_no if graded else None,
            numeric,
        )

    def item_rows(self, students, assessments):
        rows = []
        for student in students:
            for assessment in assessments:
                for attempt in self.history(student, assessment):
                    for result in self.results[attempt.id]:
                        item = self.view.items[result.assessment_item_id]
                        rows.append(
                            (
                                student.full_name,
                                assessment.title,
                                attempt.attempt_no,
                                item.title,
                                result.outcome,
                                result.score,
                                result.max_score,
                            )
                        )
        return ReportTable(
            "items",
            "Результаты частей",
            (
                ("student", "ФИО"),
                ("assessment", "Работа"),
                ("attempt", "Попытка"),
                ("item", "Часть"),
                ("outcome", "Результат"),
                ("score", "Балл"),
                ("max_score", "Максимум"),
            ),
            tuple(rows),
        )

    def attendance(self, students):
        return self.view.attendance_summary(self.lessons, {s.id for s in students})

    def report(self, kind, student_id=None, assessment_id=None):
        context = self.context
        metadata = [
            ("Учебный период", context.term.name),
            ("Дисциплина", context.course.name),
            ("Группа", context.group.number),
            (
                "Состав",
                "Включая архив и завершивших участие" if self.historical else "Текущие участники",
            ),
        ]
        tables = []
        students, assessments = self.students, self.assessments
        if kind == ReportKind.STUDENT:
            student = next((s for s in students if s.id == student_id), None)
            if student is None:
                raise ApplicationError("not_found")
            students = (student,)
            metadata.append(("ФИО", student.full_name))
            tables.append(
                ReportTable(
                    "works",
                    "Работы",
                    WORK_COLUMNS,
                    tuple(self.work_row(student, a) for a in assessments),
                )
            )
            attempts = tuple(
                (
                    a.title,
                    entry.attempt_no,
                    entry.occurred_at,
                    entry.result,
                    self.grades.get(entry.id),
                    entry.score,
                    entry.max_score,
                )
                for a in assessments
                for entry in self.history(student, a)
            )
            tables.append(
                ReportTable(
                    "attempts",
                    "История попыток",
                    (
                        ("assessment", "Работа"),
                        ("attempt", "№"),
                        ("occurred_at", "Дата"),
                        ("result", "Результат"),
                        ("grade", "Оценка"),
                        ("score", "Балл"),
                        ("max_score", "Максимум"),
                    ),
                    attempts,
                )
            )
            summary = self.view.student_summary(student.id, context.offering.id)
            for key, title, evidence in (
                ("topics", "Факты по темам", summary.topics),
                ("skills", "Факты по навыкам", summary.skills),
            ):
                tables.append(
                    ReportTable(
                        key,
                        title,
                        (
                            ("title", "Тема / навык"),
                            ("evidence", "Свидетельств"),
                            ("attempts", "Попыток"),
                            ("items", "Результатов частей"),
                            ("correct", "Верно"),
                            ("partial", "Частично"),
                            ("incorrect", "Неверно"),
                            ("sources", "Источники (тип: ID)"),
                        ),
                        tuple(
                            (
                                e.title,
                                e.evidence_count,
                                e.assessment_attempt_count,
                                e.item_result_count,
                                e.correct,
                                e.partial,
                                e.incorrect,
                                "; ".join(
                                    f"{kind}: {id.value}" for kind, id in sorted(e.evidence_ids)
                                ),
                            )
                            for e in sorted(evidence, key=lambda e: (e.title.casefold(), e.id))
                        ),
                    )
                )
        elif kind == ReportKind.ASSESSMENT:
            assessment = next((a for a in assessments if a.id == assessment_id), None)
            if assessment is None:
                raise ApplicationError("not_found")
            assessments = (assessment,)
            metadata.extend(
                (
                    ("Работа", assessment.title),
                    ("Тип", assessment.type),
                    ("Срок", assessment.due_at),
                    (
                        "Неделя срока",
                        assessment.planned_due_week.value if assessment.planned_due_week else None,
                    ),
                )
            )
        elif kind == ReportKind.GROUP:
            rows = []
            for student in students:
                summary = self.view.student_summary(student.id, context.offering.id, evidence=False)
                counts = Counter(self.view.work_facts(student.id, a)["status"] for a in assessments)
                rows.append(
                    (
                        student.full_name,
                        len(assessments),
                        summary.assessments_completed,
                        summary.attempts_total,
                        *[counts[s] for s in StudentWorkStatus],
                    )
                )
            tables.append(
                ReportTable(
                    "students",
                    "Студенты",
                    (
                        ("student", "ФИО"),
                        ("works", "Работ"),
                        ("completed", "Зачтено"),
                        ("attempts", "Попыток"),
                        *((s.value.lower(), s) for s in StudentWorkStatus),
                    ),
                    tuple(rows),
                )
            )
        else:
            raise ValueError("Unknown report kind")
        if kind != ReportKind.STUDENT:
            tables.append(
                ReportTable(
                    "works",
                    "Результаты работ",
                    (("student", "ФИО"), *WORK_COLUMNS),
                    tuple(
                        (s.full_name, *self.work_row(s, a)) for s in students for a in assessments
                    ),
                )
            )
            distributions = []
            for a in assessments:
                facts = [self.view.work_facts(s.id, a) for s in students]
                for status in StudentWorkStatus:
                    distributions.append(
                        (a.title, "Статус", status, sum(f["status"] == status for f in facts))
                    )
                for count, total in sorted(Counter(f["attempts"] for f in facts).items()):
                    distributions.append((a.title, "Попыток", count, total))
            tables.append(
                ReportTable(
                    "distribution",
                    "Распределение фактов",
                    (
                        ("assessment", "Работа"),
                        ("fact", "Факт"),
                        ("value", "Значение"),
                        ("students", "Студентов"),
                    ),
                    tuple(distributions),
                )
            )
        tables.append(self.item_rows(students, assessments))
        if kind != ReportKind.ASSESSMENT:
            tables.append(
                ReportTable(
                    "attendance",
                    "Посещаемость",
                    (("student", "ФИО"), *ATTENDANCE_COLUMNS),
                    tuple((s.full_name, *_attendance_row(self.attendance((s,)))) for s in students),
                )
            )
            tables.append(
                ReportTable(
                    "attendance_total",
                    "Итоги посещаемости",
                    ATTENDANCE_COLUMNS,
                    (_attendance_row(self.attendance(students)),),
                )
            )
        titles = {
            ReportKind.STUDENT: "Отчёт по студенту",
            ReportKind.GROUP: "Отчёт по группе",
            ReportKind.ASSESSMENT: "Отчёт по работе / РК",
        }
        return Report(
            kind, titles[kind], context.offering.id, self.view.as_of, tuple(metadata), tuple(tables)
        )


class ReportingService:
    """StudiumService mixin. All report facts come from one read transaction."""

    def report_contexts(self, term_id, *, historical=False):
        with self._transaction() as r:
            values = {
                name: getattr(r, name).list(include_deleted=historical)
                for name in ("terms", "courses", "groups", "offerings")
            }
        terms, courses, groups = (
            {v.id: v for v in values[name]} for name in ("terms", "courses", "groups")
        )
        return tuple(
            sorted(
                (
                    OfferingContext(o, terms[o.term_id], courses[o.course_id], groups[o.group_id])
                    for o in values["offerings"]
                    if o.term_id == term_id
                    and o.term_id in terms
                    and o.course_id in courses
                    and o.group_id in groups
                ),
                key=lambda c: (c.course.name.casefold(), c.group.number.casefold(), c.offering.id),
            )
        )

    def _report_projection(self, offering_id, historical, as_of):
        at = self._clock() if as_of is None else as_of
        if not isinstance(at, UtcInstant):
            raise ValueError("as_of must be an explicit UTC instant")
        with self._transaction() as r:
            snapshot = _ReportSnapshot(r, historical=historical)
        return _Projection(snapshot, at, offering_id, historical)

    def report_choices(self, offering_id, *, historical=False):
        projection = self._report_projection(offering_id, historical, None)
        return ReportChoices(
            tuple((s.id, s.full_name) for s in projection.students),
            tuple((a.id, a.title) for a in projection.assessments),
        )

    def build_report(
        self,
        kind,
        offering_id,
        *,
        student_id=None,
        assessment_id=None,
        historical=False,
        as_of=None,
    ):
        return self._report_projection(offering_id, historical, as_of).report(
            ReportKind(kind), student_id, assessment_id
        )
