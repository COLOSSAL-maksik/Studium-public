"""Discipline → WorkProgram context, reusing existing catalogue and file widgets."""

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.domain.program import KnowledgeType, SemesterType
from studium.presentation.desktop.components import (
    confirm_delete,
    hint,
    panel,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import FormDialog, date_value
from studium.presentation.desktop.learning import CheckList, LearningCatalogueDialog
from studium.presentation.desktop.library import ContentEditor, LibraryList, MaterialFiles
from studium.presentation.desktop.messages import ASSESSMENT_LABELS
from studium.presentation.desktop.models import TableModel, display_time
from studium.presentation.desktop.visuals import EmptyState, ModuleTimeline, action_card, text_label
from studium.presentation.desktop.workflow_widgets import WeekSelector, data_index, direct_calendar


def embed(dialog, parent):
    dialog.setParent(parent, Qt.WindowType.Widget)
    dialog.setMinimumSize(0, 0)
    return dialog


class ProgramForm(FormDialog):
    def __init__(self, service, course, original=None, parent=None):
        super().__init__(
            "Рабочая программа",
            lambda values: (
                service.update_work_program(original, **values)
                if original
                else service.create_work_program(course.id, **values)
            ),
            parent,
        )
        self.original = original
        self.title = self.line("name", original.title if original else "", required=True)
        self.direction = QLineEdit(original.direction if original else "")
        self.faculty = QLineEdit(original.faculty if original else "")
        self.version = QLineEdit(
            original.version
            if original
            else str(service.active_term().starts_on.year)
            if service.active_term()
            else ""
        )
        self.term = QComboBox()
        for term in service.list_terms():
            self.term.addItem(term.name, term.id)
        if original:
            self.term.setCurrentIndex(data_index(self.term, original.term_id))
            self.term.setEnabled(False)
        self.form.addRow("Учебный период", self.term)
        self.form.addRow("Направление / образовательная программа", self.direction)
        self.form.addRow("Факультет", self.faculty)
        self.form.addRow("Версия / учебный год", self.version)
        self.semester = QComboBox()
        self.semester.addItem("Осенний", SemesterType.AUTUMN)
        self.semester.addItem("Весенний", SemesterType.SPRING)
        if original:
            self.semester.setCurrentIndex(self.semester.findData(original.semester))
        self.form.addRow("Семестр", self.semester)
        self.first = self.day(
            "starts_on",
            original.first_week_start
            if original
            else service.active_term().starts_on
            if service.active_term()
            else None,
        )
        self.form.labelForField(self.first).setText("Начало первой учебной недели")
        self.weeks = QSpinBox()
        self.weeks.setRange(1, 104)
        self.weeks.setValue(original.weeks if original else 17)
        self.form.addRow("Учебных недель", self.weeks)

    def values(self):
        values = dict(
            title=self.title.text().strip(),
            direction=self.direction.text().strip(),
            faculty=self.faculty.text().strip(),
            version=self.version.text().strip(),
            semester=SemesterType(self.semester.currentData()),
            first_week_start=date_value(self.first),
            weeks=self.weeks.value(),
        )
        if not self.original:
            values["term_id"] = self.term.currentData()
        return values


class OfferingProgramForm(FormDialog):
    def __init__(self, service, term, group, parent=None):
        super().__init__(
            "Дисциплина и программа группы",
            lambda values: service.create_offering(
                term.id, values["course_id"], group.id, work_program_id=values["work_program_id"]
            ),
            parent,
        )
        self.service, self.term = service, term
        self.course, self.program = QComboBox(), QComboBox()
        for course in service.list_courses():
            self.course.addItem(course.name, course)
        self.form.addRow("Дисциплина", self.course)
        self.form.addRow("Рабочая программа", self.program)
        self.create = QPushButton("Создать рабочую программу")
        self.create.clicked.connect(lambda: run_action(self, self.create_program))
        self.body_layout.addWidget(self.create)
        self.course.currentIndexChanged.connect(self.reload_programs)
        self.reload_programs()

    def reload_programs(self):
        self.program.clear()
        course = self.course.currentData()
        if course:
            for program in self.service.list_work_programs(course.id):
                if program.term_id == self.term.id:
                    self.program.addItem(program.title, program.id)
        self.save_button.setEnabled(self.program.count() > 0)

    def create_program(self):
        course = self.course.currentData()
        if (
            course
            and ProgramForm(self.service, course, parent=self).exec() == QDialog.DialogCode.Accepted
        ):
            self.reload_programs()

    def values(self):
        return dict(
            course_id=self.course.currentData().id, work_program_id=self.program.currentData()
        )


class ModuleForm(FormDialog):
    def __init__(self, service, program, original=None, parent=None):
        super().__init__(
            "Модуль",
            lambda values: (
                service.update_program_module(original, **values)
                if original
                else service.create_program_module(program.id, **values)
            ),
            parent,
        )
        self.title = self.line("name", original.title if original else "", required=True)
        self.start, self.end = QSpinBox(), QSpinBox()
        for field in (self.start, self.end):
            field.setRange(1, program.weeks)
        self.start.setValue(original.start_week if original else 1)
        self.end.setValue(original.end_week if original else min(6, program.weeks))
        self.order = original.sort_order if original else None
        self.form.addRow("Начальная неделя", self.start)
        self.form.addRow("Последняя неделя", self.end)

    def values(self):
        return dict(
            title=self.title.text(),
            start_week=self.start.value(),
            end_week=self.end.value(),
            sort_order=self.order if self.order is not None else self.start.value(),
        )


class ProgramWorkForm(FormDialog):
    def __init__(self, service, program, original=None, parent=None):
        self.program, self.original = program, original
        super().__init__(
            "Работа в программе",
            lambda values: (
                service.update_program_work(original, **values)
                if original
                else service.add_program_work(program.id, **values)
            ),
            parent,
        )
        self.definition = QComboBox()
        for work in service.list_work_definitions(program.course_id):
            self.definition.addItem(f"{ASSESSMENT_LABELS[work.type]} · {work.title}", work.id)
        if original:
            self.definition.setCurrentIndex(data_index(self.definition, original.definition_id))
            self.definition.setEnabled(False)
        self.form.addRow("Определение работы", self.definition)
        self.module = QComboBox()
        self.module.addItem("Без модуля", None)
        for module in service.list_program_modules(program.id):
            self.module.addItem(module.title, module.id)
        self.module.setCurrentIndex(
            max(0, data_index(self.module, original.module_id if original else None))
        )
        self.form.addRow("Модуль", self.module)
        self.issue = WeekSelector(
            original.planned_issue_week if original else None, weeks=program.weeks
        )
        self.due = WeekSelector(
            original.planned_due_week if original else None, weeks=program.weeks
        )
        self.form.addRow("Неделя выдачи", self.issue)
        self.form.addRow("Неделя сдачи / проведения", self.due)
        self.issue_date, self.issue_enabled = self.week_date(
            self.issue, "Конкретная дата выдачи", original.issue_date if original else None
        )
        self.due_date, self.due_enabled = self.week_date(
            self.due, "Конкретная дата сдачи", original.due_date if original else None
        )
        self.order = (
            original.sort_order
            if original
            else max(
                (link.sort_order for link, _ in service.program_work_definitions(program.id)),
                default=-1,
            )
            + 1
        )
        hint(self.body_layout, "Дата необязательна и выбирается внутри выбранной учебной недели.")
        self.save_button.setEnabled(self.definition.count() > 0)

    def week_date(self, selector, label, value):
        field = direct_calendar(QDateEdit())
        field.setDisplayFormat("dd.MM.yyyy")
        enabled = QCheckBox(label)
        enabled.setChecked(value is not None)
        self.form.addRow(enabled, field)

        def update():
            week = selector.currentData()
            enabled.setEnabled(week is not None)
            if week is None:
                enabled.setChecked(False)
            else:
                start, end = self.program.week_dates(week)
                field.setDateRange(
                    QDate(start.year, start.month, start.day), QDate(end.year, end.month, end.day)
                )
            field.setEnabled(enabled.isChecked() and week is not None)

        selector.currentIndexChanged.connect(update)
        enabled.toggled.connect(update)
        update()
        if value:
            field.setDate(QDate(value.year, value.month, value.day))
        return field, enabled

    def values(self):
        values = dict(
            module_id=self.module.currentData(),
            planned_issue_week=self.issue.currentData(),
            planned_due_week=self.due.currentData(),
            issue_date=date_value(self.issue_date) if self.issue_enabled.isChecked() else None,
            due_date=date_value(self.due_date) if self.due_enabled.isChecked() else None,
            sort_order=self.order,
        )
        if not self.original:
            values["definition_id"] = self.definition.currentData()
        return values


class ContentLinksWidget(QWidget):
    def __init__(self, service, kind, owner_id, values, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Найти и выбрать")
        layout.addWidget(self.search)
        self.choices = CheckList(values, [v.id for v in service.content_targets(kind, owner_id)])
        self.choices.setMaximumHeight(16777215)
        layout.addWidget(self.choices, 1)
        self.search.textChanged.connect(
            lambda text: [
                self.choices.item(i).setHidden(
                    text.casefold() not in self.choices.item(i).text().casefold()
                )
                for i in range(self.choices.count())
            ]
        )
        hint(layout, "Выберите нужные записи. Снятие отметки убирает только связь.")
        self.notice = hint(layout, "")

        def save():
            service.set_content_links(kind, owner_id, self.choices.ids())
            self.notice.setText("Связи сохранены")

        toolbar(layout, [("Сохранить связи", lambda: run_action(self, save))])


class ScopedLibrary(LibraryList):
    def __init__(self, window, kind, course_id):
        self.scope_course_id = course_id
        super().__init__(window, kind)
        self.refresh()

    def refresh(self):
        self.course.blockSignals(True)
        self.course.clear()
        course = next(c for c in self.window.service.list_courses() if c.id == self.scope_course_id)
        self.course.addItem(course.name, course.id)
        self.course.setEnabled(False)
        self.course.blockSignals(False)
        self.refresh_options()

    def edit(self, original):
        super().edit(original)
        editor = self.window.pages.currentWidget()
        if hasattr(editor, "course"):
            editor.course.setCurrentIndex(data_index(editor.course, self.scope_course_id))
            editor.course.setEnabled(False)


KNOWLEDGE_LABELS = {
    KnowledgeType.QUESTION: "Типичный вопрос",
    KnowledgeType.ERROR: "Типичная ошибка",
    KnowledgeType.UNDERSTANDING: "Проблема понимания",
    KnowledgeType.ORGANIZATION: "Организационный вопрос",
}


class KnowledgeForm(FormDialog):
    def __init__(self, service, *, case_id=None, original=None, parent=None):
        super().__init__(
            "Обобщённая запись базы знаний",
            lambda values: (
                service.update_knowledge_entry(original, **values)
                if original
                else service.create_knowledge_from_case(case_id, **values)
            ),
            parent,
        )
        self.title = self.line("name", original.title if original else "", required=True)
        self.answer = self.notes("description", original.answer if original else "")
        self.form.labelForField(self.answer).setText("Ответ / объяснение")
        self.type = QComboBox()
        for key, label in KNOWLEDGE_LABELS.items():
            self.type.addItem(label, key)
        if original:
            self.type.setCurrentIndex(self.type.findData(original.type))
        self.form.addRow("Вид записи", self.type)
        self.draft = QCheckBox("Черновик")
        self.draft.setChecked(original.draft if original else True)
        if original:
            self.form.addRow(self.draft)
        hint(
            self.body_layout,
            "Обобщите формулировку вручную и уберите персональные детали. Исходная переписка сохранится отдельно.",
        )
        self.original = original

    def values(self):
        values = dict(
            title=self.title.text().strip(),
            answer=self.answer.toPlainText(),
            type=KnowledgeType(self.type.currentData()),
        )
        if self.original:
            values["draft"] = self.draft.isChecked()
        return values


class KnowledgeWidget(QWidget):
    def __init__(self, window, course_id, parent=None):
        super().__init__(parent)
        self.window, self.course_id = window, course_id
        layout = QVBoxLayout(self)
        layout.addWidget(text_label("База знаний", "heading"))
        layout.addWidget(text_label("Типичные вопросы и ошибки · обобщённые объяснения"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск типичных вопросов и ошибок")
        layout.addWidget(self.search)
        self.model = TableModel(
            [
                ("Запись", lambda v: v.title),
                ("Тип", lambda v: KNOWLEDGE_LABELS[v.type]),
                ("Состояние", lambda v: "Черновик" if v.draft else "Готово"),
            ]
        )
        self.view = table(self.model)
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(self.view)
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self.entry_title = text_label("Выберите запись", "subheading")
        detail_layout.addWidget(self.entry_title)
        detail_layout.addWidget(text_label("Ответ / объяснение", "caption"))
        self.answer = QPlainTextEdit()
        self.answer.setReadOnly(True)
        detail_layout.addWidget(self.answer, 1)
        self.entry_links = text_label("", "hint")
        detail_layout.addWidget(self.entry_links)
        self.notice = hint(detail_layout, "")
        toolbar(
            detail_layout,
            [
                ("Изменить", lambda: run_action(self, self.edit)),
                ("Темы и навыки", lambda: run_action(self, self.taxonomy)),
                ("Методические материалы", lambda: run_action(self, self.materials)),
                ("Исходные случаи", lambda: run_action(self, self.sources)),
                ("Удалить", lambda: run_action(self, self.delete)),
            ],
        )
        self.split.addWidget(detail)
        self.split.setSizes([480, 480])
        layout.addWidget(self.split, 1)
        self.empty = EmptyState(
            "База знаний пока пуста",
            "Откройте вопрос студента и выберите «Добавить в базу знаний».",
        )
        layout.addWidget(self.empty)
        self.view.selectionModel().currentChanged.connect(lambda *_: self.show_entry())
        self.search.textChanged.connect(lambda _: self.refresh())
        self.view.doubleClicked.connect(lambda _: run_action(self, self.edit))
        self.refresh()

    def refresh(self):
        current = self.view.currentIndex()
        previous = self.model.rows[current.row()].id if current.isValid() else None
        rows = self.window.service.list_knowledge_entries(self.course_id, self.search.text())
        self.model.replace_rows(rows)
        self.empty.setVisible(not rows)
        self.split.setVisible(bool(rows))
        if rows:
            self.view.selectRow(next((i for i, row in enumerate(rows) if row.id == previous), 0))

    def show_entry(self):
        index = self.view.currentIndex()
        entry = self.model.rows[index.row()] if index.isValid() else None
        self.answer.setPlainText(entry.answer if entry else "")
        self.entry_title.setText(entry.title if entry else "Выберите запись")
        self.entry_links.clear()
        if entry:
            topics = self.window.service.content_targets("knowledge_topics", entry.id)
            skills = self.window.service.content_targets("knowledge_skills", entry.id)
            materials = self.window.service.content_targets("knowledge_materials", entry.id)
            self.entry_links.setText(
                "Темы: "
                + (", ".join(t.title for t in topics) or "—")
                + "\nНавыки: "
                + (", ".join(s.title for s in skills) or "—")
                + f"\nСвязанных материалов: {len(materials)}"
            )
            occurrences = self.window.service.knowledge_occurrences(entry.id)
            self.notice.setText(
                f"Исходных случаев: {occurrences.count} · первый: {display_time(occurrences.first)} · последний: {display_time(occurrences.last)}"
            )

    def edit(self):
        entry = selected(self.view)
        if entry and KnowledgeForm(self.window.service, original=entry, parent=self).exec():
            self.refresh()

    def delete(self):
        entry = selected(self.view)
        if entry and confirm_delete(self, self.window.service, "knowledge", entry):
            self.window.service.safe_delete("knowledge", entry)
            self.refresh()

    def taxonomy(self):
        entry = selected(self.view)
        if entry:
            page, tabs = panel()
            choices = QTabWidget()
            tabs.addWidget(choices)
            for suffix, values in (
                ("topics", self.window.service.list_course_topics(self.course_id)),
                ("skills", self.window.service.list_course_skills(self.course_id)),
            ):
                choices.addTab(
                    ContentLinksWidget(
                        self.window.service, "knowledge_" + suffix, entry.id, values
                    ),
                    "Темы" if suffix == "topics" else "Навыки",
                )
            self.window.router.push(page, entry.title + " · связи")

    def materials(self):
        entry = selected(self.view)
        if entry:
            self.window.router.push(
                ContentLinksWidget(
                    self.window.service,
                    "knowledge_materials",
                    entry.id,
                    self.window.service.list_materials("methodical", course_id=self.course_id),
                ),
                "Методические материалы",
            )

    def sources(self):
        entry = selected(self.view)
        if entry:
            page, layout = panel()
            model = TableModel(
                [
                    ("Исходный случай", lambda c: c.title or "Вопрос"),
                    ("Дата", lambda c: display_time(c.opened_at)),
                ]
            )
            model.replace_rows(self.window.service.knowledge_occurrences(entry.id).cases)
            view = table(model)
            layout.addWidget(view)

            def open_case():
                case = selected(view)
                if case:
                    from studium.presentation.desktop.communication import QuestionCaseDialog
                    from studium.presentation.desktop.navigation import present_detail

                    present_detail(QuestionCaseDialog(self.window.service, case.id, page), page)

            view.doubleClicked.connect(lambda _: run_action(page, open_case))
            self.window.router.push(page, "Исходные случаи")


class DisciplinesPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        hint(layout, "Дисциплины").setProperty("role", "heading")
        hint(layout, "Рабочие программы, содержание курса и повторно используемые материалы.")
        self.model = TableModel(
            [("Дисциплина", lambda c: c.name), ("Сокращение", lambda c: c.short_name)]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        toolbar(
            layout,
            [
                ("Создать дисциплину", window.create_course),
                ("Открыть", lambda: run_action(self, self.open)),
                ("Удалить", lambda: run_action(self, self.delete)),
            ],
        )
        self.empty = hint(
            layout, "Нет дисциплин. Создайте дисциплину, чтобы сформировать рабочую программу."
        )
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))

    def refresh(self):
        rows = self.window.service.list_courses()
        self.model.replace_rows(rows)
        self.empty.setVisible(not rows)

    def open(self):
        course = selected(self.view)
        if course:
            self.window.service.remember_course(course.id)
            self.window.router.push(DisciplinePage(self.window, course), course.name)

    def delete(self):
        course = selected(self.view)
        if course and confirm_delete(self, self.window.service, "course", course):
            self.window.service.safe_delete("course", course)
            self.window.refresh()


class DisciplinePage(QWidget):
    def __init__(self, window, course):
        super().__init__()
        self.window, self.course = window, course
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        hint(layout, course.name).setProperty("role", "heading")
        hint(
            layout,
            (course.short_name + " · " if course.short_name else "")
            + "Учебное пространство дисциплины",
        )
        tabs = self.tabs = QTabWidget()
        layout.addWidget(tabs)
        overview, body = panel()
        hint(
            body,
            course.description
            or "Сформируйте рабочую программу и используйте общий каталог тем, навыков и материалов дисциплины.",
        )
        toolbar(
            body, [("Создать рабочую программу", lambda: run_action(self, self.create_program))]
        )
        body.addSpacing(16)
        self.program_count = text_label("", "hint")
        body.addWidget(self.program_count)
        sections = QGridLayout()
        sections.setSpacing(16)
        body.addLayout(sections)
        for position, (title, description, index) in enumerate(
            (
                ("Рабочие программы", "План семестра, модули и группы", 1),
                ("Темы и навыки", "Общее содержание дисциплины", 2),
                ("Банк задач", "Условия, решения и наборы задач", 3),
                ("Методические материалы", "Материалы для преподавания", 4),
                ("Литература", "Учебники и источники", 5),
            )
        ):
            sections.addWidget(
                action_card(
                    title, description, lambda _=False, index=index: tabs.setCurrentIndex(index)
                ),
                position // 2,
                position % 2,
            )
        body.addStretch()
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        overview_scroll.setWidget(overview)
        tabs.addTab(overview_scroll, "Обзор")
        programs, body = panel()
        self.program_model = TableModel(
            [
                ("Рабочая программа", lambda p: p.title),
                ("Направление", lambda p: p.direction),
                ("Недели", lambda p: p.weeks),
            ]
        )
        self.program_view = table(self.program_model)
        body.addWidget(self.program_view)
        toolbar(
            body,
            [
                ("Создать", lambda: run_action(self, self.create_program)),
                ("Открыть", lambda: run_action(self, self.open_program)),
                ("Удалить", lambda: run_action(self, self.delete_program)),
            ],
        )
        self.program_view.doubleClicked.connect(lambda _: run_action(self, self.open_program))
        tabs.addTab(programs, "Рабочие программы")
        tabs.addTab(
            embed(LearningCatalogueDialog(window.service, course, self), tabs), "Темы и навыки"
        )
        for kind, label in (
            ("problems", "Банк задач"),
            ("methodical", "Методические материалы"),
            ("literature", "Литература"),
        ):
            tabs.addTab(ScopedLibrary(window, kind, course.id), label)
        tabs.addTab(KnowledgeWidget(window, course.id), "База знаний")
        self.refresh()

    def refresh(self):
        self.program_model.replace_rows(self.window.service.list_work_programs(self.course.id))
        self.program_count.setText(f"Рабочих программ: {len(self.program_model.rows)}")

    def create_program(self):
        if ProgramForm(self.window.service, self.course, parent=self).exec():
            self.refresh()

    def open_program(self):
        program = selected(self.program_view)
        if program:
            self.window.router.push(WorkProgramPage(self.window, program), program.title)

    def delete_program(self):
        program = selected(self.program_view)
        if program and confirm_delete(self, self.window.service, "work_program", program):
            self.window.service.safe_delete("work_program", program)
            self.refresh()


class WorkProgramPage(QWidget):
    def __init__(self, window, program):
        super().__init__()
        self.window, self.program = window, program
        self.course = window.service.get_course(program.course_id, historical=True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        hint(layout, program.title).setProperty("role", "heading")
        hint(layout, self.course.name)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        overview, body = panel()
        self.summary = hint(body, "")
        toolbar(body, [("Изменить программу", lambda: run_action(self, self.edit_program))])
        body.addSpacing(12)
        body.addWidget(text_label("План семестра", "subheading"))
        self.timeline = ModuleTimeline()
        body.addWidget(self.timeline)
        self.plan_empty = EmptyState(
            "Модули пока не созданы",
            "Разделите семестр на учебные модули.",
            ("Создать модуль", lambda: run_action(self, lambda: self.edit_module(new=True))),
        )
        body.addWidget(self.plan_empty)
        sections = QGridLayout()
        sections.setSpacing(16)
        body.addLayout(sections)
        for position, (title, description, index) in enumerate(
            (
                ("Документ программы", "Официальный PDF и приложения", 1),
                ("Домашнее задание и рубежный контроль", "Работы, сроки выдачи и сдачи", 3),
                ("Темы и навыки", "Содержание учебного плана", 4),
                ("Семинары / лекции", "Материалы занятий", 5),
                ("Литература", "Источники программы", 6),
                ("Группы", "Кто работает по этому плану", 7),
            )
        ):
            sections.addWidget(
                action_card(
                    title,
                    description,
                    lambda _=False, index=index: self.tabs.setCurrentIndex(index),
                ),
                position // 2,
                position % 2,
            )
        body.addStretch()
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        overview_scroll.setWidget(overview)
        self.tabs.addTab(overview_scroll, "Обзор")
        self.files = MaterialFiles(window.service, "programs", lambda: self.program, parent=self)
        self.tabs.addTab(self.files, "Документ программы")
        modules, body = panel()
        self.module_model = TableModel(
            [
                ("Модуль", lambda m: m.title),
                ("Недели", lambda m: f"{m.start_week}–{m.end_week}"),
            ]
        )
        self.module_view = table(self.module_model)
        body.addWidget(self.module_view)
        toolbar(
            body,
            [
                ("Создать модуль", lambda: run_action(self, lambda: self.edit_module(new=True))),
                ("Изменить", lambda: run_action(self, self.edit_module)),
                ("Выше", lambda: run_action(self, lambda: self.move_module(-1))),
                ("Ниже", lambda: run_action(self, lambda: self.move_module(1))),
                ("Удалить модуль", lambda: run_action(self, self.delete_module)),
            ],
        )
        self.tabs.addTab(modules, "Модули / учебный план")
        works, body = panel()
        self.work_model = TableModel(
            [
                ("Работа", lambda row: row[1].title),
                ("Тип", lambda row: ASSESSMENT_LABELS[row[1].type]),
                (
                    "Выдача",
                    lambda row: (
                        row[0].planned_issue_week.value if row[0].planned_issue_week else "—"
                    ),
                ),
                (
                    "Сдача",
                    lambda row: row[0].planned_due_week.value if row[0].planned_due_week else "—",
                ),
            ]
        )
        self.work_view = table(self.work_model)
        body.addWidget(self.work_view)
        toolbar(
            body,
            [
                ("Добавить существующую работу", lambda: run_action(self, self.add_work)),
                ("Добавить домашнее задание", lambda: run_action(self, self.create_definition)),
                (
                    "Добавить рубежный контроль",
                    lambda: run_action(self, lambda: self.create_definition(control=True)),
                ),
                ("Планирование", lambda: run_action(self, self.edit_work)),
                ("Структура и файлы", lambda: run_action(self, self.open_definition)),
                ("Выше", lambda: run_action(self, lambda: self.move_work(-1))),
                ("Ниже", lambda: run_action(self, lambda: self.move_work(1))),
                ("Удалить из плана", lambda: run_action(self, self.delete_program_work)),
            ],
        )
        self.empty_works = hint(
            body, "Нет работ в программе. Добавьте домашнее задание или рубежный контроль."
        )
        self.tabs.addTab(works, "Домашнее задание и рубежный контроль")
        taxonomy, taxonomy_layout = panel()
        choices = QTabWidget()
        taxonomy_layout.addWidget(choices)
        choices.addTab(
            ContentLinksWidget(
                window.service,
                "program_topics",
                program.id,
                window.service.list_course_topics(program.course_id),
            ),
            "Темы",
        )
        choices.addTab(
            ContentLinksWidget(
                window.service,
                "program_skills",
                program.id,
                window.service.list_course_skills(program.course_id),
            ),
            "Навыки",
        )
        self.tabs.addTab(taxonomy, "Темы и навыки")
        self.tabs.addTab(
            ContentLinksWidget(
                window.service,
                "program_materials",
                program.id,
                window.service.list_materials("seminars", course_id=program.course_id),
            ),
            "Семинары / лекции",
        )
        self.tabs.addTab(
            ContentLinksWidget(
                window.service,
                "program_literature",
                program.id,
                window.service.list_materials("literature"),
            ),
            "Литература",
        )
        groups, body = panel()
        self.group_model = TableModel(
            [("Группа", lambda c: c.group.number), ("Период", lambda c: c.term.name)]
        )
        self.group_view = table(self.group_model)
        body.addWidget(self.group_view)

        def open_group():
            context = selected(self.group_view)
            if context:
                window.open_group_context(context)

        self.group_view.doubleClicked.connect(lambda _: run_action(self, open_group))
        self.tabs.addTab(groups, "Группы")
        self.refresh()

    def refresh(self):
        self.program = self.window.service.get_work_program(self.program.id)
        self.summary.setText(
            f"{self.course.name}\nНаправление: {self.program.direction or 'не задано'} · {self.program.version}\n{'Осенний' if self.program.semester == SemesterType.AUTUMN else 'Весенний'} семестр · {self.program.weeks} недель · первая неделя: {self.program.first_week_start}"
        )
        modules = self.window.service.list_program_modules(self.program.id)
        self.module_model.replace_rows(modules)
        self.timeline.set_modules(modules, self.select_module)
        self.plan_empty.setVisible(not modules)
        rows = self.window.service.program_work_definitions(self.program.id)
        self.work_model.replace_rows(rows)
        self.empty_works.setVisible(not rows)
        self.group_model.replace_rows(
            [
                c
                for c in self.window.service.list_offerings()
                if c.offering.work_program_id == self.program.id
            ]
        )

    def select_module(self, index):
        self.tabs.setCurrentIndex(2)
        self.module_view.selectRow(index)

    def edit_program(self):
        if ProgramForm(self.window.service, self.course, self.program, self).exec():
            self.refresh()

    def edit_module(self, *, new=False):
        original = None if new else selected(self.module_view)
        if (new or original) and ModuleForm(
            self.window.service, self.program, original, self
        ).exec():
            self.refresh()

    def delete_module(self):
        original = selected(self.module_view)
        if original and confirm_delete(self, self.window.service, "module", original):
            self.window.service.safe_delete("module", original)
            self.refresh()

    def delete_program_work(self):
        row = selected(self.work_view)
        if row and confirm_delete(
            self, self.window.service, "program_work", row[0], name=row[1].title
        ):
            self.window.service.safe_delete("program_work", row[0])
            self.refresh()

    def move_module(self, direction):
        original = selected(self.module_view)
        if original:
            self.window.service.move_presentation_item("program_modules", original, direction)
            self.refresh()

    def move_work(self, direction):
        row = selected(self.work_view)
        if row:
            self.window.service.move_presentation_item("program_works", row[0], direction)
            self.refresh()

    def add_work(self):
        if ProgramWorkForm(self.window.service, self.program, parent=self).exec():
            self.refresh()

    def edit_work(self):
        row = selected(self.work_view)
        if row and ProgramWorkForm(self.window.service, self.program, row[0], self).exec():
            self.refresh()

    def create_definition(self, *, control=False):
        editor = ContentEditor(self.window, "homework")
        if control:
            from studium.domain.enums import AssessmentType

            editor.work_type.setCurrentIndex(editor.work_type.findData(AssessmentType.CONTROL_WORK))
        editor.course.setCurrentIndex(data_index(editor.course, self.program.course_id))
        editor.course.setEnabled(False)
        editor.on_saved = lambda definition: (
            self.window.service.add_program_work(self.program.id, definition.id)
            if not any(
                link.definition_id == definition.id
                for link, _ in self.window.service.program_work_definitions(self.program.id)
            )
            else None
        )
        self.window.router.routes[-1].refresh = self.refresh
        self.window.router.push(editor, "Рубежный контроль" if control else "Домашнее задание")

    def open_definition(self):
        row = selected(self.work_view)
        if row:
            self.window.router.push(ContentEditor(self.window, "homework", row[1]), row[1].title)
