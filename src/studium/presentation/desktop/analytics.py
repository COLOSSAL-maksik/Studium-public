"""Compact Qt views of fact-derived application DTOs and optional item recording."""

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.domain.enums import AssessmentType, ItemOutcome
from studium.domain.value_objects import UtcInstant
from studium.presentation.desktop.components import hint, run_action, table, toolbar
from studium.presentation.desktop.dialogs import FormDialog, combo, number_value
from studium.presentation.desktop.messages import (
    ITEM_OUTCOME_LABELS,
    STATUS_LABELS,
    TEXT,
    context_label,
)
from studium.presentation.desktop.models import TableModel, display_score, display_time
from studium.presentation.desktop.theme import resize_to_screen
from studium.presentation.desktop.visuals import text_label


def metric(value, *, percent=False, missing=None):
    if value is None:
        return missing or TEXT["no_data"]
    if percent:
        return f"{value * 100:.1f}%".replace(".", ",")
    return f"{value:g}".replace(".", ",") if isinstance(value, float) else str(value)


def rate(value, *, applicable=True):
    return metric(
        value, percent=True, missing=TEXT["no_data"] if applicable else TEXT["not_applicable"]
    )


def response_time(seconds):
    if seconds is None:
        return TEXT["no_data"]
    return f"{seconds / 3600:.1f} ч".replace(".", ",")


def attendance_rows(a):
    return [
        ("Занятий", metric(a.lessons_total)),
        ("Присутствовало / опоздало / отсутствовало", f"{a.present} / {a.late} / {a.absent}"),
        (
            "Уважительная причина / неизвестно / не отмечено",
            f"{a.excused} / {a.unknown} / {a.unmarked}",
        ),
        ("Доля посещённых занятий", rate(a.attendance_rate)),
    ]


def question_rows(q):
    return [
        (
            "Вопросов / открытых / ожидают преподавателя",
            f"{q.question_cases_count} / {q.open_questions} / {q.questions_waiting_for_teacher}",
        ),
        (
            "Сообщений студента / преподавателя",
            f"{q.student_message_count} / {q.teacher_message_count}",
        ),
        (
            "Ответ: среднее / медиана",
            f"{response_time(q.average_teacher_response_seconds)} / {response_time(q.median_teacher_response_seconds)}",
        ),
        (
            "Эпизодов с ответом / без ответа",
            f"{q.completed_response_count} / {q.unanswered_episode_count}",
        ),
        ("Неоднозначных эпизодов ответа", metric(q.ambiguous_response_count)),
    ]


def evidence_columns():
    return [
        ("Тема / навык", lambda e: e.title),
        ("Фактов", lambda e: e.evidence_count),
        ("Оценено", lambda e: e.evaluated),
        ("Верно / частично / неверно", lambda e: f"{e.correct} / {e.partial} / {e.incorrect}"),
        ("Балл / максимум", lambda e: metric(e.average_normalized_item_score, percent=True)),
        ("Вопросов", lambda e: e.question_cases_linked),
    ]


class SummaryTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.model = TableModel([("Показатель", lambda r: r[0]), ("Значение", lambda r: r[1])])
        self.view = table(self.model)
        layout.addWidget(self.view)

    def replace_rows(self, rows):
        self.model.replace_rows(rows)


