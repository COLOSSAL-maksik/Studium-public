"""Small typed row forms for the annual editor; internal identities stay in widgets."""

from copy import deepcopy

from PySide6.QtWidgets import QComboBox, QLineEdit, QMessageBox, QPlainTextEdit, QSpinBox

from studium.domain import annual_program as a
from studium.domain.qa import score_cents, score_text
from studium.presentation.desktop.dialogs import FormDialog
from studium.presentation.desktop.learning import CheckList
from studium.presentation.desktop.qa_content import TopicTreePicker


def run_program_action(parent, action):
    from studium.presentation.desktop.components import run_action

    def command():
        try:
            return action()
        except ValueError as error:
            QMessageBox.warning(parent, "Учебная программа", str(error))
            return None

    return run_action(parent, command)


class RowForm(FormDialog):
    def __init__(self, title, source, callback, parent=None):
        super().__init__(title, callback, parent)
        self.source, self.readers = deepcopy(source), {}

    def submit(self):
        from studium.presentation.desktop.messages import error_message

        try:
            self.on_save(self.values())
        except Exception as error:
            self.error_label.setText(
                str(error) if isinstance(error, ValueError) else error_message(error)
            )
        else:
            self.accept()

    def text(self, name, label, *, multiline=False):
        field = (
            QPlainTextEdit(str(self.source.get(name, "") or ""))
            if multiline
            else QLineEdit(str(self.source.get(name, "") or ""))
        )
        if multiline:
            field.setMaximumHeight(110)
        self.form.addRow(label, field)
        self.readers[name] = field.toPlainText if multiline else field.text
        return field

    def integer(self, name, label, *, minimum=1, maximum=104, optional=False):
        field = QSpinBox()
        field.setRange(0 if optional else minimum, maximum)
        if optional:
            field.setSpecialValueText("Не указано")
        field.setValue(self.source.get(name) or (0 if optional else minimum))
        self.form.addRow(label, field)
        self.readers[name] = lambda: field.value() or None if optional else field.value()
        return field

    def choice(self, name, label, values, *, optional=False):
        field = QComboBox()
        if optional:
            field.addItem("Не указано", None)
        for value, title in values:
            field.addItem(title, value)
        field.setCurrentIndex(max(0, field.findData(self.source.get(name))))
        self.form.addRow(label, field)
        self.readers[name] = field.currentData
        return field

    def many(self, name, label, values):
        field = CheckList()
        field.fill(values, self.source.get(name, []))
        self.form.addRow(label, field)
        self.readers[name] = lambda: list(map(str, field.selected_ids()))
        return field

    def topics(self, service, course_id):
        search = QLineEdit()
        search.setPlaceholderText("Поиск тем")
        self.form.addRow(search)
        picker = TopicTreePicker()

        def refresh():
            picker.fill_topics(
                service.list_course_topics(course_id), self.source.get("topic_ids", [])
            )

        refresh()
        search.textChanged.connect(picker.search)
        self.form.addRow("Темы", picker)
        self.readers["topic_ids"] = lambda: list(map(str, picker.ids()))
        from studium.presentation.desktop.components import run_action, toolbar

        def create():
            original_selection = picker.ids()
            form = RowForm(
                "Новая тема",
                {"title": "", "description": ""},
                lambda v: service.create_topic(course_id, **v),
                self,
            )
            form.text("title", "Название")
            form.text("description", "Описание", multiline=True)
            form.choice(
                "parent_topic_id",
                "Родительская тема",
                [(t.id, t.title) for t in service.list_course_topics(course_id)],
                optional=True,
            )
            if form.exec():
                self.source["topic_ids"] = list(map(str, original_selection))
                refresh()

        toolbar(self.body_layout, [("Создать тему", lambda: run_action(self, create))])

    def score(self, name, label, fractional):
        value = self.source.get(name)
        field = QLineEdit("" if value is None else score_text(value))
        self.form.addRow(label, field)
        initial = field.text()
        self.readers[name] = lambda: (
            value
            if field.text() == initial
            else score_cents(field.text(), fractional=fractional)
            if field.text().strip()
            else None
        )
        return field

    def values(self):
        return self.source | {name: read() for name, read in self.readers.items()}


def lesson_form(editor, source, callback):
    form = RowForm("Плановое занятие", source, callback, editor)
    form.choice("kind", "Вид", a.LESSON_KINDS.items())
    form.text("title", "Название")
    form.text("hours", "Длительность, академические часы")
    form.integer("week", "Неделя семестра", optional=True)
    form.text("notes", "Примечание", multiline=True)
    form.topics(editor.service, editor.course.id)
    return form
