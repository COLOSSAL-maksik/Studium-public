"""Explicit criteria, reviewed composition, saved snapshots and assignments."""

import json

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.domain.content import GenerationCriteria
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import hint, run_action, selected, table, toolbar
from studium.presentation.desktop.library import PURPOSE_LABELS
from studium.presentation.desktop.models import TableModel
from studium.presentation.desktop.workflow_widgets import data_index


class TicketGeneratorPage(QWidget):
    def __init__(self, window, context_provider):
        super().__init__()
        self.window, self.context_provider = window, context_provider
        self.draft, self.saved, self.offering_id, self.generation = None, None, None, 0
        layout = QVBoxLayout(self)
        hint(layout, "Варианты").setProperty("role", "heading")
        hint(
            layout, "Одинаковые критерии для всех. Состав можно проверить и заменить до сохранения."
        )
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        criteria_page, self.draft_page, self.saved_page = QWidget(), QWidget(), QWidget()
        self.tabs.addTab(criteria_page, "Критерии")
        self.tabs.addTab(self.draft_page, "Проверка состава")
        self.tabs.addTab(self.saved_page, "Сохранённые наборы")
        criteria_layout = QVBoxLayout(criteria_page)
        form = QFormLayout()
        criteria_layout.addLayout(form)
        self.tags, self.collection = QLineEdit(), QComboBox()
        self.selected_problem_ids = ()
        self.purpose = QComboBox()
        self.purpose.addItem("Любое назначение", None)
        for purpose, title in PURPOSE_LABELS.items():
            self.purpose.addItem(title, purpose)
        self.tags.setPlaceholderText("балки, изгиб")
        self.count, self.size, self.seed = QSpinBox(), QSpinBox(), QSpinBox()
        self.count.setRange(1, 1000)
        self.size.setRange(1, 30)
        self.seed.setRange(0, 2_000_000_000)
        self.assessment = QComboBox()
        self.auto_assign = QCheckBox("Назначить по текущему списку студентов при сохранении")
        self.auto_assign.setChecked(True)
        for label, field in [
            ("Назначение задачи", self.purpose),
            ("Теги (все указанные)", self.tags),
            ("Набор", self.collection),
            ("Количество вариантов", self.count),
            ("Задач в варианте", self.size),
            ("Номер генерации", self.seed),
            ("Работа (по желанию)", self.assessment),
        ]:
            form.addRow(label, field)
        criteria_layout.addWidget(self.auto_assign)
        toolbar(
            criteria_layout,
            [
                ("Сформировать", lambda: run_action(self, self.generate)),
                ("Пересоздать", lambda: run_action(self, self.regenerate)),
            ],
        )
        criteria_layout.addStretch()
        self.notice = hint(layout, "")
        draft_layout = QVBoxLayout(self.draft_page)
        self.model = TableModel(
            [("Вариант", lambda r: r[0]), ("Задачи", lambda r: r[1]), ("Назначен", lambda r: r[2])]
        )
        self.view = table(self.model)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open_ticket))
        draft_layout.addWidget(self.view, 1)
        self.position, self.replacement = QSpinBox(), QComboBox()
        self.position.setRange(1, 30)
        form = QFormLayout()
        form.addRow("Номер задачи для замены", self.position)
        form.addRow("Подходящая задача", self.replacement)
        draft_layout.addLayout(form)
        toolbar(
            draft_layout,
            [
                ("Заменить задачу", lambda: run_action(self, self.replace)),
                ("Сохранить набор", lambda: run_action(self, self.save)),
            ],
        )
        saved_layout = QVBoxLayout(self.saved_page)
        self.saved_sets, self.student, self.variant = QComboBox(), QComboBox(), QComboBox()
        form = QFormLayout()
        for label, field in [
            ("Сохранённые наборы", self.saved_sets),
            ("Студент", self.student),
            ("Вариант", self.variant),
        ]:
            form.addRow(label, field)
        saved_layout.addLayout(form)
        toolbar(
            saved_layout,
            [
                ("Открыть набор", lambda: run_action(self, self.open_saved)),
                ("Назначить / заменить", lambda: run_action(self, self.assign)),
                ("Снять назначение", lambda: run_action(self, self.unassign)),
                ("Применить к рубежному контролю", lambda: run_action(self, self.apply_tasks)),
            ],
        )
        self.assignment_model = TableModel(
            [("Студент", lambda r: r[0]), ("Вариант", lambda r: r[1])]
        )
        self.assignment_view = table(self.assignment_model)
        tables = QTabWidget()
        self.saved_view = table(self.model)
        self.saved_view.doubleClicked.connect(lambda _: run_action(self, self.open_ticket))
        tables.addTab(self.saved_view, "Варианты")
        tables.addTab(self.assignment_view, "Назначения студентам")
        saved_layout.addWidget(tables, 1)

    @property
    def service(self):
        return self.window.service

    def apply_tasks(self):
        if self.saved_sets.currentData():
            values = self.service.apply_ticket_set_for_evaluation(self.saved_sets.currentData())
            self.notice.setText(f"Задач назначено для проверки рубежного контроля: {len(values)}")

    def refresh(self):
        context = self.context_provider()
        if not context:
            return
        changed = self.offering_id != context.offering.id
        self.offering_id = context.offering.id
        for field, values, placeholder in [
            (
                self.collection,
                [(c.id, c.title) for c in self.service.list_problem_collections(context.course.id)],
                "Все наборы",
            ),
            (
                self.assessment,
                [(a.id, a.title) for a in self.service.list_assessments(self.offering_id)],
                "Без связи с работой",
            ),
            (
                self.saved_sets,
                [
                    (
                        s.id,
                        s.title + " · " + s.created_at.value.astimezone().strftime("%d.%m %H:%M"),
                    )
                    for s in self.service.list_ticket_sets(self.offering_id)
                ],
                None,
            ),
        ]:
            previous = field.currentData()
            field.clear()
            if placeholder:
                field.addItem(placeholder, None)
            for id, title in values:
                field.addItem(title, id)
            field.setCurrentIndex(max(0, data_index(field, previous)))
        self.roster = self.service.list_students_for_offering(self.offering_id)
        self.student.clear()
        for entry in self.roster:
            self.student.addItem(entry.student.full_name, entry.enrollment.id)
        if changed:
            self.generation += 1
            self.draft, self.saved = None, None
            self.count.setValue(max(1, len(self.roster)))
            self.model.replace_rows([])
            self.assignment_model.replace_rows([])

    def criteria(self):
        return GenerationCriteria(
            self.context_provider().course.id,
            self.count.value(),
            self.size.value(),
            tuple(t.strip() for t in self.tags.text().split(",") if t.strip()),
            self.collection.currentData(),
            self.seed.value(),
            purpose=self.purpose.currentData(),
            problem_ids=self.selected_problem_ids,
        )

    def generate(self):
        criteria = self.criteria()
        self.generation += 1
        generation = self.generation
        self.notice.setText("Формирование…")
        BackgroundCall(
            self,
            lambda: self.service.generate_ticket_draft(criteria),
            lambda draft: self.generated(draft, generation),
            lambda error: self.failed(error, generation),
        )

    def generated(self, draft, generation):
        if generation != self.generation:
            return
        self.draft, self.saved = draft, None
        self.model.replace_rows(
            [
                (i, "; ".join(p.title for p in variant), "Пока не назначен")
                for i, variant in enumerate(draft.variants, 1)
            ]
        )
        self.assignment_model.replace_rows([])
        self.replacement.clear()
        for p in self.service.problem_pool(draft.criteria):
            self.replacement.addItem(p.title, p.id)
        self.notice.setText(
            f"Сформировано {len(draft.variants)} вариантов. Проверьте состав, затем сохраните."
        )
        self.tabs.setCurrentWidget(self.draft_page)

    def failed(self, error, generation):
        if generation == self.generation:
            from studium.presentation.desktop.messages import error_message

            self.notice.setText(error_message(error))

    def regenerate(self):
        self.seed.setValue(self.seed.value() + 1)
        self.generate()

    def replace(self):
        index, position = self.view.currentIndex().row(), self.position.value() - 1
        if (
            self.draft
            and 0 <= index < len(self.draft.variants)
            and position < len(self.draft.variants[index])
            and self.replacement.currentData()
        ):
            self.generated(
                self.service.replace_draft_problem(
                    self.draft, index, position, self.replacement.currentData()
                ),
                self.generation,
            )

    def save(self):
        if not self.draft:
            self.notice.setText("Сначала сформируйте варианты")
            return
        criteria = self.draft.criteria
        saved = self.service.save_ticket_set(
            self.offering_id,
            self.draft,
            title=f"{self.context_provider().group.number} · {criteria.variants} вариантов · {', '.join(criteria.tags) or 'задачи'}",
            assessment_id=self.assessment.currentData(),
            assign_students=self.auto_assign.isChecked(),
        )
        self.draft = None
        self.refresh()
        self.saved_sets.setCurrentIndex(data_index(self.saved_sets, saved.id))
        self.open_saved()
        self.notice.setText("Набор сохранён. Состав и условия зафиксированы.")

    def open_saved(self):
        id = self.saved_sets.currentData()
        if not id:
            return
        self.saved = next(s for s in self.service.list_ticket_sets(self.offering_id) if s.id == id)
        self.draft = None
        self.saved_views = self.service.ticket_set_details(id)
        names = {
            entry.enrollment.id: entry.student.full_name
            for entry in self.service.list_students_for_offering(
                self.offering_id, include_ended=True
            )
        }
        self.model.replace_rows(
            [
                (
                    view.ticket.number,
                    "; ".join(p.title_snapshot for p in view.problems),
                    "; ".join(
                        names.get(a.enrollment_id, "Историческое участие") for a in view.assignments
                    )
                    or "Не назначен",
                )
                for view in self.saved_views
            ]
        )
        self.variant.clear()
        for view in self.saved_views:
            self.variant.addItem(str(view.ticket.number), view.ticket.id)
        assignments = {
            a.enrollment_id: view.ticket.number
            for view in self.saved_views
            for a in view.assignments
        }
        self.assignment_model.replace_rows(
            [(name, assignments.get(id, "Не назначен")) for id, name in names.items()]
        )
        self.tabs.setCurrentWidget(self.saved_page)

    def assign(self):
        if self.saved and self.student.currentData() and self.variant.currentData():
            id = self.student.currentData()
            original = next(
                (a for view in self.saved_views for a in view.assignments if a.enrollment_id == id),
                None,
            )
            self.service.assign_ticket(
                self.saved.id, id, self.variant.currentData(), original=original
            )
            self.open_saved()

    def unassign(self):
        if self.saved and self.student.currentData():
            original = next(
                (
                    a
                    for view in self.saved_views
                    for a in view.assignments
                    if a.enrollment_id == self.student.currentData()
                ),
                None,
            )
            if original:
                self.service.unassign_ticket(original)
                self.open_saved()

    def open_ticket(self):
        row = selected(self.saved_view if self.saved else self.view)
        if row and self.saved:
            view = next(v for v in self.saved_views if v.ticket.number == row[0])
            self.window.router.push(
                TicketDetails(self.service, view), f"Вариант {view.ticket.number}"
            )


