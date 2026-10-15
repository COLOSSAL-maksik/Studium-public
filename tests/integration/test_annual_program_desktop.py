"""Real widgets/application paths, synthetic DB and Qt offscreen only."""

import json

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from studium.presentation.desktop.annual_forms import lesson_form
from studium.presentation.desktop.annual_program import ImportPreviewForm, ProgramEditor
from tests.integration.test_annual_program import filled
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


def wait_workers(qt_app):
    QThreadPool.globalInstance().waitForDone()
    for _ in range(10):
        qt_app.processEvents()


def test_editor_real_save_topic_totals_publish_and_revision(desktop, qt_app):
    window, runtime, *_ = desktop
    course, draft = filled(runtime.service)
    page = ProgramEditor(window, course, draft=draft)
    window.router.push(page, "Annual")
    page.show()
    page.tree.setCurrentItem(page.tree.topLevelItem(0).child(0))
    assert page.lessons.rowCount() == 2
    before = page.annual["semesters"][0]["modules"][0]["lessons"][0]

    def saved(value):
        page.module_action(lambda module: page.replace_row(module["lessons"], value))

    form = lesson_form(page, before, saved)
    assert len(form.findChildren(type(form))) == 0
    # Fill via actual field reader controls; preserve topic selections and stable identity.
    for line in form.findChildren(
        __import__("PySide6.QtWidgets", fromlist=["QLineEdit"]).QLineEdit
    ):
        if line.text() == "1.25":
            line.setText("1.75")
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    page.passport_fields["label"].setText("GUI revision")
    page.save()
    assert not page.dirty
    reopened = ProgramEditor(window, course, draft=runtime.service.get_program_draft(page.draft.id))
    assert reopened.passport_fields["label"].text() == "GUI revision"
    assert reopened.annual["semesters"][0]["modules"][0]["lessons"][0]["key"] == before["key"]
    assert reopened.volume_table.item(0, 3).text() == "1.75"
    reopened.close()
    reopened.deleteLater()
    page.publish()
    assert page.version and page.draft is None
    assert all(not widget.isEnabled() for widget in page.editable_pages)
    assert "режим просмотра" in page.status.text()
    page.next_revision()
    next_page = window.pages.currentWidget()
    assert next_page.draft.base_version_id == page.version.id
    assert not next_page.dirty
    form.deleteLater()


def choose_message(label):
    def choose():
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        next(b for b in box.buttons() if b.text() == label).click()

    QTimer.singleShot(0, choose)


def test_unsaved_navigation_stay_discard_save_and_stale_error_keeps_text(
    desktop, qt_app, monkeypatch
):
    window, runtime, *_ = desktop
    course, draft = filled(runtime.service)
    page = ProgramEditor(window, course, draft=draft)
    window.router.push(page, "Annual")
    page.passport_fields["label"].setText("Unsaved")
    choose_message("Остаться")
    window.open_sidebar_course(course)
    assert window.pages.currentWidget() is page
    choose_message("Остаться")
    window.router.back()
    assert window.pages.currentWidget() is page
    choose_message("Сохранить черновик")
    window.router.back()
    assert window.pages.currentWidget() is not page
    current = runtime.service.get_program_draft(draft.id)
    stale = ProgramEditor(window, course, draft=current)
    fresh = runtime.service.save_program_draft(current, json.loads(current.content_json))
    stale.passport_fields["label"].setText("Keep typed text")
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    choose_message("Сохранить черновик")
    assert not stale.can_leave()
    assert stale.passport_fields["label"].text() == "Keep typed text" and stale.dirty
    assert runtime.service.get_program_draft(current.id) == fresh
    choose_message("Не сохранять")
    assert stale.can_leave()
    stale.dirty = False
    stale.close()
    stale.deleteLater()


def test_gui_async_export_preview_cancel_import(desktop, qt_app, tmp_path, monkeypatch):
    window, runtime, *_ = desktop
    course, draft = filled(runtime.service)
    version = runtime.service.publish_program_draft(draft)
    page = ProgramEditor(window, course, version=version)
    path = tmp_path / "gui.studium-program"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    page.export()
    wait_workers(qt_app)
    assert path.is_file() and "экспортирована" in page.notice.text()
    preview = runtime.service.preview_program_import(path)
    before = len(runtime.service.list_courses())
    cancelled = ImportPreviewForm(window, preview)
    cancelled.reject()
    assert len(runtime.service.list_courses()) == before
    form = ImportPreviewForm(window, preview)
    form.submit()
    wait_workers(qt_app)
    assert form.result() == QDialog.DialogCode.Accepted
    assert len(runtime.service.list_courses()) == before + 1
    for widget in (page, cancelled, form):
        widget.close()
        widget.deleteLater()
