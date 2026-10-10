"""Selection boundaries, append-only histories, reusable links and offline help."""

from PySide6.QtCore import QItemSelectionModel, Qt, QThreadPool, QTimer
from PySide6.QtWidgets import QDialog
from sqlalchemy import event

from studium.domain.content import ProblemPurpose
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus
from studium.domain.value_objects import AcademicWeekNumber, LocalDate
from studium.presentation.desktop.dialogs import StudentDetailsDialog
from studium.presentation.desktop.help_center import help_article, help_index
from studium.presentation.desktop.learning import CatalogueForm, LearningCatalogueDialog
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.periods import PeriodManager
from studium.presentation.desktop.problem_picker import ProblemPicker
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


def settle(qt_app):
    QThreadPool.globalInstance().waitForDone()
    for _ in range(4):
        qt_app.processEvents()


def test_bulk_attendance_changes_only_three_selected_cells(desktop):
    window, runtime, group, offering, *_ = desktop
    s = runtime.service
    for i in range(5):
        s.create_student(offering.id, f"Synthetic {i}")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 9, 2), planned_week=AcademicWeekNumber(1))
    page = window.groups_page
    page.open_group(group)
    selection = page.matrix_view.selectionModel()
    for row in (0, 2, 4):
        selection.select(page.matrix_model.index(row, 1), QItemSelectionModel.SelectionFlag.Select)
    target_ids = {page.matrix_model.matrix.roster[row].enrollment.id for row in (0, 2, 4)}
    page.attendance_status.setCurrentIndex(page.attendance_status.findData(AttendanceStatus.LATE))
    page.attendance_apply.click()
    marked = [row for row in s.list_lesson_attendance(lesson.id) if row.attendance]
    assert {row.enrollment.id for row in marked} == target_ids
    assert all(row.attendance.status == AttendanceStatus.LATE for row in marked)


def test_student_categories_three_attempts_files_and_progress_are_readonly(
    desktop, tmp_path, qt_app
):
    window, runtime, _, offering, student, homework = desktop
    s = runtime.service
    s.create_assessment(offering.id, "РК №1", AssessmentType.CONTROL_WORK)
    s.create_assessment(offering.id, "Экзамен", AssessmentType.EXAM)
    work = s.get_or_create_work(student.id, homework.id)
    attempts = [
        s.add_attempt(work.id, s._clock(), result)
        for result in (
            AttemptResult.PRESENTED,
            AttemptResult.NEEDS_REVISION,
            AttemptResult.ACCEPTED,
        )
    ]
    source = tmp_path / "Synthetic submission.txt"
    source.write_text("Synthetic submission", encoding="utf8")
    link = s.import_file_for_attempt(attempts[1].id, source)
    writes = []

    def observe(_conn, _cursor, statement, *_):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", observe)
    try:
        context = s.list_offerings()[0]
        entry = s.list_students_for_offering(offering.id)[0]
        card = StudentDetailsDialog(s, context, entry, window)
        assert card.works.categories.count() == 3
        assert card.works.attempt_model.rowCount() == 3
        card.works.attempt_view.selectRow(1)
        settle(qt_app)
        assert card.works.files.model.rows[0].asset.id == link.file_asset_id
        card.progress.refresh()
        assert [card.progress.tabs.tabText(i) for i in range(3)] == [
            "Домашнее задание",
            "Рубежный контроль",
            "Экзамен",
        ]
        facts = s.student_work_facts(student.id, offering.id)
        first = next(f for f in facts if f.assessment.id == homework.id)
        assert first.attempts == 3 and first.completed_at == attempts[2].occurred_at
        assert not writes
        card.close()
    finally:
        event.remove(runtime._engine, "before_cursor_execute", observe)


def test_seminar_new_task_default_purpose_and_atomic_links(desktop, qt_app):
    window, runtime, *_ = desktop
    s = runtime.service
    course = s.list_courses()[0]
    seminar = s.create_material("seminars", title="Synthetic seminar", course_id=course.id)
    editor = ContentEditor(window, "seminars", seminar)
    assert [editor.tabs.tabText(i) for i in range(editor.tabs.count())] == [
        "План",
        "Задачи",
        "Файлы",
        "Темы",
        "Заметки",
    ]

    def save_task():
        form = editor.seminar_problems.problem_editor
        form.title.setText("Synthetic new seminar task")
        form.save()

    QTimer.singleShot(0, save_task)
    editor.seminar_problems.create_problem()
    tasks = s.content_targets("seminar_problems", seminar.id)
    assert len(tasks) == 1 and tasks[0].purposes == (ProblemPurpose.SEMINAR,)
    assert tasks[0] in s.list_materials("problems", course_id=course.id)
    editor.save()
    assert s.content_targets("seminar_problems", seminar.id) == tasks


def test_bank_multiselect_survives_search(desktop):
    window, runtime, *_ = desktop
    s = runtime.service
    course = s.list_courses()[0]
    a, b = [
        s.create_material("problems", course_id=course.id, title=title)
        for title in ("Alpha", "Beta")
    ]
    picker = ProblemPicker(s, course.id, (a.id,), window)
    picker.search.setText("Beta")
    picker.view.selectRow(0)
    picker.search.clear()
    assert set(picker.ids()) == {a.id, b.id}
    picker.close()