class AnalyticsComparison(QWidget):
    """Compare two explicit cutoffs; read-only queries never create StudentWork."""

    refreshed = Signal(object)

    def __init__(self, query, rows, parent=None):
        super().__init__(parent)
        self.query, self.rows = query, rows
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.enabled = QCheckBox(TEXT["compare_at"])
        self.cutoff = QDateTimeEdit(QDateTime.currentDateTime().addDays(-7))
        self.cutoff.setCalendarPopup(True)
        self.cutoff.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.cutoff.setEnabled(False)
        self.enabled.toggled.connect(self.cutoff.setEnabled)
        from studium.presentation.desktop.workflow_widgets import direct_calendar

        direct_calendar(self.cutoff)
        self.cutoff.dateTimeChanged.connect(
            lambda _: run_action(self, self.refresh) if self.enabled.isChecked() else None
        )
        controls.addWidget(self.enabled)
        controls.addWidget(self.cutoff)
        self.refresh_button = QPushButton(TEXT["analytics_refresh"])
        self.refresh_button.clicked.connect(lambda: run_action(self, self.refresh))
        self.enabled.toggled.connect(lambda _: run_action(self, self.refresh))
        controls.addWidget(self.refresh_button)
        controls.addStretch()
        layout.addLayout(controls)
        self.scope = hint(layout, TEXT["analytics_scope"])
        self.model = TableModel(
            [
                ("Показатель", lambda r: r[0]),
                ("Сейчас", lambda r: r[1]),
                ("На выбранный момент", lambda r: r[2]),
            ]
        )
        self.view = table(self.model)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.view.setColumnWidth(0, 390)
        layout.addWidget(self.view)

    def refresh(self):
        self.summary = self.query(None)
        current = self.rows(self.summary)
        previous = None
        if self.enabled.isChecked():
            cutoff = UtcInstant.from_epoch_microseconds(
                self.cutoff.dateTime().toMSecsSinceEpoch() * 1000
            )
            previous = dict(self.rows(self.query(cutoff)))
            self.scope.setText(
                TEXT["analytics_scope"] + "\n" + TEXT["comparison_at"] + ": " + display_time(cutoff)
            )
        else:
            self.scope.setText(TEXT["analytics_scope"])
        self.model.replace_rows(
            [
                (
                    name,
                    value,
                    previous.get(name, TEXT["not_applicable"]) if previous is not None else "—",
                )
                for name, value in current
            ]
        )
        self.view.setColumnHidden(2, previous is None)
        self.refreshed.emit(self.summary)


