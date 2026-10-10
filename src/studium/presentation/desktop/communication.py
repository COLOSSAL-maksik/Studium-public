"""Minimal factual correspondence UI using existing forms, tables and preview."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from studium.domain.communication import AuthorRole, CommunicationChannel, CommunicationState
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import (
    confirm,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import FormDialog, instant_value
from studium.presentation.desktop.files import FilePreviewDialog
from studium.presentation.desktop.messages import (
    AUTHOR_LABELS,
    CHANNEL_LABELS,
    COMMUNICATION_STATES,
    FILE_LABELS,
    QUESTION_CONTEXT_LABELS,
    TEXT,
    context_label,
)
from studium.presentation.desktop.models import TableModel, display_time
from studium.presentation.desktop.navigation import main_window, present_detail
from studium.presentation.desktop.theme import resize_to_screen
from studium.presentation.desktop.widgets import search_shortcut
from studium.presentation.desktop.workflow_widgets import FileDropZone


def context_name(value, attempt_titles=None):
    return (
        value.title
        if hasattr(value, "title")
        else f"{(attempt_titles or {}).get(value.id, '')} · {TEXT['file_attempt']} {value.attempt_no} · {display_time(value.occurred_at)}"
    )


def select_data(field, value):
    field.setCurrentIndex(next((i for i in range(field.count()) if field.itemData(i) == value), -1))


class MessageCaptureDialog(FormDialog):
    def __init__(self, service, case_id, role, *, channel=CommunicationChannel.MANUAL, parent=None):
        self.service, self.case_id, self.role = service, case_id, role
        self.saved_message = None
        super().__init__(AUTHOR_LABELS[role], self.save_message, parent)
        self.channel = QComboBox()
        for value, label in CHANNEL_LABELS.items():
            self.channel.addItem(label, value)
        select_data(self.channel, channel)
        self.form.addRow(TEXT["channel"], self.channel)
        self.sent_at = self.timestamp("sent_at")
        self.body = self.notes("message")
        self.body.setMinimumHeight(130)
        self.paste_button = QPushButton(TEXT["paste_message"])
        self.paste_button.clicked.connect(
            lambda: self.body.setPlainText(QApplication.clipboard().text())
        )
        self.form.addRow(self.paste_button)

    def values(self):
        return {
            "body": self.body.toPlainText(),
            "sent_at": instant_value(self.sent_at),
            "channel": CommunicationChannel(self.channel.currentData()),
        }

    def save_message(self, values):
        action = (
            self.service.add_student_message
            if self.role == AuthorRole.STUDENT
            else self.service.add_teacher_message
        )
        self.saved_message = action(self.case_id, **values)

    def submit(self):
        if not self.body.toPlainText().strip():
            self.error_label.setText(TEXT["question_body_required"])
            return
        super().submit()


class QuestionCaptureDialog(MessageCaptureDialog):
    def __init__(self, service, *, student_id=None, offering_id=None, parent=None):
        super().__init__(service, None, AuthorRole.STUDENT, parent=parent)
        self.setWindowTitle(TEXT["new_question"])
        resize_to_screen(self, 640, 770)
        self.student = QComboBox()
        for value in service.list_students():
            self.student.addItem(value.full_name, value.id)
        if student_id is not None:
            select_data(self.student, student_id)
            self.student.setEnabled(False)
        self.form.insertRow(0, TEXT["full_name"], self.student)
        self.offering = QComboBox()
        self.offering.addItem(TEXT["question_no_offering"], None)
        for value in service.list_offerings():
            self.offering.addItem(context_label(value), value.offering.id)
        if offering_id is not None:
            select_data(self.offering, offering_id)
        self.form.insertRow(1, TEXT["course"], self.offering)
        self.title = QLineEdit()
        self.form.insertRow(2, TEXT["question_title"], self.title)
        self.context_fields = {}
        for kind, label in QUESTION_CONTEXT_LABELS.items():
            field = QListWidget()
            field.setMaximumHeight(70)
            self.form.addRow(label, field)
            self.context_fields[kind] = field
        self.offering.currentIndexChanged.connect(lambda _: run_action(self, self.refresh_choices))
        self.student.currentIndexChanged.connect(lambda _: run_action(self, self.refresh_choices))
        self.refresh_choices()
        self.on_save = self.save_question

    def refresh_choices(self):
        attempt_titles = (
            self.service.question_attempt_titles(
                self.student.currentData(), self.offering.currentData()
            )
            if self.student.currentData()
            else {}
        )
        choices = (
            self.service.capture_context_choices(
                self.student.currentData(), self.offering.currentData()
            )
            if self.student.currentData()
            else {k: [] for k in self.context_fields}
        )
        for kind, field in self.context_fields.items():
            field.clear()
            for value in choices[kind]:
                item = QListWidgetItem(context_name(value, attempt_titles))
                item.setData(Qt.ItemDataRole.UserRole, value.id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                field.addItem(item)

    def save_question(self, values):
        context = {
            kind: [
                field.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(field.count())
                if field.item(i).checkState() == Qt.CheckState.Checked
            ]
            for kind, field in self.context_fields.items()
        }
        self.saved_case = self.service.create_question_case(
            self.student.currentData(),
            **values,
            course_offering_id=self.offering.currentData(),
            title=self.title.text(),
            context=context,
        )

    def submit(self):
        if self.student.currentData() is None:
            self.error_label.setText(TEXT["question_student_required"])
            return
        super().submit()


class MessageModel(TableModel):
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.BackgroundRole:
            from studium.presentation.desktop.theme import theme_color

            student = self.rows[index.row()].author_role == AuthorRole.STUDENT
            return theme_color(
                "#e8f0fa" if student else "#edf5ec", "#273a52" if student else "#263e36"
            )
        return super().data(index, role)


class QuestionCaseDialog(QDialog):
    def __init__(self, service, case_id, parent=None, *, asynchronous=False):
        super().__init__(parent)
        self.service, self.case_id = service, case_id
        self.asynchronous, self.attachment_generation = asynchronous, 0
        self.setWindowTitle(TEXT["question_case"])
        resize_to_screen(self, 1060, 850)
        layout = QVBoxLayout(self)
        self.heading = hint(layout, "")
        self.attempt_titles = {}
        self.heading.setTextFormat(Qt.TextFormat.PlainText)
        self.context_model = TableModel(
            [
                (TEXT["type"], lambda r: QUESTION_CONTEXT_LABELS[r[0]]),
                (TEXT["question_context"], lambda r: context_name(r[2], self.attempt_titles)),
            ]
        )
        self.context_view = table(self.context_model)
        self.context_view.setMaximumHeight(160)
        layout.addWidget(self.context_view)
        self.kind = QComboBox()
        for kind, label in QUESTION_CONTEXT_LABELS.items():
            self.kind.addItem(label, kind)
        self.target = QComboBox()
        form = QFormLayout()
        form.addRow(self.kind, self.target)
        layout.addLayout(form)
        self.kind.currentIndexChanged.connect(lambda _: run_action(self, self.refresh_targets))
        toolbar(
            layout,
            [
                (TEXT["question_link"], lambda: run_action(self, self.attach_context)),
                (TEXT["question_unlink"], lambda: run_action(self, self.detach_context)),
                (TEXT["question_open_work"], lambda: run_action(self, self.open_context_work)),
            ],
        )
        self.message_model = MessageModel(
            [
                (TEXT["author"], lambda m: AUTHOR_LABELS[m.author_role]),
                (TEXT["sent_at"], lambda m: display_time(m.sent_at)),
                (TEXT["channel"], lambda m: CHANNEL_LABELS[m.channel]),
                (TEXT["message"], lambda m: " ".join(m.body.splitlines())),
            ]
        )
        self.message_view = table(self.message_model)
        self.message_view.setMaximumHeight(125)
        layout.addWidget(self.message_view)
        self.body = QPlainTextEdit()
        self.body.setReadOnly(True)
        self.body.setMinimumHeight(110)
        layout.addWidget(self.body, 1)
        self.drop_zone = FileDropZone(self)
        self.drop_zone.pathsDropped.connect(self.import_paths)
        layout.addWidget(self.drop_zone)
        self.attachment_model = TableModel(
            [
                (TEXT["file_name"], lambda e: e.asset.original_filename),
                (TEXT["type"], lambda e: e.asset.mime_type),
                (TEXT["status"], lambda e: FILE_LABELS[e.integrity]),
            ]
        )
        self.attachment_view = table(self.attachment_model)
        self.attachment_view.setMaximumHeight(100)
        self.attachment_notice = hint(layout, "")
        self.attachment_notice.hide()
        layout.addWidget(self.attachment_view)
        self.attachment_view.doubleClicked.connect(
            lambda _: run_action(self, self.preview_attachment)
        )
        toolbar(
            layout,
            [
                (TEXT["file_add"], lambda: run_action(self, self.pick_files)),
                (TEXT["file_view"], lambda: run_action(self, self.preview_attachment)),
                (TEXT["file_detach"], lambda: run_action(self, self.detach_attachment)),
            ],
        )
        toolbar(
            layout,
            [
                (
                    TEXT["student_message"],
                    lambda: run_action(self, lambda: self.add_message(AuthorRole.STUDENT)),
                ),
                (
                    TEXT["teacher_message"],
                    lambda: run_action(self, lambda: self.add_message(AuthorRole.TEACHER)),
                ),
            ],
        )
        self.close_button = QPushButton()
        toolbar(
            layout,
            [
                ("Добавить в базу знаний", lambda: run_action(self, self.add_to_knowledge)),
                (
                    "Привязать к записи базы знаний",
                    lambda: run_action(self, self.link_to_knowledge),
                ),
            ],
        )
        self.close_button.clicked.connect(lambda: run_action(self, self.toggle_closed))
        layout.addWidget(self.close_button)
        toolbar(
            layout,
            [
                (TEXT["question_archive"], lambda: run_action(self, self.archive)),
                (TEXT["file_refresh"], lambda: run_action(self, self.refresh)),
            ],
        )
        self.message_view.selectionModel().currentChanged.connect(
            lambda *_: run_action(self, self.show_message)
        )
        self.refresh()

    def add_to_knowledge(self):
        from studium.presentation.desktop.programs import KnowledgeForm

        KnowledgeForm(self.service, case_id=self.case_id, parent=self).exec()

    def link_to_knowledge(self):
        from studium.presentation.desktop.dialogs import ChoiceDialog

        if self.case.course_offering_id:
            program = self.service.program_for_offering(self.case.course_offering_id)
            course_id = (
                program.course_id
                if program
                else next(
                    c.course.id
                    for c in self.service.list_offerings()
                    if c.offering.id == self.case.course_offering_id
                )
            )
            values = self.service.list_knowledge_entries(course_id)
            ChoiceDialog(
                "База знаний",
                "Выберите запись",
                [(v.id, v.title) for v in values],
                lambda id: self.service.link_knowledge_case(id, self.case_id),
                self,
            ).exec()

    def refresh(self):
        self.case = self.service.get_question_case(self.case_id)
        entry = next(
            q
            for q in self.service.list_student_question_cases(self.case.student_id)
            if q.case.id == self.case_id
        )
        self.heading.setText(
            f"{entry.student.full_name} · {entry.group_number} · {entry.course_name} · {entry.term_name}\n{entry.preview}\n{COMMUNICATION_STATES[entry.state]}"
        )
        self.attempt_titles = self.service.question_attempt_titles(
            self.case.student_id, self.case.course_offering_id
        )
        self.close_button.setText(
            TEXT["question_reopen"] if self.case.closed_at else TEXT["question_close"]
        )
        self.context_model.replace_rows(
            [
                (kind, link, value)
                for kind, pairs in self.service.list_question_context(self.case_id).items()
                for link, value in pairs
            ]
        )
        self.choices = self.service.question_context_choices(self.case_id)
        self.refresh_targets()
        self.message_model.replace_rows(self.service.list_messages(self.case_id))
        self.body.clear()
        self.attachment_model.replace_rows([])
        if self.message_model.rows:
            self.message_view.selectRow(len(self.message_model.rows) - 1)

    def refresh_targets(self):
        self.target.clear()
        for value in self.choices[self.kind.currentData()]:
            self.target.addItem(context_name(value, self.attempt_titles), value.id)

    def show_message(self):
        index = self.message_view.currentIndex()
        self.current_message = self.message_model.rows[index.row()] if index.isValid() else None
        self.body.setPlainText(self.current_message.body if self.current_message else "")
        self.drop_zone.setEnabled(self.current_message is not None)
        self.attachment_generation += 1
        generation = self.attachment_generation
        self.attachment_model.replace_rows([])
        self.attachment_notice.hide()
        if self.current_message:
            message_id = self.current_message.id
            if self.asynchronous:
                self.attachment_notice.setText(TEXT["files_loading"])
                self.attachment_notice.show()
                BackgroundCall(
                    self,
                    lambda: self.service.list_message_attachments(message_id),
                    lambda rows: self.apply_attachments(rows, generation),
                    lambda error: self.attachment_error(error, generation),
                )
            else:
                self.attachment_model.replace_rows(
                    self.service.list_message_attachments(message_id)
                )

    def apply_attachments(self, rows, generation):
        if generation == self.attachment_generation:
            self.attachment_model.replace_rows(rows)
            self.attachment_notice.hide()

    def attachment_error(self, error, generation):
        if generation == self.attachment_generation:
            from studium.presentation.desktop.messages import error_message

            self.attachment_notice.setText(error_message(error))

    def add_message(self, role):
        channel = (
            self.current_message.channel if self.current_message else CommunicationChannel.MANUAL
        )
        dialog = MessageCaptureDialog(
            self.service, self.case_id, role, channel=channel, parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def toggle_closed(self):
        action = (
            self.service.reopen_question_case
            if self.case.closed_at
            else self.service.close_question_case
        )
        action(self.case)
        self.refresh()

    def archive(self):
        if confirm(self, TEXT["question_archive_confirm"], action_label=TEXT["question_archive"]):
            self.service.archive_question_case(self.case)
            self.accept()

    def attach_context(self):
        if self.target.currentData():
            self.service.attach_question_context(
                self.case_id, self.kind.currentData(), self.target.currentData()
            )
            self.refresh()

    def detach_context(self):
        row = selected(self.context_view)
        if row:
            self.service.detach_question_context(row[1], row[0])
            self.refresh()

    def open_context_work(self):
        from studium.presentation.desktop.dialogs import HistoryDialog, open_work

        row = selected(self.context_view)
        if row and row[0] == "attempt":
            present_detail(
                HistoryDialog(
                    self.service,
                    row[2].student_work_id,
                    editable=False,
                    parent=self,
                    asynchronous=True,
                ),
                self,
                refresh=getattr(self, "refresh", None),
            )
        elif row and row[0] == "assessment":
            work = self.service.question_work_for_assessment(self.case_id, row[2].id)
            if work:
                present_detail(
                    HistoryDialog(
                        self.service, work.id, editable=False, parent=self, asynchronous=True
                    ),
                    self,
                    refresh=getattr(self, "refresh", None),
                )
            else:
                open_work(self, self.service, self.case.student_id, row[2].id)

    def pick_files(self):
        if self.current_message:
            paths, _ = QFileDialog.getOpenFileNames(
                self, TEXT["file_add"], "", TEXT["file_picker_filter"]
            )
            self.import_paths(paths)

    def import_paths(self, paths):
        if self.current_message:
            if self.asynchronous and paths:
                message_id = self.current_message.id
                self.drop_zone.setEnabled(False)
                self.attachment_notice.setText("Импорт файлов…")
                self.attachment_notice.show()

                def batch():
                    for path in paths:
                        self.service.import_file_for_message(message_id, path)

                def completed(_):
                    self.show_message()

                def failed(error):
                    from studium.presentation.desktop.messages import error_message

                    self.show_message()
                    self.attachment_notice.setText(error_message(error))
                    self.attachment_notice.show()

                BackgroundCall(self, batch, completed, failed)
                return
            for path in paths:
                run_action(
                    self,
                    lambda path=path: self.service.import_file_for_message(
                        self.current_message.id, path
                    ),
                )
            self.show_message()

    def preview_attachment(self):
        entry = selected(self.attachment_view)
        if entry:
            present_detail(
                FilePreviewDialog(self.service, entry, self, asynchronous=True),
                self,
                title=entry.asset.original_filename,
            )

    def detach_attachment(self):
        entry = selected(self.attachment_view)
        if entry and confirm(self, TEXT["file_detach_confirm"], action_label=TEXT["file_detach"]):
            self.service.detach_message_attachment(
                entry.attachment.id, expected_revision=entry.attachment.revision
            )
            self.show_message()


class QuestionsWidget(QWidget):
    def __init__(
        self,
        service=None,
        *,
        student_id=None,
        offering_id=None,
        assessment_id=None,
        attempt_id=None,
        parent=None,
    ):
        super().__init__(parent)
        self.service, self.student_id, self.offering_id = service, student_id, offering_id
        self.assessment_id = assessment_id
        self.attempt_id = attempt_id
        layout = QVBoxLayout(self)
        self.waiting_label = hint(layout, "")
        self.waiting_label.setProperty("role", "notice")
        hint(layout, TEXT["questions_scope"])
        self.search = QLineEdit()
        self.search.setPlaceholderText(TEXT["questions_search"])
        layout.addWidget(self.search)
        search_shortcut(self, self.search)
        self.state = QComboBox()
        self.state.addItem(TEXT["questions_all"], None)
        for state, label in COMMUNICATION_STATES.items():
            self.state.addItem(label, state)
        layout.addWidget(self.state)
        self.model = QuestionTableModel(
            [
                (TEXT["sent_at"], lambda q: display_time(q.case.opened_at)),
                (TEXT["full_name"], lambda q: q.student.full_name),
                (TEXT["group"], lambda q: q.group_number),
                (TEXT["course"], lambda q: q.course_name),
                (TEXT["question_title"], lambda q: " ".join(q.preview.splitlines())),
                (TEXT["channel"], lambda q: CHANNEL_LABELS[q.channel]),
                (TEXT["status"], lambda q: COMMUNICATION_STATES[q.state]),
            ]
        )
        if student_id is not None:
            self.model.columns = [self.model.columns[i] for i in (0, 4, 3, 6, 5)]
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        self.empty = hint(layout, TEXT["questions_empty"])
        toolbar(
            layout,
            [
                (TEXT["new_question"], lambda: run_action(self, self.create_question)),
                (TEXT["open"], lambda: run_action(self, self.open_question)),
                (TEXT["file_refresh"], lambda: run_action(self, self.refresh)),
            ],
        )
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open_question))
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(lambda: run_action(self, self.refresh))
        self.search.textChanged.connect(lambda _: self.search_timer.start())
        self.state.currentIndexChanged.connect(lambda _: run_action(self, self.refresh))
        self.refresh()

    def refresh(self):
        if self.service:
            self.search_timer.stop()
            self.model.replace_rows(
                self.service.list_question_cases(
                    student_id=self.student_id,
                    state=self.state.currentData(),
                    search=self.search.text(),
                    assessment_id=self.assessment_id,
                    attempt_id=self.attempt_id,
                )
            )
            waiting = sum(q.state == CommunicationState.WAITING for q in self.model.rows)
            self.waiting_label.setText(TEXT["waiting_count"].format(count=waiting))
            self.waiting_label.setVisible(bool(waiting))
            self.empty.setVisible(not self.model.rows)

    def create_question(self):
        dialog = QuestionCaptureDialog(
            self.service, student_id=self.student_id, offering_id=self.offering_id, parent=self
        )
        if self.assessment_id:
            field = dialog.context_fields["assessment"]
            for i in range(field.count()):
                item = field.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == self.assessment_id:
                    item.setCheckState(Qt.CheckState.Checked)
        if self.attempt_id:
            field = dialog.context_fields["attempt"]
            for i in range(field.count()):
                if field.item(i).data(Qt.ItemDataRole.UserRole) == self.attempt_id:
                    field.item(i).setCheckState(Qt.CheckState.Checked)
        if main_window(self):

            def open_created():
                case_id = dialog.saved_case.id
                QTimer.singleShot(
                    0,
                    lambda: present_detail(
                        QuestionCaseDialog(self.service, case_id, self, asynchronous=True),
                        self,
                        refresh=self.refresh,
                    ),
                )

            dialog.accepted.connect(open_created)
            present_detail(dialog, self, refresh=self.refresh)
        elif dialog.exec() == QDialog.DialogCode.Accepted:
            present_detail(
                QuestionCaseDialog(self.service, dialog.saved_case.id, self, asynchronous=True),
                self,
                refresh=self.refresh,
            )

    def open_question(self):
        entry = selected(self.view)
        if entry:
            present_detail(
                QuestionCaseDialog(self.service, entry.case.id, self, asynchronous=True),
                self,
                refresh=self.refresh,
                title=entry.case.title or "Вопрос",
            )


class QuestionTableModel(TableModel):
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and self.rows[index.row()].state == CommunicationState.WAITING:
            if role == Qt.ItemDataRole.BackgroundRole:
                from studium.presentation.desktop.theme import theme_color

                return theme_color("#fff7e7", "#443c2a")
        return super().data(index, role)