class TicketDetails(QWidget):
    def __init__(self, service, view):
        super().__init__()
        layout = QVBoxLayout(self)
        hint(layout, f"Вариант {view.ticket.number}").setProperty("role", "heading")
        tabs = QTabWidget()
        layout.addWidget(tabs)
        statement, teacher = QPlainTextEdit(), QPlainTextEdit()
        for field in (statement, teacher):
            field.setReadOnly(True)
        statement.setPlainText(
            "\n\n".join(
                f"{i}. {p.title}\n{p.statement}"
                for i, p in enumerate(service.student_ticket_content(view.ticket.id), 1)
            )
        )
        teacher.setPlainText(
            "\n\n".join(
                f"{p.title_snapshot}\nОтвет: {json.loads(p.teacher_snapshot_json)['correct_answer']}\nРешение: {json.loads(p.teacher_snapshot_json)['solution']}"
                for p in view.problems
            )
        )
        tabs.addTab(statement, "Выданное условие")
        tabs.addTab(teacher, "Ответы преподавателя (снимок)")
        files = QWidget()
        files_layout = QVBoxLayout(files)
        from studium.presentation.desktop.files import FilePreviewDialog
        from studium.presentation.desktop.navigation import present_detail

        self.file_model = TableModel(
            [
                ("Файл", lambda e: e.asset.original_filename),
                ("Область", lambda e: e.attachment.role.value),
            ]
        )
        file_view = table(self.file_model)
        files_layout.addWidget(file_view)

        def preview():
            entry = selected(file_view)
            if entry:
                present_detail(
                    FilePreviewDialog(service, entry, self, asynchronous=True),
                    self,
                    title=entry.asset.original_filename,
                )

        file_view.doubleClicked.connect(lambda _: run_action(self, preview))
        tabs.addTab(files, "Файлы (снимок)")
        BackgroundCall(
            self,
            lambda: service.list_ticket_files(view.ticket.id),
            self.file_model.replace_rows,
            lambda error: hint(files_layout, str(type(error).__name__)),
        )