def test_topic_hierarchy_module_subtopic_and_skill(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    course = s.list_courses()[0]
    program = s.program_for_offering(offering.id)
    module = s.create_program_module(program.id, "Module A", 1, 4)
    skill = s.create_skill(course.id, "Skill A")
    topic = s.create_topic(course.id, "Topic A", skill_ids=(skill.id,))
    s.create_topic(course.id, "Subtopic A", parent_topic_id=topic.id)
    s.place_topic_in_module(topic.id, module.id, course.id)
    catalogue = LearningCatalogueDialog(s, course, window)
    branch = catalogue.tree.topLevelItem(0).child(0)
    assert branch.text(0) == module.title
    assert branch.child(0).text(0) == topic.title
    assert {branch.child(0).child(i).text(0) for i in range(2)} == {"Subtopic A", "Навык: Skill A"}
    form = CatalogueForm(s, course, original=topic)
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    child = next(t for t in s.list_course_topics(course.id) if t.title == "Subtopic A")
    other = s.create_program_module(program.id, "Module B", 5, 7)
    s.set_topic_modules(child.id, (other.id,), course.id)
    catalogue.refresh()
    nested = catalogue.tree.topLevelItem(0).child(1).child(0).child(0)
    assert nested.text(0) == child.title
    catalogue.close()


def test_help_search_navigation_fallback_and_period_entry(desktop):
    window, *_ = desktop
    assert len(help_index()) == 21
    assert all(len(help_article(a["id"])) > 350 for a in help_index())
    window.open_help("attempts")
    assert window.pages.currentWidget() is window.help_page
    assert "История попыток" in window.help_page.content.toPlainText()
    window.help_page.search.setText("перетащите")
    assert window.help_page.navigation.count() == 1
    window.help_page.search.setText("no-such-help-word")
    assert "Ничего не найдено" in window.help_page.content.toPlainText()
    window.open_help("missing")
    assert "Статья не найдена" in window.help_page.content.toPlainText()
    assert window.term_combo.itemData(window.term_combo.count() - 1) == "manage"
    manager = PeriodManager(window)
    assert manager.model.rowCount() == 1
    manager.close()


def test_width_preferences_survive_recreated_window(desktop, qt_app):
    window, runtime, group, *_ = desktop
    window.show()
    window.navigation.setCurrentRow(1)
    window.groups_page.open_group(group)
    window.groups_page.tabs.setCurrentIndex(1)
    qt_app.processEvents()
    view = window.groups_page.student_view
    view.setColumnWidth(0, 327)
    service, key = view.width_preferences()
    assert service.table_widths(key)[0] == 327
    from studium.presentation.desktop.main_window import MainWindow

    reopened = MainWindow()
    try:
        reopened.initialize(runtime.service, runtime.diagnostics)
        reopened.show()
        reopened.navigation.setCurrentRow(1)
        reopened.groups_page.open_group(group)
        reopened.groups_page.tabs.setCurrentIndex(1)
        qt_app.processEvents()
        assert reopened.groups_page.student_view.columnWidth(0) == 327
    finally:
        reopened.close()


def test_bank_preview_switch_variant_and_pdf_after_source_removal(desktop, tmp_path, qt_app):
    from PySide6.QtGui import QImage, QPainter, QPdfWriter

    window, runtime, *_ = desktop
    s = runtime.service
    course = s.list_courses()[0]
    family = s.create_material("problems", course_id=course.id, title="Family", is_family=True)
    variants = [
        s.create_material(
            "problems",
            course_id=course.id,
            title=f"Variant {i}",
            family_id=family.id,
            variant_code=str(i),
        )
        for i in range(2)
    ]
    image = QImage(100, 80, QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.white)
    source = tmp_path / "Scheme.png"
    image.save(str(source))
    s.import_file_for_material("problems", variants[0].id, source)
    source.unlink()
    pdf = tmp_path / "Scheme.pdf"
    writer = QPdfWriter(str(pdf))
    painter = QPainter(writer)
    painter.drawText(100, 100, "Synthetic PDF")
    painter.end()
    del writer
    s.import_file_for_material("problems", variants[1].id, pdf)
    pdf.unlink()
    bank = window.library_page.lists["problems"]
    window.library_page.select_section("problems")
    bank.view.selectRow(0)
    bank.preview_variant.setCurrentIndex(1)
    bank.preview_variant.setCurrentIndex(2)
    for _ in range(4):
        settle(qt_app)
    assert bank.preview_pane.entries[0].material.id == variants[1].id
    assert bank.preview_pane.preview.pdf_document.pageCount() == 1
    bank.preview_variant.setCurrentIndex(1)
    for _ in range(4):
        settle(qt_app)
    assert not bank.preview_pane.preview.image.pixmap().isNull()
    bank.preview_variant.setCurrentIndex(0)
    settle(qt_app)
    assert bank.preview_pane.preview is None


def test_deleting_another_period_keeps_current_selection(desktop):
    window, runtime, *_ = desktop
    s = runtime.service
    active = s.active_term()
    other = s.create_term("Other", LocalDate(2027, 2, 1), LocalDate(2027, 6, 1))
    s.select_term(active.id)
    s.safe_delete("term", other)
    window.refresh()
    assert s.active_term().id == active.id
