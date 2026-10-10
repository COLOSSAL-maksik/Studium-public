"""Category → work → immutable attempts, with files and factual dates."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QTabBar, QVBoxLayout, QWidget

from studium.domain.enums import AssessmentType, EnrollmentStatus
from studium.presentation.desktop.components import hint, run_action, selected, table, toolbar
from studium.presentation.desktop.files import FilesWidget
from studium.presentation.desktop.messages import ASSESSMENT_LABELS
from studium.presentation.desktop.messages import STATUS_LABELS as WORK_LABELS
from studium.presentation.desktop.models import AttemptHistoryModel, TableModel, display_time

WORK_CATEGORIES = (
    (AssessmentType.HOMEWORK, "Домашнее задание"),
    (AssessmentType.CONTROL_WORK, "Рубежный контроль"),
    (AssessmentType.EXAM, "Экзамен"),
)


class StudentWorksWidget(QWidget):
    def __init__(self, service, context, entry, parent=None):
        super().__init__(parent)
        self.service, self.context, self.entry = service, context, entry
        self.facts, self.category_types = (), [value for value, _ in WORK_CATEGORIES]
        layout = QVBoxLayout(self)
        self.categories = QTabBar()
        self.categories.setExpanding(False)
        for _, title in WORK_CATEGORIES:
            self.categories.addTab(title)
        layout.addWidget(self.categories)
        self.work_model = TableModel(
            [
                ("Работа", lambda f: f.assessment.title),
                ("Состояние", lambda f: WORK_LABELS[f.status]),
                ("Попыток", lambda f: f.attempts),
                ("Последняя сдача", lambda f: display_time(f.latest_submission)),
                ("Срок", lambda f: f.deadline_relation),
            ]
        )
        self.work_view = table(self.work_model)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.work_view)
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self.caption = hint(detail_layout, "Выберите работу")
        self.caption.setProperty("role", "subheading")
        self.attempt_model = AttemptHistoryModel()
        self.attempt_view = table(self.attempt_model, stretch=False)
        self.attempt_view.setMinimumHeight(120)
        attempt_details = QSplitter(Qt.Orientation.Horizontal)
        attempt_details.addWidget(self.attempt_view)
        self.files = FilesWidget(
            service, editable=False, asynchronous=True, compact=True, parent=self
        )
        attempt_details.addWidget(self.files)
        attempt_details.setSizes([560, 340])
        detail_layout.addWidget(attempt_details, 1)
        self.splitter.addWidget(detail)
        self.splitter.setSizes([180, 300])
        layout.addWidget(self.splitter, 1)
        toolbar(
            layout,
            [
                (
                    "Открыть историю / записать попытку",
                    lambda: run_action(self, self.open_selected_work),
                ),
                ("Открыть попытку", lambda: run_action(self, self.open_attempt)),
            ],
        )
        self.work_view.selectionModel().currentChanged.connect(
            lambda *_: run_action(self, self.select_work)
        )
        self.attempt_view.selectionModel().currentChanged.connect(lambda *_: self.select_attempt())
        self.work_view.doubleClicked.connect(lambda _: run_action(self, self.open_selected_work))
        self.attempt_view.doubleClicked.connect(lambda _: run_action(self, self.open_attempt))
        self.categories.currentChanged.connect(self.filter_category)

    def refresh(self):
        self.facts = self.service.student_work_facts(
            self.entry.student.id, self.context.offering.id
        )
        for fact in self.facts:
            if fact.assessment.type not in self.category_types:
                self.category_types.append(fact.assessment.type)
                self.categories.addTab(ASSESSMENT_LABELS[fact.assessment.type])
        self.filter_category()

    def filter_category(self, *_):
        type = self.category_types[self.categories.currentIndex()]
        self.work_model.replace_rows([f for f in self.facts if f.assessment.type == type])
        self.attempt_model.replace_rows([])
        self.files.set_attempt(None)
        self.caption.setText(
            "Выберите работу" if self.work_model.rows else "В этой категории нет работ"
        )
        if self.work_model.rows:
            self.work_view.selectRow(0)

    def select_work(self):
        index = self.work_view.currentIndex()
        if not index.isValid():
            return
        fact = self.work_model.rows[index.row()]
        self.caption.setText(
            f"{fact.assessment.title} · {WORK_LABELS[fact.status]} · Попыток: {fact.attempts}"
        )
        history = self.service.history(fact.work_id) if fact.work_id else None
        self.attempt_model.replace_rows(history.entries if history else [])
        self.files.set_attempt(None)
        if self.attempt_model.rows:
            self.attempt_view.selectRow(0)

    def select_attempt(self):
        index = self.attempt_view.currentIndex()
        self.files.set_attempt(
            self.attempt_model.rows[index.row()].attempt if index.isValid() else None
        )

    def open_selected_work(self):
        from studium.presentation.desktop.dialogs import open_work

        fact = selected(self.work_view)
        if fact:
            open_work(
                self,
                self.service,
                self.entry.student.id,
                fact.assessment.id,
                editable=self.entry.enrollment.status == EnrollmentStatus.ACTIVE,
            )

    def open_attempt(self):
        from studium.presentation.desktop.dialogs import AttemptDetailsPage

        fact, history_entry = selected(self.work_view), selected(self.attempt_view)
        if fact and history_entry:
            present_detail_page = AttemptDetailsPage(
                self.service,
                self.service.history(fact.work_id),
                history_entry.attempt,
                editable=self.entry.enrollment.status == EnrollmentStatus.ACTIVE,
            )
            from studium.presentation.desktop.navigation import main_window

            window = main_window(self)
            if window:
                window.router.push(
                    present_detail_page, f"Попытка {history_entry.attempt.attempt_no}"
                )
