"""Standard Qt forms and read-only student/attempt detail dialogs."""

from PySide6.QtCore import QDate, QDateTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.application.services import ApplicationError, GradeInput
from studium.domain.enums import AssessmentType, AttemptResult, GradeKind
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.components import (
    confirm,
    confirm_delete,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.files import FilesWidget
from studium.presentation.desktop.messages import (
    ASSESSMENT_LABELS,
    ATTEMPT_LABELS,
    GRADE_LABELS,
    TEXT,
)
from studium.presentation.desktop.models import (
    AttemptHistoryModel,
    TableModel,
    display_score,
    display_time,
    progress_text,
)
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.theme import resize_to_screen
from studium.presentation.desktop.visuals import Disclosure, advanced_rows, text_label
from studium.presentation.desktop.workflow_widgets import WeekSelector, direct_calendar


def number_value(field):
    text = field.text().strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        raise ApplicationError("invalid_number") from None


def date_value(field):
    value = field.date()
    return LocalDate(value.year(), value.month(), value.day())


def instant_value(field):
    return UtcInstant.from_epoch_microseconds(field.dateTime().toMSecsSinceEpoch() * 1000)


def combo(mapping, selected_value=None):
    field = QComboBox()
    for value, label in mapping.items():
        field.addItem(label, value)
    if selected_value is not None:
        field.setCurrentIndex(max(0, field.findData(selected_value)))
    return field


class FormDialog(QDialog):
    def __init__(self, title, on_save, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.on_save = on_save
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(16)
        outer.addWidget(text_label(title, "subheading"))
        scroll = QScrollArea()
        self.scroll = scroll
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.body_layout = QVBoxLayout(content)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.resize(600, 530)
        self.form = QFormLayout()
        self.form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.form.setVerticalSpacing(12)
        self.body_layout.addLayout(self.form)
        self.error_label = QLabel()
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.body_layout.addWidget(self.error_label)
        self.required = []
        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton(TEXT["save"], QDialogButtonBox.ButtonRole.AcceptRole)
        self.save_button.setProperty("primary", True)
        self.save_button.setDefault(True)
        buttons.addButton(TEXT["cancel"], QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def line(self, key, value="", *, required=False):
        field = QLineEdit(value or "")
        self.form.addRow(TEXT[key] + (" *" if required else ""), field)
        if required:
            self.required.append((key, field))
        return field

    def notes(self, key, value=""):
        field = QPlainTextEdit(value)
        field.setMaximumHeight(110)
        self.form.addRow(TEXT[key], field)
        return field

    def day(self, key, value=None):
        field = QDateEdit(
            QDate(value.year, value.month, value.day) if value else QDate.currentDate()
        )
        field.setCalendarPopup(True)
        direct_calendar(field)
        field.setDisplayFormat("dd.MM.yyyy")
        self.form.addRow(TEXT[key], field)
        return field

    def timestamp(self, key, value=None, *, optional=False):
        field = QDateTimeEdit(
            QDateTime.fromMSecsSinceEpoch(value.epoch_microseconds // 1000)
            if value
            else QDateTime.currentDateTime()
        )
        field.setCalendarPopup(True)
        direct_calendar(field)
        field.setDisplayFormat("dd.MM.yyyy HH:mm")
        if optional:
            enabled = QCheckBox(TEXT[key])
            enabled.setChecked(value is not None)
            field.setEnabled(enabled.isChecked())
            enabled.toggled.connect(field.setEnabled)
            self.form.addRow(enabled, field)
            return field, enabled
        self.form.addRow(TEXT[key], field)
        return field

    def submit(self):
        for key, field in self.required:
            if not field.text().strip():
                self.error_label.setText(TEXT["required"].format(field=TEXT[key]))
                field.setFocus()
                return
        self.error_label.clear()

        def save():
            self.on_save(self.values())
            return True

        if run_action(self, save):
            self.accept()

    def values(self):
        raise NotImplementedError

    def advanced(self, fields):
        disclosure = advanced_rows(self.form, fields)
        self.body_layout.addWidget(disclosure)
        return disclosure


class TermDialog(FormDialog):
    def __init__(self, on_save, original=None, parent=None):
        super().__init__(TEXT["edit_period" if original else "new_period"], on_save, parent)
        self.name = self.line("name", original.name if original else "", required=True)
        self.start = self.day("starts_on", original.starts_on if original else None)
        self.end = self.day("ends_on", original.ends_on if original else None)
        self.week_timezone = QComboBox()
        for offset in range(-840, 841, 15):
            sign = "+" if offset >= 0 else "−"
            self.week_timezone.addItem(
                f"UTC{sign}{abs(offset) // 60:02d}:{abs(offset) % 60:02d}", offset
            )
        self.week_timezone.setCurrentIndex(
            self.week_timezone.findData(original.week_utc_offset_minutes if original else 180)
        )
        self.form.addRow("Часовой пояс учебных недель", self.week_timezone)
        self.advanced((self.week_timezone,))

    def values(self):
        return dict(
            name=self.name.text().strip(),
            starts_on=date_value(self.start),
            ends_on=date_value(self.end),
            week_utc_offset_minutes=self.week_timezone.currentData(),
        )


class CourseDialog(FormDialog):
    def __init__(self, on_save, original=None, parent=None):
        super().__init__(TEXT["edit_course" if original else "new_course"], on_save, parent)
        self.name = self.line("name", original.name if original else "", required=True)
        self.short = self.line("short_name", original.short_name if original else "")
        self.description = self.notes("description", original.description if original else "")

    def values(self):
        return dict(
            name=self.name.text().strip(),
            short_name=self.short.text().strip(),
            description=self.description.toPlainText().strip(),
        )


class GroupDialog(FormDialog):
    def __init__(self, on_save, original=None, parent=None):
        super().__init__(TEXT["edit_group" if original else "new_group"], on_save, parent)
        self.number = self.line("number", original.number if original else "", required=True)
        self.department = self.line("department", original.department if original else "")
        self.faculty = QLineEdit(original.faculty if original else "")
        self.faculty_short = QLineEdit(original.faculty_short if original else "")
        self.form.addRow("Факультет", self.faculty)
        self.form.addRow("Сокращение факультета", self.faculty_short)
        self.note = self.notes("notes", original.notes if original else "")

    def values(self):
        return dict(
            number=self.number.text().strip(),
            department=self.department.text().strip(),
            faculty=self.faculty.text().strip(),
            faculty_short=self.faculty_short.text().strip(),
            notes=self.note.toPlainText().strip(),
        )


class StudentDialog(FormDialog):
    def __init__(self, on_save, original=None, parent=None):
        super().__init__(TEXT["edit_student" if original else "new_student"], on_save, parent)
        self.full_name = self.line(
            "full_name", original.full_name if original else "", required=True
        )
        self.preferred = self.line("preferred_name", original.preferred_name if original else "")
        self.note = self.notes("notes", original.notes if original else "")

    def values(self):
        return dict(
            full_name=self.full_name.text().strip(),
            preferred_name=self.preferred.text().strip() or None,
            notes=self.note.toPlainText().strip(),
        )


class ChoiceDialog(FormDialog):
    def __init__(self, title, label, choices, on_save, parent=None):
        super().__init__(title, on_save, parent)
        self.choice = QComboBox()
        for id, text in choices:
            self.choice.addItem(text, id)
        self.form.addRow(label, self.choice)
        self.save_button.setEnabled(bool(choices))

    def values(self):
        return self.choice.currentData()


class AssessmentDialog(FormDialog):
    def __init__(self, on_save, original=None, parent=None, *, program=None):
        super().__init__(TEXT["edit_assessment" if original else "new_assessment"], on_save, parent)
        self.title = self.line(
            "assessment_title", original.title if original else "", required=True
        )
        self.type = combo(ASSESSMENT_LABELS, original.type if original else None)
        self.form.addRow(TEXT["type"], self.type)
        self.number = self.line("work_number", original.number if original else "")
        self.issue_week = WeekSelector(
            original.planned_issue_week if original else None,
            weeks=program.weeks if program else 17,
        )
        self.due_week = WeekSelector(
            original.planned_due_week if original else None, weeks=program.weeks if program else 17
        )
        self.form.addRow("Неделя выдачи", self.issue_week)
        self.form.addRow("Неделя сдачи", self.due_week)
        self.issued, self.issued_enabled = self.timestamp(
            "issued_at", original.issued_at if original else None, optional=True
        )
        self.due, self.due_enabled = self.timestamp(
            "due_at", original.due_at if original else None, optional=True
        )
        if program:

            def constrain(selector, field):
                week = selector.currentData()
                if week:
                    first, last = program.week_dates(week)
                    field.setDateRange(
                        QDate(first.year, first.month, first.day),
                        QDate(last.year, last.month, last.day),
                    )
                else:
                    field.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))

            for selector, field in ((self.issue_week, self.issued), (self.due_week, self.due)):
                selector.currentIndexChanged.connect(
                    lambda _, selector=selector, field=field: constrain(selector, field)
                )
                if original is None:
                    constrain(selector, field)
        self.maximum = self.line(
            "max_score",
            str(original.max_score) if original and original.max_score is not None else "",
        )
        self.maximum.setPlaceholderText(TEXT["score_hint"])
        self.note = self.notes("work_notes", original.description if original else "")
        hint(self.body_layout, TEXT["issue_hint"])
        hint(self.body_layout, TEXT["local_time"])
        self.advanced((self.issued, self.due, self.maximum, self.note))

    def values(self):
        return dict(
            title=self.title.text().strip(),
            type=self.type.currentData(),
            number=self.number.text().strip() or None,
            planned_issue_week=self.issue_week.currentData(),
            planned_due_week=self.due_week.currentData(),
            issued_at=instant_value(self.issued) if self.issued_enabled.isChecked() else None,
            due_at=instant_value(self.due) if self.due_enabled.isChecked() else None,
            max_score=number_value(self.maximum),
            description=self.note.toPlainText().strip(),
        )


class AttemptDialog(FormDialog):
    def __init__(self, on_save, max_score=None, parent=None, *, assessment_type=None):
        super().__init__(TEXT["new_attempt"], on_save, parent)
        self.occurred = self.timestamp("occurred_at")
        self.result_combo = combo(ATTEMPT_LABELS)
        if assessment_type == AssessmentType.HOMEWORK:
            self.result_combo.removeItem(self.result_combo.findData(AttemptResult.REJECTED))
        self.form.addRow(TEXT["result"], self.result_combo)
        self.comment = self.notes("comment")
        self.score = self.line("score")
        self.maximum = self.line("max_score", str(max_score) if max_score is not None else "")
        self.score.setPlaceholderText(TEXT["score_hint"])
        self.grade_kind = QComboBox()
        self.grade_kind.addItem(TEXT["no_grade"], None)
        for kind, label in GRADE_LABELS.items():
            self.grade_kind.addItem(label, kind)
        self.form.addRow(TEXT["grade"], self.grade_kind)
        self.passed = QComboBox()
        self.passed.addItem(TEXT["pass"], True)
        self.passed.addItem(TEXT["fail"], False)
        self.form.addRow(TEXT["grade"], self.passed)
        self.label = self.line("grade_label")
        self.grade_labels = {
            field: self.form.labelForField(field) for field in (self.passed, self.label)
        }
        self.grade_kind.currentIndexChanged.connect(self.grade_changed)
        self.grade_changed()
        hint(self.body_layout, TEXT["history_hint"])
        hint(self.body_layout, TEXT["progress_hint"])
        hint(self.body_layout, TEXT["local_time"])

    def grade_changed(self):
        for field, visible in (
            (self.passed, self.grade_kind.currentData() == GradeKind.PASS_FAIL),
            (self.label, self.grade_kind.currentData() == GradeKind.TRADITIONAL),
        ):
            field.setVisible(visible)
            label = self.grade_labels.get(field)
            if label:
                label.setVisible(visible)

    def values(self):
        kind = self.grade_kind.currentData()
        grade = (
            GradeInput(
                kind,
                passed=self.passed.currentData() if kind == GradeKind.PASS_FAIL else None,
                label=self.label.text().strip() if kind == GradeKind.TRADITIONAL else None,
            )
            if kind
            else None
        )
        return dict(
            occurred_at=instant_value(self.occurred),
            result=self.result_combo.currentData(),
            comment=self.comment.toPlainText().strip(),
            score=number_value(self.score),
            max_score=number_value(self.maximum),
            grade=grade,
        )


class HistoryDialog(QDialog):
    def __init__(self, service, work_id, *, editable=True, asynchronous=False, parent=None):
        super().__init__(parent)
        self.service, self.work_id = service, work_id
        self.editable = editable
        self.setWindowTitle(TEXT["history"])
        resize_to_screen(self, 1080, 800)
        layout = QVBoxLayout(self)
        self.heading = hint(layout, "")
        self.work_title = hint(layout, "")
        self.work_title.setProperty("role", "subheading")
        self.summary = hint(layout, "")
        self.model = AttemptHistoryModel()
        self.view = table(self.model, stretch=False)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open_attempt))
        self.view.setMinimumHeight(120)
        for i, width in enumerate([45, 140, 150, 280, 90, 120]):
            self.view.setColumnWidth(i, width)
        self.history_split = QSplitter(Qt.Orientation.Vertical)
        self.history_split.setChildrenCollapsible(False)
        history_area = QWidget()
        history_area.setMaximumHeight(280)
        history_layout = QVBoxLayout(history_area)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.addWidget(text_label("История попыток", "subheading"))
        history_layout.addWidget(self.view)
        self.history_split.addWidget(history_area)
        layout.addWidget(self.history_split, 1)
        details = QWidget()
        detail_layout = QVBoxLayout(details)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        self.attempt_caption = text_label("", "subheading")
        detail_layout.addWidget(self.attempt_caption)
        self.comment = QPlainTextEdit()
        self.comment.setReadOnly(True)
        self.comment.setMaximumHeight(64)
        detail_layout.addWidget(self.comment)
        from studium.presentation.desktop.analytics import AttemptItemsWidget

        assessment_id = service.history(work_id).assessment.id
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setMinimumHeight(250)
        self.files = FilesWidget(service, editable=editable, asynchronous=asynchronous, parent=self)
        self.detail_tabs.addTab(self.files, TEXT["files"])
        self.item_results = AttemptItemsWidget(
            service, assessment_id, editable=editable, parent=self.detail_tabs
        )
        if service.list_assessment_items(assessment_id, historical=True):
            self.detail_tabs.addTab(self.item_results, TEXT["item_results"])
        else:
            self.item_results.hide()
        self.attachments_disclosure = Disclosure("Файлы и результаты попытки", self.detail_tabs)
        self.attachments_disclosure.toggle.toggled.connect(
            lambda shown: self.history_split.setSizes(
                [180 if shown else 280, 480 if shown else 220]
            )
        )
        detail_layout.addWidget(self.attachments_disclosure)
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setMinimumHeight(140)
        detail_scroll.setWidget(details)
        self.history_split.addWidget(detail_scroll)
        self.history_split.setStretchFactor(0, 2)
        self.history_split.setStretchFactor(1, 1)
        self.view.selectionModel().currentChanged.connect(
            lambda *args: run_action(self, lambda: self.show_comment(*args))
        )
        self.empty = hint(layout, TEXT["empty_history"])
        button = QPushButton(TEXT["new_attempt"])
        button.setProperty("primary", True)
        button.setEnabled(editable)
        button.clicked.connect(lambda: run_action(self, self.add_attempt))
        layout.insertWidget(3, button, 0, Qt.AlignmentFlag.AlignLeft)
        if not editable:
            hint(layout, TEXT["read_only"])
        self.refresh()

    def refresh(self):
        self.history = self.service.history(self.work_id)
        self.heading.setText(self.history.student.full_name)
        self.work_title.setText(self.history.assessment.title)
        self.heading.setProperty("role", "heading")
        p = self.history.progress
        self.summary.setText(
            f"{progress_text(p)} · {TEXT['attempts']}: {p.attempt_count} · {TEXT['score']}: {display_score(p.final_score)}"
        )
        self.model.replace_rows(self.history.entries)
        self.empty.setVisible(not self.history.entries)
        self.comment.clear()
        self.files.set_attempt(None)
        self.attachments_disclosure.setVisible(bool(self.history.entries))
        self.attempt_caption.clear()
        self.item_results.set_attempt(None)
        if self.history.entries:
            self.view.selectRow(0)

    def show_comment(self, index, _previous):
        if index.isValid():
            attempt = self.model.rows[index.row()].attempt
            self.attempt_caption.setText(
                f"Попытка {attempt.attempt_no} · {ATTEMPT_LABELS[attempt.result]} · {display_time(attempt.occurred_at)}"
            )
            self.comment.setPlainText(attempt.comment)
            self.files.set_attempt(attempt)
            self.item_results.set_attempt(attempt)

    def add_attempt(self):
        dialog = AttemptDialog(
            lambda values: self.service.add_attempt(self.work_id, **values),
            self.history.assessment.max_score,
            self,
            assessment_type=self.history.assessment.type,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def open_attempt(self):
        entry = selected(self.view)
        if entry:
            page = AttemptDetailsPage(
                self.service, self.history, entry.attempt, editable=self.editable
            )
            from studium.presentation.desktop.navigation import main_window

            window = main_window(self)
            if window:
                window.router.routes[-1].refresh = self.refresh
                window.router.push(page, f"Попытка {entry.attempt.attempt_no}")


class AttemptDetailsPage(QWidget):
    def __init__(self, service, history, attempt, *, editable=True):
        super().__init__()
        layout = QVBoxLayout(self)
        hint(
            layout, f"Попытка {attempt.attempt_no} · {ATTEMPT_LABELS[attempt.result]}"
        ).setProperty("role", "heading")
        hint(
            layout,
            f"{history.student.full_name}\n{history.assessment.title} · {display_time(attempt.occurred_at)}",
        )
        comment = QPlainTextEdit(attempt.comment)
        comment.setReadOnly(True)
        comment.setMaximumHeight(120)
        layout.addWidget(comment)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.files = FilesWidget(service, editable=editable, asynchronous=True, parent=self)
        self.files.set_attempt(attempt)
        self.tabs.addTab(self.files, TEXT["files"])
        from studium.presentation.desktop.analytics import AttemptItemsWidget

        self.items = AttemptItemsWidget(
            service, history.assessment.id, editable=editable, parent=self
        )
        self.items.set_attempt(attempt)
        self.tabs.addTab(self.items, TEXT["item_results"])
        from studium.presentation.desktop.communication import QuestionsWidget

        self.questions = QuestionsWidget(
            service,
            student_id=history.student.id,
            offering_id=history.context.offering.id,
            assessment_id=history.assessment.id,
            attempt_id=attempt.id,
            parent=self,
        )
        self.tabs.addTab(self.questions, TEXT["questions"])


def open_work(parent, service, student_id, assessment_id, *, editable=True):
    work = service.get_or_create_work(student_id, assessment_id)
    present_detail(
        HistoryDialog(service, work.id, editable=editable, asynchronous=True, parent=parent),
        parent,
        refresh=getattr(parent, "refresh_works", getattr(parent, "refresh", None)),
        title=service.history(work.id).assessment.title,
    )


class StudentDetailsDialog(QDialog):
    def __init__(self, service, context, entry, parent=None):
        super().__init__(parent)
        self.service, self.context, self.entry = service, context, entry
        self.student = entry.student
        self.setWindowTitle(TEXT["student_card"])
        resize_to_screen(self, 1100, 760)
        self.setMinimumSize(800, 570)
        layout = QVBoxLayout(self)
        self.name_label = hint(layout, self.student.full_name)
        self.name_label.setProperty("role", "heading")
        hint(layout, f"{context.group.number} · {context.course.name}\n{context.term.name}")
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        hint(overview_layout, TEXT["notes"])
        self.notes = QPlainTextEdit(self.student.notes)
        self.notes.setReadOnly(True)
        self.notes.setMaximumHeight(150)
        overview_layout.addWidget(self.notes)
        self.overview_summary = hint(overview_layout, "")
        self.activity_label = hint(overview_layout, "")
        overview_layout.addStretch()
        toolbar(
            overview_layout,
            [
                (TEXT["edit"], lambda: run_action(self, self.edit_student)),
                (TEXT["student_hide"], lambda: run_action(self, self.hide_student)),
            ],
        )
        self.tabs.addTab(overview, TEXT["overview"])
        from studium.presentation.desktop.student_works import StudentWorksWidget

        self.works = StudentWorksWidget(service, context, entry, self)
        self.work_model, self.work_view = self.works.work_model, self.works.work_view
        self.tabs.addTab(self.works, TEXT["works"])
        from studium.presentation.desktop.analytics import StudentProgressWidget

        self.progress = StudentProgressWidget(service, self.student.id, context.offering.id, self)
        self.tabs.addTab(self.progress, TEXT["progress"])
        self.files = FilesWidget(
            service, student_id=self.student.id, lazy=True, asynchronous=True, parent=self
        )
        self.tabs.addTab(self.files, TEXT["files"])
        from studium.presentation.desktop.communication import QuestionsWidget

        self.questions = QuestionsWidget(
            service, student_id=self.student.id, offering_id=context.offering.id, parent=self
        )
        self.tabs.addTab(self.questions, TEXT["questions"])
        self.tabs.currentChanged.connect(self.refresh_progress)
        self.refresh_works()
        self.refresh_overview()

    def refresh_progress(self, index):
        widget = self.tabs.widget(index)
        if widget in (self.progress, self.files, self.questions):
            run_action(self, widget.refresh)
        elif index == 0:
            run_action(self, self.refresh_overview)

    def refresh_overview(self):
        from studium.presentation.desktop.analytics import rate

        summary = self.service.student_progress(self.student.id, self.context.offering.id)
        self.overview_summary.setText(
            f"Работы: {summary.assessments_completed} из {summary.assessments_total} · Попыток: {summary.attempts_total}\n"
            f"Посещаемость: {rate(summary.attendance.attendance_rate)} · Не отмечено: {summary.attendance.unmarked}\n"
            f"Открытых вопросов: {summary.open_questions} · Ожидают ответа: {summary.questions_waiting_for_teacher}"
        )
        events = self.service.student_recent_activity(self.student.id, self.context.offering.id)
        self.activity_label.setText(
            TEXT["latest_activity"]
            + "\n"
            + (
                "\n".join(
                    f"{display_time(e.occurred_at)} · {e.title} · {ATTEMPT_LABELS[e.result] if e.result else TEXT['questions']}"
                    for e in events
                )
                or TEXT["no_data"]
            )
        )

    def refresh_works(self):
        self.works.refresh()

    def edit_student(self):
        def save(values):
            self.student = self.service.update_student(self.student, **values)

        if StudentDialog(save, self.student, self).exec() == QDialog.DialogCode.Accepted:
            self.name_label.setText(self.student.full_name)
            self.notes.setPlainText(self.student.notes)

    def hide_student(self):
        if confirm(self, TEXT["confirm_student_hide"]):
            self.service.hide("student", self.student)
            self.accept()

    def open_selected_work(self):
        self.works.open_selected_work()


class CoursesDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle(TEXT["courses"])
        resize_to_screen(self, 800, 460)
        layout = QVBoxLayout(self)
        self.model = TableModel(
            [
                (TEXT["name"], lambda c: c.name),
                (TEXT["short_name"], lambda c: c.short_name),
                (TEXT["description"], lambda c: c.description),
            ]
        )
        self.view = table(self.model)
        toolbar(
            layout,
            [
                (TEXT["new_course"], lambda: run_action(self, self.create)),
                (TEXT["edit"], lambda: run_action(self, self.edit)),
                (TEXT["hide"], lambda: run_action(self, self.hide)),
                (TEXT["learning_catalogue"], lambda: run_action(self, self.learning_catalogue)),
            ],
        )
        layout.addWidget(self.view)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.edit))
        self.refresh()

    def refresh(self):
        self.model.replace_rows(self.service.list_courses())

    def create(self):
        if (
            CourseDialog(lambda values: self.service.create_course(**values), parent=self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def edit(self):
        course = selected(self.view)
        if (
            course
            and CourseDialog(
                lambda values: self.service.update_course(course, **values), course, self
            ).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def hide(self):
        course = selected(self.view)
        if course and confirm_delete(self, self.service, "course", course):
            self.service.hide("course", course)
            self.refresh()

    def learning_catalogue(self):
        from studium.presentation.desktop.learning import LearningCatalogueDialog

        course = selected(self.view)
        if course:
            present_detail(
                LearningCatalogueDialog(self.service, course, self),
                self,
                refresh=self.refresh,
                title=course.name + " · темы",
            )
