"""Four teaching libraries share filters, editing and the Phase 4 preview pipeline."""

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.domain.content import (
    GenerationCriteria,
    LiteratureType,
    MaterialFileRole,
    ProblemPurpose,
)
from studium.domain.enums import AssessmentType, LessonType
from studium.domain.value_objects import AcademicWeekNumber
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import (
    confirm,
    confirm_delete,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.files import FilePreviewDialog
from studium.presentation.desktop.learning import CheckList
from studium.presentation.desktop.messages import ASSESSMENT_LABELS, FILE_LABELS, error_message
from studium.presentation.desktop.models import TableModel
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.preview_pane import FilePreviewPane
from studium.presentation.desktop.visuals import EmptyState
from studium.presentation.desktop.widgets import search_shortcut
from studium.presentation.desktop.workflow_widgets import (
    WeekSelector,
    data_index,
    week_label,
)

LIBRARY_LABELS = {
    "homework": "Домашнее задание",
    "problems": "Банк задач",
    "control": "Рубежный контроль",
    "seminars": "Семинары",
    "lectures": "Лекции",
    "literature": "Литература",
    "methodical": "Методические материалы",
}
EDITOR_LABELS = {**LIBRARY_LABELS, "packs": "Комплект домашних заданий"}
PURPOSE_LABELS = {
    ProblemPurpose.SEMINAR: "Семинар",
    ProblemPurpose.CONTROL: "Рубежный контроль",
    ProblemPurpose.EXAM: "Экзамен",
    ProblemPurpose.CONSULTATION: "Консультация",
}
LITERATURE_LABELS = {
    LiteratureType.TEXTBOOK: "Учебник",
    LiteratureType.STUDY_GUIDE: "Учебное пособие",
    LiteratureType.METHOD_GUIDE: "Методическое пособие",
    LiteratureType.ARTICLE: "Статья",
    LiteratureType.OTHER: "Другое",
}
FILE_ROLES = {
    MaterialFileRole.STATEMENT: "Условие / материал",
    MaterialFileRole.REFERENCE: "Эталонные эпюры",
    MaterialFileRole.SOLUTION: "Решение преподавателя",
}


class MaterialFiles(QWidget):
    def __init__(self, service, kind, owner_provider, role=MaterialFileRole.STATEMENT, parent=None):
        super().__init__(parent)
        self.service, self.kind, self.owner_provider, self.role = (
            service,
            kind,
            owner_provider,
            role,
        )
        self.pending, self.generation = [], 0
        layout = QVBoxLayout(self)
        from studium.presentation.desktop.attachment_picker import StagedAttachmentPicker

        self.staged = StagedAttachmentPicker(self)
        self.drop_zone = self.staged.list
        layout.addWidget(self.staged)
        if not isinstance(parent, ContentEditor):
            toolbar(layout, [("Сохранить вложения", lambda: run_action(self, self.import_pending))])
        self.notice = hint(layout, "")
        self.model = TableModel(
            [
                ("Файл", lambda e: e.asset.original_filename),
                ("Состояние", lambda e: FILE_LABELS[e.integrity]),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.preview))
        toolbar(
            layout,
            [
                ("Открыть", lambda: run_action(self, self.preview)),
                ("Отсоединить", lambda: run_action(self, self.detach)),
            ],
        )
        self.refresh()

    def import_paths(self, paths):
        self.staged.add_paths(paths)

    def imported(self, failures):
        self.drop_zone.setEnabled(True)
        self.refresh()
        self.notice.setText("\n".join(failures) if failures else "Файлы добавлены")

    def failed(self, error):
        self.drop_zone.setEnabled(True)
        self.staged.setEnabled(True)
        self.notice.setText(error_message(error))

    def import_pending(self):
        owner = self.owner_provider()
        if not owner or not self.staged.paths:
            self.refresh()
            return
        paths = self.staged.paths
        self.staged.setEnabled(False)

        def complete(_):
            self.staged.clear()
            self.staged.setEnabled(True)
            self.imported(())

        BackgroundCall(
            self,
            lambda: self.service.import_material_files(
                self.kind, owner.id, tuple((p, self.role) for p in paths)
            ),
            complete,
            self.failed,
        )

    def refresh(self):
        owner = self.owner_provider()
        self.generation += 1
        generation = self.generation
        if owner:
            BackgroundCall(
                self,
                lambda: self.service.list_material_files(self.kind, owner.id),
                lambda rows: self.apply_rows(rows, generation),
                self.failed,
            )

    def apply_rows(self, rows, generation):
        if generation == self.generation:
            self.model.replace_rows([entry for entry in rows if entry.attachment.role == self.role])

    def preview(self):
        entry = selected(self.view)
        if entry:
            present_detail(
                FilePreviewDialog(self.service, entry, self, asynchronous=True),
                self,
                title=entry.asset.original_filename,
            )

    def detach(self):
        entry = selected(self.view)
        if entry and confirm(self, "Отсоединить файл? Содержимое сохранится."):
            self.service.detach_material_file(self.kind, entry.attachment)
            self.refresh()


class ContentEditor(QWidget):
    def __init__(
        self, window, kind, original=None, *, family=None, lesson_type=None, on_cancel=None
    ):
        super().__init__()
        self.window, self.service, self.kind, self.original = window, window.service, kind, original
        self.fields, self.file_widgets = {}, []
        self.family = family or (
            self.service.get_material("problems", original.family_id)
            if kind == "problems" and original and original.family_id
            else None
        )
        layout = QVBoxLayout(self)
        hint(layout, original.title if original else "Новый материал").setProperty(
            "role", "heading"
        )
        hint(layout, EDITOR_LABELS[kind])
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        self.scroll.setWidget(body)
        layout.addWidget(self.scroll, 1)
        metadata = QWidget()
        form = QFormLayout(metadata)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.title = QLineEdit(original.title if original else "")
        form.addRow("Название *", self.title)
        self.course = QComboBox()
        if kind == "literature":
            self.course.addItem("Без дисциплины", None)
        for course in self.service.list_courses():
            self.course.addItem(course.name, course.id)
        if original:
            if original.course_id and data_index(self.course, original.course_id) < 0:
                archived_course = self.service.get_course(original.course_id, historical=True)
                self.course.addItem(archived_course.name + " (удалена)", archived_course.id)
            self.course.setCurrentIndex(data_index(self.course, original.course_id))
            self.course.setEnabled(False)
        form.addRow("Дисциплина", self.course)
        self.tags = QLineEdit(", ".join(original.tags) if original else "")
        self.tags.setPlaceholderText("Например: балки, изгиб")
        form.addRow("Теги", self.tags)
        if kind == "homework":
            self.line(form, "label", "Номер / обозначение")
            self.work_type = QComboBox()
            for type, label in ASSESSMENT_LABELS.items():
                self.work_type.addItem(label, type)
            self.work_type.setCurrentIndex(
                self.work_type.findData(original.type if original else AssessmentType.HOMEWORK)
            )
            form.addRow("Тип работы", self.work_type)
        elif kind == "problems":
            if self.family:
                self.line(form, "variant_code", "Номер / код варианта *")
                self.line(form, "parameters", "Параметры / примечание к схеме")
                for field in (self.tags, self.title):
                    removed = form.takeRow(field)
                    removed.labelItem.widget().hide()
                    field.hide()
                self.course.setCurrentIndex(data_index(self.course, self.family.course_id))
                self.course.setEnabled(False)
                hint(body_layout, "Общее условие и классификация: " + self.family.title)
            else:
                self.line(form, "identifier", "Номер / идентификатор")
                self.problem_kind = QComboBox()
                self.problem_kind.addItem("Отдельная задача", False)
                self.problem_kind.addItem("Общее условие с вариантами", True)
                self.problem_kind.setCurrentIndex(1 if original and original.is_family else 0)
                self.problem_kind.setEnabled(original is None)
                form.addRow("Содержание", self.problem_kind)
                self.purposes = CheckList([])
                self.purposes.fill(
                    list(PURPOSE_LABELS.items()), original.purposes if original else ()
                )
                self.purposes.setMaximumHeight(
                    self.purposes.count() * self.purposes.sizeHintForRow(0)
                    + 2 * self.purposes.frameWidth()
                    + 8
                )
                form.addRow("Назначение (можно несколько)", self.purposes)
            self.line(form, "difficulty", "Сложность / уровень (по желанию)")
        elif kind == "literature":
            self.line(form, "authors", "Авторы")
            self.line(form, "year", "Год")
            self.literature_type = QComboBox()
            for type, name in LITERATURE_LABELS.items():
                self.literature_type.addItem(name, type)
            self.literature_type.setCurrentIndex(
                self.literature_type.findData(original.type if original else LiteratureType.OTHER)
            )
            form.addRow("Вид", self.literature_type)
        elif kind == "seminars":
            self.material_type = QComboBox()
            self.material_type.addItem("Семинар", LessonType.SEMINAR)
            self.material_type.addItem("Лекция", LessonType.LECTURE)
            self.material_type.setCurrentIndex(
                self.material_type.findData(
                    original.type if original else lesson_type or LessonType.SEMINAR
                )
            )
            form.addRow("Тип материала", self.material_type)
            self.week = WeekSelector(original.planned_week if original else None)
            form.addRow("Плановая неделя", self.week)
        body_layout.addWidget(metadata)
        if kind == "problems" and not self.family:
            from studium.presentation.desktop.visuals import advanced_rows

            body_layout.addWidget(
                advanced_rows(
                    form,
                    (
                        self.tags,
                        self.fields.get("identifier"),
                        self.purposes,
                        self.fields.get("difficulty"),
                    ),
                    title="Теги, назначение и параметры",
                )
            )
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(180)
        # Pages scroll independently; the tallest page must not force the outer
        # form to its preferred height when a short page is selected.
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        body_layout.addWidget(self.tabs, 1)
        if kind == "problems":
            if self.family:
                shared = QWidget()
                shared_layout = QVBoxLayout(shared)
                shared_text = QPlainTextEdit(self.family.statement)
                shared_text.setReadOnly(True)
                shared_layout.addWidget(shared_text)
                self.add_files(shared_layout)
                self.tabs.addTab(shared, "Общее условие / схема варианта")
            else:
                self.text_tab(
                    "statement",
                    "Общее условие" if original and original.is_family else "Условие",
                    files=True,
                )
            self.text_tab("correct_answer", "Правильный ответ")
            page = QWidget()
            page_layout = QVBoxLayout(page)
            hint(page_layout, "Только для преподавателя; в условие билета не включаются.")
            self.add_files(page_layout, MaterialFileRole.REFERENCE)
            self.tabs.addTab(page, "Эталонные эпюры")
            self.text_tab(
                "solution", "Решение / комментарий", files=True, role=MaterialFileRole.SOLUTION
            )
            self.collection_page = QWidget()
            collection_layout = QVBoxLayout(self.collection_page)
            self.collections = CheckList([], [])
            collection_layout.addWidget(self.collections)
            toolbar(
                collection_layout,
                [
                    ("Создать набор", lambda: run_action(self, self.new_collection)),
                    ("Удалить набор", lambda: run_action(self, self.delete_collection)),
                ],
            )
            if not self.family:
                self.tabs.addTab(self.collection_page, "Коллекции")
            self.course.currentIndexChanged.connect(self.refresh_collections)
            self.refresh_collections()
        elif kind in {"homework", "packs", "methodical"}:
            self.text_tab("description", "Условие", files=True)
        elif kind == "seminars":
            self.text_tab("plan_text", "План")
            plan_layout = self.tabs.widget(0).layout()
            hint(plan_layout, "Подробный текст (по желанию)")
            full_text = QPlainTextEdit(original.full_text if original else "")
            self.fields["full_text"] = full_text
            plan_layout.addWidget(full_text)
            self.seminar_problems = SeminarProblems(self)
            self.tabs.addTab(self.seminar_problems, "Задачи")
            files_page = QWidget()
            self.add_files(QVBoxLayout(files_page))
            self.tabs.addTab(files_page, "Файлы")
            page = QWidget()
            topic_layout = QVBoxLayout(page)
            self.topics = CheckList([], [])
            topic_layout.addWidget(self.topics)
            self.tabs.addTab(page, "Темы")
            self.course.currentIndexChanged.connect(self.refresh_topics)
            self.refresh_topics()
        else:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            self.add_files(page_layout)
            self.tabs.addTab(page, "Файлы")
        if kind == "problems":
            from studium.presentation.desktop.qa_content import StructuredAnswers

            self.answers = StructuredAnswers(
                self.service, original.details_json if original else "{}", self
            )
            self.tabs.addTab(self.answers, "Структурированные ответы")
        self.text_tab("notes", "Заметки")
        self.taxonomy_fields = {}
        if kind in {"homework", "problems", "methodical"} and not self.family:
            page = QWidget()
            content_layout = QVBoxLayout(page)
            self.taxonomy_search = QLineEdit()
            self.taxonomy_search.setPlaceholderText("Поиск тем и навыков")
            content_layout.addWidget(self.taxonomy_search)
            for suffix, label in (("topics", "Темы"), ("skills", "Навыки")):
                hint(content_layout, label)
                if suffix == "topics":
                    from studium.presentation.desktop.qa_content import TopicTreePicker

                    choices = TopicTreePicker(self)
                else:
                    choices = CheckList([])
                self.taxonomy_fields[suffix] = choices
                content_layout.addWidget(choices)
            self.tabs.addTab(page, "Темы и навыки")
            self.course.currentIndexChanged.connect(self.refresh_taxonomy)
            self.taxonomy_search.textChanged.connect(self.search_taxonomy)
            self.refresh_taxonomy()
        if kind == "homework":
            self.pack_page = QWidget()
            pack_layout = QVBoxLayout(self.pack_page)
            hint(
                pack_layout,
                "Один комплект может содержать несколько домашних заданий и общий PDF. Файлы переиспользуются.",
            )
            self.packs = CheckList([])
            pack_layout.addWidget(self.packs)
            toolbar(
                pack_layout,
                [("Создать комплект домашних заданий", lambda: run_action(self, self.create_pack))],
            )
            self.tabs.addTab(self.pack_page, "Комплект условий")
            self.course.currentIndexChanged.connect(self.refresh_packs)
            self.refresh_packs()
            self.bank_tasks = CheckList([])
            task_page = QWidget()
            task_layout = QVBoxLayout(task_page)
            hint(
                task_layout,
                "Задачи из банка задач для структуры рубежного контроля.",
            )
            self.bank_search = QLineEdit()
            self.bank_search.setPlaceholderText("Номер, название или тег")
            task_layout.addWidget(self.bank_search)
            task_layout.addWidget(self.bank_tasks)
            self.bank_search.textChanged.connect(
                lambda text: [
                    self.bank_tasks.item(i).setHidden(
                        text.casefold() not in self.bank_tasks.item(i).text().casefold()
                    )
                    for i in range(self.bank_tasks.count())
                ]
            )
            self.tabs.addTab(task_page, "Задачи рубежного контроля")
            self.course.currentIndexChanged.connect(self.refresh_bank_tasks)
            self.refresh_bank_tasks()
        # Each tab controls its own overflow. A tall attachment/answer tab must
        # not impose its minimum height on a short Collections tab.
        pages = [(self.tabs.widget(i), self.tabs.tabText(i)) for i in range(self.tabs.count())]
        for page, title in pages:
            self.tabs.removeTab(0)
        for page, title in pages:
            scroll = QScrollArea(self.tabs)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.tabs.addTab(scroll, title)
        self.notice = hint(layout, "")
        actions = [("Сохранить", lambda: run_action(self, self.save))]
        if hasattr(window, "router"):
            actions.append(("Отмена", on_cancel or window.router.back))
        if kind == "homework":
            actions.append(("Выдать группе", lambda: run_action(self, self.issue)))
        toolbar(layout, actions)
        if kind == "problems" and original and original.is_family:
            self.add_variants_tab()

    def add_variants_tab(self):
        self.variant_page = QWidget()
        variant_layout = QVBoxLayout(self.variant_page)
        self.variant_model = TableModel(
            [("Вариант", lambda p: p.variant_code), ("Параметры", lambda p: p.parameters)]
        )
        self.variant_view = table(self.variant_model)
        variant_layout.addWidget(self.variant_view, 1)
        self.variant_view.doubleClicked.connect(lambda _: self.open_variant())
        toolbar(
            variant_layout,
            [
                ("Добавить вариант", lambda: self.open_variant(new=True)),
                ("Открыть вариант", self.open_variant),
                ("Удалить вариант", lambda: run_action(self, self.delete_variant)),
            ],
        )
        self.tabs.addTab(self.variant_page, "Варианты схем")
        self.refresh_variants()

    def refresh_variants(self):
        self.variant_model.replace_rows(self.service.list_problem_variants(self.original.id))

    def delete_variant(self):
        variant = selected(self.variant_view)
        if variant and confirm(
            self,
            f"Удалить вариант «{variant.variant_code}»? Назначенные работы и файлы сохранятся.",
            action_label="Удалить",
        ):
            self.service.archive_material("problems", variant)
            self.refresh_variants()

    def open_variant(self, *, new=False):
        variant = None if new else selected(self.variant_view)
        if not new and variant is None:
            return
        self.window.router.routes[-1].refresh = self.refresh_variants
        self.window.router.push(
            ContentEditor(self.window, "problems", variant, family=self.original), "Вариант схемы"
        )

    def line(self, form, name, label):
        value = getattr(self.original, name, "") if self.original else ""
        field = QLineEdit(str(value) if value is not None else "")
        self.fields[name] = field
        form.addRow(label, field)

    def refresh_taxonomy(self):
        course = self.course.currentData()
        prefix = {"homework": "definition", "problems": "problem", "methodical": "methodical"}[
            self.kind
        ]
        for suffix, field in self.taxonomy_fields.items():
            values = (
                self.service.list_course_topics(course)
                if suffix == "topics"
                else self.service.list_course_skills(course)
            )
            linked = (
                self.service.content_targets(prefix + "_" + suffix, self.original.id)
                if self.original
                else ()
            )
            if suffix == "topics":
                by_id = {v.id: v for v in values + list(linked)}
                field.fill_topics(list(by_id.values()), [v.id for v in linked])
            else:
                field.fill([(v.id, v.title) for v in values], [v.id for v in linked])

    def search_taxonomy(self, text):
        for suffix, field in self.taxonomy_fields.items():
            if suffix == "topics":
                field.search(text)
                continue
            for i in range(field.count()):
                field.item(i).setHidden(text.casefold() not in field.item(i).text().casefold())

    def refresh_packs(self):
        selected_ids = (
            self.service.pack_ids_for_definition(self.original.id) if self.original else ()
        )
        self.packs.fill(
            [
                (v.id, v.title)
                for v in self.service.list_materials("packs", course_id=self.course.currentData())
            ],
            selected_ids,
        )

    def create_pack(self):
        editor = ContentEditor(self.window, "packs")
        editor.course.setCurrentIndex(data_index(editor.course, self.course.currentData()))
        self.window.router.routes[-1].refresh = self.refresh_packs
        self.window.router.push(editor, "Новый комплект домашних заданий")

    def refresh_bank_tasks(self):
        linked = (
            self.service.content_targets("definition_problems", self.original.id)
            if self.original
            else ()
        )
        self.bank_tasks.fill(
            [
                (v.id, f"{v.identifier or str(v.id)[:8]} · {v.title} · {', '.join(v.tags)}")
                for v in self.service.problem_pool(GenerationCriteria(self.course.currentData(), 1))
                if self.course.currentData()
            ],
            [v.id for v in linked],
        )

    def text_tab(self, name, title, *, files=False, role=MaterialFileRole.STATEMENT):
        page = QWidget()
        layout = QVBoxLayout(page)
        field = QPlainTextEdit(getattr(self.original, name, "") if self.original else "")
        field.setPlaceholderText("Обычный текст или Markdown")
        self.fields[name] = field
        if self.original:
            field.setReadOnly(True)
            edit = QPushButton("Изменить текст")
            edit.setCheckable(True)
            edit.toggled.connect(lambda checked: field.setReadOnly(not checked))
            layout.addWidget(edit, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(field, 1)
        if files:
            self.add_files(layout, role)
        self.tabs.addTab(page, title)

    def add_files(self, layout, role=MaterialFileRole.STATEMENT):
        widget = MaterialFiles(self.service, self.kind, lambda: self.original, role, self)
        self.file_widgets.append(widget)
        layout.addWidget(widget, 1)

    def refresh_topics(self):
        self.topics.clear()
        course_id = self.course.currentData()
        ids = self.service.seminar_topic_ids(self.original.id) if self.original else ()
        if course_id:
            self.topics.fill(
                [(node.id, node.title) for node in self.service.list_course_topics(course_id)],
                ids,
            )

    def refresh_collections(self):
        self.collections.clear()
        course_id = self.course.currentData()
        ids = self.service.problem_collection_ids(self.original.id) if self.original else ()
        self.collections.fill(
            [
                (collection.id, collection.title)
                for collection in self.service.list_problem_collections(course_id)
            ],
            ids,
        )

    def new_collection(self):
        from studium.presentation.desktop.dialogs import FormDialog

        owner = self

        class CollectionForm(FormDialog):
            def __init__(self):
                super().__init__(
                    "Создать набор",
                    lambda values: owner.service.create_problem_collection(
                        owner.course.currentData(), **values
                    ),
                    owner,
                )
                self.title = self.line("name", required=True)
                self.resize(520, 280)

            def values(self):
                return {"title": self.title.text()}

        if self.course.currentData() and CollectionForm().exec():
            self.refresh_collections()

    def delete_collection(self):
        item = self.collections.currentItem()
        if item:
            id = item.data(Qt.ItemDataRole.UserRole)
            original = next(
                c
                for c in self.service.list_problem_collections(self.course.currentData())
                if c.id == id
            )
            if confirm_delete(self, self.service, "collection", original):
                self.service.safe_delete("collection", original)
                self.refresh_collections()

    def values(self):
        values = {
            "title": self.title.text().strip(),
            "course_id": self.course.currentData(),
            "tags": tuple(t.strip() for t in self.tags.text().split(",") if t.strip()),
        }
        for name, field in self.fields.items():
            values[name] = (
                field.toPlainText() if isinstance(field, QPlainTextEdit) else field.text()
            )
        if self.kind == "literature":
            values["year"] = int(values["year"]) if values["year"].strip() else None
            values["type"] = LiteratureType(self.literature_type.currentData())
        if self.kind == "seminars":
            values["type"] = LessonType(self.material_type.currentData())
            values["planned_week"] = self.week.currentData()
            values["topic_ids"] = self.topics.ids()
            values["problem_ids"] = self.seminar_problems.ids()
        if self.kind == "homework":
            values["type"] = AssessmentType(self.work_type.currentData())
        if self.kind == "problems":
            values["details_json"] = self.answers.document()
            if self.family:
                values.update(
                    family_id=self.family.id, tags=(), title="Вариант " + values["variant_code"]
                )
            else:
                values["purposes"] = self.purposes.ids()
                if not self.original:
                    values["is_family"] = self.problem_kind.currentData()
        return values

    def save(self):
        values = self.values()
        if not values["title"]:
            self.notice.setText("Введите название")
            return
        prefix = {"homework": "definition", "problems": "problem", "methodical": "methodical"}.get(
            self.kind
        )
        links = (
            {prefix + "_" + suffix: field.ids() for suffix, field in self.taxonomy_fields.items()}
            if prefix
            else {}
        )
        if self.kind == "homework":
            links["definition_problems"] = self.bank_tasks.ids()
        payload = dict(
            links=links,
            packs=self.packs.ids() if self.kind == "homework" else None,
            collections=self.collections.ids()
            if self.kind == "problems" and not self.family
            else None,
            files=tuple(
                (path, widget.role) for widget in self.file_widgets for path in widget.staged.paths
            ),
        )
        if payload["files"]:
            if getattr(self, "saving", False):
                return
            self.saving = True
            self.notice.setText("Сохранение материала и файлов…")
            service, kind, original = self.service, self.kind, self.original
            for widget in self.file_widgets:
                widget.setEnabled(False)
            BackgroundCall(
                self,
                lambda: service.save_content_package(kind, original, values, **payload),
                self.content_saved,
                self.content_failed,
            )
            return
        self.content_saved(
            self.service.save_content_package(self.kind, self.original, values, **payload)
        )

    def content_failed(self, error):
        self.saving = False
        for widget in self.file_widgets:
            widget.setEnabled(True)
        self.notice.setText(error_message(error))

    def content_saved(self, value):
        self.saving = False
        self.original = value
        for widget in self.file_widgets:
            widget.setEnabled(True)
        self.course.setEnabled(False)
        for widget in self.file_widgets:
            widget.staged.clear()
            widget.refresh()
        self.notice.setText("Сохранено локально")
        callback = getattr(self, "on_saved", None)
        if callback:
            callback(self.original)
        if (
            self.kind == "problems"
            and self.original.is_family
            and not hasattr(self, "variant_page")
        ):
            self.add_variants_tab()
            self.problem_kind.setEnabled(False)

    def issue(self):
        if self.original is None:
            self.save()
        if self.original:
            page = IssueHomeworkPage(self.window, self.original)
            self.window.router.push(page, "Выдать группе")


class SeminarProblems(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.problem_ids = (
            list(
                p.id for p in editor.service.content_targets("seminar_problems", editor.original.id)
            )
            if editor.original
            else []
        )
        layout = QVBoxLayout(self)
        hint(layout, "Задачи связаны с Банком задач; их условия и файлы не копируются.")
        self.model = TableModel(
            [
                ("Задача", lambda p: p.title + (" (удалена)" if p.deleted_at else "")),
                ("Номер", lambda p: p.identifier),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        toolbar(
            layout,
            [
                ("Добавить из банка задач", lambda: run_action(self, self.pick)),
                ("Создать новую задачу", lambda: run_action(self, self.create_problem)),
                ("Убрать из семинара", lambda: run_action(self, self.remove)),
            ],
        )
        self.refresh()

    def ids(self):
        return tuple(self.problem_ids)

    def refresh(self):
        self.model.replace_rows(
            [
                self.editor.service.get_material("problems", id, historical=True)
                for id in self.problem_ids
            ]
        )

    def pick(self):
        from studium.presentation.desktop.problem_picker import ProblemPicker

        picker = ProblemPicker(
            self.editor.service, self.editor.course.currentData(), self.ids(), self
        )
        if picker.exec():
            self.problem_ids = list(picker.ids())
            self.refresh()

    def remove(self):
        problem = selected(self.view)
        if problem:
            self.problem_ids.remove(problem.id)
            self.refresh()

    def create_problem(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Новая задача для семинара")
        dialog.resize(820, 650)
        layout = QVBoxLayout(dialog)
        editor = ContentEditor(self.editor.window, "problems", on_cancel=dialog.reject)
        editor.course.setCurrentIndex(data_index(editor.course, self.editor.course.currentData()))
        editor.course.setEnabled(False)
        editor.purposes.fill(list(PURPOSE_LABELS.items()), [ProblemPurpose.SEMINAR])
        layout.addWidget(editor)

        def saved(problem):
            if problem.id not in self.problem_ids:
                self.problem_ids.append(problem.id)
            if self.editor.original:
                self.editor.service.set_content_links(
                    "seminar_problems", self.editor.original.id, self.ids()
                )
            self.refresh()
            dialog.accept()

        editor.on_saved = saved
        self.problem_dialog, self.problem_editor = dialog, editor
        dialog.exec()


class IssueHomeworkPage(QWidget):
    def __init__(self, window, definition):
        super().__init__()
        self.window, self.definition = window, definition
        layout = QVBoxLayout(self)
        hint(layout, definition.title).setProperty("role", "heading")
        hint(
            layout,
            "Создаётся самостоятельная работа с копией названия и условия. Правки библиотеки не меняют эту работу.",
        )
        form = QFormLayout()
        layout.addLayout(form)
        self.offering = QComboBox()
        for context in window.service.list_offerings():
            if context.course.id == definition.course_id:
                self.offering.addItem(
                    f"{context.group.number} · {context.term.name}", context.offering.id
                )
        form.addRow("Группа / период", self.offering)
        self.issue_week, self.due_week = WeekSelector(), WeekSelector()
        form.addRow("Выдача", self.issue_week)
        form.addRow("Сдача", self.due_week)
        self.notice = hint(layout, "")
        toolbar(layout, [("Выдать", lambda: run_action(self, self.save))])
        self.offering.currentIndexChanged.connect(self.update_weeks)
        self.update_weeks()
        layout.addStretch()

    def update_weeks(self):
        id = self.offering.currentData()
        program = self.window.service.program_for_offering(id) if id else None
        for field in (self.issue_week, self.due_week):
            field.clear()
            field.addItem("Не задана", None)
            for week in range(1, (program.weeks if program else 17) + 1):
                value = AcademicWeekNumber(week)
                field.addItem(week_label(value), value)

    def save(self):
        if self.offering.currentData() is None:
            self.notice.setText("Сначала добавьте дисциплину группе")
            return
        program = self.window.service.program_for_offering(self.offering.currentData())
        if program:
            link = self.window.service.add_program_work(
                program.id,
                self.definition.id,
                planned_issue_week=self.issue_week.currentData(),
                planned_due_week=self.due_week.currentData(),
            )
            self.window.service.issue_program_work(self.offering.currentData(), link.id)
        else:
            self.window.service.create_assessment(
                self.offering.currentData(),
                self.definition.title,
                self.definition.type,
                number=self.definition.label or None,
                description=self.definition.description,
                homework_definition_id=self.definition.id,
                planned_issue_week=self.issue_week.currentData(),
                planned_due_week=self.due_week.currentData(),
            )
        self.window.router.back()
        self.window.refresh()


class MaterialDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(280, 68)

    def paint(self, painter, option, index):
        item = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return super().paint(painter, option, index)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        # Let Qt retain its native selection/focus/hover painting.
        from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

        background = QStyleOptionViewItem(option)
        self.initStyleOption(background, index)
        background.text = ""
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, background, painter)
        rect = option.rect.adjusted(12, 8, -12, -8)
        painter.setPen(option.palette.text().color())
        font = option.font
        font.setBold(True)
        painter.setFont(font)
        title = (item.identifier + " · " if getattr(item, "identifier", "") else "") + item.title
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignTop,
            option.fontMetrics.elidedText(title, Qt.TextElideMode.ElideRight, rect.width()),
        )
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(option.palette.placeholderText().color())
        subtitle = " · ".join(item.tags) or "Без тегов"
        painter.drawText(
            rect.adjusted(0, 27, 0, 0),
            Qt.AlignmentFlag.AlignTop,
            option.fontMetrics.elidedText(subtitle, Qt.TextElideMode.ElideRight, rect.width()),
        )
        painter.restore()


class LibraryList(QWidget):
    def __init__(self, window, kind, *, lesson_type=None):
        super().__init__()
        self.window, self.kind = window, kind
        self.lesson_type = lesson_type
        layout = QVBoxLayout(self)
        self.create_button = QPushButton(
            "Добавить задачу" if kind == "problems" else "Создать материал"
        )
        self.create_button.setProperty("primary", True)
        self.create_button.clicked.connect(lambda: run_action(self, lambda: self.edit(None)))
        action_row = QHBoxLayout()
        action_row.addWidget(self.create_button)
        if kind == "problems":
            generate = QPushButton("Сформировать набор вариантов")
            generate.clicked.connect(lambda: run_action(self, self.generate_set))
            action_row.addWidget(generate)
        action_row.addStretch()
        layout.addLayout(action_row)
        row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Номер, название или текст" if kind == "problems" else "Поиск по названию и тексту"
        )
        self.course = QComboBox()
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Теги через запятую")
        row.addWidget(self.search, 2)
        row.addWidget(self.course, 1)
        self.purpose = QComboBox()
        self.purpose.addItem("Любое назначение", None)
        for purpose, title in PURPOSE_LABELS.items():
            self.purpose.addItem(title, purpose)
        if kind == "problems":
            row.addWidget(self.purpose, 1)
        else:
            row.addWidget(self.tags, 1)
        layout.addLayout(row)
        self.collection, self.week, self.topic, self.type = (
            QComboBox(),
            WeekSelector(),
            QComboBox(),
            QComboBox(),
        )
        self.skill = QComboBox()
        self.type.addItem("Любой вид", None)
        for type, title in LITERATURE_LABELS.items():
            self.type.addItem(title, type)
        if kind == "problems":
            filters = QWidget()
            filter_layout = QGridLayout(filters)
            for index, (label, field) in enumerate(
                (
                    ("Тема", self.topic),
                    ("Навык", self.skill),
                    ("Теги", self.tags),
                    ("Коллекция", self.collection),
                )
            ):
                filter_layout.addWidget(QLabel(label), index // 2, (index % 2) * 2)
                filter_layout.addWidget(field, index // 2, (index % 2) * 2 + 1)
            filter_layout.setColumnStretch(1, 1)
            filter_layout.setColumnStretch(3, 1)
            self.extra_filters = filters
            layout.addWidget(self.extra_filters)
        if kind == "seminars":
            row = QHBoxLayout()
            row.addWidget(self.week)
            row.addWidget(self.topic)
            layout.addLayout(row)
        if kind == "literature":
            layout.addWidget(self.type)
        self.model = TableModel(
            [
                ("Название", lambda m: m.title),
                ("Теги", lambda m: ", ".join(m.tags)),
                (
                    "Дополнительно",
                    lambda m: (
                        week_label(m.planned_week)
                        if kind == "seminars"
                        else LITERATURE_LABELS[m.type]
                        if kind == "literature"
                        else m.label
                        if kind == "homework"
                        else "Комплект условий"
                        if kind == "packs"
                        else ""
                        if kind == "methodical"
                        else m.difficulty
                    ),
                ),
            ]
        )
        self.view = table(self.model)
        if kind == "problems":
            self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            self.view.setItemDelegateForColumn(0, MaterialDelegate(self.view))
            self.view.verticalHeader().setDefaultSectionSize(68)
            self.view.horizontalHeader().hide()
            self.view.hideColumn(1)
            self.view.hideColumn(2)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))
        if kind == "problems":
            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            self.splitter.addWidget(self.view)
            self.preview_panel = QWidget()
            preview_layout = QVBoxLayout(self.preview_panel)
            self.preview_variant = QComboBox()
            self.preview_variant.setAccessibleName("Вариант условия")
            preview_layout.addWidget(self.preview_variant)
            self.preview_pane = FilePreviewPane(window.service)
            preview_layout.addWidget(self.preview_pane, 1)
            self.splitter.addWidget(self.preview_panel)
            self.splitter.setSizes([560, 380])
            layout.addWidget(self.splitter, 1)
            self.view.selectionModel().currentChanged.connect(lambda *_: self.select_preview())
            self.preview_variant.currentIndexChanged.connect(lambda _: self.load_preview())
            self.preview_toggle = QPushButton("Предпросмотр")
            self.preview_toggle.setCheckable(True)
            self.preview_toggle.clicked.connect(self.update_preview_layout)
            action_row.insertWidget(1, self.preview_toggle)
        else:
            layout.addWidget(self.view, 1)
        self.notice = hint(layout, "")
        self.empty = EmptyState(
            "Материалов пока нет",
            "Создайте материал или измените поисковые фильтры.",
        )
        layout.addWidget(self.empty)
        toolbar(
            layout,
            [
                ("Открыть", lambda: run_action(self, self.open)),
                ("Удалить", lambda: run_action(self, self.archive)),
            ],
        )
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(lambda: run_action(self, self.load))
        for field in (self.search, self.tags):
            field.textChanged.connect(lambda _: self.timer.start())
        for field in (self.collection, self.week, self.topic, self.type, self.skill, self.purpose):
            field.currentIndexChanged.connect(lambda _: self.timer.start())
        self.course.currentIndexChanged.connect(lambda _: self.refresh_options())
        search_shortcut(self, self.search)

    def refresh(self):
        previous = self.course.currentData()
        self.course.blockSignals(True)
        self.course.clear()
        self.course.addItem("Все дисциплины", None)
        for course in self.window.service.list_courses():
            self.course.addItem(course.name, course.id)
        self.course.setCurrentIndex(max(0, data_index(self.course, previous)))
        self.course.blockSignals(False)
        self.refresh_options()

    def refresh_options(self):
        s, course = self.window.service, self.course.currentData()
        for field, label in (
            (self.collection, "Все наборы"),
            (self.topic, "Все темы"),
            (self.skill, "Все навыки"),
        ):
            previous = field.currentData()
            field.blockSignals(True)
            field.clear()
            field.addItem(label, None)
            values = (
                [(c.id, c.title) for c in s.list_problem_collections(course)]
                if field is self.collection
                else [
                    (node.id, node.title)
                    for node in (
                        s.list_course_skills(course)
                        if field is self.skill
                        else s.list_course_topics(course)
                    )
                ]
                if course
                else []
            )
            for id, title in values:
                field.addItem(title, id)
            field.setCurrentIndex(max(0, data_index(field, previous)))
            field.blockSignals(False)
        self.load()

    def load(self):
        if not self.window.service:
            return
        rows = self.window.service.list_materials(
            self.kind,
            course_id=self.course.currentData(),
            search=self.search.text(),
            tags=tuple(t.strip() for t in self.tags.text().split(",") if t.strip()),
            collection_id=self.collection.currentData() if self.kind == "problems" else None,
            week=self.week.currentData() if self.kind == "seminars" else None,
            topic_id=self.topic.currentData() if self.kind in {"seminars", "problems"} else None,
            skill_id=self.skill.currentData() if self.kind == "problems" else None,
            literature_type=self.type.currentData() if self.kind == "literature" else None,
            purpose=self.purpose.currentData() if self.kind == "problems" else None,
            material_type=self.lesson_type
            if self.kind == "seminars"
            else AssessmentType.HOMEWORK
            if self.kind == "homework"
            else None,
        )
        self.model.replace_rows(rows)
        self.empty.setVisible(not rows)
        self.view.setVisible(bool(rows))
        self.notice.setText(
            f"Материалов: {len(rows)}"
            if rows
            else "Материалов пока нет или фильтр не дал результатов"
        )
        self.update_preview_layout()

    def edit(self, original):
        self.window.router.routes[-1].refresh = self.refresh
        self.window.router.push(
            ContentEditor(self.window, self.kind, original, lesson_type=self.lesson_type),
            original.title if original else "Новый материал",
        )

    def select_preview(self):
        index = self.view.currentIndex()
        problem = self.model.rows[index.row()] if index.isValid() else None
        self.preview_variant.blockSignals(True)
        self.preview_variant.clear()
        if problem:
            self.preview_variant.addItem(
                "Общее условие" if problem.is_family else problem.title, problem.id
            )
            if problem.is_family:
                for variant in self.window.service.list_problem_variants(problem.id):
                    self.preview_variant.addItem("Вариант " + variant.variant_code, variant.id)
        self.preview_variant.blockSignals(False)
        self.preview_variant.setVisible(bool(problem and problem.is_family))
        self.load_preview()

    def load_preview(self):
        if self.kind != "problems":
            return
        self.preview_pane.service = self.window.service
        id = self.preview_variant.currentData()
        self.preview_generation = getattr(self, "preview_generation", 0) + 1
        generation = self.preview_generation
        self.preview_pane.set_entries(
            (), placeholder="Чтение условия…" if id else "Выберите задачу для просмотра условия."
        )
        if id:
            BackgroundCall(
                self,
                lambda: self.window.service.problem_preview_files(id),
                lambda entries: (
                    self.preview_pane.set_entries(entries)
                    if generation == self.preview_generation
                    else None
                ),
                lambda error: (
                    self.preview_pane.set_entries((), placeholder=error_message(error))
                    if generation == self.preview_generation
                    else None
                ),
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview_layout()

    def update_preview_layout(self):
        if hasattr(self, "preview_toggle"):
            wide = self.width() >= 850
            preview = self.preview_toggle.isChecked()
            self.preview_panel.setVisible(wide or preview)
            self.view.setVisible((wide or not preview) and bool(self.model.rows))
            self.extra_filters.setVisible(wide or not preview)
            self.preview_toggle.setVisible(not wide)
            self.preview_toggle.setText("Список" if preview else "Предпросмотр")

    def on_navigation_leave(self):
        if hasattr(self, "preview_pane"):
            self.preview_generation = getattr(self, "preview_generation", 0) + 1
            self.preview_pane.on_navigation_leave()

    def open(self):
        original = selected(self.view)
        if original:
            self.edit(original)

    def archive(self):
        original = selected(self.view)
        if original and confirm(
            self,
            f"Удалить «{original.title}» из Библиотеки? История выданных работ, вариантов и файлы сохранятся.",
            action_label="Удалить",
        ):
            self.window.service.archive_material(self.kind, original)
            self.load()

    def generate_set(self):
        from studium.presentation.desktop.dialogs import ChoiceDialog
        from studium.presentation.desktop.tickets import TicketGeneratorPage

        contexts = self.window.service.list_offerings()
        if not contexts:
            self.notice.setText("Добавьте группу и дисциплину для назначения рубежного контроля")
            return
        chosen = []
        picker = ChoiceDialog(
            "Рубежный контроль",
            "Группа",
            [(c, c.group.number + " · " + c.course.name) for c in contexts],
            chosen.append,
            self,
        )
        if not picker.exec():
            return
        context = chosen[0]
        ids = tuple(
            self.model.rows[index.row()].id for index in self.view.selectionModel().selectedRows()
        )
        if any(
            self.model.rows[index.row()].course_id != context.course.id
            for index in self.view.selectionModel().selectedRows()
        ):
            self.notice.setText("Выбранные задачи должны относиться к дисциплине группы")
            return
        page = TicketGeneratorPage(self.window, lambda: context)
        page.refresh()
        page.selected_problem_ids = ids
        page.purpose.setCurrentIndex(page.purpose.findData(self.purpose.currentData()))
        page.tags.setText(self.tags.text())
        page.collection.setCurrentIndex(
            max(0, data_index(page.collection, self.collection.currentData()))
        )
        self.window.router.push(page, "Рубежный контроль · варианты")


class HomeworkLibrary(QWidget):
    def __init__(self, window):
        super().__init__()
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.definitions = LibraryList(window, "homework")
        self.packs = LibraryList(window, "packs")
        self.tabs.addTab(self.definitions, "Условия заданий")
        self.tabs.addTab(self.packs, "Комплекты условий / общий PDF")
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(lambda _: self.refresh())

    def refresh(self):
        self.tabs.currentWidget().refresh()


class ControlSetsPage(QWidget):
    """Only saved TicketSets here; raw source problems remain in the bank."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        hint(layout, "Сохранённые наборы вариантов из банка задач")
        self.model = TableModel(
            [
                ("Набор вариантов", lambda row: row[0].title),
                ("Группа", lambda row: row[1].group.number),
                ("Дисциплина", lambda row: row[1].course.name),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))
        self.empty = hint(
            layout, "Наборов пока нет. Выберите задачи в банке и сформируйте варианты."
        )
        toolbar(
            layout,
            [
                ("Перейти в банк задач", lambda: window.library_page.select_section("problems")),
                ("Открыть набор", lambda: run_action(self, self.open)),
                ("Удалить", lambda: run_action(self, self.delete)),
            ],
        )

    def refresh(self):
        rows = [
            (s, c)
            for c in self.window.service.list_offerings()
            for s in self.window.service.list_ticket_sets(c.offering.id)
        ]
        self.model.replace_rows(rows)
        self.empty.setVisible(not rows)

    def open(self):
        from studium.presentation.desktop.tickets import TicketGeneratorPage

        row = selected(self.view)
        if row:
            saved, context = row
            page = TicketGeneratorPage(self.window, lambda: context)
            page.refresh()
            page.saved_sets.setCurrentIndex(data_index(page.saved_sets, saved.id))
            page.open_saved()
            self.window.router.push(page, saved.title)

    def delete(self):
        row = selected(self.view)
        if row and confirm_delete(self, self.window.service, "ticket_set", row[0]):
            self.window.service.safe_delete("ticket_set", row[0])
            self.refresh()


class LibraryPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        hint(layout, "Библиотека").setProperty("role", "heading")
        self.tabs = QTabWidget()
        self.lists = {}
        for kind, title in LIBRARY_LABELS.items():
            page = (
                HomeworkLibrary(window)
                if kind == "homework"
                else ControlSetsPage(window)
                if kind == "control"
                else LibraryList(
                    window,
                    "seminars",
                    lesson_type=LessonType.LECTURE if kind == "lectures" else LessonType.SEMINAR,
                )
                if kind in {"seminars", "lectures"}
                else LibraryList(window, kind)
            )
            self.lists[kind] = page
            self.tabs.addTab(page, title)
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(lambda _: self.refresh())

    def refresh(self):
        if self.window.service:
            self.tabs.currentWidget().refresh()

    def select_section(self, kind):
        self.tabs.setCurrentWidget(self.lists[kind])
        self.refresh()
