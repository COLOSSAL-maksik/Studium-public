import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from studium.domain.enums import AttendanceStatus
from studium.domain.repositories import RepositoryError
from studium.presentation.desktop.dialogs import CoursesDialog
from studium.presentation.desktop.learning import (
    AssessmentContentDialog,
    AttendanceForm,
    CatalogueForm,
    ContentForm,
    ItemForm,
    LearningCatalogueDialog,
    LessonDialog,
    LessonForm,
    TopicSkillsDialog,
)
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


@pytest.fixture(autouse=True)
def fail_on_unexpected_message(monkeypatch):
    def fail(parent, title, text):
        pytest.fail(f"Unexpected Qt message: {text}")

    monkeypatch.setattr(QMessageBox, "warning", fail)
    monkeypatch.setattr(QMessageBox, "information", fail)


def check_all(field):
    for i in range(field.count()):
        field.item(i).setCheckState(Qt.CheckState.Checked)


def test_learning_catalogue_forms_tree_and_skills(desktop):
    _, runtime, _, _, _, _ = desktop
    s = runtime.service
    course = s.list_courses()[0]
    form = CatalogueForm(s, course)
    form.title.setText("Тестовая тема")
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    topic = s.list_course_topics(course.id)[0]
    child = s.create_topic(course.id, "Подтема", parent_topic_id=topic.id)
    skill_form = CatalogueForm(s, course, skill=True)
    skill_form.title.setText("Тестовый навык")
    skill_form.submit()
    catalogue = LearningCatalogueDialog(s, course)
    assert catalogue.tree.topLevelItemCount() == 1
    assert (
        catalogue.tree.topLevelItem(0).child(0).child(0).data(0, Qt.ItemDataRole.UserRole) == child
    )
    assert catalogue.skill_model.rowCount() == 1
    links = TopicSkillsDialog(s, course, topic)
    check_all(links.skills)
    links.submit()
    assert s.learning_targets("topic_skills", topic.id)[0].title == "Тестовый навык"
    for dialog in [form, skill_form, catalogue, links]:
        dialog.close()


def test_group_lesson_form_topics_card_attendance_and_reload(desktop):
    window, runtime, group, offering, _, _ = desktop
    s = runtime.service
    context = s.list_offerings()[0]
    s.create_topic(context.course.id, "Тестовая тема")
    form = LessonForm(s, context)
    form.title.setText("Тестовое занятие")
    form.notes_field.setPlainText("Пройденный материал")
    check_all(form.topics)
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    window.groups_page.open_group(group)
    tabs = window.groups_page.tabs
    assert [tabs.tabText(i) for i in range(tabs.count())] == [
        "Журнал",
        "Студенты",
        "Работы",
        "План семестра",
        "Занятия",
        "Аналитика",
        "Вопросы",
        "Настройки группы",
    ]
    page = window.groups_page.lessons_page
    tabs.setCurrentWidget(page)
    assert page.model.rowCount() == 1
    assert page.model.data(page.model.index(0, 1)) == "Семинар"
    assert page.model.data(page.model.index(0, 3)) == "Тестовая тема"
    lesson = s.list_lessons(offering.id)[0]
    card = LessonDialog(s, context, lesson)
    assert card.notes_label.text() == "Пройденный материал"
    assert card.model.data(card.model.index(0, 2)) == "Не отмечено"
    row = card.model.rows[0]
    attendance = AttendanceForm(s, lesson, row)
    attendance.status.setCurrentIndex(attendance.status.findData(AttendanceStatus.LATE))
    attendance.submit()
    card.refresh()
    assert card.model.data(card.model.index(0, 2)) == "Опоздал"
    for dialog in [form, card, attendance]:
        dialog.close()


