"""Workflow/keyboard/transaction regressions, without screenshot comparisons."""

from threading import Event

import pytest
from PySide6.QtCore import QItemSelectionModel, Qt, QThreadPool, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from sqlalchemy import event

from studium.application.errors import ApplicationError
from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, GradeKind
from studium.domain.repositories import RepositoryError
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.dialogs import StudentDetailsDialog
from studium.presentation.desktop.files import FilesWidget
from studium.presentation.desktop.learning import LessonDialog
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.pages import AssessmentStudentsDialog
from studium.presentation.desktop.quick_attempt import QuickAttemptDialog
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


def wait_until(predicate):
    for _ in range(150):
        if predicate():
            return
        QTest.qWait(20)
        # QTest.qWait may hold the Python GIL on Windows; let Python workers run.
        Event().wait(0.005)
    assert predicate()


def test_first_run_guided_setup(qt_app, tmp_path):
    runtime = create_runtime(tmp_path)
    window = MainWindow()
    window.initialize(runtime.service, runtime.diagnostics)
    assert window.overview_stack.currentWidget() is window.onboarding
    assert [b.isEnabled() for b in window.steps] == [True, False, False]
    s = runtime.service
    term = s.create_term("Синтетический период", LocalDate(2026, 9, 1), LocalDate(2027, 1, 1))
    window.refresh()
    assert [b.isEnabled() for b in window.steps] == [False, True, False]
    course = s.create_course("Механика")
    window.refresh()
    assert [b.isEnabled() for b in window.steps] == [False, False, True]
    group = s.create_group("ТЕСТ-02")
    s.create_offering(term.id, course.id, group.id)
    window.refresh()
    assert window.overview_stack.currentWidget() is not window.onboarding
    window.close()
    runtime.close()


def test_group_workspace_context_survives_navigation_and_refresh(desktop):
    window, runtime, group, offering, *_ = desktop
    page = window.groups_page
    other_course = runtime.service.create_course("Другая дисциплина")
    other = runtime.service.create_offering(offering.term_id, other_course.id, group.id)
    page.open_group(group)
    page.contexts.setCurrentIndex(
        next(
            i
            for i in range(page.contexts.count())
            if page.contexts.itemData(i).offering.id == other.id
        )
    )
    page.tabs.setCurrentWidget(page.works_page)
    for index in [2, 0, 1]:
        window.navigation.setCurrentRow(index)
    page.open_group(group)
    window.refresh()
    assert page.context().offering.id == other.id
    assert page.tabs.currentWidget() is page.works_page
    assert page.heading.text() == group.number
    assert page.course_heading.text() == other_course.name
    assert page.works_page.contexts.currentData().offering.id == other.id
    assert [page.tabs.tabText(i) for i in range(page.tabs.count())] == [
        "Журнал",
        "Студенты",
        "Работы",
        "Занятия",
        "Аналитика",
        "Вопросы",
        "Варианты",
        "Настройки группы",
    ]


@pytest.mark.parametrize(
    "result",
    [
        AttemptResult.PRESENTED,
        AttemptResult.NEEDS_REVISION,
        AttemptResult.ACCEPTED,
        AttemptResult.REJECTED,
    ],
)
def test_quick_attempt_preserves_history_and_automatic_number(desktop, result):
    _, runtime, _, _, student, assessment = desktop
    s = runtime.service
    if result == AttemptResult.REJECTED:
        assessment = s.update_assessment(assessment, type=AssessmentType.CONTROL_WORK)
    work = s.get_or_create_work(student.id, assessment.id)
    previous = s.add_attempt(
        work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION, comment="Исходная запись"
    )
    form = QuickAttemptDialog(s, student, assessment)
    assert form.optional.isHidden()
    form.result_combo.setCurrentIndex(form.result_combo.findData(result))
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    history = s.history(work.id)
    assert history.entries[0].attempt == previous
    assert history.entries[1].attempt.attempt_no == 2
    assert history.entries[1].attempt.result == result
    form.close()


def test_quick_cancel_does_not_create_work_or_attempt(desktop):
    _, runtime, _, offering, student, assessment = desktop
    form = QuickAttemptDialog(runtime.service, student, assessment)
    form.show()
    QTest.keyClick(form, Qt.Key.Key_Escape)
    assert form.result() == QDialog.DialogCode.Rejected
    assert runtime.service.matrix(offering.id).cells[student.id, assessment.id].work is None


