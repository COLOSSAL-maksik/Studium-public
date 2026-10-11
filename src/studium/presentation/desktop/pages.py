"""Group roster, progress matrix and assessment workspace."""

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from studium.domain.enums import AssessmentType, AttendanceStatus, EnrollmentStatus
from studium.presentation.desktop.components import (
    confirm,
    confirm_delete,
    hint,
    panel,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import (
    AssessmentDialog,
    ChoiceDialog,
    GroupDialog,
    StudentDetailsDialog,
    StudentDialog,
    open_work,
)
from studium.presentation.desktop.journal import GroupedJournalHeader, JournalModel
from studium.presentation.desktop.learning import AssessmentContentDialog, LessonsPage
from studium.presentation.desktop.messages import (
    ASSESSMENT_LABELS,
    ATTENDANCE_LABELS,
    TEXT,
    context_label,
)
from studium.presentation.desktop.models import (
    StudentTableModel,
    TableModel,
    display_score,
    display_time,
    progress_text,
)
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.theme import resize_to_screen
from studium.presentation.desktop.widgets import JournalTable, search_shortcut


def fill_contexts(field, contexts, selected_id=None):
    field.blockSignals(True)
    field.clear()
    for context in contexts:
        field.addItem(context_label(context), context)
    index = next((i for i, c in enumerate(contexts) if c.offering.id == selected_id), 0)
    field.setCurrentIndex(index if contexts else -1)
    field.blockSignals(False)


class GroupsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.current_group = window, None
        self.stack = QStackedWidget()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)
        listing, layout = panel()
        toolbar(
            layout,
            [
                ("Добавить группу", lambda: self.act(self.create_group)),
                (TEXT["edit"], lambda: self.act(self.edit_group)),
                (TEXT["hide"], lambda: self.act(self.hide_group)),
                (TEXT["open"], lambda: self.act(self.open_selected_group)),
            ],
        )
        self.group_model = TableModel(
            [
                (TEXT["number"], lambda r: r.group.number),
                (TEXT["department"], lambda r: r.group.department),
                (TEXT["student_count"], lambda r: r.student_count),
            ]
        )
        self.group_search = QLineEdit()
        self.group_search.setPlaceholderText(TEXT["search"])
        layout.addWidget(self.group_search)
        self.group_proxy = QSortFilterProxyModel(self)
        self.group_proxy.setSourceModel(self.group_model)
        self.group_proxy.setFilterKeyColumn(-1)
        self.group_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.group_search.textChanged.connect(self.group_proxy.setFilterFixedString)
        search_shortcut(listing, self.group_search)
        self.group_view = table(self.group_proxy)
        self.group_view.setSortingEnabled(False)
        self.group_view.doubleClicked.connect(lambda _: self.act(self.open_selected_group))
        layout.addWidget(self.group_view)
        self.empty_groups = hint(layout, TEXT["empty_groups"])
        self.stack.addWidget(listing)
        detail, layout = panel()
        header = QHBoxLayout()
        self.heading = hint(layout, "")
        self.heading.setProperty("role", "heading")
        layout.removeWidget(self.heading)
        header.addWidget(self.heading)
        self.course_heading = hint(layout, "")
        self.course_heading.setProperty("role", "subheading")
        layout.removeWidget(self.course_heading)
        header.addWidget(self.course_heading, 1)
        layout.addLayout(header)
        self.period_heading = hint(layout, "")
        self.period_heading.setProperty("role", "caption")
        self.contexts = QComboBox()
        self.contexts.currentIndexChanged.connect(lambda _: self.act(self.load_roster))
        context_row = QHBoxLayout()
        context_row.addWidget(self.contexts)
        context_row.addStretch()
        layout.addLayout(context_row)
        self.empty_context = hint(layout, TEXT["empty_offering"])
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        students, student_layout = panel()
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(TEXT["search"])
        self.show_ended = QCheckBox(TEXT["show_ended"])
        self.show_ended.toggled.connect(lambda _: self.act(self.load_roster))
        self.add_student_button = QToolButton()
        self.add_student_button.setText("+ Добавить студента ▾")
        self.add_student_button.setAccessibleName(
            "Добавить студента: создать нового или выбрать существующего"
        )
        self.add_student_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.add_student_button)
        menu.addAction(TEXT["create_new_student"], lambda: self.act(self.create_student))
        menu.addAction(TEXT["add_existing_student"], lambda: self.act(self.add_existing))
        self.add_student_button.setMenu(menu)
        search_row.addWidget(self.add_student_button)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.show_ended)
        student_layout.addLayout(search_row)
        search_shortcut(students, self.search)
        self.student_model = StudentTableModel()
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.student_model)
        self.proxy.setFilterKeyColumn(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.student_view = table(self.proxy)
        self.student_view.setSortingEnabled(True)
        self.student_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.student_view.doubleClicked.connect(lambda _: self.act(self.open_student))
        self.student_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.student_view.customContextMenuRequested.connect(self.student_menu)
        student_layout.addWidget(self.student_view)
        self.empty_students = hint(student_layout, TEXT["empty_students"])
        matrix, matrix_layout = panel()
        journal_row = toolbar(matrix_layout, [])
        self.journal_search = QLineEdit()
        self.journal_search.setPlaceholderText(TEXT["journal_search"])
        journal_row.insertWidget(1, self.journal_search, 1)
        self.journal_search.textChanged.connect(self.find_journal_student)
        search_shortcut(matrix, self.journal_search)
        self.journal_mode = QComboBox()
        for title, kind in (
            ("Все", None),
            ("Посещаемость", "attendance"),
            ("ДЗ", "homework"),
            ("РК", "control"),
        ):
            self.journal_mode.addItem(title, kind)
        journal_row.addWidget(self.journal_mode)
        self.journal_mode.currentIndexChanged.connect(self.filter_journal)
        self.module_toggle = QToolButton()
        self.module_toggle.setText("Модули")
        self.module_toggle.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.module_menu = QMenu(self.module_toggle)
        self.module_toggle.setMenu(self.module_menu)
        journal_row.addWidget(self.module_toggle)
        self.collapsed_modules = set()
        self.matrix_model = JournalModel()
        self.matrix_view = table(
            self.matrix_model, stretch=False, view=JournalTable(self.matrix_model)
        )
        self.matrix_view.setSelectionBehavior(self.matrix_view.SelectionBehavior.SelectItems)
        self.matrix_view.setSelectionMode(self.matrix_view.SelectionMode.ExtendedSelection)
        self.matrix_view.setHorizontalHeader(GroupedJournalHeader(self.matrix_view))
        self.matrix_view.verticalHeader().setDefaultSectionSize(32)
        self.matrix_view.setHorizontalScrollMode(self.matrix_view.ScrollMode.ScrollPerPixel)
        self.matrix_view.setVerticalScrollMode(self.matrix_view.ScrollMode.ScrollPerPixel)
        self.matrix_view.frozen.setVerticalScrollMode(self.matrix_view.ScrollMode.ScrollPerPixel)
        self.matrix_view.clicked.connect(
            lambda index: self.act(lambda: self.journal_clicked(index))
        )
        self.matrix_view.activated.connect(
            lambda index: self.act(lambda: self.open_matrix_cell(index))
        )
        attendance_row = QHBoxLayout()
        self.attendance_status = QComboBox()
        for status, label in ATTENDANCE_LABELS.items():
            self.attendance_status.addItem(label, status)
        attendance_row.addWidget(self.attendance_status)
        self.attendance_apply = QPushButton("Отметить выбранных")
        self.attendance_apply.clicked.connect(lambda: self.act(self.mark_selected_attendance))
        attendance_row.addWidget(self.attendance_apply)
        attendance_row.addStretch()
        self.attendance_tools = QWidget()
        self.attendance_tools.setLayout(attendance_row)
        matrix_layout.addWidget(self.attendance_tools)
        self.attendance_tools.hide()
        self.matrix_view.selectionModel().selectionChanged.connect(
            self.attendance_selection_changed
        )
        self.journal_structure = hint(
            matrix_layout, "Посещаемость · Домашнее задание · Рубежный контроль"
        )
        matrix_layout.addWidget(self.matrix_view)
        self.empty_journal = hint(matrix_layout, TEXT["journal_empty"])
        self.matrix_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.matrix_view.customContextMenuRequested.connect(self.matrix_menu)
        self.matrix_view.frozen.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.matrix_view.frozen.customContextMenuRequested.connect(self.matrix_student_menu)
        hint(matrix_layout, TEXT["matrix_hint"])
        self.tabs.addTab(matrix, TEXT["journal"])
        self.tabs.addTab(students, TEXT["students"])
        self.works_page = WorksPage(window, self.context)
        self.tabs.addTab(self.works_page, TEXT["works"])
        from studium.presentation.desktop.qa_plans import SemesterPlanWidget

        self.semester_plan_page = SemesterPlanWidget(window, self.context, self)
        self.tabs.addTab(self.semester_plan_page, "План семестра")
        self.lessons_page = LessonsPage(lambda: self.service, self.context, self)
        self.tabs.addTab(self.lessons_page, TEXT["lessons"])
        from studium.presentation.desktop.analytics import GroupAnalyticsWidget

        self.analytics = GroupAnalyticsWidget(lambda: self.service, self.context, self)
        self.tabs.addTab(self.analytics, TEXT["analytics"])
        from studium.presentation.desktop.communication import QuestionsWidget

        self.questions = QuestionsWidget(parent=self)
        self.tabs.addTab(self.questions, TEXT["questions"])
        from studium.presentation.desktop.tickets import TicketGeneratorPage

        self.tickets = TicketGeneratorPage(window, self.context)
        self.tickets.hide()
        group_settings, settings_layout = panel()
        hint(settings_layout, "Реквизиты группы и учебные контексты")
        toolbar(
            settings_layout,
            [
                ("Изменить группу", lambda: self.act(self.edit_current_group)),
                (TEXT["add_course"], lambda: self.act(self.add_course)),
                ("Удалить группу", lambda: self.act(self.delete_current_group)),
            ],
        )
        settings_layout.addStretch()
        self.tabs.addTab(group_settings, "Настройки группы")
        self.tabs.currentChanged.connect(self.refresh_tab)
        self.stack.addWidget(detail)

    @property
    def service(self):
        return self.window.service

    def act(self, action):
        return run_action(self, action)

    def context(self):
        return self.contexts.currentData()

    def delete_current_group(self):
        if self.current_group and confirm_delete(self, self.service, "group", self.current_group):
            self.service.safe_delete("group", self.current_group)
            self.back()
            self.window.refresh()

    def require_context(self):
        context = self.context()
        if not context:
            QMessageBox.information(self, TEXT["app"], TEXT["choose_offering"])
        return context

    def refresh(self):
        term = self.service.active_term()
        rows = self.service.groups(term.id if term else None)
        self.group_model.replace_rows(rows)
        self.empty_groups.setVisible(not rows)
        if self.current_group:
            self.current_group = next(
                (r.group for r in rows if r.group.id == self.current_group.id), None
            )
            if self.current_group:
                self.load_contexts()
            else:
                self.back()

    def create_group(self):
        if (
            GroupDialog(lambda v: self.service.create_group(**v), parent=self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def edit_group(self):
        row = selected(self.group_view)
        if (
            row
            and GroupDialog(
                lambda v: self.service.update_group(row.group, **v), row.group, self
            ).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def hide_group(self):
        row = selected(self.group_view)
        if row and confirm_delete(self, self.service, "group", row.group):
            self.service.hide("group", row.group)
            self.window.refresh()

    def edit_current_group(self):
        if (
            self.current_group
            and GroupDialog(
                lambda v: self.service.update_group(self.current_group, **v),
                self.current_group,
                self,
            ).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def open_selected_group(self):
        row = selected(self.group_view)
        if row:
            self.open_group(row.group)

    def open_group(self, group):
        self.current_group = group
        self.search.clear()
        self.load_contexts()
        self.stack.setCurrentIndex(1)
        if hasattr(self.window, "router"):
            self.window.router.push(
                self, group.number, leave=self.back, refresh=self.load_roster, transient=False
            )

    def back(self):
        self.current_group = None
        self.stack.setCurrentIndex(0)

    def navigation_state(self):
        context = self.context()
        return (
            (self.current_group, context.offering.id if context else None, self.tabs.currentIndex())
            if self.current_group
            else None
        )

    def restore_navigation_state(self, state):
        self.current_group, offering_id, tab = state
        self.load_contexts()
        for index in range(self.contexts.count()):
            if self.contexts.itemData(index).offering.id == offering_id:
                self.contexts.setCurrentIndex(index)
                break
        self.stack.setCurrentIndex(1)
        self.tabs.setCurrentIndex(tab)

    def load_contexts(self):
        self.heading.setText(self.current_group.number)
        term = self.service.active_term()
        previous = self.context()
        contexts = (
            self.service.list_offerings(group_id=self.current_group.id, term_id=term.id)
            if term
            else []
        )
        fill_contexts(self.contexts, contexts, previous.offering.id if previous else None)
        # Only the discipline varies here; group and period are in the common header.
        for i, context in enumerate(contexts):
            self.contexts.setItemText(i, context.course.name)
        self.contexts.setVisible(len(contexts) > 1)
        self.load_roster()

    def load_roster(self):
        cursor = self.matrix_view.currentIndex()
        previous_student = (
            self.matrix_model.matrix.roster[cursor.row()].student.id
            if cursor.isValid() and self.matrix_model.matrix
            else None
        )

        def column_key(column):
            if column is None:
                return None
            return (
                column.kind,
                column.assessment.id
                if column.assessment
                else column.program_work.id
                if column.program_work
                else tuple(lesson.id for lesson in column.lessons)
                if column.lessons
                else column.week,
            )

        previous_column = (
            column_key(self.matrix_model.column(cursor.column())) if cursor.isValid() else None
        )
        context = self.context()
        self.course_heading.setText(context.course.name if context else "")
        self.period_heading.setText(context.term.name if context else "")
        self.tabs.setEnabled(context is not None)
        self.empty_context.setVisible(context is None)
        if context:
            journal = self.service.journal(
                context.offering.id, include_ended=self.show_ended.isChecked()
            )
            matrix = journal.matrix
            self.student_model.replace_rows(matrix.roster)
            self.matrix_model.replace_matrix(journal)
            labels = {"homework": "Домашнее задание", "control": "Рубежный контроль"}
            self.journal_structure.setText(
                "Посещаемость · Домашнее задание · Рубежный контроль"
                + (
                    "\n"
                    + " · ".join(
                        f"{title}: {labels[kind]} —" for title, kind in journal.empty_sections
                    )
                    if journal.empty_sections
                    else ""
                )
            )
            self.period_heading.setText(
                f"План семестра · {journal.program.weeks} недель"
                if journal.program
                else context.term.name
            )
            self.service.remember_offering(context.offering.id)
            self.module_menu.clear()
            for title in dict.fromkeys(column.module_title for column in journal.columns):
                action = self.module_menu.addAction(title)
                action.setCheckable(True)
                action.setChecked(title not in self.collapsed_modules)
                action.toggled.connect(
                    lambda checked, title=title: self.toggle_module(title, checked)
                )
            self.empty_students.setVisible(not matrix.roster)
            self.matrix_view.setColumnWidth(0, 236)
            for col in range(1, self.matrix_model.columnCount()):
                self.matrix_view.setColumnWidth(
                    col, 38 if self.matrix_model.column(col).kind == "attendance" else 66
                )
            self.filter_journal()
            self.matrix_view.sync_frozen()
            if previous_student:
                row = next(
                    (
                        i
                        for i, entry in enumerate(matrix.roster)
                        if entry.student.id == previous_student
                    ),
                    None,
                )
                col = next(
                    (
                        i
                        for i in range(self.matrix_model.columnCount())
                        if column_key(self.matrix_model.column(i)) == previous_column
                    ),
                    None,
                )
                if row is not None and col is not None:
                    self.matrix_view.setCurrentIndex(self.matrix_model.index(row, col))
        else:
            self.student_model.replace_rows([])
            self.matrix_model.replace_matrix(None)
        self.empty_journal.setVisible(
            not context
            or not self.matrix_model.rowCount()
            or not self.matrix_model.snapshot.columns
        )
        self.works_page.refresh()
        self.refresh_tab(self.tabs.currentIndex())
        self.window.update_route_header()

    def toggle_module(self, title, checked):
        self.collapsed_modules.discard(title) if checked else self.collapsed_modules.add(title)
        self.filter_journal()

    def filter_journal(self):
        if not hasattr(self, "matrix_view") or not self.matrix_model.snapshot:
            return
        kind = self.journal_mode.currentData()
        for index, column in enumerate(self.matrix_model.snapshot.columns, 1):
            self.matrix_view.setColumnHidden(
                index,
                column.module_title in self.collapsed_modules
                or (kind is not None and column.kind != kind),
            )
        self.matrix_view.sync_frozen()

    def refresh_tab(self, index):
        widget = self.tabs.widget(index)
        if widget is self.questions and self.context():
            self.questions.service = self.service
            self.questions.offering_id = self.context().offering.id
        if self.service and widget in (
            self.analytics,
            self.semester_plan_page,
            self.lessons_page,
            self.questions,
            self.tickets,
        ):
            self.act(widget.refresh)

    def find_journal_student(self, text):
        for row in range(self.matrix_model.rowCount()):
            if (
                text.casefold()
                in self.matrix_model.data(self.matrix_model.index(row, 0)).casefold()
            ):
                self.matrix_view.setCurrentIndex(self.matrix_model.index(row, 1))
                self.matrix_view.scrollTo(self.matrix_model.index(row, 1))
                break

    def student_menu(self, point):
        index = self.student_view.indexAt(point)
        if not index.isValid():
            return
        self.student_view.setCurrentIndex(index)
        menu = QMenu(self)
        for key, action in [
            ("open", self.open_student),
            ("edit", self.edit_student),
            ("withdraw", self.withdraw),
            ("archive_student", self.archive_student),
        ]:
            item = menu.addAction(TEXT[key], lambda _checked=False, action=action: self.act(action))
            if key == "withdraw":
                item.setEnabled(
                    selected(self.student_view).enrollment.status == EnrollmentStatus.ACTIVE
                )
        menu.exec(self.student_view.viewport().mapToGlobal(point))

    def archive_student(self):
        entry = selected(self.student_view)
        if entry and confirm(
            self, TEXT["archive_student_confirm"], action_label=TEXT["archive_student"]
        ):
            self.service.hide("student", entry.student)
            self.window.refresh()

    def matrix_menu(self, point):
        index = self.matrix_view.indexAt(point)
        if not index.isValid():
            return
        if not self.matrix_view.selectionModel().isSelected(index):
            self.matrix_view.setCurrentIndex(index)
        menu = QMenu(self)
        if (
            self.matrix_model.column(index.column())
            and self.matrix_model.column(index.column()).kind == "attendance"
        ):
            for status, label in ATTENDANCE_LABELS.items():
                menu.addAction(
                    label,
                    lambda status=status: self.act(lambda: self.mark_selected_attendance(status)),
                )
        menu.addAction("Сдачи и проверки", lambda: self.act(lambda: self.open_matrix_cell(index)))
        if index.column() > 0:
            menu.addAction(
                TEXT["history"], lambda: self.act(lambda: self.open_matrix_history(index))
            )
        menu.addAction(
            TEXT["student_card"], lambda: self.act(lambda: self.open_matrix_student(index.row()))
        )
        menu.exec(self.matrix_view.viewport().mapToGlobal(point))

    def journal_clicked(self, index):
        column = self.matrix_model.column(index.column())
        if column and column.kind == "attendance":
            return
        if QApplication.keyboardModifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            return
        self.open_matrix_cell(index)

    def attendance_selection_changed(self, *_):
        indexes = self.matrix_view.selectionModel().selectedIndexes()
        columns = {i.column() for i in indexes}
        column = self.matrix_model.column(next(iter(columns))) if len(columns) == 1 else None
        self.attendance_tools.setVisible(bool(column and column.kind == "attendance"))
        self.attendance_apply.setText(f"Отметить выбранных ({len(indexes)})")

    def mark_selected_attendance(self, status=None):
        indexes = self.matrix_view.selectionModel().selectedIndexes()
        columns = {i.column() for i in indexes}
        if len(columns) != 1:
            return
        column = self.matrix_model.column(next(iter(columns)))
        if column is None or column.kind != "attendance":
            return
        if column.lessons and all(lesson.cancelled for lesson in column.lessons):
            QMessageBox.information(
                self,
                "Посещаемость",
                "Занятие отменено. Его история сохранена; отметки посещения не изменяются.",
            )
            return
        lessons = [lesson for lesson in column.lessons if not lesson.cancelled]
        if not lessons:
            self.open_journal_attendance(indexes[0], column)
            return
        lesson = lessons[0]
        if len(lessons) > 1:
            chosen = []
            if not ChoiceDialog(
                "Посещаемость",
                "Занятие",
                [(lesson.id, f"{lesson.lesson_date} · {lesson.title}") for lesson in lessons],
                chosen.append,
                self,
            ).exec():
                return
            lesson = next(lesson for lesson in lessons if lesson.id == chosen[0])
        enrollment_ids = {self.matrix_model.matrix.roster[i.row()].enrollment.id for i in indexes}
        entries = [
            row
            for row in self.service.list_lesson_attendance(lesson.id)
            if row.enrollment.id in enrollment_ids
        ]
        self.service.mark_attendance_many(
            lesson.id, entries, status or AttendanceStatus(self.attendance_status.currentData())
        )
        self.load_roster()

    def matrix_student_menu(self, point):
        index = self.matrix_view.frozen.indexAt(point)
        if index.isValid():
            menu = QMenu(self)
            menu.addAction(
                TEXT["student_card"],
                lambda: self.act(lambda: self.open_matrix_student(index.row())),
            )
            menu.exec(self.matrix_view.frozen.viewport().mapToGlobal(point))

    def open_matrix_student(self, row):
        entry = self.matrix_model.matrix.roster[row]
        present_detail(
            StudentDetailsDialog(self.service, self.context(), entry, self),
            self,
            refresh=self.load_roster,
            title=entry.student.full_name,
        )

    def add_course(self):
        term = self.service.active_term()
        if not term:
            QMessageBox.information(self, TEXT["app"], TEXT["choose_period"])
            return
        courses = self.service.list_courses()
        if not courses:
            QMessageBox.information(self, TEXT["app"], TEXT["no_courses"])
            self.window.manage_courses()
            return
        from studium.presentation.desktop.programs import OfferingProgramForm

        if (
            OfferingProgramForm(self.service, term, self.current_group, self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def create_student(self):
        context = self.require_context()
        if (
            context
            and StudentDialog(
                lambda v: self.service.create_student(context.offering.id, **v), parent=self
            ).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def add_existing(self):
        context = self.require_context()
        if not context:
            return
        enrolled = {
            r.student.id for r in self.service.list_students_for_offering(context.offering.id)
        }
        choices = [
            (s.id, s.full_name) for s in self.service.list_students() if s.id not in enrolled
        ]
        if not choices:
            QMessageBox.information(self, TEXT["app"], TEXT["no_existing"])
            return
        if (
            ChoiceDialog(
                TEXT["existing_student"],
                TEXT["full_name"],
                choices,
                lambda id: self.service.enroll_student(context.offering.id, id),
                self,
            ).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def open_student(self):
        entry = selected(self.student_view)
        if entry:
            present_detail(
                StudentDetailsDialog(self.service, self.context(), entry, self),
                self,
                refresh=self.window.refresh,
                title=entry.student.full_name,
            )

    def edit_student(self):
        entry = selected(self.student_view)
        if (
            entry
            and StudentDialog(
                lambda v: self.service.update_student(entry.student, **v), entry.student, self
            ).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def withdraw(self):
        entry = selected(self.student_view)
        if entry and confirm(self, TEXT["confirm_withdraw"], action_label=TEXT["withdraw"]):
            self.service.withdraw_student(entry.enrollment)
            self.window.refresh()

    def create_assessment(self):
        context = self.require_context()
        if (
            context
            and present_detail(
                AssessmentDialog(
                    lambda v: self.service.create_assessment(context.offering.id, **v),
                    parent=self,
                    program=self.service.program_for_offering(context.offering.id),
                ),
                self,
                refresh=getattr(self, "refresh", None),
            )
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def open_matrix_cell(self, index):
        if index.column() == 0:
            self.open_matrix_student(index.row())
            return
        column = self.matrix_model.column(index.column())
        if column.kind == "attendance":
            self.open_journal_attendance(index, column)
            return
        if column.assessment is None:
            self.tabs.setCurrentWidget(self.semester_plan_page)
            self.semester_plan_page.refresh()
            return
        cell = self.matrix_model.data(index, Qt.ItemDataRole.UserRole)
        if cell:
            entry = self.matrix_model.matrix.roster[index.row()]
            if entry.enrollment.status != EnrollmentStatus.ACTIVE:
                self.open_matrix_history(index)
                return
            self.open_matrix_history(index)

    def open_journal_attendance(self, index, column):
        from studium.presentation.desktop.learning import AttendanceForm, LessonForm

        entry = self.matrix_model.matrix.roster[index.row()]
        lessons = [lesson for lesson in column.lessons if not lesson.cancelled]
        if not lessons:
            form = LessonForm(self.service, self.context(), parent=self)
            program = self.matrix_model.snapshot.program
            if program:
                if hasattr(program, "week_dates"):
                    first, _ = program.week_dates(column.week)
                else:
                    from datetime import date, timedelta

                    from studium.domain.value_objects import LocalDate

                    start = program.first_week_start
                    day = date(start.year, start.month, start.day) + timedelta(
                        weeks=column.week - 1
                    )
                    first = LocalDate(day.year, day.month, day.day)
                from PySide6.QtCore import QDate

                form.date.setDate(QDate(first.year, first.month, first.day))
                form.week.setCurrentIndex(form.week.findData(column.week))
            if form.exec() == QDialog.DialogCode.Accepted:
                self.load_roster()
            return
        lesson = lessons[0]
        if len(lessons) > 1:
            choices = [(v.id, f"{v.lesson_date} · {v.title}") for v in lessons]
            chosen = []
            if (
                ChoiceDialog("Занятие", "Выберите занятие", choices, chosen.append, self).exec()
                != QDialog.DialogCode.Accepted
            ):
                return
            lesson = next(v for v in lessons if v.id == chosen[0])
        row = next(
            (
                r
                for r in self.service.list_lesson_attendance(lesson.id)
                if r.enrollment.id == entry.enrollment.id
            ),
            None,
        )
        if (
            row
            and AttendanceForm(self.service, lesson, row, self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.load_roster()

    def open_matrix_history(self, index):
        cell = self.matrix_model.data(index, Qt.ItemDataRole.UserRole)
        if cell:
            entry = self.matrix_model.matrix.roster[index.row()]
            open_work(
                self,
                self.service,
                cell.student_id,
                cell.assessment_id,
                editable=entry.enrollment.status == EnrollmentStatus.ACTIVE,
            )
            self.load_roster()


class WorksPage(QWidget):
    def __init__(self, window, context_provider=None):
        super().__init__()
        self.window = window
        self.context_provider = context_provider
        self.plan_snapshot, self.planned, self.rules = None, {}, {}
        layout = QVBoxLayout(self)
        self.contexts = QComboBox()
        layout.addWidget(self.contexts)
        self.contexts.setVisible(context_provider is None)
        self.contexts.currentIndexChanged.connect(lambda _: run_action(self, self.load))
        toolbar(
            layout,
            [
                ("+ Добавить", lambda: run_action(self, self.create)),
                (TEXT["edit"], lambda: run_action(self, self.edit)),
                (TEXT["hide"], lambda: run_action(self, self.hide)),
                (TEXT["open"], lambda: run_action(self, self.open)),
                (TEXT["assessment_content"], lambda: run_action(self, self.content)),
            ],
        )
        self.categories = QTabBar()
        for label in ("ДЗ", "Контрольные", "Экзамены", "Другие"):
            self.categories.addTab(label)
        layout.addWidget(self.categories)
        self.categories.currentChanged.connect(lambda _: self.load())
        self.model = TableModel(
            [
                (TEXT["assessment_title"], lambda a: a.title),
                (TEXT["type"], lambda a: ASSESSMENT_LABELS[a.type]),
                (TEXT["work_number"], lambda a: a.number or "—"),
                ("Текущий срок", self.deadline),
                ("Минимум / максимум", self.bounds),
            ]
        )
        self.view = table(self.model)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.menu)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))
        layout.addWidget(self.view)
        self.empty = hint(layout, TEXT["empty_assessments"])

    @property
    def service(self):
        return self.window.service

    def refresh(self):
        term = self.service.active_term()
        previous = self.contexts.currentData()
        contexts = (
            ([self.context_provider()] if self.context_provider and self.context_provider() else [])
            if self.context_provider
            else (self.service.list_offerings(term_id=term.id) if term else [])
        )
        fill_contexts(self.contexts, contexts, previous.offering.id if previous else None)
        self.load()

    def load(self):
        context = self.contexts.currentData()
        self.plan_snapshot, self.planned, self.rules = (
            self.service.work_settings(context.offering.id) if context else (None, {}, {})
        )
        rows = self.service.list_assessments(context.offering.id) if context else []
        kinds = (AssessmentType.HOMEWORK, AssessmentType.CONTROL_WORK, AssessmentType.EXAM)
        category = self.categories.currentIndex()
        rows = [
            a for a in rows if (a.type == kinds[category] if category < 3 else a.type not in kinds)
        ]
        self.model.replace_rows(rows)
        self.empty.setText(TEXT["empty_assessments"] if context else TEXT["choose_offering"])
        self.empty.setVisible(not rows)

    def deadline(self, assessment):
        work = self.planned.get(assessment.id)
        if not work:
            return display_time(assessment.due_at)
        if work.deadline_kind == "WEEK_ONLY":
            return f"Неделя {work.due_week}"
        return (
            display_time(work.exact_due_at)
            if work.deadline_kind == "EXACT_INCLUSIVE"
            else str(work.due_date or "—")
        )

    def bounds(self, assessment):
        from studium.domain.qa import score_text

        rule = self.rules.get(assessment.id)
        return (
            f"{score_text(rule.min_cents)} / {score_text(rule.max_cents)}"
            if rule
            else "— / " + display_score(assessment.max_score)
        )

    def menu(self, point):
        index = self.view.indexAt(point)
        if index.isValid():
            self.view.setCurrentIndex(index)
        menu = QMenu(self)
        menu.addAction("+ Добавить", lambda: run_action(self, self.create))
        if selected(self.view):
            for title, action in (
                ("Открыть", self.open),
                ("Задачи и варианты", self.content),
                ("Правило баллов", self.rule),
                ("Изменить", self.edit),
                ("Скрыть", self.hide),
            ):
                menu.addAction(title, lambda checked=False, action=action: run_action(self, action))
        menu.exec(self.view.viewport().mapToGlobal(point))

    def rule(self):
        from studium.presentation.desktop.qa_workflow import RuleForm

        assessment = selected(self.view)
        if assessment and RuleForm(self.service, assessment.id, self).exec():
            self.load()

    def create(self):
        context = self.contexts.currentData()
        if not context:
            return
        from studium.presentation.desktop.qa_plans import SemesterPlanWidget

        page = SemesterPlanWidget(self.window, lambda: context, self)
        self.window.router.push(page, "План семестра · добавление работы")
        page.refresh()
        page.add_work()

    def edit(self):
        assessment = selected(self.view)
        work = self.planned.get(assessment.id) if assessment else None
        if work:
            from studium.presentation.desktop.qa_plans import PlannedWorkForm

            if PlannedWorkForm(
                self.service, self.contexts.currentData(), self.plan_snapshot, work, self
            ).exec():
                self.window.refresh()
            return
        if (
            assessment
            and present_detail(
                AssessmentDialog(
                    lambda v: self.service.update_assessment(assessment, **v),
                    assessment,
                    self,
                    program=self.service.program_for_offering(assessment.offering_id),
                ),
                self,
                refresh=getattr(self, "refresh", None),
            )
            == QDialog.DialogCode.Accepted
        ):
            self.window.refresh()

    def hide(self):
        assessment = selected(self.view)
        if assessment and confirm(self, TEXT["confirm_hide"].format(name=assessment.title)):
            self.service.hide("assessment", assessment)
            self.window.refresh()

    def open(self):
        assessment = selected(self.view)
        if assessment:
            present_detail(
                AssessmentStudentsDialog(
                    self.service, self.contexts.currentData(), assessment, self
                ),
                self,
                refresh=self.window.refresh,
                title=assessment.title,
            )

    def content(self):
        assessment = selected(self.view)
        context = self.contexts.currentData()
        if assessment and context:
            present_detail(
                AssessmentContentDialog(self.service, context, assessment, self),
                self,
                refresh=self.window.refresh,
                title=assessment.title + " · содержание",
            )


class AssessmentStudentsDialog(QDialog):
    def __init__(self, service, context, assessment, parent=None):
        super().__init__(parent)
        self.service, self.context, self.assessment = service, context, assessment
        self.setWindowTitle(assessment.title)
        resize_to_screen(self, 880, 520)
        layout = QVBoxLayout(self)
        hint(layout, f"{assessment.title}\n{context_label(context)}")
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        students, layout = panel()
        self.tabs.addTab(students, TEXT["students"])
        self.show_ended = QCheckBox(TEXT["show_ended"])
        self.show_ended.toggled.connect(lambda _: run_action(self, self.refresh))
        layout.addWidget(self.show_ended)
        self.model = TableModel(
            [
                (TEXT["full_name"], lambda row: row[0].student.full_name),
                (TEXT["status"], lambda row: progress_text(row[1].progress)),
                (
                    TEXT["attempts"],
                    lambda row: row[1].progress.attempt_count if row[1].progress else 0,
                ),
            ]
        )
        self.view = table(self.model)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open_work))
        layout.addWidget(self.view)
        toolbar(
            layout,
            [
                (TEXT["history"], lambda: run_action(self, self.open_work)),
                (TEXT["assessment_content"], lambda: run_action(self, self.content)),
            ],
        )
        from studium.presentation.desktop.analytics import AssessmentAnalyticsWidget

        self.results = AssessmentAnalyticsWidget(service, assessment.id, self)
        self.tabs.addTab(self.results, TEXT["assessment_results"])
        from studium.presentation.desktop.communication import QuestionsWidget

        self.questions = QuestionsWidget(
            service, offering_id=context.offering.id, assessment_id=assessment.id, parent=self
        )
        self.tabs.addTab(self.questions, TEXT["questions"])
        self.tabs.currentChanged.connect(
            lambda index: (
                run_action(self, self.results.refresh)
                if self.tabs.widget(index) is self.results
                else None
            )
        )
        self.refresh()

    def refresh(self):
        matrix = self.service.matrix(
            self.context.offering.id, include_ended=self.show_ended.isChecked()
        )
        self.model.replace_rows(
            [(entry, matrix.cells[entry.student.id, self.assessment.id]) for entry in matrix.roster]
        )

    def open_work(self):
        row = selected(self.view)
        if row:
            editable = row[0].enrollment.status == EnrollmentStatus.ACTIVE
            if not editable and row[1].work is None:
                QMessageBox.information(self, TEXT["app"], TEXT["read_only"])
                return
            open_work(self, self.service, row[0].student.id, self.assessment.id, editable=editable)
            self.refresh()

    def content(self):
        present_detail(
            AssessmentContentDialog(self.service, self.context, self.assessment, self),
            self,
            refresh=self.refresh,
        )