def test_assessment_and_item_tags_remain_independent_and_ordered(desktop):
    _, runtime, _, _, _, assessment = desktop
    s = runtime.service
    context = s.list_offerings()[0]
    s.create_topic(context.course.id, "Тема")
    s.create_skill(context.course.id, "Навык")
    content = ContentForm(s, context.course.id, assessment)
    check_all(content.topics)
    check_all(content.skills)
    content.submit()
    assert len(s.learning_targets("assessment_topics", assessment.id)) == 1
    item_form = ItemForm(s, assessment)
    item_form.title.setText("Задача 1")
    item_form.maximum.setText("5,5")
    item_form.submit()
    item = s.list_assessment_items(assessment.id)[0]
    item_content = ContentForm(s, context.course.id, item, item=True)
    check_all(item_content.skills)
    item_content.submit()
    assert s.learning_targets("item_topics", item.id) == ()
    assert len(s.learning_targets("item_skills", item.id)) == 1
    second = s.create_assessment_item(assessment.id, "Задача 2", sort_order=1)
    dialog = AssessmentContentDialog(s, context, assessment)
    dialog.view.setCurrentIndex(dialog.model.index(1, 0))
    dialog.move(-1)
    assert dialog.model.rows[0][0].id == second.id
    assert dialog.model.rows[1][0].max_score == 5.5
    for form in [content, item_form, item_content, dialog]:
        form.close()


def test_new_item_without_selection_opens_form(desktop):
    _, runtime, _, _, _, assessment = desktop
    dialog = AssessmentContentDialog(
        runtime.service, runtime.service.list_offerings()[0], assessment
    )

    def fill():
        form = QApplication.activeModalWidget()
        assert isinstance(form, ItemForm)
        form.title.setText("Первая задача")
        form.submit()

    QTimer.singleShot(0, fill)
    dialog.edit_item(new=True)
    assert dialog.model.rowCount() == 1
    dialog.close()


def test_stale_content_selection_is_rejected(desktop, monkeypatch):
    _, runtime, _, _, _, assessment = desktop
    s = runtime.service
    course = s.list_courses()[0]
    topic = s.create_topic(course.id, "Тема")
    form = ContentForm(s, course.id, assessment)
    s.attach_assessment_topic(assessment.id, topic.id)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: warnings.append(text))
    form.submit()
    assert form.result() != QDialog.DialogCode.Accepted
    assert warnings and "другом окне" in warnings[0]
    assert s.learning_targets("assessment_topics", assessment.id) == (topic,)
    form.close()


def test_stale_item_order_rejected_without_losing_external_edit(desktop):
    _, runtime, _, _, _, assessment = desktop
    s = runtime.service
    first = s.create_assessment_item(assessment.id, "Первая")
    second = s.create_assessment_item(assessment.id, "Вторая", sort_order=1)
    dialog = AssessmentContentDialog(s, s.list_offerings()[0], assessment)
    edited = s.update_assessment_item(first, description="Из другого окна")
    dialog.view.setCurrentIndex(dialog.model.index(1, 0))
    with pytest.raises(RepositoryError):
        dialog.move(-1)
    assert s.list_assessment_items(assessment.id) == [edited, second]
    dialog.close()


def test_catalogue_accessible_from_courses_dialog(desktop):
    _, runtime, *_ = desktop
    dialog = CoursesDialog(runtime.service)
    dialog.view.setCurrentIndex(dialog.model.index(0, 0))

    def inspect():
        form = QApplication.activeModalWidget()
        assert isinstance(form, LearningCatalogueDialog)
        form.reject()

    QTimer.singleShot(0, inspect)
    dialog.learning_catalogue()
    dialog.close()


def test_archived_linked_topic_is_visible_and_preserved_on_lesson_edit(desktop):
    _, runtime, *_ = desktop
    s = runtime.service
    context = s.list_offerings()[0]
    topic = s.create_topic(context.course.id, "Архивная тема")
    form = LessonForm(s, context)
    check_all(form.topics)
    form.submit()
    lesson = s.list_lessons(context.offering.id)[0]
    s.archive_topic(topic)
    edit = LessonForm(s, context, lesson)
    assert "в архиве" in edit.topics.item(0).text()
    assert edit.topics.item(0).checkState() == Qt.CheckState.Checked
    edit.title.setText("Изменено")
    edit.submit()
    assert edit.result() == QDialog.DialogCode.Accepted
    assert s.learning_targets("lesson_topics", lesson.id)[0].id == topic.id
    form.close()
    edit.close()