def test_quick_optional_numeric_grade_and_invalid_input(desktop, monkeypatch):
    _, runtime, _, _, student, assessment = desktop
    form = QuickAttemptDialog(runtime.service, student, assessment)
    form.details_button.setChecked(True)
    form.result_combo.setCurrentIndex(form.result_combo.findData(AttemptResult.ACCEPTED))
    form.grade_kind.setCurrentIndex(form.grade_kind.findData(GradeKind.NUMERIC))
    form.score.setText("11")
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    form.submit()
    assert form.result() != QDialog.DialogCode.Accepted and warnings
    form.score.setText("8,5")
    form.submit()
    work = runtime.service.get_or_create_work(student.id, assessment.id)
    history = runtime.service.history(work.id)
    assert len(history.entries) == 1
    assert history.entries[0].grade.score == 8.5
    form.close()


def test_journal_enter_save_and_arrow_keys(desktop):
    window, runtime, group, _, student, assessment = desktop
    page = window.groups_page
    window.navigation.setCurrentRow(1)
    page.open_group(group)
    window.show()
    view = page.matrix_view
    view.setFocus()
    view.setCurrentIndex(page.matrix_model.index(0, 0))
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert view.currentIndex().column() == 1
    work_column = next(
        i + 1
        for i, c in enumerate(page.matrix_model.snapshot.columns)
        if c.assessment and c.assessment.id == assessment.id
    )
    view.setCurrentIndex(page.matrix_model.index(0, work_column))

    def save():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QuickAttemptDialog)
        dialog.result_combo.setCurrentIndex(dialog.result_combo.findData(AttemptResult.ACCEPTED))
        QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, save)
    QTest.keyClick(view, Qt.Key.Key_Return)
    assert page.matrix_model.data(page.matrix_model.index(0, work_column)) == "✓"
    assert view.currentIndex().column() == work_column
    work = runtime.service.get_or_create_work(student.id, assessment.id)
    assert len(runtime.service.history(work.id).entries) == 1


def test_frozen_names_remain_visible_and_selection_shared(desktop):
    window, runtime, group, offering, *_ = desktop
    for i in range(20):
        runtime.service.create_assessment(
            offering.id, f"Очень длинная работа {i}", AssessmentType.HOMEWORK
        )
    window.groups_page.open_group(group)
    window.navigation.setCurrentRow(1)
    window.show()
    QTest.qWait(30)
    view = window.groups_page.matrix_view
    view.horizontalScrollBar().setValue(view.horizontalScrollBar().maximum())
    assert view.frozen.geometry().left() == view.frameWidth()
    assert view.frozen.columnWidth(0) == view.columnWidth(0)
    assert not view.frozen.isColumnHidden(0)
    assert all(view.frozen.isColumnHidden(i) for i in range(1, view.model().columnCount()))
    assert view.frozen.selectionModel() is view.selectionModel()
    view.setCurrentIndex(view.model().index(0, 20))
    QTest.keyClick(view, Qt.Key.Key_Left)
    assert view.currentIndex().column() == 19


def test_scoped_find_for_roster_and_questions(desktop):
    window, _, group, *_ = desktop
    window.navigation.setCurrentRow(1)
    page = window.groups_page
    page.open_group(group)
    page.tabs.setCurrentIndex(1)
    window.show()
    window.activateWindow()
    QTest.qWait(50)
    page.student_view.setFocus()
    QTest.keyClick(page.student_view, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert QApplication.focusWidget() is page.search
    page.tabs.setCurrentWidget(window.questions_page)
    window.questions_page.view.setFocus()
    QTest.keyClick(window.questions_page.view, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert QApplication.focusWidget() is window.questions_page.search


def test_student_overview_tabs_and_lazy_file_io(desktop, monkeypatch):
    _, runtime, _, offering, _, _ = desktop
    s = runtime.service
    monkeypatch.setattr(
        s, "list_student_files", lambda *_: pytest.fail("Files read on the overview")
    )
    card = StudentDetailsDialog(
        s, s.list_offerings()[0], s.list_students_for_offering(offering.id)[0]
    )
    assert [card.tabs.tabText(i) for i in range(5)] == [
        "Обзор",
        "Работы",
        "Прогресс",
        "Файлы",
        "Вопросы",
    ]
    assert "Работы:" in card.overview_summary.text()
    card.tabs.setCurrentWidget(card.progress)
    assert card.progress.metrics.summary.assessments_total == 1
    card.close()


def test_assessment_questions_use_same_case_dialog(desktop):
    _, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    case = s.create_question_case(
        student.id,
        "Синтетический вопрос",
        UtcInstant.now(),
        course_offering_id=offering.id,
        context={"assessment": [assessment.id]},
    )
    card = AssessmentStudentsDialog(s, s.list_offerings()[0], assessment)
    assert card.questions.model.rows[0].case.id == case.id
    card.questions.view.selectRow(0)
    from studium.presentation.desktop.communication import QuestionCaseDialog

    def inspect():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QuestionCaseDialog)
        assert dialog.case.id == case.id
        dialog.reject()

    QTimer.singleShot(0, inspect)
    card.questions.open_question()
    card.close()


def test_archive_cancel_and_confirm_preserve_history(desktop, monkeypatch):
    window, runtime, group, _, student, assessment = desktop
    s = runtime.service
    work = s.get_or_create_work(student.id, assessment.id)
    attempt = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    page = window.groups_page
    page.open_group(group)
    page.student_view.selectRow(0)
    monkeypatch.setattr("studium.presentation.desktop.pages.confirm", lambda *a, **k: False)
    page.archive_student()
    assert s.list_students()[0].id == student.id
    monkeypatch.setattr("studium.presentation.desktop.pages.confirm", lambda *a, **k: True)
    page.archive_student()
    assert not s.list_students()
    assert s.history(work.id).entries[0].attempt == attempt


def test_bulk_attendance_preserves_comment_and_rolls_back_stale_batch(desktop):
    _, runtime, _, offering, _, _ = desktop
    s = runtime.service
    s.create_student(offering.id, "Альфа Второй")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 10, 2))
    entries = s.list_lesson_attendance(lesson.id)
    s.mark_attendance(
        lesson.id, entries[1].enrollment.id, AttendanceStatus.LATE, comment="Исходный комментарий"
    )
    entries = s.list_lesson_attendance(lesson.id)
    s.mark_attendance(
        lesson.id, entries[1].enrollment.id, AttendanceStatus.ABSENT, original=entries[1].attendance
    )
    with pytest.raises(RepositoryError):
        s.mark_attendance_many(lesson.id, entries, AttendanceStatus.PRESENT)
    assert s.list_lesson_attendance(lesson.id)[0].attendance is None
    current = s.list_lesson_attendance(lesson.id)
    s.mark_attendance_many(lesson.id, current, AttendanceStatus.PRESENT)
    assert all(
        e.attendance.status == AttendanceStatus.PRESENT for e in s.list_lesson_attendance(lesson.id)
    )


