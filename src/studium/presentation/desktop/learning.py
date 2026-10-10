"""Small standard Qt dialogs for the learning model, without a shell redesign."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from studium.domain.entities import Topic
from studium.domain.enums import AssessmentType, AttendanceStatus, LessonType
from studium.presentation.desktop.components import (
    confirm,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import FormDialog, combo, date_value, number_value
from studium.presentation.desktop.messages import (
    ATTENDANCE_LABELS,
    ENROLLMENT_LABELS,
    TEXT,
    context_label,
)
from studium.presentation.desktop.models import TableModel, display_score
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.theme import resize_to_screen
from studium.presentation.desktop.visuals import Disclosure, EmptyState, TagList, text_label
from studium.presentation.desktop.workflow_widgets import WeekSelector, data_index


class CataloguePicker(QWidget):
    """Searchable linked selection with a real create action, including empty lists."""

    def __init__(self, service, course, *, skills=False, values=(), ids=(), parent=None):
        super().__init__(parent)
        self.service, self.course, self.skills = service, course, skills
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Найти навык" if skills else "Найти тему")
        layout.addWidget(self.search)
        self.list = CheckList(values, ids)
        self.selected_tags = TagList()
        layout.addWidget(self.selected_tags)
        layout.addWidget(self.list)
        self.empty = hint(layout, "Нет навыков" if skills else "Нет тем")
        self.empty.setVisible(not values)
        self.create = QPushButton("Создать навык" if skills else "Создать тему")
        self.create.clicked.connect(lambda: run_action(self, self.create_value))
        layout.addWidget(self.create)
        self.search.textChanged.connect(
            lambda text: [
                self.list.item(i).setHidden(
                    text.casefold() not in self.list.item(i).text().casefold()
                )
                for i in range(self.list.count())
            ]
        )
        self.list.itemChanged.connect(lambda _: self.refresh_selected())
        self.refresh_selected()

    def refresh_selected(self):
        values = [
            (self.list.item(i).data(Qt.ItemDataRole.UserRole), self.list.item(i).text())
            for i in range(self.list.count())
            if self.list.item(i).checkState() == Qt.CheckState.Checked
        ]
        self.selected_tags.set_values(values, self.remove_selected)

    def remove_selected(self, key):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                item.setCheckState(Qt.CheckState.Unchecked)

    def create_value(self):
        selected_ids = self.ids()
        if (
            CatalogueForm(self.service, self.course, skill=self.skills, parent=self).exec()
            == QDialog.DialogCode.Accepted
        ):
            values = (
                self.service.list_course_skills(self.course.id)
                if self.skills
                else self.service.list_course_topics(self.course.id)
            )
            self.list.fill([(v.id, v.title) for v in values], selected_ids)
            self.empty.setVisible(not values)
            self.refresh_selected()

    def ids(self):
        return self.list.ids()

    def item(self, index):
        return self.list.item(index)

    def count(self):
        return self.list.count()


def display_day(value):
    return f"{value.day:02d}.{value.month:02d}.{value.year}"


class CheckList(QListWidget):
    def __init__(self, values, selected_ids=()):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(180)
        for value in values:
            item = QListWidgetItem(value.title + (" (в архиве)" if value.deleted_at else ""))
            item.setData(Qt.ItemDataRole.UserRole, value.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if value.id in selected_ids else Qt.CheckState.Unchecked
            )
            self.addItem(item)

    def ids(self):
        return tuple(
            self.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        )

    def fill(self, values, selected_ids=()):
        self.clear()
        for id, title in values:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if id in selected_ids else Qt.CheckState.Unchecked
            )
            self.addItem(item)


def catalogue_choices(service, course_id, kind, owner_id=None):
    current = (
        service.list_course_topics(course_id)
        if kind.endswith("topics")
        else service.list_course_skills(course_id)
    )
    linked = service.learning_targets(kind, owner_id) if owner_id else ()
    by_id = {v.id: v for v in current}
    by_id.update({v.id: v for v in linked})
    return sorted(by_id.values(), key=lambda v: (v.sort_order, v.title)), {v.id for v in linked}


class CatalogueForm(FormDialog):
    def __init__(
        self,
        service,
        course,
        *,
        skill=False,
        original=None,
        parent=None,
        parent_topic_id=None,
        module_id=None,
    ):
        self.skill = skill

        def save(values):
            if original:
                result = (service.update_skill if skill else service.update_topic)(
                    original, **values
                )
            else:
                result = (service.create_skill if skill else service.create_topic)(
                    course.id, **values
                )
            if not skill:
                service.set_topic_modules(result.id, self.module.ids(), course.id)

        super().__init__(
            TEXT["edit"] if original else TEXT["new_skill" if skill else "new_topic"], save, parent
        )
        self.title = self.line("name", original.title if original else "", required=True)
        self.description = self.notes("description", original.description if original else "")
        rows = (
            service.list_course_skills(course.id)
            if skill
            else service.list_course_topics(course.id)
        )
        self.order = (
            original.sort_order if original else max((v.sort_order for v in rows), default=-1) + 1
        )
        self.parent_topic = QComboBox()
        if not skill:
            self.parent_topic.addItem("Без родительской темы", None)
            for topic in service.list_course_topics(course.id):
                if original is None or topic.id != original.id:
                    self.parent_topic.addItem(topic.title, topic.id)
            if original:
                self.parent_topic.setCurrentIndex(
                    max(0, data_index(self.parent_topic, original.parent_topic_id))
                )
            elif parent_topic_id:
                self.parent_topic.setCurrentIndex(data_index(self.parent_topic, parent_topic_id))
            self.form.addRow(TEXT["parent_topic"], self.parent_topic)
            self.module = CheckList([])
            module_values, module_ids = [], {module_id} if module_id else set()
            for program in service.list_work_programs(course.id):
                for module in service.list_program_modules(program.id):
                    module_values.append((module.id, f"{program.title} · {module.title}"))
                    if original and original.id in {
                        t.id for t in service.content_targets("module_topics", module.id)
                    }:
                        module_ids.add(module.id)
            self.module.fill(module_values, module_ids)
            self.form.addRow("Модули / семестры", self.module)
            values, ids = catalogue_choices(
                service, course.id, "topic_skills", original.id if original else None
            )
            self.expected_skills = (
                service.learning_links("topic_skills", original.id) if original else None
            )
            self.skills = CataloguePicker(
                service, course, skills=True, values=values, ids=ids, parent=self
            )
            self.form.addRow("Навыки", self.skills)

    def values(self):
        values = dict(
            title=self.title.text().strip(),
            description=self.description.toPlainText(),
            sort_order=self.order,
        )
        if not self.skill:
            values["parent_topic_id"] = self.parent_topic.currentData()
            values["skill_ids"] = self.skills.ids()
            if self.expected_skills is not None:
                values["expected_skills"] = self.expected_skills
        return values


class TopicSkillsDialog(FormDialog):
    def __init__(self, service, course, topic, parent=None):
        expected = service.learning_links("topic_skills", topic.id)
        super().__init__(
            f"{topic.title} · {TEXT['skills']}",
            lambda ids: service.set_learning_links(
                "topic_skills", topic.id, ids, expected=expected
            ),
            parent,
        )
        values, ids = catalogue_choices(service, course.id, "topic_skills", topic.id)
        self.skills = CataloguePicker(
            service, course, skills=True, values=values, ids=ids, parent=self
        )
        self.form.addRow(TEXT["skills"], self.skills)

    def values(self):
        return self.skills.ids()


class LearningCatalogueDialog(QDialog):
    def __init__(self, service, course, parent=None):
        super().__init__(parent)
        self.service, self.course = service, course
        self.setWindowTitle(f"{course.name} · {TEXT['learning_catalogue']}")
        resize_to_screen(self, 820, 560)
        layout = QVBoxLayout(self)
        hint(layout, "Темы и навыки").setProperty("role", "heading")
        hint(layout, TEXT["catalogue_hint"])
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        topics = QWidget()
        topic_layout = QVBoxLayout(topics)
        toolbar(
            topic_layout,
            [
                (TEXT["new_topic"], lambda: self.act(lambda: self.edit_topic(new=True))),
                (
                    "Добавить подтему",
                    lambda: self.act(lambda: self.edit_topic(new=True, subtopic=True)),
                ),
                (TEXT["edit"], lambda: self.act(self.edit_topic)),
                (TEXT["archive"], lambda: self.act(self.archive_topic)),
                (TEXT["skills"], lambda: self.act(self.topic_skills)),
            ],
        )
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([TEXT["name"], TEXT["description"]])
        self.tree.itemDoubleClicked.connect(lambda *_: self.act(self.edit_topic))
        topic_layout.addWidget(self.tree)
        self.empty_topics = EmptyState(
            "Тем пока нет",
            "Создайте первую тему для дисциплины.",
        )
        topic_layout.addWidget(self.empty_topics)
        self.tabs.addTab(topics, TEXT["topics"])
        skills = QWidget()
        skill_layout = QVBoxLayout(skills)
        toolbar(
            skill_layout,
            [
                (TEXT["new_skill"], lambda: self.act(lambda: self.edit_skill(new=True))),
                (TEXT["edit"], lambda: self.act(self.edit_skill)),
                (TEXT["archive"], lambda: self.act(self.archive_skill)),
            ],
        )
        self.skill_model = TableModel(
            [
                (TEXT["name"], lambda v: v.title),
                (TEXT["description"], lambda v: v.description),
            ]
        )
        self.skill_view = table(self.skill_model)
        self.skill_view.doubleClicked.connect(lambda _: self.act(self.edit_skill))
        skill_layout.addWidget(self.skill_view)
        self.empty_skills = EmptyState(
            "Навыков пока нет",
            "Создайте первый навык для дисциплины.",
        )
        skill_layout.addWidget(self.empty_skills)
        self.tabs.addTab(skills, TEXT["skills"])
        self.refresh()

    def act(self, action):
        return run_action(self, action)

    def refresh(self):
        self.tree.clear()

        def subtree_ids(node):
            return {node.topic.id}.union(*(subtree_ids(child) for child in node.children))

        def add(node, parent, included=None, excluded=frozenset()):
            if node.topic.id in excluded or (
                included is not None and not subtree_ids(node).intersection(included)
            ):
                return
            item = QTreeWidgetItem([node.topic.title, node.topic.description])
            item.setData(0, Qt.ItemDataRole.UserRole, node.topic)
            parent.addChild(item) if isinstance(
                parent, QTreeWidgetItem
            ) else parent.addTopLevelItem(item)
            for child in node.children:
                add(
                    child,
                    item,
                    None if included is None or node.topic.id in included else included,
                    excluded,
                )
            for skill in self.service.learning_targets("topic_skills", node.topic.id):
                linked = QTreeWidgetItem(["Навык: " + skill.title, skill.description])
                item.addChild(linked)

        nodes = self.service.topic_hierarchy(self.course.id)
        placed = set()
        terms = {t.id: t for t in self.service.list_terms()}
        for program in self.service.list_work_programs(self.course.id):
            modules = self.service.list_program_modules(program.id)
            if not modules:
                continue
            term = terms.get(program.term_id)
            root = QTreeWidgetItem(
                [(term.name + " · " if term else "Удалённый период · ") + program.title, "Семестр"]
            )
            self.tree.addTopLevelItem(root)
            for module in modules:
                branch = QTreeWidgetItem(
                    [module.title, f"Недели {module.start_week}–{module.end_week}"]
                )
                branch.setData(0, Qt.ItemDataRole.UserRole, ("module", module.id))
                root.addChild(branch)
                ids = {t.id for t in self.service.content_targets("module_topics", module.id)}
                for node in nodes:
                    add(node, branch, included=ids)

                def record_placed(node):
                    if node.topic.id in ids:
                        placed.update(subtree_ids(node))
                    else:
                        for child in node.children:
                            record_placed(child)

                for node in nodes:
                    record_placed(node)
        unplaced = [node for node in nodes if node.topic.id not in placed]
        if unplaced:
            branch = QTreeWidgetItem(["Темы вне модулей", ""])
            self.tree.addTopLevelItem(branch)
            for node in unplaced:
                add(node, branch, excluded=placed)
        self.tree.expandAll()
        self.tree.setColumnWidth(0, 310)
        self.skill_model.replace_rows(self.service.list_course_skills(self.course.id))
        self.empty_topics.setVisible(self.tree.topLevelItemCount() == 0)
        self.empty_skills.setVisible(self.skill_model.rowCount() == 0)

    def topic(self):
        item = self.tree.currentItem()
        value = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value, Topic) else None

    def move_catalogue(self, kind, direction):
        original = self.topic() if kind == "topics" else selected(self.skill_view)
        if original:
            self.service.move_presentation_item(kind, original, direction)
            self.refresh()

    def edit_topic(self, *, new=False, subtopic=False):
        original = None if new else self.topic()
        item = self.tree.currentItem()
        value = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        module_id = value[1] if isinstance(value, tuple) and value[0] == "module" else None
        parent_topic = self.topic() if subtopic else None
        if subtopic and parent_topic is None:
            return
        if new or original:
            if (
                present_detail(
                    CatalogueForm(
                        self.service,
                        self.course,
                        original=original,
                        parent=self,
                        parent_topic_id=parent_topic.id if parent_topic else None,
                        module_id=module_id,
                    ),
                    self,
                    refresh=getattr(self, "refresh", None),
                )
                == QDialog.DialogCode.Accepted
            ):
                self.refresh()

    def archive_topic(self):
        topic = self.topic()
        if topic and confirm(self, TEXT["archive_topic_confirm"], action_label=TEXT["archive"]):
            self.service.archive_topic(topic)
            self.refresh()

    def edit_skill(self, *, new=False):
        original = None if new else selected(self.skill_view)
        if new or original:
            if (
                present_detail(
                    CatalogueForm(
                        self.service, self.course, skill=True, original=original, parent=self
                    ),
                    self,
                    refresh=getattr(self, "refresh", None),
                )
                == QDialog.DialogCode.Accepted
            ):
                self.refresh()

    def archive_skill(self):
        skill = selected(self.skill_view)
        if skill and confirm(
            self, TEXT["confirm_hide"].format(name=skill.title), action_label=TEXT["archive"]
        ):
            self.service.archive_skill(skill)
            self.refresh()

    def topic_skills(self):
        topic = self.topic()
        if topic:
            present_detail(
                TopicSkillsDialog(self.service, self.course, topic, self),
                self,
                refresh=getattr(self, "refresh", None),
            )

    def topic_evidence(self):
        from studium.presentation.desktop.analytics import EvidenceDialog

        topic = self.topic()
        if topic:
            present_detail(
                EvidenceDialog(self.service, topic, parent=self),
                self,
                refresh=getattr(self, "refresh", None),
            )

    def skill_evidence(self):
        from studium.presentation.desktop.analytics import EvidenceDialog

        skill = selected(self.skill_view)
        if skill:
            present_detail(
                EvidenceDialog(self.service, skill, skill=True, parent=self),
                self,
                refresh=getattr(self, "refresh", None),
            )


class LessonForm(FormDialog):
    def __init__(self, service, context, original=None, parent=None):
        self.expected_topics = (
            service.learning_links("lesson_topics", original.id) if original else None
        )
        self.original = original

        def save(values):
            if original:
                service.update_lesson(original, **values)
            else:
                service.create_lesson(context.offering.id, **values)

        super().__init__(TEXT["edit"] if original else TEXT["new_lesson"], save, parent)
        self.date = self.day("lesson_date", original.lesson_date if original else None)
        self.lesson_type = combo(
            {LessonType.SEMINAR: "Семинар", LessonType.LECTURE: "Лекция"},
            original.type if original else LessonType.SEMINAR,
        )
        self.form.addRow("Тип занятия", self.lesson_type)
        self.title = self.line("lesson_title", original.title if original else "")
        self.notes_field = self.notes("lesson_notes", original.notes if original else "")
        values, ids = catalogue_choices(
            service, context.course.id, "lesson_topics", original.id if original else None
        )
        self.topics = CataloguePicker(service, context.course, values=values, ids=ids, parent=self)
        self.form.addRow(TEXT["topics"], self.topics)
        self.program = service.program_for_offering(context.offering.id)
        if self.program:
            self.week = WeekSelector(
                original.planned_week
                if original
                else self.program.week_for_date(date_value(self.date)),
                weeks=self.program.weeks,
            )
            self.form.addRow("Плановая неделя", self.week)
            self.module = QComboBox()
            self.module.addItem("Без модуля", None)
            for module in service.list_program_modules(self.program.id):
                self.module.addItem(module.title, module.id)
            if original:
                self.module.setCurrentIndex(max(0, data_index(self.module, original.module_id)))
            self.form.addRow("Модуль", self.module)
        hint(self.body_layout, TEXT["lesson_hint"])

    def values(self):
        values = dict(
            lesson_date=date_value(self.date),
            type=LessonType(self.lesson_type.currentData()),
            title=self.title.text().strip(),
            notes=self.notes_field.toPlainText(),
            topic_ids=self.topics.ids(),
        )
        if self.original:
            values["expected_topics"] = self.expected_topics
        if self.program:
            values["planned_week"] = self.week.currentData()
            values["module_id"] = self.module.currentData()
        return values


class AttendanceForm(FormDialog):
    def __init__(self, service, lesson, entry, parent=None):
        def save(values):
            service.mark_attendance(
                lesson.id, entry.enrollment.id, original=entry.attendance, **values
            )

        super().__init__(f"{TEXT['attendance']} · {entry.student.full_name}", save, parent)
        self.status = combo(
            ATTENDANCE_LABELS, entry.attendance.status if entry.attendance else None
        )
        self.form.addRow(TEXT["attendance"], self.status)
        self.comment = self.notes("comment", entry.attendance.comment if entry.attendance else "")

    def values(self):
        return dict(
            status=AttendanceStatus(self.status.currentData()), comment=self.comment.toPlainText()
        )


class LessonDialog(QDialog):
    def __init__(self, service, context, lesson, parent=None):
        super().__init__(parent)
        self.service, self.context, self.lesson = service, context, lesson
        self.setWindowTitle(TEXT["lessons"])
        resize_to_screen(self, 880, 590)
        layout = QVBoxLayout(self)
        self.heading = hint(layout, "")
        self.notes_label = hint(layout, "")
        self.topics_label = hint(layout, "")
        self.advanced = QToolButton()
        self.advanced.setText("Другие действия")
        self.advanced.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.advanced)
        menu.addAction("Отменить занятие", lambda: run_action(self, self.cancel))
        menu.addAction("Перенести занятие", lambda: run_action(self, self.transfer))
        self.advanced.setMenu(menu)
        layout.addWidget(self.advanced)
        toolbar(
            layout,
            [
                (TEXT["edit"], lambda: run_action(self, self.edit)),
                (TEXT["attendance"], lambda: run_action(self, self.mark)),
            ],
        )
        hint(
            layout,
            "Выберите участие студента. После повторного зачисления предыдущая отметка сохраняется.",
        )
        self.model = TableModel(
            [
                (TEXT["full_name"], lambda r: r.student.full_name),
                (
                    TEXT["enrollment"],
                    lambda r: (
                        ENROLLMENT_LABELS[r.enrollment.status]
                        + " с "
                        + r.enrollment.enrolled_at.value.astimezone().strftime("%d.%m.%Y")
                    ),
                ),
                (
                    TEXT["attendance"],
                    lambda r: (
                        ATTENDANCE_LABELS[r.attendance.status]
                        if r.attendance
                        else TEXT["not_marked"]
                    ),
                ),
                (TEXT["comment"], lambda r: r.attendance.comment if r.attendance else ""),
            ]
        )
        self.view = table(self.model)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.mark))
        hint(layout, TEXT["bulk_attendance_hint"])
        row = toolbar(
            layout, [(TEXT["bulk_attendance"], lambda: run_action(self, self.mark_selected))]
        )
        self.bulk_status = combo(ATTENDANCE_LABELS)
        row.insertWidget(0, self.bulk_status)
        layout.addWidget(self.view)
        self.refresh()

    def refresh(self):
        self.heading.setText(
            f"{'Лекция' if self.lesson.type == LessonType.LECTURE else 'Семинар'} · {display_day(self.lesson.lesson_date)} · {self.lesson.title}\n{context_label(self.context)}"
        )
        self.notes_label.setText(self.lesson.notes)
        if self.lesson.cancelled:
            self.notes_label.setText(
                "Занятие отменено"
                + (
                    ": " + self.lesson.cancellation_reason
                    if self.lesson.cancellation_reason
                    else ""
                )
            )
        self.topics_label.setText(
            TEXT["topics"]
            + ": "
            + ", ".join(
                t.title + (" (в архиве)" if t.deleted_at else "")
                for t in self.service.learning_targets("lesson_topics", self.lesson.id)
            )
        )
        self.model.replace_rows(self.service.list_lesson_attendance(self.lesson.id))
        self.view.setEnabled(not self.lesson.cancelled)

    def cancel(self):
        owner = self

        class CancelForm(FormDialog):
            def __init__(self):
                super().__init__("Отменить занятие", self.save, owner)
                self.reason = self.notes("comment")

            def values(self):
                return self.reason.toPlainText()

            def save(self, reason):
                owner.lesson = owner.service.cancel_lesson(owner.lesson, reason)

        if CancelForm().exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def transfer(self):
        owner = self

        class TransferForm(FormDialog):
            def __init__(self):
                super().__init__("Перенести занятие", self.save, owner)
                self.day_field = self.day("lesson_date", owner.lesson.lesson_date)

            def values(self):
                return date_value(self.day_field)

            def save(self, day):
                owner.lesson = owner.service.transfer_lesson(owner.lesson, day)

        if TransferForm().exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit(self):
        def save(values):
            self.lesson = self.service.update_lesson(self.lesson, **values)

        form = LessonForm(self.service, self.context, self.lesson, self)
        form.on_save = save
        present_detail(form, self, refresh=self.refresh)

    def mark(self):
        row = selected(self.view)
        if (
            row
            and AttendanceForm(self.service, self.lesson, row, self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def mark_selected(self):
        entries = [
            self.model.rows[index.row()] for index in self.view.selectionModel().selectedRows()
        ]
        if entries:
            self.service.mark_attendance_many(
                self.lesson.id, entries, AttendanceStatus(self.bulk_status.currentData())
            )
            self.refresh()


class LessonsPage(QWidget):
    def __init__(self, service_provider, context_provider, parent=None):
        super().__init__(parent)
        self.service_provider, self.context_provider = service_provider, context_provider
        layout = QVBoxLayout(self)
        toolbar(
            layout,
            [
                (TEXT["new_lesson"], lambda: run_action(self, self.create)),
                (TEXT["open"], lambda: run_action(self, self.open)),
                (TEXT["learning_catalogue"], lambda: run_action(self, self.catalogue)),
            ],
        )
        self.model = TableModel(
            [
                (TEXT["lesson_date"], lambda row: display_day(row.lesson.lesson_date)),
                (
                    "Тип",
                    lambda row: "Лекция" if row.lesson.type == LessonType.LECTURE else "Семинар",
                ),
                (TEXT["name"], lambda row: row.lesson.title),
                (TEXT["topics"], lambda row: ", ".join(t.title for t in row.topics)),
                (
                    TEXT["attendance_summary"],
                    lambda row: (
                        " · ".join(
                            f"{ATTENDANCE_LABELS[status]}: {count}"
                            for status, count in row.attendance_counts
                        )
                        or TEXT["not_marked"]
                    ),
                ),
            ]
        )
        self.view = table(self.model)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))
        layout.addWidget(self.view)
        self.empty = hint(layout, TEXT["empty_lessons"])

    @property
    def service(self):
        return self.service_provider()

    def refresh(self):
        context = self.context_provider()
        rows = self.service.lesson_list(context.offering.id) if context else []
        self.model.replace_rows(rows)
        self.empty.setVisible(not rows)

    def create(self):
        context = self.context_provider()
        if (
            context
            and present_detail(
                LessonForm(self.service, context, parent=self),
                self,
                refresh=getattr(self, "refresh", None),
            )
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def open(self):
        row = selected(self.view)
        context = self.context_provider()
        if row and context:
            present_detail(
                LessonDialog(self.service, context, row.lesson, self),
                self,
                refresh=self.refresh,
                title=("Лекция" if row.lesson.type == LessonType.LECTURE else "Семинар")
                + " · "
                + display_day(row.lesson.lesson_date),
            )

    def catalogue(self):
        context = self.context_provider()
        if context:
            present_detail(
                LearningCatalogueDialog(self.service, context.course, self),
                self,
                refresh=self.refresh,
                title=context.course.name + " · темы",
            )


class ContentForm(FormDialog):
    def __init__(self, service, course_id, owner, *, item=False, parent=None):
        super().__init__(
            TEXT["learning_catalogue"],
            lambda v: service.set_assessment_content(owner.id, **v, item=item),
            parent,
        )
        prefix = "item" if item else "assessment"
        self.expected_topics = service.learning_links(prefix + "_topics", owner.id)
        self.expected_skills = service.learning_links(prefix + "_skills", owner.id)
        values, ids = catalogue_choices(service, course_id, prefix + "_topics", owner.id)
        self.topics = CheckList(values, ids)
        values, ids = catalogue_choices(service, course_id, prefix + "_skills", owner.id)
        self.skills = CheckList(values, ids)
        self.form.addRow(TEXT["topics"], self.topics)
        self.form.addRow(TEXT["skills"], self.skills)
        hint(self.body_layout, TEXT["content_hint"])

    def values(self):
        return dict(
            topic_ids=self.topics.ids(),
            skill_ids=self.skills.ids(),
            expected_topics=self.expected_topics,
            expected_skills=self.expected_skills,
        )


class ItemForm(FormDialog):
    def __init__(self, service, assessment, original=None, parent=None):
        def save(values):
            if original:
                service.update_assessment_item(original, **values)
            else:
                service.create_assessment_item(assessment.id, **values)

        super().__init__(TEXT["edit"] if original else TEXT["new_item"], save, parent)
        self.title = self.line("item_title", original.title if original else "", required=True)
        self.description = self.notes("description", original.description if original else "")
        self.maximum = self.line(
            "max_score",
            str(original.max_score) if original and original.max_score is not None else "",
        )
        self.order = (
            original.sort_order
            if original
            else max(
                (v.sort_order for v in service.list_assessment_items(assessment.id)), default=-1
            )
            + 1
        )

    def values(self):
        return dict(
            title=self.title.text().strip(),
            description=self.description.toPlainText(),
            max_score=number_value(self.maximum),
            sort_order=self.order,
        )


class AssessmentContentDialog(QDialog):
    def __init__(self, service, context, assessment, parent=None):
        super().__init__(parent)
        self.service, self.context, self.assessment = service, context, assessment
        self.setWindowTitle(f"{assessment.title} · {TEXT['assessment_content']}")
        resize_to_screen(self, 900, 560)
        layout = QVBoxLayout(self)
        hint(layout, assessment.title).setProperty("role", "heading")
        hint(layout, "Структура работы · " + context.course.name)
        self.main_tabs = QTabWidget()
        layout.addWidget(self.main_tabs)
        structure = QWidget()
        layout = QVBoxLayout(structure)
        structure_scroll = QScrollArea()
        structure_scroll.setWidgetResizable(True)
        structure_scroll.setWidget(structure)
        self.main_tabs.addTab(structure_scroll, "Темы, навыки и части")
        self.content = hint(layout, "")
        self.content.hide()
        layout.addWidget(text_label("Темы", "subheading"))
        self.topic_tags = TagList()
        layout.addWidget(self.topic_tags)
        layout.addWidget(text_label("Навыки", "subheading"))
        self.skill_tags = TagList()
        layout.addWidget(self.skill_tags)
        self.locked_hint = hint(layout, TEXT["content_locked_hint"])
        toolbar(layout, [(TEXT["learning_catalogue"], lambda: run_action(self, self.edit_content))])
        conditions = QPushButton("Условия и общие файлы")
        conditions.clicked.connect(lambda: self.main_tabs.setCurrentIndex(1))
        layout.addWidget(conditions, 0, Qt.AlignmentFlag.AlignLeft)
        hint(layout, "Части работы").setProperty("role", "subheading")
        management = QWidget()
        management_layout = QVBoxLayout(management)
        management_layout.setContentsMargins(0, 0, 0, 0)
        toolbar(
            management_layout,
            [
                (TEXT["new_item"], lambda: run_action(self, lambda: self.edit_item(new=True))),
                (TEXT["edit"], lambda: run_action(self, self.edit_item)),
                (TEXT["learning_catalogue"], lambda: run_action(self, self.item_content)),
                (TEXT["up"], lambda: run_action(self, lambda: self.move(-1))),
                (TEXT["down"], lambda: run_action(self, lambda: self.move(1))),
                (TEXT["archive"], lambda: run_action(self, self.archive_item)),
            ],
        )
        self.model = TableModel(
            [
                (TEXT["name"], lambda row: row[0].title),
                (TEXT["max_score"], lambda row: display_score(row[0].max_score)),
                (TEXT["topics"], lambda row: ", ".join(t.title for t in row[1])),
                (TEXT["skills"], lambda row: ", ".join(s.title for s in row[2])),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.parts_empty = EmptyState(
            "У работы нет отдельных частей",
            "Условия, темы и навыки относятся ко всей работе. Части добавляются при необходимости.",
        )
        layout.addWidget(self.parts_empty)
        layout.addWidget(Disclosure("Изменить части работы", management))
        self.view.doubleClicked.connect(lambda _: run_action(self, self.edit_item))
        self.sections = QTabWidget()
        from studium.presentation.desktop.library import MaterialFiles

        files = MaterialFiles(service, "assessment_files", lambda: assessment, parent=self)
        self.sections.addTab(files, "Условия / файлы работы")
        shared = QWidget()
        shared_layout = QVBoxLayout(shared)
        hint(
            shared_layout,
            "Файлы определения и общего комплекта домашних заданий используются без копирования. Части работы необязательны.",
        )
        self.shared_model = TableModel([("Общий файл", lambda e: e.asset.original_filename)])
        self.shared_view = table(self.shared_model)
        shared_layout.addWidget(self.shared_view)
        toolbar(
            shared_layout,
            [
                ("Открыть общий файл", lambda: run_action(self, self.open_shared)),
                ("Выбрать комплект условий", lambda: run_action(self, self.select_pack)),
            ],
        )
        self.sections.addTab(shared, "Общие комплекты")
        self.main_tabs.addTab(self.sections, "Условия и комплекты")
        if assessment.type == AssessmentType.CONTROL_WORK:
            toolbar(
                layout,
                [
                    ("Добавить задачи из банка", lambda: run_action(self, self.add_bank_tasks)),
                    ("Назначить задачи студенту", lambda: run_action(self, self.assign_tasks)),
                    ("Варианты / генератор", lambda: run_action(self, self.open_variants)),
                ],
            )
        self.refresh()

    def refresh(self):
        self.shared_model.replace_rows(self.service.assessment_shared_files(self.assessment))
        self.locked_hint.setVisible(self.service.assessment_content_locked(self.assessment.id))
        topics = self.service.learning_targets("assessment_topics", self.assessment.id)
        skills = self.service.learning_targets("assessment_skills", self.assessment.id)
        self.topic_tags.set_values([(t.id, t.title) for t in topics])
        self.skill_tags.set_values([(s.id, s.title) for s in skills])
        self.content.setText(
            TEXT["topics"]
            + ": "
            + ", ".join(t.title for t in topics)
            + "\n"
            + TEXT["skills"]
            + ": "
            + ", ".join(s.title for s in skills)
        )
        self.model.replace_rows(
            [
                (
                    i,
                    self.service.learning_targets("item_topics", i.id),
                    self.service.learning_targets("item_skills", i.id),
                )
                for i in self.service.list_assessment_items(self.assessment.id)
            ]
        )
        self.view.setVisible(bool(self.model.rows))
        self.parts_empty.setVisible(not self.model.rows)

    def edit_content(self):
        present_detail(
            ContentForm(self.service, self.context.course.id, self.assessment, parent=self),
            self,
            refresh=getattr(self, "refresh", None),
        )
        self.refresh()

    def edit_item(self, *, new=False):
        row = None if new else selected(self.view)
        if new or row:
            present_detail(
                ItemForm(self.service, self.assessment, None if new else row[0], self),
                self,
                refresh=getattr(self, "refresh", None),
            )
            self.refresh()

    def item_content(self):
        row = selected(self.view)
        if row:
            present_detail(
                ContentForm(self.service, self.context.course.id, row[0], item=True, parent=self),
                self,
                refresh=getattr(self, "refresh", None),
            )
            self.refresh()

    def move(self, direction):
        index = self.view.currentIndex().row()
        items = [row[0] for row in self.model.rows]
        if 0 <= index < len(items) and 0 <= index + direction < len(items):
            items[index], items[index + direction] = items[index + direction], items[index]
            self.service.reorder_assessment_items(self.assessment.id, items)
            self.refresh()
            self.view.setCurrentIndex(self.model.index(index + direction, 0))

    def archive_item(self):
        row = selected(self.view)
        if row and confirm(
            self, TEXT["confirm_hide"].format(name=row[0].title), action_label=TEXT["archive"]
        ):
            self.service.archive_assessment_item(row[0])
            self.refresh()

    def open_shared(self):
        entry = selected(self.shared_view)
        if entry:
            from studium.presentation.desktop.files import FilePreviewDialog

            present_detail(
                FilePreviewDialog(self.service, entry, self),
                self,
                title=entry.asset.original_filename,
            )

    def select_pack(self):
        definition = self.service.definition_for_assessment(self.assessment)
        if definition:
            form = FormDialog(
                "Общие комплекты домашних заданий",
                lambda ids: self.service.set_definition_packs(definition.id, ids),
                self,
            )
            packs = CheckList(
                self.service.list_materials("packs", course_id=self.context.course.id),
                self.service.pack_ids_for_definition(definition.id),
            )
            form.body_layout.insertWidget(0, packs)
            form.values = packs.ids
            if form.exec() == QDialog.DialogCode.Accepted:
                self.refresh()

    def add_bank_tasks(self):
        def save(ids):
            order = len(self.service.list_assessment_items(self.assessment.id))
            for index, id in enumerate(ids):
                self.service.add_control_problem(self.assessment.id, id, order + index)

        if (
            ProblemSelectionForm(self.service, self.context.course.id, save, self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def assign_tasks(self):
        StudentProblemForm(self.service, self.context, self.assessment, self).exec()

    def open_variants(self):
        from studium.presentation.desktop.navigation import main_window

        window = main_window(self)
        if window:
            window.router.back()
            window.groups_page.tabs.setCurrentIndex(6)


class ProblemSelectionForm(FormDialog):
    def __init__(self, service, course_id, on_save, parent=None):
        super().__init__("Выбор задач из банка", on_save, parent)
        self.service, self.course_id = service, course_id
        self.search = self.line("search")
        self.tags = self.line("tags") if "tags" in TEXT else QLineEdit()
        if "tags" not in TEXT:
            self.form.addRow("Теги через запятую", self.tags)
        self.topic, self.skill, self.collection = QComboBox(), QComboBox(), QComboBox()
        for field, title, values in (
            (self.topic, "Тема", service.list_course_topics(course_id)),
            (self.skill, "Навык", service.list_course_skills(course_id)),
            (self.collection, "Коллекция", service.list_problem_collections(course_id)),
        ):
            field.addItem("Любая", None)
            for value in values:
                field.addItem(value.title, value.id)
            self.form.addRow(title, field)
            field.currentIndexChanged.connect(lambda _: self.reload())
        self.tasks = CheckList([])
        self.body_layout.insertWidget(1, self.tasks)
        self.search.textChanged.connect(self.reload)
        self.tags.textChanged.connect(self.reload)
        self.reload()

    def reload(self):
        if not hasattr(self, "tasks"):
            return
        selected_ids = self.tasks.ids()
        values = self.service.list_materials(
            "problems",
            course_id=self.course_id,
            search=self.search.text(),
            tags=self.tags.text().split(","),
            topic_id=self.topic.currentData(),
            skill_id=self.skill.currentData(),
            collection_id=self.collection.currentData(),
        )
        from studium.domain.content import GenerationCriteria

        values = (
            self.service.problem_pool(
                GenerationCriteria(self.course_id, 1, problem_ids=tuple(v.id for v in values))
            )
            if values
            else ()
        )
        self.tasks.fill([(v.id, f"{v.identifier} · {v.title}") for v in values], selected_ids)

    def values(self):
        return self.tasks.ids()


class StudentProblemForm(ProblemSelectionForm):
    def __init__(self, service, context, assessment, parent=None):
        super().__init__(service, context.course.id, self.assign, parent)
        self.student, self.item = QComboBox(), QComboBox()
        for entry in service.list_students_for_offering(context.offering.id):
            self.student.addItem(entry.student.full_name, entry.student.id)
        for item in service.list_assessment_items(assessment.id):
            self.item.addItem(item.title, item.id)
        self.form.insertRow(0, "Студент", self.student)
        self.form.insertRow(1, "Задача рубежного контроля", self.item)
        self.setWindowTitle("Ручное назначение задачи студенту")

    def assign(self, ids):
        if len(ids) != 1 or self.student.currentData() is None or self.item.currentData() is None:
            raise ValueError(
                "Выберите студента, задачу рубежного контроля и ровно одну задачу из банка"
            )
        return self.service.assign_student_problem(
            self.student.currentData(), self.item.currentData(), ids[0]
        )
