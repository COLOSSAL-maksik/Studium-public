import os
from dataclasses import is_dataclass
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from studium.application.services import GradeInput
from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult, GradeKind
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.dialogs import (
    AssessmentDialog,
    AttemptDialog,
    GroupDialog,
    HistoryDialog,
    StudentDetailsDialog,
)
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.messages import ATTEMPT_LABELS, TEXT
from studium.presentation.desktop.models import AttemptHistoryModel, StudentTableModel


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    # Match preview_desktop: Windows offscreen has no system font discovery.
    # Load installed fonts into this test process; never copy or package them.
    if (
        os.name == "nt"
        and app.platformName() == "offscreen"
        and not app.property("studiumOffscreenFontsLoaded")
    ):
        font_root = Path(os.environ["WINDIR"]) / "Fonts"
        for filename in ("arial.ttf", "arialbd.ttf", "segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"):
            assert QFontDatabase.addApplicationFont(str(font_root / filename)) >= 0, filename
        app.setProperty("studiumOffscreenFontsLoaded", True)
    yield app


@pytest.fixture
def desktop(qt_app, tmp_path):
    runtime = create_runtime(tmp_path)
    s = runtime.service
    term = s.create_term("Осень 2026", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Тестовая дисциплина", "Тест")
    group = s.create_group("ТЕСТ-01", "Учебная кафедра")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Тестовый Студент", "Внимателен\nк деталям")
    assessment = s.create_assessment(offering.id, "ДЗ №1", AssessmentType.HOMEWORK, max_score=10)
    window = MainWindow()
    window.initialize(s, runtime.diagnostics)
    yield window, runtime, group, offering, student, assessment
    window.close()
    window.deleteLater()
    QThreadPool.globalInstance().waitForDone()
    qt_app.processEvents()
    runtime.close()


def test_mainwindow_navigation_and_settings(desktop):
    window, runtime, *_ = desktop
    assert window.windowTitle() == "Studium"
    assert window.navigation.count() == 5
    for index in range(5):
        window.navigation.setCurrentRow(index)
        assert window.pages.currentIndex() == index
    QTest.mouseClick(window.settings_button, Qt.MouseButton.LeftButton)
    assert window.pages.currentWidget() is window.settings_page
    assert runtime.diagnostics.schema_version == "0009_daily_workflow"
    assert str(runtime.diagnostics.database_path).endswith("studium.sqlite")


def test_group_dialog_requires_name_and_submits_to_application(desktop):
    _, runtime, *_ = desktop
    dialog = GroupDialog(lambda v: runtime.service.create_group(**v))
    dialog.submit()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert TEXT["number"] in dialog.error_label.text()
    dialog.number.setText("ТЕСТ-02")
    dialog.department.setText("Другая кафедра")
    QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert len(runtime.service.groups()) == 2
    dialog.close()


def test_students_model_search_sort_and_domain_only(desktop):
    window, runtime, group, offering, student, _ = desktop
    runtime.service.create_student(offering.id, "Альфа Тестовый")
    page = window.groups_page
    page.open_group(group)
    assert isinstance(page.student_model, StudentTableModel)
    assert page.proxy.rowCount() == 2
    assert page.proxy.data(page.proxy.index(0, 0)) == "Альфа Тестовый"
    page.search.setText("тестовый студент")
    assert page.proxy.rowCount() == 1
    assert page.proxy.data(page.proxy.index(0, 1)) == "Внимателен к деталям"
    assert page.proxy.data(page.proxy.index(0, 2)) == "Участвует"
    row = page.proxy.data(page.proxy.index(0, 0), Qt.ItemDataRole.UserRole)
    assert is_dataclass(row) and is_dataclass(row.student)
    assert row.student == student
    assert not hasattr(row.student, "_sa_instance_state")


def test_student_details_has_overview_works_and_files(desktop):
    _, runtime, _, offering, _, _ = desktop
    context = runtime.service.list_offerings()[0]
    entry = runtime.service.list_students_for_offering(offering.id)[0]
    dialog = StudentDetailsDialog(runtime.service, context, entry)
    assert [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())] == [
        TEXT["overview"],
        TEXT["works"],
        "Прогресс",
        TEXT["files"],
        TEXT["questions"],
    ]
    assert dialog.work_model.rowCount() == 1
    dialog.close()


