"""Small filtered multiselect of existing bank records, without copying tasks."""

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from studium.presentation.desktop.components import table
from studium.presentation.desktop.models import TableModel


class ProblemPicker(QDialog):
    def __init__(self, service, course_id, selected_ids=(), parent=None):
        super().__init__(parent)
        from studium.presentation.desktop.library import PURPOSE_LABELS

        self.service, self.picked = service, set(selected_ids)
        self.setWindowTitle("Добавить из банка задач")
        self.resize(760, 590)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.addLayout(form)
        self.search, self.tags = QLineEdit(), QLineEdit()
        self.course, self.topic, self.purpose = QComboBox(), QComboBox(), QComboBox()
        for course in service.list_courses():
            self.course.addItem(course.name, course.id)
        from studium.presentation.desktop.workflow_widgets import data_index

        self.course.setCurrentIndex(data_index(self.course, course_id))
        self.course.setEnabled(False)
        self.topic.addItem("Все темы", None)
        for topic in service.list_course_topics(course_id):
            self.topic.addItem(topic.title, topic.id)
        self.purpose.addItem("Любое назначение", None)
        for value, title in PURPOSE_LABELS.items():
            self.purpose.addItem(title, value)
        for label, field in (
            ("Поиск", self.search),
            ("Дисциплина", self.course),
            ("Тема", self.topic),
            ("Назначение", self.purpose),
            ("Теги", self.tags),
        ):
            form.addRow(label, field)
        self.model = TableModel(
            [
                ("Задача", lambda p: p.title),
                ("Номер", lambda p: p.identifier),
                ("Теги", lambda p: ", ".join(p.tags)),
            ]
        )
        self.view = table(self.model)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.view, 1)
        self.view.selectionModel().selectionChanged.connect(self.selection_changed)
        for field in (self.search, self.tags):
            field.textChanged.connect(self.refresh)
        for field in (self.topic, self.purpose):
            field.currentIndexChanged.connect(self.refresh)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Добавить выбранные")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self):
        rows = self.service.list_materials(
            "problems",
            course_id=self.course.currentData(),
            search=self.search.text(),
            topic_id=self.topic.currentData(),
            purpose=self.purpose.currentData(),
            tags=self.tags.text().split(","),
        )
        self.view.selectionModel().blockSignals(True)
        self.model.replace_rows(rows)
        from PySide6.QtCore import QItemSelectionModel

        for index, row in enumerate(rows):
            if row.id in self.picked:
                self.view.selectionModel().select(
                    self.model.index(index, 0),
                    QItemSelectionModel.SelectionFlag.Select
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
        self.view.selectionModel().blockSignals(False)

    def selection_changed(self, *_):
        visible = {p.id for p in self.model.rows}
        self.picked.difference_update(visible)
        self.picked.update(
            self.model.rows[i.row()].id for i in self.view.selectionModel().selectedRows()
        )

    def ids(self):
        return tuple(sorted(self.picked))
