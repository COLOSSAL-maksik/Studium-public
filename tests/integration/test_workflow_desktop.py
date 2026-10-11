import pytest
from PySide6.QtCore import QDate, QMimeData, QPointF, Qt, QThreadPool, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox

from studium.domain.enums import AttemptResult, LessonType
from studium.domain.value_objects import UtcInstant
from studium.presentation.desktop.dialogs import AssessmentDialog, HistoryDialog
from studium.presentation.desktop.learning import AssessmentContentDialog, LessonForm
from studium.presentation.desktop.library import ContentEditor, MaterialFiles
from studium.presentation.desktop.qa_workflow import SubmissionHistory
from studium.presentation.desktop.theme import apply_theme
from studium.presentation.desktop.workflow_widgets import FileDropZone, data_index
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app
from tests.integration.test_phase65_desktop import wait_until


@pytest.fixture(autouse=True)
def no_unexpected_modal(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail(f"Unexpected message: {args[-1]}")

    monkeypatch.setattr(QMessageBox, "warning", fail)


def open_group(window, group):
    window.navigation.setCurrentRow(1)
    window.groups_page.open_group(group)


def test_internal_student_work_attempt_push_back_no_top_level(desktop):
    window, runtime, group, _, student, assessment = desktop
    s = runtime.service
    s.record_attempt(
        student.id, assessment.id, occurred_at=UtcInstant.now(), result=AttemptResult.PRESENTED
    )
    open_group(window, group)
    window.show()
    top_before = {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}
    window.groups_page.open_matrix_student(0)
    card = window.pages.currentWidget()
    assert not card.isWindow() and student.full_name in window.breadcrumb.text()
    card.work_view.selectRow(0)
    card.open_selected_work()
    history = window.pages.currentWidget()
    assert isinstance(history, SubmissionHistory) and not history.isWindow()
    history.legacy()
    legacy = window.pages.currentWidget()
    assert isinstance(legacy, HistoryDialog) and not legacy.isWindow()
    history = legacy
    history.view.selectRow(0)
    history.open_attempt()
    attempt_page = window.pages.currentWidget()
    assert not attempt_page.isWindow()
    assert "Попытка 1" in window.breadcrumb.text()
    assert {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()} == top_before
    window.router.back()
    assert window.pages.currentWidget() is history
    window.router.back()
    assert isinstance(window.pages.currentWidget(), SubmissionHistory)
    window.router.back()
    assert window.pages.currentWidget() is card
    window.router.back()
    assert window.pages.currentWidget() is window.groups_page
    assert window.groups_page.current_group.id == group.id


def test_sidebar_expand_direct_group_questions_absent_add_page(desktop):
    window, _, group, offering, *_ = desktop
    roots = [window.navigation.topLevelItem(i).text(0) for i in range(window.navigation.count())]
    assert roots == ["Главная", "Работа", "Дисциплины", "Библиотека", "Отчёты"]
    item = window.navigation.topLevelItem(1)
    assert item.childCount() == 1  # All groups; no recent context on first run.
    item.setExpanded(False)
    assert not item.isExpanded()
    item.setExpanded(True)
    window.open_sidebar_group(window.service.list_offerings()[0])
    assert window.groups_page.current_group.id == group.id
    assert window.groups_page.context().offering.id == offering.id
    window.navigation.setCurrentRow(0)
    assert window.pages.currentIndex() == 0
    assert window.back_button.isHidden()


@pytest.mark.parametrize(
    "group",
    [QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled],
)
def test_combo_popup_readable_palette(qt_app, group):
    apply_theme()
    field = QComboBox()
    field.addItems(["Числитель", "Знаменатель", "Длинный русский пункт"])
    palette = field.view().palette()
    assert palette.color(group, QPalette.ColorRole.Text).lightness() < 160
    assert palette.color(group, QPalette.ColorRole.Base).lightness() > 220
    assert palette.color(group, QPalette.ColorRole.Highlight).lightness() > 160
    assert palette.color(group, QPalette.ColorRole.HighlightedText).lightness() < 160
    field.deleteLater()


def test_datepicker_one_selection_updates_value_and_signal(qt_app):
    from studium.presentation.desktop.dialogs import TermDialog

    form = TermDialog(lambda _: None)
    changes = []
    form.start.dateChanged.connect(changes.append)
    target = QDate(2026, 11, 17)
    form.start.calendarWidget().clicked.emit(target)
    assert form.start.date() == target and changes == [target]
    assert form.values()["starts_on"].day == 17
    form.deleteLater()


@pytest.mark.parametrize("kind", ["homework", "problems", "seminars", "literature"])
def test_reusable_drop_multifile_import_from_library(desktop, tmp_path, kind):
    window, runtime, _, offering, *_ = desktop
    material = runtime.service.create_material(
        kind, course_id=offering.course_id, title="Synthetic"
    )
    files = MaterialFiles(runtime.service, kind, lambda: material)
    sources = [tmp_path / f"Synthetic {i}.txt" for i in range(2)]
    for path in sources:
        path.write_text("Synthetic placeholder", encoding="utf8")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in sources])
    enter = QDragEnterEvent(
        files.drop_zone.rect().center(),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    files.drop_zone.dragEnterEvent(enter)
    assert enter.isAccepted() and files.drop_zone.property("dragActive")
    drop = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    files.drop_zone.dropEvent(drop)
    assert drop.isAccepted() and not files.drop_zone.property("dragActive")
    assert len(files.staged.paths) == 2
    assert not runtime.service.list_material_files(kind, material.id)
    files.import_pending()
    wait_until(lambda: files.model.rowCount() == 2)
    assert len(runtime.service.list_material_files(kind, material.id)) == 2
    QThreadPool.globalInstance().waitForDone()
    files.deleteLater()


def test_drop_zone_rejects_url_directory_and_disabled(qt_app, tmp_path):
    zone = FileDropZone()
    for url in [QUrl("https://example.org/file"), QUrl.fromLocalFile(str(tmp_path))]:
        mime = QMimeData()
        mime.setUrls([url])
        event = QDragEnterEvent(
            zone.rect().center(),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        zone.dragEnterEvent(event)
        assert not event.isAccepted()
    zone.deleteLater()


@pytest.mark.parametrize("kind", ["homework", "problems", "seminars", "literature"])
def test_library_editor_persists_portable_text_and_types(desktop, kind):
    window, runtime, _, offering, *_ = desktop
    window.navigation.setCurrentRow(2)
    editor = ContentEditor(window, kind)
    window.router.push(editor, "Synthetic editor")
    editor.title.setText("Synthetic title")
    editor.course.setCurrentIndex(data_index(editor.course, offering.course_id))
    editor.tags.setText("балки, тест")
    if kind == "seminars":
        editor.week.setCurrentIndex(5)
    if kind == "problems":
        editor.fields["statement"].setPlainText("Statement")
        editor.fields["correct_answer"].setPlainText("Teacher answer")
    editor.save()
    value = runtime.service.get_material(kind, editor.original.id)
    assert value.tags == ("балки", "тест") and value.course_id == offering.course_id
    if kind == "problems":
        assert value.statement == "Statement" and value.correct_answer == "Teacher answer"
    if kind == "seminars":
        assert value.planned_week.value == 5
    window.router.back()


def test_week_selector_lecture_form_and_chart_empty_na_safe(desktop):
    window, runtime, group, offering, student, *_ = desktop
    form = AssessmentDialog(lambda _: None)
    form.title.setText("Synthetic")
    form.issue_week.setCurrentIndex(5)
    form.due_week.setCurrentIndex(7)
    assert form.values()["planned_issue_week"].value == 5
    assert "числитель" in form.issue_week.currentText()
    context = runtime.service.list_offerings()[0]
    lesson = LessonForm(runtime.service, context)
    lesson.lesson_type.setCurrentIndex(1)
    lesson.submit()
    assert runtime.service.list_lessons(offering.id)[0].type == LessonType.LECTURE
    open_group(window, group)
    analytics = window.groups_page.analytics
    analytics.refresh()
    analytics.tabs.setCurrentWidget(analytics.charts)
    assert len(analytics.charts.workflow.weeks) > 0
    assert analytics.charts.workflow.lectures.attendance_rate is None
    assert "Нет данных" in analytics.charts.notice.text()
    assert analytics.charts.summary is analytics.metrics.summary
    window.groups_page.open_matrix_student(0)
    card = window.pages.currentWidget()
    card.progress.refresh()
    card.progress.tabs.setCurrentWidget(card.progress.charts)
    assert card.progress.charts.summary is card.progress.metrics.summary
    form.deleteLater()
    lesson.deleteLater()


def test_generator_ui_save_select_set_unassign_restore(desktop):
    window, runtime, group, offering, *_ = desktop
    for i in range(3):
        runtime.service.create_material(
            "problems", course_id=offering.course_id, title=f"Problem {i}", tags=("балки",)
        )
    open_group(window, group)
    content = AssessmentContentDialog(
        runtime.service, window.groups_page.context(), desktop[-1], window
    )
    content.open_variants()
    tickets = window.pages.currentWidget()
    assert tickets.target_assessment_id == desktop[-1].id
    tickets.tags.setText("балки")
    tickets.generate()
    wait_until(lambda: tickets.draft is not None)
    assert tickets.tabs.currentWidget() is tickets.draft_page
    tickets.save()
    assert tickets.saved_sets.currentData() == tickets.saved.id
    assert tickets.tabs.currentWidget() is tickets.saved_page
    assert sum(len(v.assignments) for v in tickets.saved_views) == 1
    tickets.unassign()
    assert sum(len(v.assignments) for v in tickets.saved_views) == 0
    tickets.assign()
    assert sum(len(v.assignments) for v in tickets.saved_views) == 1


def test_generator_insufficient_pool_notice_readable(desktop):
    window, runtime, group, _, _, assessment = desktop
    open_group(window, group)
    content = AssessmentContentDialog(
        runtime.service, window.groups_page.context(), assessment, window
    )
    content.open_variants()
    page = window.pages.currentWidget()
    page.generate()
    wait_until(lambda: "Недостаточно" in page.notice.text())
    assert page.draft is None


def test_internal_pdf_back_releases_document_and_ignores_late_worker(desktop, tmp_path):
    from PySide6.QtGui import QPainter, QPdfWriter

    from studium.presentation.desktop.files import FilePreviewDialog
    from studium.presentation.desktop.navigation import present_detail

    window, runtime, _, offering, *_ = desktop
    source = tmp_path / "Synthetic.pdf"
    writer = QPdfWriter(str(source))
    painter = QPainter(writer)
    painter.drawText(100, 100, "Synthetic PDF")
    painter.end()
    del writer
    material = runtime.service.create_material(
        "literature", course_id=offering.course_id, title="Synthetic"
    )
    runtime.service.import_file_for_material("literature", material.id, source)
    entry = runtime.service.list_material_files("literature", material.id)[0]
    preview = FilePreviewDialog(runtime.service, entry, window)
    present_detail(preview, window)
    assert preview.pdf_document.pageCount() == 1
    window.router.back()
    assert preview.preview_closed and preview.pdf_document.pageCount() == 0
    preview.load_pdf(preview.layout(), source)
    assert preview.pdf_document.pageCount() == 0
