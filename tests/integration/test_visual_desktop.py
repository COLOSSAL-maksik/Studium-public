"""Regressions for retained theme state, file layout and disclosed input values."""

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView, QApplication, QScrollArea, QToolButton

from studium.domain.enums import AttemptResult
from studium.domain.value_objects import UtcInstant
from studium.presentation.desktop.calendar import StudyCalendar
from studium.presentation.desktop.design import DARK, LIGHT
from studium.presentation.desktop.dialogs import GroupDialog, HistoryDialog
from studium.presentation.desktop.icons import icon
from studium.presentation.desktop.programs import WorkProgramPage
from studium.presentation.desktop.theme import apply_theme
from studium.presentation.desktop.visuals import Disclosure, HomeTile
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_and_primary_action_contrast(theme, qt_app):
    palette = DARK if theme == "dark" else LIGHT

    def luminance(value):
        c = QColor(value)
        channels = [c.redF(), c.greenF(), c.blueF()]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, [0.2126, 0.7152, 0.0722], strict=True))

    for foreground, background in (
        (palette.text, palette.surface),
        (palette.muted, palette.background),
        (palette.on_accent, palette.accent),
    ):
        a, b = sorted([luminance(foreground), luminance(background)])
        assert (b + 0.05) / (a + 0.05) >= 4.5


def test_original_icons_have_transparency_and_disabled_state(qt_app):
    for symbol in ("home", "work", "course", "library", "settings", "back", "file", "add"):
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Disabled):
            bitmap = icon(symbol).pixmap(24, 24, mode).toImage()
            assert bitmap.pixelColor(0, 0).alpha() == 0
            assert any(bitmap.pixelColor(x, y).alpha() for x in range(24) for y in range(24))


@pytest.mark.windows
def test_home_tiles_have_room_and_keyboard_navigation(desktop):
    window, *_ = desktop
    window.resize(960, 620)
    window.show()
    QApplication.processEvents()
    tiles = window.findChildren(HomeTile)
    assert len(tiles) == 3
    for tile in tiles:
        assert tile.height() >= 156
    work = next(tile for tile in tiles if tile.accessibleName() == "Работа")
    work.setFocus()
    QTest.keyClick(work, Qt.Key.Key_Space)
    assert window.pages.currentWidget() is window.groups_page


def test_collapsed_group_fields_preserve_existing_values(qt_app):
    values = []
    form = GroupDialog(values.append)
    form.number.setText("SYNTHETIC-01")
    form.faculty.setText("Synthetic faculty")
    disclosure = form.findChild(Disclosure)
    assert disclosure is None
    assert not form.faculty.isHidden()
    form.submit()
    assert values[0]["faculty"] == "Synthetic faculty"
    form.close()


def test_history_file_layout_can_scroll_without_overlapping(desktop):
    window, runtime, _, _, student, assessment = desktop
    service = runtime.service
    work = service.get_or_create_work(student.id, assessment.id)
    service.add_attempt(work.id, UtcInstant.now(), AttemptResult.PRESENTED)
    history = HistoryDialog(service, work.id)
    window.router.push(history, "Synthetic history")
    window.resize(960, 620)
    window.show()
    history.attachments_disclosure.toggle.setChecked(True)
    QApplication.processEvents()
    assert not history.item_results.isVisibleTo(history)
    widgets = [
        history.files.heading,
        history.files.drop_zone,
        history.files.search,
        history.files.view,
    ]
    for first, second in zip(widgets, widgets[1:]):
        assert first.geometry().bottom() < second.geometry().top()
    scroll = next(
        child
        for child in history.history_split.findChildren(QScrollArea)
        if child.widget() is history.comment.parentWidget()
    )
    assert scroll.widget().height() >= scroll.viewport().height()
    assert len(service.history(work.id).entries) == 1


@pytest.mark.windows
def test_calendar_keyboard_survives_theme_change(qt_app):
    calendar = StudyCalendar()
    calendar.setSelectedDate(QDate(2026, 10, 4))
    calendar.show()
    grid = calendar.findChild(QAbstractItemView, "qt_calendar_calendarview")
    grid.setFocus()
    QApplication.processEvents()
    QTest.keyClick(grid, Qt.Key.Key_Right)
    assert calendar.selectedDate() == QDate(2026, 10, 5)
    apply_theme("dark")
    assert calendar.selectedDate() == QDate(2026, 10, 5)
    arrow = calendar.findChild(QToolButton, "qt_calendar_nextmonth").icon().pixmap(24, 24)
    assert any(
        arrow.toImage().pixelColor(x, y) == QColor(DARK.text) for x in range(24) for y in range(24)
    )
    QTest.keyClick(grid, Qt.Key.Key_PageDown)
    assert calendar.monthShown() == 11
    calendar.close()
    apply_theme("light")


def test_program_timeline_selects_the_existing_module(desktop):
    window, runtime, _, offering, *_ = desktop
    program = runtime.service.program_for_offering(offering.id)
    module = runtime.service.create_program_module(program.id, "Synthetic module", 1, 6)
    page = WorkProgramPage(window, program)
    page.select_module(0)
    assert page.tabs.currentIndex() == 2
    assert page.module_model.rows[page.module_view.currentIndex().row()].id == module.id
    page.close()
