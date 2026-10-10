"""Acceptance regressions: actual routes, semantic library sections and geometry."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QScrollArea

from studium.domain.content import GenerationCriteria, ProblemPurpose
from studium.domain.enums import LessonType
from studium.presentation.desktop.learning import CatalogueForm
from studium.presentation.desktop.library import LIBRARY_LABELS, ContentEditor
from studium.presentation.desktop.programs import ModuleForm, ProgramForm, ProgramWorkForm
from studium.presentation.desktop.quick_attempt import QuickAttemptDialog
from studium.presentation.desktop.theme import apply_theme
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


@pytest.fixture(autouse=True)
def no_unexpected_modal(monkeypatch):
    def fail(*values):
        pytest.fail(f"Unexpected UI warning: {values[-1]}")

    monkeypatch.setattr(QMessageBox, "warning", fail)


def test_home_resume_back_returns_to_home(desktop):
    window, _, group, *_ = desktop
    home = window.pages.currentWidget()
    assert window.back_button.isHidden()
    window.resume_work()
    assert window.groups_page.current_group.id == group.id
    assert len(window.router.routes) == 2
    window.router.back()
    assert window.pages.currentWidget() is home
    assert window.back_button.isHidden()


def test_work_group_back_and_sidebar_root(desktop):
    window, _, group, *_ = desktop
    window.navigation.setCurrentRow(1)
    window.groups_page.open_group(group)
    window.router.back()
    assert window.pages.currentWidget() is window.groups_page
    assert window.groups_page.stack.currentIndex() == 0
    assert window.back_button.isHidden()
    window.groups_page.open_group(group)
    window.navigation.setCurrentRow(2)
    assert len(window.router.routes) == 1
    assert window.groups_page.current_group is None


def test_program_to_other_group_restores_actual_history_and_original_group(desktop):
    from studium.presentation.desktop.programs import WorkProgramPage

    window, runtime, group, offering, *_ = desktop
    s = runtime.service
    window.resume_work()
    window.groups_page.tabs.setCurrentIndex(1)
    program_page = WorkProgramPage(window, s.program_for_offering(offering.id))
    window.router.push(program_page, "Program")
    other_group = s.create_group("OTHER-GROUP")
    other = s.create_offering(offering.term_id, offering.course_id, other_group.id)
    window.open_group_context(next(c for c in s.list_offerings() if c.offering.id == other.id))
    assert window.groups_page.current_group.id == other_group.id
    window.router.back()
    assert window.pages.currentWidget() is program_page
    window.router.back()
    assert window.groups_page.current_group.id == group.id
    assert window.groups_page.tabs.currentIndex() == 1
    window.router.back()
    assert window.pages.currentIndex() == 0


def test_home_single_card_and_recent_row_open(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    group = s.create_group("TEST-02")
    s.create_offering(offering.term_id, offering.course_id, group.id)
    window.refresh()
    assert window.overview_model.rowCount() == 1
    assert not any(b.text() == "Открыть группу" for b in window.findChildren(QPushButton))
    assert not hasattr(window, "add_button")
    window.show()
    QApplication.processEvents()
    assert window.continue_button.height() >= 80
    assert (
        window.continue_context.height() >= window.continue_context.fontMetrics().lineSpacing() * 2
    )
    expected = window.overview_model.rows[0].group.id
    QTest.mouseClick(
        window.overview_view.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.overview_view.visualRect(window.overview_model.index(0, 0)).center(),
    )
    assert window.groups_page.current_group.id == expected
    window.router.back()
    assert window.pages.currentIndex() == 0


def test_sidebar_one_level_shortcuts_and_persistence(desktop):
    window, runtime, _, offering, *_ = desktop
    runtime.service.remember_offering(offering.id)
    window.refresh()
    nav = window.navigation
    assert nav.count() == 5
    root = nav.topLevelItem(1)
    assert root.childCount() == 2
    for i in range(nav.count()):
        parent = nav.topLevelItem(i)
        assert all(parent.child(j).childCount() == 0 for j in range(parent.childCount()))
    root.setExpanded(True)
    assert 1 in runtime.service.sidebar_state()
    nav.setCurrentItem(root.child(0))
    assert window.groups_page.context().offering.id == offering.id
    window.router.back()
    assert window.groups_page.stack.currentIndex() == 0
    nav.setCurrentItem(nav.topLevelItem(3).child(1))
    assert window.library_page.tabs.currentWidget() is window.library_page.lists["problems"]
    assert len(window.router.routes) == 1


def test_library_sections_split_and_single_primary_create(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    for kind, title in LIBRARY_LABELS.items():
        window.library_page.select_section(kind)
        assert window.library_page.tabs.tabText(window.library_page.tabs.currentIndex()) == title
    assert list(LIBRARY_LABELS.values()) == [
        "Домашнее задание",
        "Банк задач",
        "Рубежный контроль",
        "Семинары",
        "Лекции",
        "Литература",
        "Методические материалы",
    ]
    seminar = s.create_material(
        "seminars", course_id=offering.course_id, title="Seminar", type=LessonType.SEMINAR
    )
    lecture = s.create_material(
        "seminars", course_id=offering.course_id, title="Lecture", type=LessonType.LECTURE
    )
    for kind, expected in (("seminars", seminar), ("lectures", lecture)):
        window.library_page.select_section(kind)
        assert window.library_page.lists[kind].model.rows == [expected]
    bank = window.library_page.lists["problems"]
    window.library_page.select_section("problems")
    assert len([b for b in bank.findChildren(QPushButton) if b.property("primary")]) == 1
    assert not hasattr(bank.extra_filters, "toggle")
    family = s.create_material(
        "problems",
        course_id=offering.course_id,
        title="Family",
        statement="Common",
        is_family=True,
        purposes=(ProblemPurpose.CONTROL,),
    )
    bank.purpose.setCurrentIndex(bank.purpose.findData(ProblemPurpose.CONTROL))
    bank.load()
    assert bank.model.rows == [family]
    homework = window.library_page.lists["homework"]
    s.create_material("packs", course_id=offering.course_id, title="Shared PDF pack")
    homework.tabs.setCurrentIndex(1)
    homework.refresh()
    assert len(homework.packs.model.rows) == 1
    window.library_page.select_section("control")
    assert window.library_page.lists["control"].model.rows == []
    problem = s.create_material("problems", course_id=offering.course_id, title="Standalone")
    saved = s.save_ticket_set(
        offering.id,
        s.generate_ticket_draft(
            GenerationCriteria(offering.course_id, 1, problem_ids=(problem.id,))
        ),
    )
    controls = window.library_page.lists["control"]
    controls.refresh()
    assert controls.model.rows[0][0].id == saved.id
    controls.view.selectRow(0)
    controls.open()
    assert window.pages.currentWidget().saved.id == saved.id


def test_family_editor_does_not_require_duplicate_statement(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    family = s.create_material(
        "problems",
        course_id=offering.course_id,
        title="Family",
        statement="Shared condition",
        is_family=True,
    )
    editor = ContentEditor(window, "problems", family)
    window.router.push(editor, "Family")
    assert editor.variant_model.rowCount() == 0
    editor.open_variant(new=True)
    variant = window.pages.currentWidget()
    assert "statement" not in variant.fields
    variant.fields["variant_code"].setText("1")
    variant.save()
    assert variant.original.family_id == family.id
    assert variant.original.statement == ""
    window.router.back()
    assert editor.variant_model.rowCount() == 1


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("size", [(960, 620), (1240, 780)])
@pytest.mark.windows
def test_frozen_journal_pixel_alignment_after_scroll(desktop, theme, size):
    window, runtime, group, offering, *_ = desktop
    for i in range(26):
        runtime.service.create_student(
            offering.id, f"Synthetic long student name surname patronymic {i:02}"
        )
    window.open_sidebar_group(runtime.service.list_offerings()[0])
    window.resize(*size)
    window.show()
    apply_theme(theme)
    QApplication.processEvents()
    view = window.groups_page.matrix_view
    view.horizontalScrollBar().setValue(view.horizontalScrollBar().maximum())
    view.verticalScrollBar().setValue(view.verticalScrollBar().maximum() // 2)
    QApplication.processEvents()
    assert view.horizontalScrollBar().maximum() > 0
    assert view.verticalScrollBar().value() == view.frozen.verticalScrollBar().value()
    for row in range(view.model().rowCount()):
        assert view.rowHeight(row) == view.frozen.rowHeight(row)
        assert view.viewport().y() + view.rowViewportPosition(
            row
        ) == view.frozen.y() + view.frozen.viewport().y() + view.frozen.rowViewportPosition(row)
    assert view.horizontalHeader().height() == view.frozen.horizontalHeader().height()
    assert view.frozen.horizontalHeader().isVisibleTo(window)
    assert view.childAt(view.frozen.geometry().center()).parentWidget() is view.frozen
    assert view.frozen.y() + view.frozen.horizontalHeader().y() == view.horizontalHeader().y()
    snapshot = view.model().snapshot
    assert all(c.title not in {"Нет ДЗ", "Нет РК"} for c in snapshot.columns)
    assert all(c.kind == "attendance" or c.assessment or c.program_work for c in snapshot.columns)
    assert snapshot.empty_sections
    assert "Домашнее задание" in window.groups_page.journal_structure.text()
    apply_theme("light")


def test_material_advanced_scroll_and_save_at_small_window(desktop):
    window, *_ = desktop
    editor = ContentEditor(window, "problems")
    window.router.push(editor, "New Material")
    window.resize(960, 620)
    window.show()
    assert not editor.fields["difficulty"].isHidden()
    QApplication.processEvents()
    assert editor.scroll.verticalScrollBar().maximum() > 0
    editor.scroll.ensureWidgetVisible(editor.fields["difficulty"])
    QApplication.processEvents()
    assert (
        editor.scroll.viewport()
        .rect()
        .intersects(
            editor.fields["difficulty"]
            .rect()
            .translated(
                editor.fields["difficulty"].mapTo(
                    editor.scroll.viewport(), editor.fields["difficulty"].rect().topLeft()
                )
            )
        )
    )
    save = next(b for b in editor.findChildren(QPushButton) if b.text() == "Сохранить")
    assert save.isVisibleTo(window)
    assert window.rect().contains(save.mapTo(window, save.rect().bottomRight()))


def test_order_is_internal_and_forms_remain_scrollable(desktop):
    window, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    program = s.program_for_offering(offering.id)
    course = next(c for c in s.list_courses() if c.id == offering.course_id)
    topic = s.create_topic(course.id, "Original", sort_order=12)
    forms = [
        ProgramForm(s, course),
        ModuleForm(s, program),
        ProgramWorkForm(s, program),
        CatalogueForm(s, course, original=topic),
        QuickAttemptDialog(s, student, assessment),
    ]
    for form in forms:
        window.router.push(form, form.windowTitle())
        window.resize(960, 620)
        window.show()
        QApplication.processEvents()
        assert form.findChildren(QScrollArea)
        assert not any(label.text() == "Порядок" for label in form.findChildren(QLabel))
        assert window.rect().contains(
            form.save_button.mapTo(window, form.save_button.rect().bottomRight())
        )
        if isinstance(form, CatalogueForm):
            assert form.values()["sort_order"] == 12
        window.router.back()
    first = s.create_skill(course.id, "First", sort_order=0)
    second = s.create_skill(course.id, "Second", sort_order=1)
    s.move_presentation_item("skills", second, -1)
    assert [v.id for v in s.list_course_skills(course.id)][:2] == [second.id, first.id]