def test_bulk_attendance_requires_explicit_single_participation(desktop):
    _, runtime, _, offering, *_ = desktop
    s = runtime.service
    lesson = s.create_lesson(offering.id, LocalDate(2026, 10, 2))
    entries = s.list_lesson_attendance(lesson.id)
    with pytest.raises(ApplicationError):
        s.mark_attendance_many(lesson.id, [entries[0], entries[0]], AttendanceStatus.PRESENT)
    assert s.list_lesson_attendance(lesson.id)[0].attendance is None


def test_lesson_selected_rows_bulk_and_summary(desktop):
    _, runtime, _, offering, *_ = desktop
    s = runtime.service
    s.create_student(offering.id, "Второй Студент")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 10, 2))
    card = LessonDialog(s, s.list_offerings()[0], lesson)
    for row in range(card.model.rowCount()):
        card.view.selectionModel().select(
            card.model.index(row, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )
    card.mark_selected()
    assert all(
        e.attendance.status == AttendanceStatus.PRESENT for e in s.list_lesson_attendance(lesson.id)
    )
    assert dict(s.lesson_list(offering.id)[0].attendance_counts)[AttendanceStatus.PRESENT] == 2
    card.close()


def test_lesson_list_query_count_does_not_grow_per_lesson(desktop):
    _, runtime, _, offering, *_ = desktop
    s = runtime.service
    for day in range(1, 9):
        s.create_lesson(offering.id, LocalDate(2026, 9, day))
    queries = []

    def count(_conn, _cursor, statement, *_):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", count)
    try:
        assert len(s.lesson_list(offering.id)) == 8
    finally:
        event.remove(runtime._engine, "before_cursor_execute", count)
    assert len(queries) <= 10


def test_file_loading_keeps_event_loop_running_and_ignores_stale_results(desktop, monkeypatch):
    _, runtime, *_ = desktop
    gate = Event()
    monkeypatch.setattr(
        runtime.service, "list_student_files", lambda *_: (gate.wait(2), ["old"])[1]
    )
    files = FilesWidget(runtime.service, student_id="synthetic", lazy=True, asynchronous=True)
    ticks = []
    QTimer.singleShot(0, lambda: ticks.append(True))
    files.refresh()
    QTest.qWait(30)
    assert ticks and files.model.rowCount() == 0
    files.generation += 1
    gate.set()
    QThreadPool.globalInstance().waitForDone()
    QApplication.processEvents()
    assert files.model.rowCount() == 0
    files.deleteLater()


def test_attendance_view_uses_bulk_reads_for_roster(desktop):
    _, runtime, _, offering, *_ = desktop
    s = runtime.service
    for number in range(20):
        s.create_student(offering.id, f"Синтетический студент {number:02d}")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 10, 2))
    queries = []

    def count(_conn, _cursor, statement, *_):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", count)
    try:
        assert len(s.list_lesson_attendance(lesson.id)) == 21
    finally:
        event.remove(runtime._engine, "before_cursor_execute", count)
    assert len(queries) <= 10
