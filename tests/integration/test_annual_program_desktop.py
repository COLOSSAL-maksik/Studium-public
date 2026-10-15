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
    window.resize(960, 620)
    window.show()
    page.tabs.setCurrentIndex(1)
    page.show()
    qt_app.processEvents()
    assert page.lessons.viewport().height() >= page.lessons.rowHeight(0) * 2
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
    assert page.passport_fields["title"].isReadOnly()
    assert page.tree.isEnabled() and page.lessons.isEnabled()
    assert page.actions.isHidden()
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


def test_empty_profile_gui_create_discipline_module_bulk_topics_and_reopen(qt_app, tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSpinBox

    from studium.composition import create_runtime
    from studium.presentation.desktop.main_window import MainWindow
    from studium.presentation.desktop.qa_content import TopicTreePicker

    runtime = create_runtime(tmp_path)
    window = MainWindow()
    window.initialize(runtime.service, runtime.diagnostics)
    window.resize(960, 620)
    window.show()

    def course_form():
        form = QApplication.activeModalWidget()
        form.name.setText("Synthetic GUI discipline")
        form.submit()

    QTimer.singleShot(0, course_form)
    window.create_course()
    course = runtime.service.list_courses()[0]
    assert not runtime.service.list_terms() and not runtime.service.list_students()
    window.open_sidebar_course(course)
    parent = window.pages.currentWidget()
    parent.course_programs.create()
    page = window.pages.currentWidget()
    page.passport_fields["title"].setText("Created entirely in GUI")
    page.tabs.setCurrentIndex(1)
    page.tree.setCurrentItem(page.tree.topLevelItem(0))

    def module_form():
        form = QApplication.activeModalWidget()
        form.readers["title"].__self__.setText("Module created in GUI")
        form.submit()

    QTimer.singleShot(0, module_form)
    page.edit_module()

    def bulk_form():
        form = QApplication.activeModalWidget()
        form.findChildren(QSpinBox)[0].setValue(3)
        form.submit()

    QTimer.singleShot(0, bulk_form)
    page.bulk_lessons()
    assert page.lessons.rowCount() == 3
    page.lessons.selectRow(0)

    def lesson_form():
        from PySide6.QtWidgets import QPushButton

        form = QApplication.activeModalWidget()
        form.readers["title"].__self__.setText("Lesson created in GUI")
        form.readers["hours"].__self__.setText("1.5")

        def topic_form():
            dialog = QApplication.activeModalWidget()
            dialog.readers["title"].__self__.setText("Topic created in program")
            dialog.submit()

        QTimer.singleShot(0, topic_form)
        next(b for b in form.findChildren(QPushButton) if b.text() == "Создать тему").click()
        picker = form.findChild(TopicTreePicker)
        next(iter(picker.nodes.values())).setCheckState(0, Qt.CheckState.Checked)
        form.submit()

    QTimer.singleShot(0, lesson_form)
    page.edit_lesson(edit=True)
    page.save()
    draft_id = page.draft.id
    window.router.back()
    assert window.pages.currentWidget() is parent
    assert parent.course_programs.model.rowCount() == 1
    parent.course_programs.view.selectRow(0)
    parent.course_programs.next_version()
    reopened = window.pages.currentWidget()
    assert reopened.draft.id == draft_id
    module = reopened.annual["semesters"][0]["modules"][0]
    assert len(module["lessons"]) == 3 and module["lessons"][0]["topic_ids"]
    assert module["lessons"][0]["hours"] == "1.5"
    assert not runtime.service._r.lessons.list()
    window.close()
    window.deleteLater()
    qt_app.processEvents()
    runtime.close()