class SummaryHighlights(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.values = []
        for title in ["Выполнение", "С первого раза", "Своевременность", "Посещаемость", "Вопросы"]:
            column = QVBoxLayout()
            label = QLabel(title)
            label.setWordWrap(True)
            label.setProperty("role", "hint")
            value = QLabel()
            value.setProperty("role", "metric")
            value.setWordWrap(True)
            column.addWidget(label)
            column.addWidget(value)
            layout.addLayout(column, 1)
            self.values.append(value)

    def update_summary(self, summary):
        completion = getattr(
            summary, "completion_rate", getattr(summary, "average_completion_rate", None)
        )
        values = [
            rate(completion),
            rate(summary.first_pass_rate),
            rate(summary.on_time_rate, applicable=bool(summary.deadline_assessments_total)),
            rate(summary.attendance.attendance_rate),
            str(summary.questions.open_questions),
        ]
        for label, value in zip(self.values, values, strict=True):
            label.setText(value)


class StudentProgressWidget(QWidget):
    def __init__(self, service, student_id, offering_id, parent=None):
        super().__init__(parent)
        self.service, self.student_id, self.offering_id = service, student_id, offering_id
        layout = QVBoxLayout(self)
        self.module = QComboBox()
        self.module.addItem("Весь семестр", None)
        program = service.program_for_offering(offering_id)
        canonical = service.semester_plan(offering_id)
        for module in (
            canonical.modules
            if canonical
            else service.list_program_modules(program.id)
            if program
            else ()
        ):
            self.module.addItem(module.title, module.id)
        layout.addWidget(self.module)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.work_fact_models = {}
        for category, title in (
            (AssessmentType.HOMEWORK, "Домашнее задание"),
            (AssessmentType.CONTROL_WORK, "Рубежный контроль"),
            (AssessmentType.EXAM, "Экзамен"),
        ):
            page = QWidget()
            body = QVBoxLayout(page)
            hint(
                body,
                "Факты по каждой работе. Результаты задач и навыков доступны в истории попыток.",
            )
            model = TableModel(
                [
                    ("Работа", lambda f: f.assessment.title),
                    ("Состояние", lambda f: STATUS_LABELS[f.status]),
                    ("Попыток", lambda f: f.attempts),
                    ("Первая сдача", lambda f: display_time(f.first_submission)),
                    ("Последняя сдача", lambda f: display_time(f.latest_submission)),
                    ("Зачтено", lambda f: display_time(f.completed_at)),
                    ("Относительно срока", lambda f: f.deadline_relation),
                ]
            )
            view = table(model)
            view.doubleClicked.connect(
                lambda _, view=view: run_action(self, lambda: self.open_work_facts(view))
            )
            body.addWidget(view)
            self.work_fact_models[category] = model
            self.tabs.addTab(page, title)
        self.metrics = AnalyticsComparison(
            lambda cutoff: service.student_progress(
                student_id, offering_id, as_of=cutoff, module_id=self.module.currentData()
            ),
            self.rows,
            self,
        )
        self.highlights = SummaryHighlights(self)
        layout.insertWidget(0, self.highlights)
        self.metrics.refreshed.connect(self.highlights.update_summary)
        self.tabs.addTab(self.metrics, "Показатели")
        from studium.presentation.desktop.qa_workflow import PackageSummary

        self.package_summary = PackageSummary(
            service,
            student_id,
            self,
            on_section=lambda section: self.tabs.setCurrentWidget(
                evidence if section == "evidence" else self.charts
            ),
        )
        self.tabs.insertTab(0, self.package_summary, "Сводка")
        self.tabs.setCurrentIndex(0)
        evidence = QWidget()
        evidence_layout = QVBoxLayout(evidence)
        hint(evidence_layout, TEXT["evidence_hint"])
        self.evidence_model = TableModel(evidence_columns())
        self.evidence_view = table(self.evidence_model)
        self.evidence_view.doubleClicked.connect(lambda _: run_action(self, self.open_evidence))
        evidence_layout.addWidget(self.evidence_view)
        self.skill_model = TableModel(
            [("Навык", lambda r: r[0]), ("Верно / частично / неверно", lambda r: r[1])]
        )
        evidence_layout.addWidget(table(self.skill_model))
        self.tabs.addTab(evidence, TEXT["evidence"])
        from studium.presentation.desktop.charts import AnalyticsCharts

        self.charts = AnalyticsCharts(self)
        self.tabs.addTab(self.charts, "Графики")
        self.tabs.currentChanged.connect(
            lambda _: self.highlights.setVisible(self.tabs.currentWidget() is self.metrics)
        )
        self.tabs.currentChanged.connect(
            lambda _: self.refresh_charts() if self.tabs.currentWidget() is self.charts else None
        )
        self.module.currentIndexChanged.connect(lambda _: run_action(self, self.refresh))
        self.highlights.hide()

    def open_work_facts(self, view):
        from studium.presentation.desktop.components import selected
        from studium.presentation.desktop.dialogs import HistoryDialog
        from studium.presentation.desktop.navigation import present_detail

        fact = selected(view)
        if fact and fact.work_id:
            present_detail(
                HistoryDialog(self.service, fact.work_id, asynchronous=True, parent=self),
                self,
                title=fact.assessment.title,
            )

    def refresh_charts(self):
        if not hasattr(self.metrics, "summary"):
            self.metrics.refresh()
        self.charts.update_data(
            self.metrics.summary,
            self.service.workflow_analytics(
                self.offering_id, student_id=self.student_id, module_id=self.module.currentData()
            ),
        )

    @staticmethod
    def rows(s):
        return (
            [
                (
                    "Выполнено работ",
                    f"{s.assessments_completed} из {s.assessments_total} · {rate(s.completion_rate)}",
                ),
                ("Начато работ / попыток", f"{s.assessments_started} / {s.attempts_total}"),
                ("С первого раза", f"{s.first_pass_count} · {rate(s.first_pass_rate)}"),
                (
                    "Среднее число попыток на начатую работу",
                    metric(s.average_attempts_per_started_work),
                ),
                (
                    "Своевременно / поздно / не сдано в срок",
                    f"{s.on_time_count} / {s.late_count} / {s.overdue_count}",
                ),
                (
                    "Доля своевременных сдач",
                    rate(
                        s.on_time_rate,
                        applicable=bool(s.deadline_assessments_total),
                    ),
                ),
                ("Средний балл / максимум", metric(s.average_normalized_score, percent=True)),
            ]
            + attendance_rows(s.attendance)
            + question_rows(s.questions)
        )

    def refresh(self):
        if hasattr(self, "package_summary"):
            self.package_summary.refresh()
        self.metrics.refresh()
        s = self.metrics.summary
        facts = self.service.student_work_facts(
            self.student_id, self.offering_id, module_id=self.module.currentData()
        )
        for category, model in self.work_fact_models.items():
            model.replace_rows([fact for fact in facts if fact.assessment.type == category])
        self.evidence_model.replace_rows([*s.topics, *s.skills])
        context = next(
            c for c in self.service.list_offerings() if c.offering.id == self.offering_id
        )
        skills = {v.id: v for v in self.service.list_course_skills(context.course.id)}
        counts = self.service.skill_outcome_counts(
            self.offering_id, self.student_id, module_id=self.module.currentData()
        )
        self.skill_model.replace_rows(
            [
                (
                    skills[id].title,
                    " / ".join(
                        str(values.get(outcome, 0))
                        for outcome in (
                            ItemOutcome.CORRECT,
                            ItemOutcome.PARTIAL,
                            ItemOutcome.INCORRECT,
                        )
                    ),
                )
                for id, values in counts.items()
                if id in skills
            ]
        )
        if self.tabs.currentWidget() is self.charts:
            self.refresh_charts()

    def open_evidence(self):
        from studium.application.analytics_models import SkillEvidenceSummary
        from studium.presentation.desktop.components import selected

        value = selected(self.evidence_view)
        if value:
            skill = isinstance(value, SkillEvidenceSummary)
            values = (
                self.service.list_course_skills(value.course_id)
                if skill
                else self.service.list_course_topics(value.course_id)
            )
            entity = next(v for v in values if v.id == value.id)
            EvidenceDialog(
                self.service,
                entity,
                skill=skill,
                offering_id=self.offering_id,
                student_id=self.student_id,
                module_id=self.module.currentData(),
                parent=self,
            ).exec()


class GroupAnalyticsWidget(QWidget):
    def __init__(self, service_provider, context_provider, parent=None):
        super().__init__(parent)
        self.service_provider, self.context_provider = service_provider, context_provider
        layout = QVBoxLayout(self)
        self.module = QComboBox()
        self.module.addItem("Весь семестр", None)
        self.module.currentIndexChanged.connect(lambda _: run_action(self, self.refresh))
        layout.addWidget(self.module)
        self.metrics = AnalyticsComparison(self.query, self.rows, self)
        self.highlights = SummaryHighlights(self)
        layout.addWidget(self.highlights)
        self.metrics.refreshed.connect(self.highlights.update_summary)
        from studium.presentation.desktop.charts import AnalyticsCharts

        self.charts = AnalyticsCharts(self)
        from studium.presentation.desktop.progress_charts import ProgressCharts

        self.progress_charts = ProgressCharts(self)
        self.evidence_model = TableModel(evidence_columns())
        evidence = QWidget()
        evidence_layout = QVBoxLayout(evidence)
        hint(evidence_layout, TEXT["evidence_hint"])
        self.evidence_view = table(self.evidence_model)
        evidence_layout.addWidget(self.evidence_view)
        self.evidence_view.doubleClicked.connect(lambda _: run_action(self, self.open_evidence))
        self.skill_model = TableModel(
            [("Навык", lambda r: r[0]), ("Верно / частично / неверно", lambda r: r[1])]
        )
        evidence_layout.addWidget(table(self.skill_model))
        self.tabs = QTabWidget()
        self.tabs.addTab(self.metrics, "Показатели")
        self.tabs.addTab(self.progress_charts, "Прогресс")
        self.tabs.addTab(evidence, "Темы и навыки")
        self.tabs.addTab(self.charts, "Графики")
        self.tabs.currentChanged.connect(
            lambda _: self.highlights.setVisible(self.tabs.currentWidget() is self.metrics)
        )
        self.tabs.currentChanged.connect(
            lambda _: self.refresh_charts() if self.tabs.currentWidget() is self.charts else None
        )
        layout.addWidget(self.tabs)

    def refresh_charts(self):
        if self.context_provider():
            if not hasattr(self.metrics, "summary"):
                self.metrics.refresh()
            self.charts.update_data(
                self.metrics.summary,
                self.service_provider().workflow_analytics(
                    self.context_provider().offering.id, module_id=self.module.currentData()
                ),
            )

    def query(self, cutoff):
        return self.service_provider().group_analytics(
            self.context_provider().offering.id, as_of=cutoff, module_id=self.module.currentData()
        )

    @staticmethod
    def rows(s):
        return (
            [
                ("Студентов", metric(s.student_count)),
                (
                    "Выполнено / начато работ",
                    f"{s.assessments_completed} / {s.assessments_started}",
                ),
                ("Средняя доля выполненных работ", rate(s.average_completion_rate)),
                (
                    "Распределение: выполнено работ → студентов",
                    "; ".join(
                        f"{v.completed_count} → {v.student_count}"
                        for v in s.completion_distribution
                    )
                    or TEXT["no_data"],
                ),
                ("С первого раза", f"{s.first_pass_count} · {rate(s.first_pass_rate)}"),
                ("Среднее число попыток на начатую работу", metric(s.average_attempts)),
                (
                    "Своевременно / поздно / не сдано в срок",
                    f"{s.on_time_count} / {s.late_count} / {s.overdue_count}",
                ),
                (
                    "Доля своевременных сдач",
                    rate(
                        s.on_time_rate,
                        applicable=bool(s.deadline_assessments_total),
                    ),
                ),
                (
                    "Студентов с открытыми вопросами / без ответа",
                    f"{s.students_with_open_questions} / {s.students_with_unanswered_questions}",
                ),
            ]
            + attendance_rows(s.attendance)
            + question_rows(s.questions)
        )

    def refresh(self):
        if self.context_provider():
            service = self.service_provider()
            offering = self.context_provider().offering
            program = service.program_for_offering(offering.id)
            canonical = service.semester_plan(offering.id)
            modules = (
                canonical.modules
                if canonical
                else service.list_program_modules(program.id)
                if program
                else ()
            )
            ids = [self.module.itemData(i) for i in range(1, self.module.count())]
            if ids != [m.id for m in modules]:
                self.module.blockSignals(True)
                self.module.clear()
                self.module.addItem("Весь семестр", None)
                for module in modules:
                    self.module.addItem(module.title, module.id)
                self.module.blockSignals(False)
            self.metrics.refresh()
            self.evidence_model.replace_rows(
                service.context_evidence(offering.id, module_id=self.module.currentData())
            )
            self.progress_charts.update_data(
                service.progress_chart_data(offering.id, module_id=self.module.currentData())
            )
            skills = {
                s.id: s for s in service.list_course_skills(self.context_provider().course.id)
            }
            counts = service.skill_outcome_counts(offering.id, module_id=self.module.currentData())
            self.skill_model.replace_rows(
                [
                    (
                        skills[id].title,
                        " / ".join(
                            str(values.get(outcome, 0))
                            for outcome in (
                                ItemOutcome.CORRECT,
                                ItemOutcome.PARTIAL,
                                ItemOutcome.INCORRECT,
                            )
                        ),
                    )
                    for id, values in counts.items()
                    if id in skills
                ]
            )
            if self.tabs.currentWidget() is self.charts:
                self.refresh_charts()
        else:
            self.metrics.model.replace_rows([])

    def open_evidence(self):
        from studium.presentation.desktop.components import selected

        value = selected(self.evidence_view)
        if value:
            service = self.service_provider()
            from studium.application.analytics_models import SkillEvidenceSummary

            id = value.id
            skill = isinstance(value, SkillEvidenceSummary)
            values = (
                service.list_course_skills(value.course_id)
                if skill
                else service.list_course_topics(value.course_id)
            )
            entity = next(v for v in values if v.id == id)
            EvidenceDialog(
                service,
                entity,
                skill=skill,
                offering_id=self.context_provider().offering.id,
                module_id=self.module.currentData(),
                parent=self,
            ).exec()


class AssessmentAnalyticsWidget(QWidget):
    def __init__(self, service, assessment_id, parent=None):
        super().__init__(parent)
        self.service, self.assessment_id = service, assessment_id
        layout = QVBoxLayout(self)
        hint(layout, TEXT["analytics_scope"])
        toolbar(layout, [(TEXT["analytics_refresh"], lambda: run_action(self, self.refresh))])
        self.metrics = SummaryTable(self)
        layout.addWidget(self.metrics)
        hint(layout, TEXT["item_results"])
        self.item_model = TableModel(
            [
                ("Часть работы", lambda i: i.title),
                ("Результатов", lambda i: i.result_count),
                (
                    "Верно / частично / неверно",
                    lambda i: f"{i.correct} / {i.partial} / {i.incorrect}",
                ),
                ("Не оценивалось", lambda i: i.not_evaluated),
                (
                    "Средний балл / максимум",
                    lambda i: metric(i.average_normalized_score, percent=True),
                ),
            ]
        )
        self.item_view = table(self.item_model)
        layout.addWidget(self.item_view)

    def refresh(self):
        s = self.service.assessment_analytics(self.assessment_id)
        self.summary = s
        self.metrics.replace_rows(
            [
                (
                    "Назначено / начали / не начинали",
                    f"{s.assigned_students} / {s.started} / {s.not_started}",
                ),
                (
                    "В процессе / на доработку / зачтено",
                    f"{s.in_progress} / {s.revision_required} / {s.passed}",
                ),
                (
                    "Попыток / среднее на начатую работу",
                    f"{s.attempts_total} / {metric(s.average_attempts)}",
                ),
                ("С первого раза", f"{s.first_pass_count} · {rate(s.first_pass_rate)}"),
                (
                    "Своевременно / поздно / не сдано в срок",
                    f"{s.on_time_count} / {s.late_count} / {s.overdue_count}",
                ),
                (
                    "Доля своевременных сдач",
                    rate(
                        s.on_time_rate,
                        applicable=bool(s.deadline_assessments_total),
                    ),
                ),
                (
                    "Балл / максимум: среднее / медиана",
                    f"{metric(s.average_normalized_score, percent=True)} / {metric(s.median_normalized_score, percent=True)}",
                ),
            ]
        )
        self.item_model.replace_rows(s.items)


class EvidenceDialog(QDialog):
    def __init__(
        self,
        service,
        entity,
        *,
        skill=False,
        offering_id=None,
        student_id=None,
        module_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.service, self.entity, self.skill = service, entity, skill
        self.offering_id, self.student_id = offering_id, student_id
        self.module_id = module_id
        self.setWindowTitle(f"{entity.title} · {TEXT['evidence']}")
        resize_to_screen(self, 900, 690)
        layout = QVBoxLayout(self)
        hint(layout, f"{TEXT['skills' if skill else 'topics']}: {entity.title}")
        hint(layout, TEXT["evidence_hint"])
        self.scope = QComboBox()
        self.scope.addItem("Все учебные контексты дисциплины", None)
        for context in service.list_offerings():
            if context.course.id == entity.course_id:
                self.scope.addItem(context_label(context), context.offering.id)
        if offering_id:
            self.scope.setCurrentIndex(
                next(
                    (i for i in range(self.scope.count()) if self.scope.itemData(i) == offering_id),
                    0,
                )
            )
        layout.addWidget(self.scope)
        self.scope.setEnabled(module_id is None)
        self.scope.currentIndexChanged.connect(lambda _: run_action(self, self.refresh))
        self.descendants = QCheckBox("Включить дочерние темы без повторного счёта фактов")
        self.descendants.setChecked(True)
        self.descendants.setVisible(not skill)
        self.descendants.toggled.connect(lambda _: run_action(self, self.refresh))
        layout.addWidget(self.descendants)
        self.metrics = SummaryTable(self)
        layout.addWidget(self.metrics)
        self.refresh()

    def refresh(self):
        kwargs = dict(
            offering_id=self.scope.currentData(),
            student_id=self.student_id,
            module_id=self.module_id,
        )
        if self.skill:
            s = self.service.skill_evidence(self.entity.id, **kwargs)
            covering, items = s.assessments_covering_skill, s.assessment_items_covering_skill
        else:
            s = self.service.topic_evidence(
                self.entity.id, include_descendants=self.descendants.isChecked(), **kwargs
            )
            covering, items = s.assessments_covering_topic, s.assessment_items_covering_topic
        self.summary = s
        self.metrics.replace_rows(
            [
                ("Работ / частей работы", f"{covering} / {items}"),
                (
                    "Наблюдаемых фактов / попыток связанных работ",
                    f"{s.evidence_count} / {s.assessment_attempt_count}",
                ),
                ("Студентов с наблюдаемыми фактами", metric(s.students_with_evidence)),
                ("Результатов частей", metric(s.item_result_count)),
                ("Оценённых элементов", metric(s.evaluated)),
                ("Верно", metric(s.correct)),
                ("Частично", metric(s.partial)),
                ("Неверно", metric(s.incorrect)),
                ("Не оценивалось", metric(s.not_evaluated)),
                (
                    "Средний балл части / максимум",
                    metric(s.average_normalized_item_score, percent=True),
                ),
                (
                    "Связанных вопросов / студентов с вопросами",
                    f"{s.question_cases_linked} / {s.questions_by_students_count}",
                ),
                (
                    "Занятий с темой / навыком",
                    TEXT["not_applicable"] if self.skill else metric(s.lesson_exposure_count),
                ),
            ]
            + (
                attendance_rows(s.attendance)
                if not self.skill
                else [("Посещаемость занятий с навыком", TEXT["not_applicable"])]
            )
        )


class AttemptItemResultForm(FormDialog):
    def __init__(self, service, attempt, item, parent=None):
        super().__init__(
            f"Попытка {attempt.attempt_no} · {item.title}",
            lambda values: service.create_attempt_item_result(attempt.id, item.id, **values),
            parent,
        )
        self.outcome = combo({None: "Без категориального результата", **ITEM_OUTCOME_LABELS})
        self.outcome.setAccessibleName("Результат части")
        self.form.addRow("Результат части", self.outcome)
        self.outcome_status = text_label("")
        self.body_layout.addWidget(self.outcome_status)
        self.outcome.currentIndexChanged.connect(
            lambda _: self.show_outcome(self.outcome_status, self.outcome.currentData())
        )
        self.show_outcome(self.outcome_status, None)
        self.score = self.line("score")
        self.maximum = self.line(
            "max_score", str(item.max_score) if item.max_score is not None else ""
        )
        self.teacher_comment = self.notes("comment")
        history = service.history(attempt.student_work_id)
        self.body_layout.insertWidget(
            0, text_label(history.student.full_name + "\n" + history.assessment.title, "subheading")
        )
        self.advanced((self.score, self.maximum))
        self.skill_fields = {}
        self.skills_panel = QVBoxLayout()
        self.body_layout.addLayout(self.skills_panel)
        heading = QLabel("Навыки этой задачи")
        heading.setProperty("role", "subheading")
        self.skills_panel.addWidget(heading)
        linked = service.learning_targets("item_skills", item.id)
        assignment = next(
            (
                v
                for v in service.list_student_problem_assignments(attempt.student_work_id)
                if v.assessment_item_id == item.id
            ),
            None,
        )
        if assignment:
            linked = service.assignment_skills(assignment)
            hint(self.body_layout, assignment.title_snapshot + "\n" + assignment.statement_snapshot)
            files = QPushButton("Файлы назначенной задачи")
            files.clicked.connect(
                lambda: run_action(
                    self, lambda: AssignmentFilesDialog(service, assignment, self).exec()
                )
            )
            self.body_layout.addWidget(files)
        for skill in linked:
            self.add_skill(skill)
        self.skill_choice = QComboBox()
        self.skill_choice.setAccessibleName("Выбор навыка дисциплины")
        for skill in service.list_course_skills(history.context.course.id):
            self.skill_choice.addItem(skill.title, skill)
        row = QHBoxLayout()
        row.addWidget(self.skill_choice, 1)
        button = QPushButton("Добавить навык из дисциплины")
        button.clicked.connect(
            lambda: (
                self.add_skill(self.skill_choice.currentData())
                if self.skill_choice.currentData()
                else None
            )
        )
        row.addWidget(button)
        self.body_layout.addLayout(row)
        hint(self.body_layout, TEXT["item_result_hint"])

    def values(self):
        score = number_value(self.score)
        outcome = self.outcome.currentData()
        return dict(
            outcome=ItemOutcome(outcome) if outcome is not None else None,
            score=score,
            max_score=number_value(self.maximum) if score is not None else None,
            teacher_comment=self.teacher_comment.toPlainText() or None,
            skill_results=tuple(
                (id, ItemOutcome(field.currentData()), "")
                for id, field in self.skill_fields.items()
                if field.currentData() is not None
            ),
        )

    def add_skill(self, skill):
        if skill.id in self.skill_fields:
            return
        row = QHBoxLayout()
        row.addWidget(QLabel(skill.title), 1)
        field = combo({None: "Не отмечено", **ITEM_OUTCOME_LABELS})
        field.setAccessibleName(skill.title + " · результат навыка")
        self.skill_fields[skill.id] = field
        status = text_label("—")
        status.setFixedWidth(24)
        field.currentIndexChanged.connect(
            lambda _: self.show_outcome(status, field.currentData(), symbol_only=True)
        )
        row.addWidget(status)
        row.addWidget(field)
        self.skills_panel.addLayout(row)

    @staticmethod
    def show_outcome(label, outcome, *, symbol_only=False):
        symbol, role = {
            ItemOutcome.CORRECT: ("✓", "success"),
            ItemOutcome.PARTIAL: ("◷", "warning"),
            ItemOutcome.INCORRECT: ("×", "error"),
        }.get(outcome, ("—", "hint"))
        label.setText(
            symbol
            if symbol_only
            else symbol + " " + ITEM_OUTCOME_LABELS.get(outcome, "Результат пока не отмечен")
        )
        label.setProperty("role", role)
        label.style().unpolish(label)
        label.style().polish(label)


class AttemptItemsWidget(QWidget):
    def __init__(self, service, assessment_id, *, editable=True, parent=None):
        super().__init__(parent)
        self.service, self.assessment_id, self.editable = service, assessment_id, editable
        self.attempt = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint(layout, TEXT["item_result_hint"])
        row = QHBoxLayout()
        self.item_choice = QComboBox()
        row.addWidget(self.item_choice)
        self.add_button = QPushButton(TEXT["record_item_result"])
        self.add_button.clicked.connect(lambda: run_action(self, self.record))
        row.addWidget(self.add_button)
        layout.addLayout(row)
        self.model = TableModel(
            [
                ("Часть работы", lambda r: r[0].title),
                ("Результат", lambda r: ITEM_OUTCOME_LABELS.get(r[1].outcome, "—")),
                (TEXT["score"], lambda r: display_score(r[1].score, r[1].max_score)),
                (TEXT["comment"], lambda r: r[1].teacher_comment or ""),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.set_attempt(None)

    def set_attempt(self, attempt):
        self.attempt = attempt
        items = self.service.list_assessment_items(self.assessment_id, historical=True)
        results = self.service.list_attempt_item_results(attempt.id) if attempt else []
        item_by_id = {i.id: i for i in items}
        self.model.replace_rows([(item_by_id[r.assessment_item_id], r) for r in results])
        self.item_choice.clear()
        recorded = {r.assessment_item_id for r in results}
        for item in items:
            if item.id not in recorded and item.deleted_at is None:
                self.item_choice.addItem(item.title, item)
        enabled = self.editable and attempt is not None and self.item_choice.count() > 0
        self.add_button.setEnabled(enabled)
        self.item_choice.setEnabled(enabled)

    def record(self):
        item = self.item_choice.currentData()
        if self.editable and self.attempt and item:
            form = AttemptItemResultForm(self.service, self.attempt, item, self)
            if form.exec() == QDialog.DialogCode.Accepted:
                self.set_attempt(self.attempt)


class AssignmentFilesDialog(QDialog):
    def __init__(self, service, assignment, parent=None):
        super().__init__(parent)
        self.setWindowTitle(assignment.title_snapshot + " · снимки файлов")
        resize_to_screen(self, 780, 500)
        layout = QVBoxLayout(self)
        hint(
            layout,
            "Файлы на момент назначения задачи. Содержимое FileAsset сохраняется без повторного импорта.",
        )
        self.model = TableModel(
            [
                ("Файл", lambda e: e.asset.original_filename),
                ("Назначение", lambda e: e.attachment.role.value),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.model.replace_rows(service.assigned_task_files(assignment.id))

        def preview():
            from studium.presentation.desktop.components import selected
            from studium.presentation.desktop.files import FilePreviewDialog

            entry = selected(self.view)
            if entry:
                FilePreviewDialog(service, entry, self).exec()

        self.view.doubleClicked.connect(lambda _: run_action(self, preview))
        toolbar(layout, [("Открыть", lambda: run_action(self, preview))])
