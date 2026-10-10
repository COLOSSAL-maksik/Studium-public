"""Report routes, context invalidation, exports and offscreen theme/geometry."""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QScrollArea, QTableView

from studium.application.report_models import ReportKind
from studium.domain.enums import AssessmentType
from studium.domain.value_objects import LocalDate
from studium.presentation.desktop.messages import ATTENDANCE_LABELS, STATUS_LABELS
from studium.presentation.desktop.theme import apply_theme
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app
from tests.integration.test_reporting import database_facts


@pytest.fixture(autouse=True)
def no_unexpected_modal(monkeypatch):
    def fail(*values):
        pytest.fail(f"Unexpected UI warning: {values[-1]}")

    monkeypatch.setattr(QMessageBox, "warning", fail)


def open_reports(window):
    window.navigation.setCurrentRow(4)
    assert window.pages.currentWidget() is window.reports_page
    return window.reports_page


def test_report_types_selectors_preview_and_section_selection_are_read_only(desktop):
    window, runtime, _, offering, student, assessment = desktop
    page = open_reports(window)
    before = database_facts(runtime._engine)
    assert page.contexts.currentData().offering.id == offering.id
    assert (
        page.students.currentData() == student.id
        and page.assessments.currentData() == assessment.id
    )
    for kind in ReportKind:
        page.kind.setCurrentIndex(page.kind.findData(kind))
        assert not page.csv_button.isEnabled() and page.report is None
        QTest.mouseClick(page.generate_button, Qt.MouseButton.LeftButton)
        assert page.report.kind == kind
        assert page.preview.count() == len(page.report.tables)
        assert page.csv_button.isEnabled() and page.pdf_button.isEnabled()
        assert page.preview.widget(0).findChildren(QScrollArea) == []
        for i, section in enumerate(page.report.tables):
            if section.key in {"attendance", "attendance_total"}:
                expected = ["Занятий", *ATTENDANCE_LABELS.values(), "Не отмечено"]
                if section.key == "attendance":
                    expected.insert(0, "ФИО")
            elif section.key == "students":
                expected = ["ФИО", "Работ", "Зачтено", "Попыток", *STATUS_LABELS.values()]
            else:
                continue
            model = page.preview.widget(i).findChild(QTableView).model()
            assert [
                model.headerData(column, Qt.Orientation.Horizontal)
                for column in range(model.columnCount())
            ] == expected
    assert database_facts(runtime._engine) == before


@pytest.mark.parametrize("format", ["csv", "pdf"])
def test_save_actions_and_cancel(desktop, monkeypatch, tmp_path_factory, format):
    window, runtime, *_ = desktop
    page = open_reports(window)
    page.generate()
    before = database_facts(runtime._engine)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    button = page.csv_button if format == "csv" else page.pdf_button
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert database_facts(runtime._engine) == before
    destination = tmp_path_factory.mktemp("report-exports") / f"synthetic-{format}"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    saved = destination.with_suffix(f".{format}")
    assert saved.stat().st_size > 0
    assert database_facts(runtime._engine) == before


@pytest.mark.parametrize("format", ["csv", "pdf"])
def test_managed_storage_is_not_an_export_destination(desktop, monkeypatch, format):
    window, runtime, *_ = desktop
    page = open_reports(window)
    page.generate()
    destination = Path(runtime.diagnostics.data_directory) / f"managed-export.{format}"
    before = set(destination.parent.iterdir())
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    page.save(format)
    assert "вне хранилища" in page.empty.text()
    assert not destination.exists() and set(destination.parent.iterdir()) == before


@pytest.mark.parametrize("format", ["csv", "pdf"])
@pytest.mark.parametrize("marker", ["directory", "file"])
def test_reports_save_rejects_git_checkout_with_clear_message(
    desktop, monkeypatch, tmp_path_factory, format, marker
):
    window, *_ = desktop
    page = open_reports(window)
    page.generate()
    checkout = tmp_path_factory.mktemp("export-checkout")
    if marker == "directory":
        (checkout / ".git").mkdir()
    else:
        (checkout / ".git").write_text(
            "gitdir: ../synthetic-main/.git/worktrees/synthetic\n", encoding="utf-8"
        )
    nested = checkout / "nested"
    nested.mkdir()
    destination = nested / f"report.{format}"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), ""))
    page.save(format)
    assert "Git" in page.empty.text() and not page.empty.isHidden()
    assert list(nested.iterdir()) == []


def test_empty_groups_and_no_assessments_have_safe_empty_preview(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    group = s.create_group("Synthetic empty")
    empty = s.create_offering(offering.term_id, offering.course_id, group.id)
    page = open_reports(window)
    page.contexts.setCurrentIndex(
        next(
            i
            for i in range(page.contexts.count())
            if page.contexts.itemData(i).offering.id == empty.id
        )
    )
    page.kind.setCurrentIndex(page.kind.findData(ReportKind.GROUP))
    page.generate()
    assert page.report and not page.empty.isHidden()
    page.kind.setCurrentIndex(page.kind.findData(ReportKind.ASSESSMENT))
    page.generate()
    assert page.report is None and "Нет студентов" in page.empty.text()


def test_global_period_change_invalidates_preview_and_repopulates_existing_context(desktop):
    window, runtime, *_ = desktop
    s = runtime.service
    page = open_reports(window)
    page.generate()
    term = s.create_term("Synthetic next", LocalDate(2027, 2, 1), LocalDate(2027, 6, 1))
    course, group = s.create_course("Other synthetic"), s.create_group("Other synthetic")
    offering = s.create_offering(term.id, course.id, group.id)
    window.refresh()
    assert page.report is None and not page.csv_button.isEnabled()
    assert page.contexts.count() == 1 and page.contexts.currentData().offering.id == offering.id


def test_stale_archived_selection_is_safe_and_historical_opt_in_restores_preview(desktop):
    window, runtime, _, _, _, assessment = desktop
    page = open_reports(window)
    page.kind.setCurrentIndex(page.kind.findData(ReportKind.ASSESSMENT))
    runtime.service.hide("assessment", assessment)
    page.generate()
    assert page.report is None and "устарел" in page.empty.text()
    page.historical.setChecked(True)
    page.generate()
    assert page.report and page.report.kind == ReportKind.ASSESSMENT


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("size", [(960, 620), (1240, 780)])
@pytest.mark.windows
def test_reports_long_unicode_geometry_keyboard_and_help(desktop, tmp_path, theme, size):
    window, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    s.update_student(student, full_name="Синтетический Студент " * 15)
    s.update_assessment(assessment, title="Синтетическое длинное название работы Ω " * 12)
    s.create_assessment(offering.id, "Синтетический РК", AssessmentType.CONTROL_WORK)
    apply_theme(theme)
    window.resize(*size)
    page = open_reports(window)
    window.show()
    page.generate()
    QApplication.processEvents()
    assert window.size().width() == size[0] and window.size().height() == size[1]
    outer_scroll = page.findChildren(QScrollArea)[0]
    assert outer_scroll.horizontalScrollBar().maximum() == 0
    assert outer_scroll.verticalScrollBar().maximum() >= 0
    page.kind.setFocus()
    QTest.keyClick(page.kind, Qt.Key.Key_Tab)
    assert QApplication.focusWidget() is page.contexts
    assert window.grab().save(str(tmp_path / f"reports-{theme}-{size[0]}.png"))
    page.help_button.click()
    assert window.pages.currentWidget() is window.help_page
    assert window.help_page.current_article_id == "reporting"
    window.help_page.search.setText("Отчёты и экспорт")
    assert window.help_page.navigation.count() == 1
