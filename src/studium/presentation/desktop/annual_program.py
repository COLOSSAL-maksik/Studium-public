"""One annual program workspace: drafts, frozen editions, plan, totals and usage."""

import json
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from studium.domain import annual_program as a
from studium.domain.qa import direction_identity, score_text
from studium.domain.value_objects import EntityId
from studium.presentation.desktop.annual_forms import RowForm, lesson_form
from studium.presentation.desktop.annual_forms import run_program_action as run_action
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import hint, toolbar
from studium.presentation.desktop.messages import ASSESSMENT_LABELS


def readonly_table(labels):
    from PySide6.QtWidgets import QAbstractItemView

    view = QTableWidget(0, len(labels))
    view.setHorizontalHeaderLabels(labels)
    view.setMinimumHeight(180)
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    view.horizontalHeader().setStretchLastSection(True)
    return view


def fill(view, rows):
    view.setRowCount(0)
    for values in rows:
        i = view.rowCount()
        view.insertRow(i)
        for j, value in enumerate(values):
            item = QTableWidgetItem(str(value if value is not None else "—"))
            item.setToolTip(item.text())
            view.setItem(i, j, item)
    view.resizeColumnsToContents()


class ProgramEditor(QWidget):
    def __init__(self, window, course, *, draft=None, version=None):
        super().__init__()
        self.window, self.service, self.course = window, window.service, course
        self.draft, self.version = draft, version
        self.data = json.loads((draft or version).content_json)
        self.legacy = "annual" not in self.data
        if self.legacy:
            self.data = self.service.annual_version_content(version)
        self.dirty = False
        self.busy = False
        self.selected_key = None
        layout = QVBoxLayout(self)
        self.heading = hint(layout, "")
        self.heading.setProperty("role", "heading")
        self.status = hint(layout, "")
        self.actions = QWidget()
        actions = QVBoxLayout(self.actions)
        actions.setContentsMargins(0, 0, 0, 0)
        toolbar(
            actions,
            [
                ("Сохранить черновик", lambda: run_action(self, self.save)),
                ("Проверить заполнение", lambda: run_action(self, self.check)),
                ("Подготовить версию", lambda: run_action(self, self.publish)),
            ],
        )
        self.actions.setVisible(draft is not None)
        layout.addWidget(self.actions)
        toolbar(
            layout,
            [
                ("Создать новую редакцию", lambda: run_action(self, self.next_revision)),
                (
                    "Создать копию",
                    lambda: run_action(self, lambda: self.next_revision(independent=True)),
                ),
                ("Экспортировать", lambda: run_action(self, self.export)),
                ("Импортировать", lambda: import_program(self.window, self.course)),
            ],
        )
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        layout.addWidget(self.tabs, 1)
        self.passport_page()
        self.plan_page()
        self.collection_page(
            "outcomes", "Результаты обучения", ["Категория", "Код", "Формулировка"]
        )
        self.collection_page(
            "prerequisites", "Предварительная подготовка", ["Дисциплина", "Необходимая подготовка"]
        )
        self.volume_page()
        self.points_page()
        self.materials_page()
        self.usage_page()
        self.notice = hint(layout, "")
        self.tabs.currentChanged.connect(lambda _: self.refresh_summaries())
        self.shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        self.shortcut.activated.connect(lambda: run_action(self, self.save))
        self.refresh_all()
        if not draft:
            self.lock_editor()
            self.status.setText(
                "Готовая версия · режим просмотра. Для изменений создайте новую редакцию."
                + (" Номер семестра старых модулей может быть неизвестен." if self.legacy else "")
            )

    @property
    def annual(self):
        return self.data["annual"]

    def page(self, label, *, editable=True):
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, label)
        if not hasattr(self, "editable_pages"):
            self.editable_pages = []
        if editable:
            self.editable_pages.append(page)
        return page, layout

    def mark_dirty(self, *_):
        if self.draft:
            self.dirty = True
            self.status.setText("Черновик · есть несохранённые изменения")

    def passport_page(self):
        page, layout = self.page("Паспорт")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.passport_fields = {}
        p = self.annual["passport"]
        for name, label in (
            ("title", "Название программы"),
            ("label", "Редакция"),
            ("academic_year", "Учебный год применения (необязательно)"),
        ):
            field = QLineEdit(p[name])
            field.textChanged.connect(self.mark_dirty)
            form.addRow(label, field)
            self.passport_fields[name] = field
        form.addRow("Дисциплина", QLabel(self.course.name))
        self.minutes = QSpinBox()
        self.minutes.setRange(1, 180)
        self.minutes.setValue(p["academic_hour_minutes"])
        self.minutes.valueChanged.connect(self.mark_dirty)
        form.addRow("Минут в академическом часе (по умолчанию 45)", self.minutes)
        self.notes = QPlainTextEdit(p["notes"])
        self.notes.setMaximumHeight(110)
        self.notes.textChanged.connect(self.mark_dirty)
        form.addRow("Описание / примечания", self.notes)
        self.directions = QPlainTextEdit(
            "\n".join(v["code"] + (" — " + v["name"] if v["name"] else "") for v in p["directions"])
        )
        self.directions.setPlaceholderText("Один код на строку; необязательно: код — название")
        self.directions.setMaximumHeight(110)
        self.directions.textChanged.connect(self.mark_dirty)
        form.addRow("Специальности / направления", self.directions)
        self.na = {}
        for name, label in (
            ("outcomes", "Результаты обучения"),
            ("prerequisites", "Предварительная подготовка"),
            ("lessons", "Занятия"),
            ("works", "Предусмотренные работы"),
        ):
            box = QCheckBox(label + " — не предусмотрено")
            box.setChecked(name in self.annual["not_applicable"])
            box.toggled.connect(self.mark_dirty)
            form.addRow(box)
            self.na[name] = box
        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def collect(self):
        data = deepcopy(self.data)
        p = data["annual"]["passport"]
        p.update({name: field.text() for name, field in self.passport_fields.items()})
        p.update(notes=self.notes.toPlainText(), academic_hour_minutes=self.minutes.value())
        p["directions"] = []
        for line in self.directions.toPlainText().splitlines():
            if line.strip():
                parts = line.split("—", 1)
                code, _ = direction_identity(parts[0])
                p["directions"].append(
                    {"code": code, "name": parts[1].strip() if len(parts) > 1 else ""}
                )
        data["annual"]["not_applicable"] = [
            name for name, box in self.na.items() if box.isChecked()
        ]
        return data

    def change(self, action):
        if not self.draft:
            raise ValueError("Готовая версия доступна только для просмотра")
        data = self.collect()
        action(data["annual"])
        a.validate(data["annual"])
        self.data = data
        self.mark_dirty()
        self.refresh_all()

    def plan_page(self):
        page, layout = self.page("Годовой план")
        hint(layout, "Относительные недели курса. Реальные даты задаются в рабочем плане группы.")
        split = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Семестр / модуль", "Недели"])
        self.tree.currentItemChanged.connect(lambda *_: self.show_lessons())
        split.addWidget(self.tree)
        right = QWidget()
        body = QVBoxLayout(right)
        self.lessons = readonly_table(["Вид", "№", "Название", "Темы", "Акад. часы", "Неделя"])
        body.addWidget(self.lessons)
        self.lessons.doubleClicked.connect(
            lambda _: run_action(self, lambda: self.edit_lesson(edit=True))
        )
        toolbar(
            body,
            [
                ("+ Занятие", lambda: run_action(self, self.edit_lesson)),
                ("Добавить несколько", lambda: run_action(self, self.bulk_lessons)),
                ("Изменить", lambda: run_action(self, lambda: self.edit_lesson(edit=True))),
                ("↑", lambda: run_action(self, lambda: self.move_lesson(-1))),
                ("↓", lambda: run_action(self, lambda: self.move_lesson(1))),
                ("Убрать занятие", lambda: run_action(self, self.remove_lesson)),
            ],
        )
        self.lesson_summary = hint(body, "Выберите модуль слева")
        split.addWidget(right)
        split.setSizes([260, 640])
        layout.addWidget(split, 1)
        toolbar(
            layout,
            [
                ("+ Семестр", lambda: run_action(self, self.edit_semester)),
                ("+ Модуль", lambda: run_action(self, self.edit_module)),
                ("Изменить", lambda: run_action(self, self.edit_node)),
                ("Копировать", lambda: run_action(self, self.copy_node)),
                ("↑", lambda: run_action(self, lambda: self.move_node(-1))),
                ("↓", lambda: run_action(self, lambda: self.move_node(1))),
                ("Удалить фрагмент", lambda: run_action(self, self.remove_node)),
                ("Сопоставить старый модуль", lambda: run_action(self, self.map_legacy)),
            ],
        )

    def nodes(self):
        item = self.tree.currentItem()
        id = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        for s in self.annual["semesters"]:
            if s["key"] == id:
                return s, None
            for m in s["modules"]:
                if m["key"] == id:
                    return s, m
        return None, None

    def refresh_tree(self):
        s, m = self.nodes()
        selected = self.selected_key or (m["key"] if m else s["key"] if s else None)
        self.selected_key = None
        self.tree.blockSignals(True)
        self.tree.clear()
        current = None
        for s in self.annual["semesters"]:
            top = QTreeWidgetItem([f"{s['number']}. {s['title']}", str(s["weeks"])])
            top.setData(0, Qt.ItemDataRole.UserRole, s["key"])
            self.tree.addTopLevelItem(top)
            if s["key"] == selected:
                current = top
            for m in s["modules"]:
                item = QTreeWidgetItem([m["title"], f"{m['start_week']}–{m['end_week']}"])
                item.setData(0, Qt.ItemDataRole.UserRole, m["key"])
                top.addChild(item)
                if m["key"] == selected:
                    current = item
        for old in self.annual.get("legacy_unmapped_modules", []):
            item = QTreeWidgetItem([old["title"], "Семестр неизвестен"])
            item.setData(0, Qt.ItemDataRole.UserRole, old.get("key", old.get("id")))
            self.tree.addTopLevelItem(item)
        self.tree.expandAll()
        if current:
            self.tree.setCurrentItem(current)
        self.tree.blockSignals(False)
        self.show_lessons()

    def show_lessons(self):
        s, m = self.nodes()
        topics = {str(t.id): t.title for t in self.service.list_course_topics(self.course.id)}
        topics.update({v["id"]: v["title"] for v in self.data.get("topic_ids_snapshots", [])})
        fill(
            self.lessons,
            [
                (
                    a.LESSON_KINDS[lesson["kind"]],
                    i + 1,
                    lesson["title"],
                    ", ".join(topics.get(id, "Тема недоступна") for id in lesson["topic_ids"]),
                    lesson.get("hours") or "Не указано",
                    lesson.get("week"),
                )
                for i, lesson in enumerate(m["lessons"] if m else [])
            ],
        )
        if m:
            counts = {
                kind: sum(lesson["kind"] == kind for lesson in m["lessons"])
                for kind in a.LESSON_KINDS
            }
            total = sum(
                (a.hours(lesson.get("hours") or "0") for lesson in m["lessons"]), a.hours("0")
            )
            semtotal = sum(
                (
                    a.hours(lesson.get("hours") or "0")
                    for mod in s["modules"]
                    for lesson in mod["lessons"]
                ),
                a.hours("0"),
            )
            self.lesson_summary.setText(
                " · ".join(f"{a.LESSON_KINDS[k]}: {v}" for k, v in counts.items())
                + f"\nМодуль: {total} акад. ч. · Семестр: {semtotal} акад. ч."
            )
        else:
            self.lesson_summary.setText(
                "Выберите модуль. Пустые строки занятий можно сохранить в черновике."
            )

    def edit_semester(self, source=None):
        source = source or dict(
            key=a.key(),
            number=max((s["number"] for s in self.annual["semesters"]), default=0) + 1,
            title="",
            weeks=17,
            modules=[],
        )

        def apply(value):
            self.change(lambda annual: self.replace_row(annual["semesters"], value))
            self.selected_key = value["key"]
            self.refresh_tree()

        form = RowForm("Семестр курса", source, apply, self)
        form.integer("number", "Номер семестра курса")
        form.text("title", "Название")
        form.integer("weeks", "Учебных недель")
        form.exec()

    @staticmethod
    def replace_row(rows, value):
        index = next((i for i, v in enumerate(rows) if v["key"] == value["key"]), len(rows))
        if index == len(rows):
            rows.append(value)
        else:
            rows[index] = value

    def edit_module(self, source=None):
        s, _ = self.nodes()
        if not s:
            raise ValueError("Выберите семестр")
        source = source or dict(
            key=a.key(), title="", start_week=1, end_week=s["weeks"], lessons=[], works=[]
        )

        def apply(value):
            self.change(
                lambda annual: self.replace_row(
                    next(row for row in annual["semesters"] if row["key"] == s["key"])["modules"],
                    value,
                )
            )
            self.selected_key = value["key"]
            self.refresh_tree()

        form = RowForm("Учебный модуль", source, apply, self)
        form.text("title", "Название")
        form.integer("start_week", "С недели", maximum=s["weeks"])
        form.integer("end_week", "По неделю", maximum=s["weeks"])
        form.exec()

    def edit_node(self):
        s, m = self.nodes()
        if m:
            self.edit_module(m)
        elif s:
            self.edit_semester(s)

    def copy_node(self):
        s, m = self.nodes()
        if m:
            self.edit_module(a.copy_fragment(m))
        elif s:
            copied = a.copy_fragment(s)
            copied["number"] = max(v["number"] for v in self.annual["semesters"]) + 1
            self.edit_semester(copied)

    def move_node(self, delta):
        s, m = self.nodes()
        if not s:
            return

        def apply(annual):
            rows = (
                next(v for v in annual["semesters"] if v["key"] == s["key"])["modules"]
                if m
                else annual["semesters"]
            )
            i = next(i for i, v in enumerate(rows) if v["key"] == (m or s)["key"])
            j = i + delta
            if 0 <= j < len(rows):
                rows[i], rows[j] = rows[j], rows[i]

        self.change(apply)

    def remove_node(self):
        s, m = self.nodes()
        if not s:
            return

        def apply(annual):
            rows = (
                next(v for v in annual["semesters"] if v["key"] == s["key"])["modules"]
                if m
                else annual["semesters"]
            )
            rows[:] = [v for v in rows if v["key"] != (m or s)["key"]]

        if (
            QMessageBox.question(
                self,
                "Удаление",
                "Удалить фрагмент из черновика? Сохранённые версии и планы остаются.",
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.change(apply)

    def map_legacy(self):
        pending = self.annual.get("legacy_unmapped_modules", [])
        if not pending:
            raise ValueError("Несопоставленных старых модулей нет")
        s, _ = self.nodes()
        if not s:
            raise ValueError("Сначала добавьте и выберите семестр курса")
        names = [v["title"] for v in pending]
        selected, ok = QInputDialog.getItem(
            self,
            "Сопоставить модуль",
            "Исходный модуль (номер семестра неизвестен)",
            names,
            0,
            False,
        )
        if ok:
            old = pending[names.index(selected)]
            value = dict(
                key=old.get("key", old.get("id", a.key())),
                title=old["title"],
                start_week=old["start_week"],
                end_week=old["end_week"],
                lessons=[],
                works=[],
            )

            definitions = {str(d["id"]): d for d in self.data.get("definitions", [])}
            old_key = old.get("key", old.get("id"))
            for work in self.data.get("works", []):
                if work.get("module_key", work.get("module_id")) == old_key:
                    definition = definitions.get(str(work["definition_id"]), {})
                    value["works"].append(
                        dict(
                            work,
                            key=a.key(),
                            title=definition.get("title", work.get("title", "")),
                            category=definition.get("type", "HOMEWORK"),
                        )
                    )

            def apply(annual):
                next(v for v in annual["semesters"] if v["key"] == s["key"])["modules"].append(
                    value
                )
                annual["legacy_unmapped_modules"].remove(old)

            self.change(apply)

    def module_action(self, action):
        s, m = self.nodes()
        if not m:
            raise ValueError("Выберите модуль в годовом плане")

        def apply(annual):
            module = next(
                mod
                for sem in annual["semesters"]
                for mod in sem["modules"]
                if mod["key"] == m["key"]
            )
            action(module)

        self.change(apply)

    def edit_lesson(self, *, edit=False):
        _, m = self.nodes()
        if not m:
            raise ValueError("Выберите модуль")
        index = self.lessons.currentRow()
        if edit and index < 0:
            return
        source = (
            m["lessons"][index]
            if edit
            else dict(
                key=a.key(), kind="LECTURE", title="", hours="", topic_ids=[], week=None, notes=""
            )
        )
        lesson_form(
            self,
            source,
            lambda value: self.module_action(
                lambda module: self.replace_row(module["lessons"], value)
            ),
        ).exec()

    def bulk_lessons(self):
        form = RowForm(
            "Добавить занятия",
            {"kind": "LECTURE", "count": 1},
            lambda value: self.module_action(
                lambda m: m["lessons"].extend(
                    dict(
                        key=a.key(),
                        kind=value["kind"],
                        title="",
                        hours="",
                        topic_ids=[],
                        week=None,
                        notes="",
                    )
                    for _ in range(value["count"])
                )
            ),
            self,
        )
        form.choice("kind", "Вид занятий", a.LESSON_KINDS.items())
        form.integer("count", "Количество строк", maximum=100)
        form.exec()

    def move_lesson(self, delta):
        index = self.lessons.currentRow()

        def apply(m):
            j = index + delta
            if index >= 0 and 0 <= j < len(m["lessons"]):
                m["lessons"][index], m["lessons"][j] = m["lessons"][j], m["lessons"][index]

        self.module_action(apply)
        self.lessons.selectRow(index + delta)

    def remove_lesson(self):
        index = self.lessons.currentRow()
        if index >= 0:
            self.module_action(lambda m: m["lessons"].pop(index))

    def collection_page(self, name, label, columns):
        page, layout = self.page(label)
        view = readonly_table(columns)
        setattr(self, name + "_table", view)
        layout.addWidget(view, 1)
        toolbar(
            layout,
            [
                ("Добавить", lambda: run_action(self, lambda: self.edit_collection(name))),
                (
                    "Изменить",
                    lambda: run_action(self, lambda: self.edit_collection(name, edit=True)),
                ),
                ("↑", lambda: run_action(self, lambda: self.move_collection(name, -1))),
                ("↓", lambda: run_action(self, lambda: self.move_collection(name, 1))),
                ("Удалить", lambda: run_action(self, lambda: self.remove_collection(name))),
            ],
        )
        view.doubleClicked.connect(
            lambda _: run_action(self, lambda: self.edit_collection(name, edit=True))
        )

    def edit_collection(self, name, *, edit=False):
        view = getattr(self, name + "_table")
        if edit and view.currentRow() < 0:
            return
        source = self.annual[name][view.currentRow()] if edit else {"key": a.key()}
        form = RowForm(
            "Результат обучения" if name == "outcomes" else "Предварительная подготовка",
            source,
            lambda value: self.change(lambda annual: self.replace_row(annual[name], value)),
            self,
        )
        if name == "outcomes":
            form.choice("category", "Категория", a.OUTCOME_KINDS.items())
            form.text("code", "Код (необязательно)")
            form.text("text", "Формулировка", multiline=True)
            form.topics(self.service, self.course.id)
            form.many(
                "skill_ids",
                "Навыки",
                [(str(v.id), v.title) for v in self.service.list_course_skills(self.course.id)],
            )
            form.many(
                "module_keys",
                "Модули",
                [
                    (m["key"], f"{s['title']} / {m['title']}")
                    for s in self.annual["semesters"]
                    for m in s["modules"]
                ],
            )
            form.many(
                "work_keys",
                "Предусмотренные работы",
                [
                    (w["key"], w["title"])
                    for s in self.annual["semesters"]
                    for m in s["modules"]
                    for w in m["works"]
                ],
            )
        else:
            form.text("discipline", "Дисциплина")
            form.text("content", "Необходимая подготовка", multiline=True)
            form.choice(
                "course_id",
                "Связь с местным справочником",
                [(str(c.id), c.name) for c in self.service.list_courses()],
                optional=True,
            )
        form.exec()

    def move_collection(self, name, delta):
        index = getattr(self, name + "_table").currentRow()

        def apply(annual):
            rows = annual[name]
            j = index + delta
            if index >= 0 and 0 <= j < len(rows):
                rows[index], rows[j] = rows[j], rows[index]

        self.change(apply)
        getattr(self, name + "_table").selectRow(index + delta)

    def remove_collection(self, name):
        index = getattr(self, name + "_table").currentRow()
        if index >= 0:
            self.change(lambda annual: annual[name].pop(index))

    def volume_page(self):
        page, layout = self.page("Объём дисциплины")
        hint(
            layout,
            "Академические часы: точность до 0,01 без округления. Лекции, семинары и лабораторные считаются только из занятий. Другие виды нагрузки вводятся отдельными непересекающимися строками.",
        )
        self.volume_table = readonly_table(
            ["Семестр", "Вид", "Занятий", "Акад. часы", "Норматив", "Расхождение"]
        )
        layout.addWidget(self.volume_table, 1)
        self.loads_table = readonly_table(["Семестр / модуль", "Вид", "Акад. часы", "Роль"])
        layout.addWidget(self.loads_table, 1)
        toolbar(
            layout,
            [
                ("+ Нагрузка", lambda: run_action(self, self.edit_load)),
                ("+ Норматив", lambda: run_action(self, lambda: self.edit_load(norm=True))),
                ("Изменить", lambda: run_action(self, lambda: self.edit_load(edit=True))),
                ("Удалить", lambda: run_action(self, self.remove_load)),
            ],
        )

    def edit_load(self, *, norm=False, edit=False):
        index = self.loads_table.currentRow()
        entries = [("loads", v) for v in self.annual["loads"]] + [
            ("norms", v) for v in self.annual["norms"]
        ]
        name = "norms" if norm else "loads"
        source = {"key": a.key(), "hours": "0"}
        if edit:
            if index < 0:
                return
            name, source = entries[index]
        form = RowForm(
            "Норматив" if name == "norms" else "Нагрузка вне занятий",
            source,
            lambda value: self.change(lambda annual: self.replace_row(annual[name], value)),
            self,
        )
        form.choice(
            "semester_key",
            "Семестр",
            [(s["key"], s["title"]) for s in self.annual["semesters"]],
        )
        if name == "loads":
            form.choice(
                "module_key",
                "Модуль (иначе остаток семестра вне модулей)",
                [(m["key"], m["title"]) for s in self.annual["semesters"] for m in s["modules"]],
                optional=True,
            )
        form.choice(
            "kind",
            "Вид",
            [(k, v) for k, v in a.LOAD_KINDS.items() if name == "norms" or k not in a.LESSON_KINDS],
        )
        form.text("hours", "Академические часы")
        form.exec()

    def remove_load(self):
        index = self.loads_table.currentRow()
        entries = [("loads", v) for v in self.annual["loads"]] + [
            ("norms", v) for v in self.annual["norms"]
        ]
        if index >= 0:
            name, value = entries[index]
            self.change(lambda annual: annual[name].remove(value))

    def points_page(self):
        page, layout = self.page("Баллы и задания")
        self.scoring = QComboBox()
        self.scoring.addItem("Используется балльная система", "POINTS")
        self.scoring.addItem("Балльная система не используется", "NONE")
        self.scoring.setCurrentIndex(max(0, self.scoring.findData(self.annual["scoring"])))
        self.scoring.currentIndexChanged.connect(
            lambda _: run_action(
                self,
                lambda: self.change(
                    lambda annual: annual.update(scoring=self.scoring.currentData())
                ),
            )
        )
        layout.addWidget(self.scoring)
        self.fractional = QCheckBox("Дробный ввод баллов: до двух знаков")
        self.fractional.setChecked(self.service.fractional_scores_enabled())
        self.fractional.toggled.connect(self.service.set_fractional_scores_enabled)
        layout.addWidget(self.fractional)
        hint(
            layout,
            "Минимум — минимальный начисляемый балл; отсутствие оценки не является нулём. Бюджет и работы не суммируются повторно.",
        )
        self.works_table = readonly_table(
            ["Семестр / модуль", "Вид", "Работа", "Минимум", "Максимум", "Правила"]
        )
        layout.addWidget(self.works_table, 1)
        toolbar(
            layout,
            [
                ("+ Работа", lambda: run_action(self, self.edit_work)),
                ("Изменить", lambda: run_action(self, lambda: self.edit_work(edit=True))),
                ("Удалить", lambda: run_action(self, self.remove_work)),
            ],
        )
        self.budgets_table = readonly_table(
            ["Модуль", "Категория", "Лимит", "Распределено", "Остаток"]
        )
        layout.addWidget(self.budgets_table, 1)
        toolbar(
            layout,
            [
                ("Задать бюджет", lambda: run_action(self, self.edit_budget)),
                ("Убрать выбранный бюджет", lambda: run_action(self, self.remove_budget)),
            ],
        )
        self.score_summary = hint(layout, "")
        self.legacy_works = readonly_table(["Прежний модуль", "Работа", "Семестр курса"])
        layout.addWidget(self.legacy_works)

    def module_values(self):
        return [
            (m["key"], f"{s['title']} / {m['title']}")
            for s in self.annual["semesters"]
            for m in s["modules"]
        ]

    def work_rows(self):
        return [
            (s, m, w) for s in self.annual["semesters"] for m in s["modules"] for w in m["works"]
        ]

    def edit_work(self, *, edit=False):
        index = self.works_table.currentRow()
        if edit and index < 0:
            return
        source = (
            dict(self.work_rows()[index][2], module_key=self.work_rows()[index][1]["key"])
            if edit
            else dict(
                key=a.key(), title="", category="HOMEWORK", min_cents=None, max_cents=None, rules=""
            )
        )

        def apply(value):
            module_id = value.pop("module_key")

            def change(annual):
                for s in annual["semesters"]:
                    for m in s["modules"]:
                        m["works"][:] = [w for w in m["works"] if w["key"] != value["key"]]
                        if m["key"] == module_id:
                            m["works"].append(value)

            self.change(change)

        form = RowForm("Предусмотренная работа", source, apply, self)
        form.choice("module_key", "Модуль", self.module_values())
        form.choice("category", "Вид", [(k.value, v) for k, v in ASSESSMENT_LABELS.items()])
        form.text("title", "Название")
        form.choice(
            "definition_id",
            "Шаблон из библиотеки (по желанию)",
            [(str(w.id), w.title) for w in self.service.list_work_definitions(self.course.id)],
            optional=True,
        )
        form.score(
            "min_cents",
            "Минимум (необязательно в черновике)",
            self.service.fractional_scores_enabled(),
        )
        form.score("max_cents", "Максимум", self.service.fractional_scores_enabled())
        form.text("rules", "Правила начисления", multiline=True)
        form.exec()

    def remove_work(self):
        index = self.works_table.currentRow()
        if index < 0:
            return
        _, module, work = self.work_rows()[index]
        self.change(
            lambda annual: next(
                m for s in annual["semesters"] for m in s["modules"] if m["key"] == module["key"]
            )["works"].remove(work)
        )

    def edit_budget(self):
        index = self.budgets_table.currentRow()
        rows = a.score_totals(self.annual)
        source = {"key": a.key(), "category": "*", "max_cents": 0}
        if index >= 0:
            row = rows[index]
            source = next(
                (
                    v
                    for v in self.annual["budgets"]
                    if v["module_key"] == row.module_key and v["category"] == row.category
                ),
                source | {"module_key": row.module_key, "category": row.category},
            )

        def apply(value):
            def change(annual):
                annual["budgets"][:] = [
                    b
                    for b in annual["budgets"]
                    if (b["module_key"], b["category"]) != (value["module_key"], value["category"])
                ]
                annual["budgets"].append(value)

            self.change(change)

        form = RowForm("Бюджет баллов", source, apply, self)
        form.choice("module_key", "Модуль", self.module_values())
        form.choice(
            "category",
            "Категория",
            [("*", "Весь модуль")] + [(k.value, v) for k, v in ASSESSMENT_LABELS.items()],
        )
        form.score("max_cents", "Лимит", self.service.fractional_scores_enabled())
        form.exec()

    def remove_budget(self):
        index = self.budgets_table.currentRow()
        if index >= 0:
            row = a.score_totals(self.annual)[index]
            self.change(
                lambda annual: annual.update(
                    budgets=[
                        b
                        for b in annual["budgets"]
                        if (b["module_key"], b["category"]) != (row.module_key, row.category)
                    ]
                )
            )

    def materials_page(self):
        _, layout = self.page("Материалы", editable=False)
        hint(
            layout,
            "Документы программы, материалы занятий и литература. В экспорт попадают только явно выбранные файлы.",
        )
        self.material_table = readonly_table(["Вид", "Название", "Размер"])
        layout.addWidget(self.material_table)
        self.material_actions = QWidget()
        actions = QVBoxLayout(self.material_actions)
        toolbar(
            actions,
            [
                ("Выбрать материалы / литературу", lambda: run_action(self, self.select_materials)),
                ("Добавить документ", lambda: run_action(self, self.attach_file)),
                ("Обновить библиотечные источники", lambda: run_action(self, self.refresh_sources)),
                ("Убрать документ из черновика", lambda: run_action(self, self.detach_file)),
            ],
        )
        self.material_actions.setVisible(self.draft is not None)
        layout.addWidget(self.material_actions)
        toolbar(layout, [("Открыть выбранный документ", lambda: run_action(self, self.open_file))])

    def select_materials(self):
        form = RowForm(
            "Материалы программы", self.data, lambda values: self.set_materials(values), self
        )
        for name, kind, label in (
            ("seminar_material_ids", "seminars", "Материалы занятий"),
            ("literature_item_ids", "literature", "Литература"),
        ):
            form.many(
                name,
                label,
                [
                    (str(v.id), v.title)
                    for v in self.service.list_materials(kind, course_id=self.course.id)
                ],
            )
        form.exec()

    def set_materials(self, values):
        self.data = self.collect() | {
            name: values[name] for name in ("seminar_material_ids", "literature_item_ids")
        }
        self.mark_dirty()
        self.refresh_materials()

    def refresh_sources(self):
        if (
            QMessageBox.question(
                self,
                "Обновить источники",
                "Зафиксировать текущее содержание выбранных библиотечных шаблонов и материалов при подготовке новой версии? Прежние версии и планы сохранятся.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.save()
        self.draft = self.service.refresh_program_draft_sources(self.draft)
        self.data = json.loads(self.draft.content_json)
        self.refresh_all()

    def attach_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Документы программы")
        if paths:
            self.save()
            self.busy = True
            original = self.draft
            BackgroundCall(
                self,
                lambda: self.service.attach_program_documents(original, paths),
                self.attached,
                self.failed,
            )

    def attached(self, draft):
        self.busy = False
        self.draft = draft
        self.data = json.loads(draft.content_json)
        self.dirty = False
        self.refresh_materials()
        self.status.setText("Черновик · документы сохранены")

    def detach_file(self):
        index = self.material_table.currentRow()
        if index >= 0 and self.material_rows[index][0] == "file":
            id = self.material_rows[index][1]
            if id not in self.data.get("document_file_ids", self.data.get("file_asset_ids", [])):
                raise ValueError(
                    "Файл принадлежит выбранному шаблону/материалу; измените состав источников"
                )
            self.data["file_asset_ids"] = [
                v for v in self.data.get("file_asset_ids", []) if v != id
            ]
            self.data["document_file_ids"] = [
                v for v in self.data.get("document_file_ids", []) if v != id
            ]
            self.mark_dirty()
            self.refresh_materials()

    def open_file(self):
        index = self.material_table.currentRow()
        if index >= 0 and self.material_rows[index][0] == "file":
            self.service.open_file_asset(EntityId(self.material_rows[index][1]))

    def refresh_materials(self):
        rows = []
        self.material_rows = []
        for field, kind, label in (
            ("seminar_material_ids", "seminars", "Материал"),
            ("literature_item_ids", "literature", "Литература"),
        ):
            values = {
                str(v.id): v.title
                for v in self.service.list_materials(kind, course_id=self.course.id)
            }
            values.update({v["id"]: v["title"] for v in self.data.get(field + "_snapshots", [])})
            for id in self.data.get(field, []):
                rows.append((label, values.get(id, "Сохранённый материал"), "—"))
                self.material_rows.append((kind, id))
        for id in self.data.get("file_asset_ids", []):
            asset = self.service.get_file_asset(EntityId(id), include_deleted=True)
            rows.append(("Документ", asset.original_filename, f"{asset.size_bytes} байт"))
            self.material_rows.append(("file", id))
        fill(self.material_table, rows)

    def usage_page(self):
        _, layout = self.page("Использование / версии", editable=False)
        self.usage = readonly_table(["Версия", "Группа", "Период", "Семестр курса"])
        layout.addWidget(self.usage)
        self.version_list = readonly_table(["Версия", "Редакция"])
        layout.addWidget(self.version_list)
        toolbar(
            layout,
            [
                ("Открыть версию", lambda: run_action(self, self.open_version)),
                ("Применить к группе", lambda: run_action(self, self.assign)),
                ("Открыть рабочий план", lambda: run_action(self, self.open_plan)),
            ],
        )
        hint(
            layout,
            "Программа хранит содержание. Рабочий план хранит календарь группы. Проведённые занятия и результаты записываются отдельно.",
        )

    def open_version(self):
        index = self.version_list.currentRow()
        if index >= 0:
            self.window.router.push(
                ProgramEditor(self.window, self.course, version=self.versions[index]),
                "Учебная программа",
            )

    def assign(self):
        if not self.version:
            raise ValueError("Сначала подготовьте готовую версию")
        offerings = [v for v in self.service.list_offerings() if v.course.id == self.course.id]
        if not offerings:
            raise ValueError("Создайте группу и добавьте в неё дисциплину через раздел «Работа»")
        form = RowForm(
            "Использование программы", {}, lambda value: self.apply_assignment(value), self
        )
        form.choice(
            "offering_id",
            "Группа / период",
            [(v.offering.id, v.group.number + " / " + v.term.name) for v in offerings],
        )
        form.choice(
            "course_semester",
            "Семестр курса",
            [(s["number"], s["title"]) for s in self.annual["semesters"]],
        )
        form.exec()

    def apply_assignment(self, value):
        offering_id = value["offering_id"]
        snapshot = self.service.semester_plan(offering_id)
        if snapshot is None:
            self.service.create_semester_plan(
                offering_id,
                version_id=self.version.id,
                course_semester=value["course_semester"],
                weeks=next(
                    s["weeks"]
                    for s in self.annual["semesters"]
                    if s["number"] == value["course_semester"]
                ),
            )
        else:
            from studium.presentation.desktop.qa_plans import PlanContentForm

            context = next(v for v in self.service.list_offerings() if v.offering.id == offering_id)
            form = PlanContentForm(self.service, context, snapshot, self)
            form.version.setCurrentIndex(form.version.findData(self.version.id))
            form.ordinal.setValue(value["course_semester"])
            form.mode.setCurrentIndex(form.mode.findData("replace_unissued"))
            form.exec()
        self.refresh_usage()

    def open_plan(self):
        index = self.usage.currentRow()
        if index >= 0:
            from studium.presentation.desktop.qa_plans import SemesterPlanWidget

            usage = self.usages[index]
            context = next(
                v for v in self.service.list_offerings() if v.offering.id == usage.plan.offering_id
            )
            page = SemesterPlanWidget(self.window, lambda: context)
            page.refresh()
            self.window.router.push(page, "Рабочий план группы")

    def refresh_usage(self):
        program_id = (self.draft or self.version).course_program_id
        self.usages = self.service.program_usage(program_id)
        fill(
            self.usage,
            [
                (v.version.version_no, v.group, v.term, v.plan.course_semester or "Неизвестен")
                for v in self.usages
            ],
        )
        self.versions = [
            v
            for v in self.service.program_versions(self.course.id)
            if v.course_program_id == program_id
        ]
        fill(self.version_list, [(v.version_no, v.label) for v in self.versions])

    def refresh_summaries(self):
        labels = {s["key"]: s["title"] for s in self.annual["semesters"]}
        modules = {m["key"]: m["title"] for s in self.annual["semesters"] for m in s["modules"]}
        fill(
            self.volume_table,
            [
                (
                    labels.get(v.semester_key, "За год"),
                    a.LOAD_KINDS[v.kind],
                    v.count,
                    v.hours,
                    v.normative,
                    v.difference,
                )
                for v in a.volume(self.annual)
            ]
            + [
                (
                    labels[v.semester_key] + " / " + modules[v.module_key],
                    a.LOAD_KINDS[v.kind],
                    v.count,
                    v.hours,
                    None,
                    None,
                )
                for v in a.module_volume(self.annual)
            ],
        )
        fill(
            self.loads_table,
            [
                (
                    labels[v["semester_key"]]
                    + (" / " + modules[v["module_key"]] if v.get("module_key") else ""),
                    a.LOAD_KINDS[v["kind"]],
                    v["hours"],
                    "Норматив"
                    if name == "norms"
                    else "Нагрузка модуля"
                    if v.get("module_key")
                    else "Остаток семестра вне модулей",
                )
                for name in ("loads", "norms")
                for v in self.annual[name]
            ],
        )
        fill(
            self.works_table,
            [
                (
                    s["title"] + " / " + m["title"],
                    ASSESSMENT_LABELS.get(w["category"], w["category"]),
                    w["title"],
                    score_text(w.get("min_cents")),
                    score_text(w.get("max_cents")),
                    w.get("rules", ""),
                )
                for s, m, w in self.work_rows()
            ],
        )
        pending = {
            v.get("key", v.get("id")): v["title"]
            for v in self.annual.get("legacy_unmapped_modules", [])
        }
        definitions = {str(v["id"]): v["title"] for v in self.data.get("definitions", [])}
        legacy_rows = [
            (
                pending[w.get("module_key", w.get("module_id"))],
                definitions.get(str(w["definition_id"]), w.get("title", "Работа")),
                "Неизвестен",
            )
            for w in self.data.get("works", [])
            if w.get("module_key", w.get("module_id")) in pending
        ]
        fill(self.legacy_works, legacy_rows)
        self.legacy_works.setVisible(bool(legacy_rows))
        scores = a.score_totals(self.annual)
        fill(
            self.budgets_table,
            [
                (
                    modules[v.module_key],
                    "Весь модуль"
                    if v.category == "*"
                    else ASSESSMENT_LABELS.get(v.category, v.category),
                    score_text(v.budget),
                    score_text(v.allocated),
                    score_text(v.budget - v.allocated)
                    if v.budget is not None and v.budget >= v.allocated
                    else "Превышение"
                    if v.budget is not None
                    else "—",
                )
                for v in scores
            ],
        )
        self.score_summary.setText(
            "Балльная система не используется"
            if self.annual["scoring"] == "NONE"
            else " · ".join(
                f"{s['title']}: {score_text(sum(v.maximum for v in scores if v.category == '*' and v.semester_key == s['key']))}"
                for s in self.annual["semesters"]
            )
            + " · За год: "
            + score_text(sum(v.maximum for v in scores if v.category == "*"))
        )

    def refresh_all(self):
        self.heading.setText(
            self.annual["passport"]["title"]
            + " · "
            + (self.annual["passport"]["label"] or "Редакция без обозначения")
        )
        self.status.setText(
            "Черновик · " + ("есть изменения" if self.dirty else "сохранён")
            if self.draft
            else "Готовая версия · режим просмотра"
            + (" · импортирована" if self.data.get("exchange_origin") else "")
        )
        self.status.setToolTip(self.data.get("exchange_origin", ""))
        self.refresh_tree()
        fill(
            self.outcomes_table,
            [
                (a.OUTCOME_KINDS[v["category"]], v.get("code", ""), v["text"])
                for v in self.annual["outcomes"]
            ],
        )
        fill(
            self.prerequisites_table,
            [(v["discipline"], v["content"]) for v in self.annual["prerequisites"]],
        )
        self.refresh_summaries()
        self.refresh_materials()
        self.refresh_usage()

    def lock_editor(self):
        from PySide6.QtWidgets import QPushButton

        for page in self.editable_pages:
            for kind in (QLineEdit, QPlainTextEdit):
                for field in page.findChildren(kind):
                    field.setReadOnly(True)
            for kind in (QComboBox, QSpinBox, QCheckBox, QPushButton):
                for field in page.findChildren(kind):
                    field.setEnabled(False)
        for view in (self.lessons, self.outcomes_table, self.prerequisites_table):
            view.doubleClicked.disconnect()
        self.shortcut.setEnabled(False)

    def save(self):
        if not self.draft:
            raise ValueError("Версия доступна только для просмотра")
        if self.busy:
            raise ValueError("Дождитесь завершения файловой операции")
        self.draft = self.service.save_program_draft(self.draft, self.collect())
        self.data = json.loads(self.draft.content_json)
        self.dirty = False
        self.status.setText("Черновик · сохранён")
        self.notice.setText(
            "Черновик сохранён. "
            + str(len(self.service.check_program_draft(self.draft)))
            + " пунктов требуют заполнения."
        )
        return True

    def check(self):
        data = self.collect()
        issues = a.validate(data["annual"])
        self.notice.setText(
            "\n".join(issues)
            if issues
            else "Обязательные поля заполнены; можно подготовить версию."
        )

    def publish(self):
        self.save()
        version = self.service.publish_program_draft(self.draft)
        self.dirty = False
        self.version, self.draft = version, None
        self.data = json.loads(version.content_json)
        self.actions.hide()
        self.material_actions.hide()
        self.lock_editor()
        self.refresh_all()

    def next_revision(self, independent=False):
        if not self.version:
            raise ValueError("Редакция создаётся из готовой версии")
        draft = self.service.create_program_draft(
            self.course.id, previous=self.version, independent=independent
        )
        self.window.router.push(
            ProgramEditor(self.window, self.course, draft=draft), "Учебная программа · черновик"
        )

    def export(self):
        if not self.version:
            raise ValueError("Экспорт доступен после подготовки версии")
        count = len(self.data.get("file_asset_ids", []))
        include = False
        if count:
            size = sum(
                self.service.get_file_asset(EntityId(id), include_deleted=True).size_bytes
                for id in self.data["file_asset_ids"]
            )
            box = QMessageBox(self)
            box.setWindowTitle("Состав экспорта")
            box.setText(f"Документов: {count}; {size} байт. Состав показан на вкладке «Материалы».")
            yes = box.addButton("Включить все файлы", QMessageBox.ButtonRole.AcceptRole)
            no = box.addButton("Экспортировать без файлов", QMessageBox.ButtonRole.ActionRole)
            box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() not in (yes, no):
                return
            include = box.clickedButton() == yes
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт программы", "", "Программа Studium (*.studium-program)"
        )
        if path:
            self.busy = True
            self.notice.setText("Экспорт программы…")
            BackgroundCall(
                self,
                lambda: self.service.export_program(self.version.id, path, include_files=include),
                self.exported,
                self.failed,
            )

    def exported(self, result):
        self.busy = False
        self.notice.setText(
            "Программа экспортирована. Исключено файлов: " + str(result.excluded_files)
        )

    def failed(self, error):
        self.busy = False
        self.notice.setText(str(error))

    def can_leave(self):
        if self.busy:
            self.notice.setText("Дождитесь завершения файловой операции")
            return False
        if not self.dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Несохранённая программа")
        box.setText("Сохранить изменения черновика перед уходом?")
        save = box.addButton("Сохранить черновик", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Не сохранять", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Остаться", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == discard:
            self.data = json.loads(self.draft.content_json)
            passport = self.annual["passport"]
            for name, field in self.passport_fields.items():
                field.setText(passport[name])
            self.notes.setPlainText(passport["notes"])
            self.minutes.setValue(passport["academic_hour_minutes"])
            self.directions.setPlainText(
                "\n".join(
                    v["code"] + (" — " + v["name"] if v["name"] else "")
                    for v in passport["directions"]
                )
            )
            for name, box in self.na.items():
                box.setChecked(name in self.annual["not_applicable"])
            self.scoring.blockSignals(True)
            self.scoring.setCurrentIndex(self.scoring.findData(self.annual["scoring"]))
            self.scoring.blockSignals(False)
            self.dirty = False
            self.refresh_all()
            return True
        if box.clickedButton() == save:
            return bool(run_action(self, self.save))
        return False


def import_program(window, course=None):
    path, _ = QFileDialog.getOpenFileName(
        window, "Импорт программы", "", "Программа Studium (*.studium-program)"
    )
    if not path:
        return

    def show(preview):
        form = ImportPreviewForm(window, preview, course)
        form.exec()

    BackgroundCall(
        window,
        lambda: window.service.preview_program_import(path),
        show,
        lambda error: QMessageBox.warning(window, "Импорт программы", str(error)),
    )


class ImportPreviewForm(RowForm):
    def __init__(self, window, preview, course=None):
        self.window, self.preview = window, preview
        data = json.loads(preview.package.payload_json)
        annual = data["content"]["annual"]
        super().__init__("Предварительный просмотр программы", {}, lambda _: None, window)
        self.course_field = self.choice(
            "course_id",
            "Дисциплина",
            [(None, "Создать новую: " + data["course"]["name"])]
            + [(c.id, c.name) for c in window.service.list_courses()],
        )
        if course:
            self.course_field.setCurrentIndex(max(0, self.course_field.findData(course.id)))
        summary = [
            annual["passport"]["title"],
            "Редакция: " + annual["passport"]["label"],
            "Направления: " + ", ".join(d["code"] for d in annual["passport"]["directions"]),
            f"Семестров: {len(annual['semesters'])}; модулей: {sum(len(s['modules']) for s in annual['semesters'])}",
            "Академических часов: "
            + str(sum(v.hours for v in a.volume(annual) if v.semester_key is None)),
            "Баллы за год: "
            + score_text(sum(v.maximum for v in a.score_totals(annual) if v.category == "*")),
            f"Файлов: {len(preview.package.files)}; {sum(v['size'] for v in preview.package.files)} байт",
            *preview.warnings,
        ]
        for semester in annual["semesters"]:
            summary.append(
                f"{semester['number']}. {semester['title']} · {semester['weeks']} недель"
            )
            for module in semester["modules"]:
                summary.append(
                    f"  {module['title']} · недели {module['start_week']}–{module['end_week']} · занятий {len(module['lessons'])} · работ {len(module['works'])}"
                )
        hint(self.body_layout, "\n".join(summary))
        for file in preview.package.files:
            hint(self.body_layout, f"{file['name']} · {file['size']} байт")
        self.independent = QCheckBox("Явно создать независимую копию")
        self.form.addRow(self.independent)
        if preview.matches:
            toolbar(self.body_layout, [("Открыть существующую программу", self.open_existing)])
        self.save_button.setText("Импортировать")

    def submit(self):
        # Import stays open until the worker finishes; Qt widgets are read on GUI thread.
        if self.save_button.isEnabled():
            values = self.values()
            copy = self.independent.isChecked()
            self.save_button.setEnabled(False)
            self.independent.setEnabled(False)
            self.scroll.setEnabled(False)
            BackgroundCall(
                self,
                lambda: self.window.service.commit_program_import(
                    self.preview, course_id=values["course_id"], independent_copy=copy
                ),
                self.imported,
                self.failed,
            )

    def imported(self, version):
        self.save_button.setEnabled(True)
        self.accept()
        program = self.window.service.get_course_program(version.course_program_id)
        course = self.window.service.get_course(program.course_id)
        self.window.router.push(
            ProgramEditor(self.window, course, version=version), "Учебная программа"
        )

    def failed(self, error):
        self.save_button.setEnabled(True)
        self.independent.setEnabled(True)
        self.scroll.setEnabled(True)
        self.error_label.setText(str(error))

    def reject(self):
        if self.save_button.isEnabled():
            super().reject()

    def open_existing(self):
        version = self.window.service.get_program_version(
            self.preview.matches[0].program_version_id
        )
        self.imported(version)
