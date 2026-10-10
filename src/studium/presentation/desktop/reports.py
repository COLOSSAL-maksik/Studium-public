"""Report center using the global academic period, standard selectors and tables."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.application.errors import ApplicationError
from studium.application.report_models import ReportKind
from studium.presentation.desktop.components import hint, run_action, table
from studium.presentation.desktop.models import TableModel, display_time
from studium.presentation.desktop.report_export import (
    column_title,
    display_cell,
    export_csv,
    export_pdf,
    validate_export_destination,
)
from studium.presentation.desktop.theme import SPACING


class ReportsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.report = window, None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(SPACING)
        hint(layout, "Отчёты").setProperty("role", "heading")
        hint(
            layout,
            "Выберите контекст текущего учебного периода и просмотрите отчёт перед экспортом.",
        )
        form = QFormLayout()
        self.kind, self.contexts, self.students, self.assessments = (QComboBox() for _ in range(4))
        for combo, title in (
            (self.kind, "Вид отчёта"),
            (self.contexts, "Дисциплина / группа"),
            (self.students, "Студент"),
            (self.assessments, "Работа / РК"),
        ):
            combo.setAccessibleName(title)
            combo.setMinimumWidth(0)
            combo.setMinimumContentsLength(16)
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            form.addRow(title, combo)
        self.form = form
        for label, kind in (
            ("По студенту", ReportKind.STUDENT),
            ("По группе", ReportKind.GROUP),
            ("По работе / РК", ReportKind.ASSESSMENT),
        ):
            self.kind.addItem(label, kind)
        layout.addLayout(form)
        self.historical = QCheckBox("Включить архивный контекст и завершивших участие")
        layout.addWidget(self.historical)
        actions = QHBoxLayout()
        self.generate_button = QPushButton("Сформировать")
        self.generate_button.setProperty("primary", True)
        self.csv_button, self.pdf_button = (
            QPushButton("Сохранить CSV…"),
            QPushButton("Сохранить PDF…"),
        )
        self.help_button = QPushButton("Справка")
        for button in (self.generate_button, self.csv_button, self.pdf_button, self.help_button):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.metadata = QLabel()
        self.metadata.setTextFormat(Qt.TextFormat.PlainText)
        self.metadata.setWordWrap(True)
        self.metadata.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.metadata)
        self.empty = hint(layout, "Выберите контекст и сформируйте отчёт. Данных пока нет.")
        self.preview = QTabWidget()
        self.preview.setMinimumHeight(240)
        self.preview.setAccessibleName("Предпросмотр отчёта; CSV сохраняет выбранную таблицу")
        layout.addWidget(self.preview, 1)
        hint(
            layout,
            "CSV сохраняет выбранную таблицу. PDF содержит весь отчёт. "
            "Файлы сохраняются вне хранилища Studium и Git-репозиториев.",
        )
        self.kind.currentIndexChanged.connect(self.selection_changed)
        self.contexts.currentIndexChanged.connect(lambda: run_action(self, self.load_choices))
        self.students.currentIndexChanged.connect(self.invalidate)
        self.assessments.currentIndexChanged.connect(self.invalidate)
        self.historical.toggled.connect(lambda: run_action(self, self.refresh))
        self.generate_button.clicked.connect(lambda: run_action(self, self.generate))
        self.csv_button.clicked.connect(lambda: run_action(self, lambda: self.save("csv")))
        self.pdf_button.clicked.connect(lambda: run_action(self, lambda: self.save("pdf")))
        self.help_button.clicked.connect(lambda: window.open_help("reporting"))
        self.selection_changed()

    def invalidate(self):
        self.report = None
        self.metadata.clear()
        self.empty.setText("Выберите контекст и сформируйте отчёт.")
        while self.preview.count():
            widget = self.preview.widget(0)
            self.preview.removeTab(0)
            widget.deleteLater()
        self.csv_button.setEnabled(False)
        self.pdf_button.setEnabled(False)
        self.empty.show()
        self.generate_button.setEnabled(self.contexts.currentData() is not None)

    def selection_changed(self):
        self.form.setRowVisible(self.students, self.kind.currentData() == ReportKind.STUDENT)
        self.form.setRowVisible(self.assessments, self.kind.currentData() == ReportKind.ASSESSMENT)
        self.invalidate()

    def refresh(self):
        self.invalidate()
        service = self.window.service
        selected = self.contexts.currentData()
        selected_id = (
            selected.offering.id if selected else service.recent_offering_id() if service else None
        )
        term = service.active_term() if service else None
        self.contexts.blockSignals(True)
        self.contexts.clear()
        if term:
            for context in service.report_contexts(term.id, historical=self.historical.isChecked()):
                archived = any(
                    v.deleted_at is not None
                    for v in (context.offering, context.course, context.group, context.term)
                )
                label = f"{context.course.name} · {context.group.number}"
                self.contexts.addItem(label + (" (архив)" if archived else ""), context)
                if context.offering.id == selected_id:
                    self.contexts.setCurrentIndex(self.contexts.count() - 1)
        self.contexts.blockSignals(False)
        self.load_choices()

    def load_choices(self):
        previous = self.students.currentData(), self.assessments.currentData()
        self.invalidate()
        for combo in (self.students, self.assessments):
            combo.blockSignals(True)
            combo.clear()
        context = self.contexts.currentData()
        try:
            if context:
                choices = self.window.service.report_choices(
                    context.offering.id, historical=self.historical.isChecked()
                )
                for combo, values, selected_id in zip(
                    (self.students, self.assessments),
                    (choices.students, choices.assessments),
                    previous,
                    strict=True,
                ):
                    for id, label in values:
                        combo.addItem(label, id)
                    if combo.findData(selected_id) >= 0:
                        combo.setCurrentIndex(combo.findData(selected_id))
        except ApplicationError:
            self.empty.setText("Контекст больше недоступен. Обновите выбор отчёта.")
            self.generate_button.setEnabled(False)
        finally:
            for combo in (self.students, self.assessments):
                combo.blockSignals(False)

    def generate(self):
        self.invalidate()
        context = self.contexts.currentData()
        kind = self.kind.currentData()
        if context is None:
            return
        if (kind == ReportKind.STUDENT and self.students.currentData() is None) or (
            kind == ReportKind.ASSESSMENT and self.assessments.currentData() is None
        ):
            self.empty.setText("Нет студентов или работ для выбранного отчёта.")
            return
        try:
            report = self.window.service.build_report(
                kind,
                context.offering.id,
                student_id=self.students.currentData(),
                assessment_id=self.assessments.currentData(),
                historical=self.historical.isChecked(),
            )
        except ApplicationError:
            self.empty.setText("Выбор устарел. Обновите контекст и сформируйте отчёт снова.")
            return
        self.report = report
        self.metadata.setText(
            report.title
            + "\n"
            + " · ".join(f"{label}: {display_cell(value)}" for label, value in report.metadata)
            + f"\nСформирован: {display_time(report.generated_at)}"
        )
        for section in report.tables:
            widget = QWidget()
            section_layout = QVBoxLayout(widget)
            model = TableModel(
                [
                    (column_title(title), lambda row, i=i: display_cell(row[i]))
                    for i, (_, title) in enumerate(section.columns)
                ],
                section.rows,
                widget,
            )
            section_layout.addWidget(table(model), 1)
            if not section.rows:
                hint(section_layout, "Нет данных в этой таблице.")
            self.preview.addTab(widget, section.title)
        self.empty.setVisible(not report.tables[0].rows)
        self.empty.setText(
            "Основная таблица пуста. Проверьте другие разделы или выбранные условия."
        )
        self.csv_button.setEnabled(True)
        self.pdf_button.setEnabled(True)

    def save(self, format):
        report = self.report
        if report is None:
            return
        table_key = report.tables[self.preview.currentIndex()].key
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            f"studium-{report.kind.value}.{format}",
            f"{format.upper()} (*.{format})",
        )
        if not path:
            return
        destination = Path(path)
        if not destination.suffix:
            destination = destination.with_suffix(f".{format}")
        data_directory = self.window.data_directory
        try:
            validate_export_destination(destination, data_directory=data_directory)
            if format == "csv":
                export_csv(report, table_key, destination, data_directory=data_directory)
            else:
                export_pdf(report, destination, data_directory=data_directory)
        except ValueError as error:
            self.empty.setText(str(error))
            self.empty.show()