def test_attempt_history_multiple_records_and_readonly(desktop):
    _, runtime, _, _, student, assessment = desktop
    service = runtime.service
    work = service.get_or_create_work(student.id, assessment.id)
    first = service.add_attempt(
        work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION, comment="Первый комментарий"
    )
    second = service.add_attempt(
        work.id,
        UtcInstant.now(),
        AttemptResult.ACCEPTED,
        grade=GradeInput(GradeKind.PASS_FAIL, passed=True),
    )
    dialog = HistoryDialog(service, work.id)
    assert isinstance(dialog.model, AttemptHistoryModel)
    assert dialog.model.rowCount() == 2
    assert dialog.model.data(dialog.model.index(0, 0)) == "1"
    assert dialog.model.data(dialog.model.index(0, 2)) == ATTEMPT_LABELS[first.result]
    assert dialog.model.data(dialog.model.index(1, 2)) == ATTEMPT_LABELS[second.result]
    assert dialog.model.data(dialog.model.index(1, 5)) == TEXT["pass"]
    assert not dialog.model.flags(dialog.model.index(0, 0)) & Qt.ItemFlag.ItemIsEditable
    dialog.view.setCurrentIndex(dialog.model.index(0, 0))
    assert dialog.comment.toPlainText() == "Первый комментарий"
    dialog.close()


def test_history_add_attempt_button_uses_application_number(desktop):
    _, runtime, _, _, student, assessment = desktop
    service = runtime.service
    work = service.get_or_create_work(student.id, assessment.id)
    dialog = HistoryDialog(service, work.id)

    def fill_form():
        form = QApplication.activeModalWidget()
        assert isinstance(form, AttemptDialog)
        form.result_combo.setCurrentIndex(form.result_combo.findData(AttemptResult.NEEDS_REVISION))
        form.comment.setPlainText("Исправить вычисление")
        form.submit()

    QTimer.singleShot(0, fill_form)
    dialog.add_attempt()
    assert dialog.model.rowCount() == 1
    assert dialog.model.data(dialog.model.index(0, 0)) == "1"
    assert dialog.model.data(dialog.model.index(0, 3)) == "Исправить вычисление"
    dialog.close()


def test_matrix_displays_status_and_count_without_persisted_state(desktop):
    window, runtime, group, _, student, assessment = desktop
    work = runtime.service.get_or_create_work(student.id, assessment.id)
    runtime.service.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
    runtime.service.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    window.groups_page.open_group(group)
    model = window.groups_page.matrix_model
    column = next(
        i + 1
        for i, c in enumerate(model.snapshot.columns)
        if c.assessment and c.assessment.id == assessment.id
    )
    assert model.data(model.index(0, column)) == "✓²"
    assert "Зачтено" in model.data(model.index(0, column), Qt.ItemDataRole.ToolTipRole)
    assert model.data(model.index(0, column), Qt.ItemDataRole.UserRole).work == work


def test_invalid_domain_values_keep_form_open_with_friendly_error(desktop, monkeypatch):
    _, runtime, _, offering, *_ = desktop
    errors = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: errors.append(text))
    dialog = AssessmentDialog(lambda v: runtime.service.create_assessment(offering.id, **v))
    dialog.title.setText("ДЗ с ошибкой")
    dialog.maximum.setText("-1")
    dialog.submit()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert errors == ["Максимальный балл должен быть конечным числом больше нуля."]
    assert dialog.title.text() == "ДЗ с ошибкой"
    dialog.close()


def test_attempt_dialog_converts_local_timestamp_to_utc_and_numeric_grade(desktop):
    _, runtime, _, _, student, assessment = desktop
    work = runtime.service.get_or_create_work(student.id, assessment.id)
    dialog = AttemptDialog(lambda v: runtime.service.add_attempt(work.id, **v), max_score=10)
    dialog.result_combo.setCurrentIndex(dialog.result_combo.findData(AttemptResult.SCORED))
    dialog.score.setText("8,5")
    dialog.grade_kind.setCurrentIndex(dialog.grade_kind.findData(GradeKind.NUMERIC))
    expected = dialog.occurred.dateTime().toMSecsSinceEpoch() * 1000
    dialog.submit()
    history = runtime.service.history(work.id)
    assert history.entries[0].attempt.occurred_at.epoch_microseconds == expected
    assert history.entries[0].grade.score == 8.5
    dialog.close()
