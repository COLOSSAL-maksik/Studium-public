"""Standard Qt capture, chronology, filters, student tab and preview reuse."""

import pytest
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from studium.domain.communication import AuthorRole, CommunicationChannel, CommunicationState
from studium.presentation.desktop.communication import (
    MessageCaptureDialog,
    QuestionCaptureDialog,
    QuestionCaseDialog,
)
from studium.presentation.desktop.dialogs import StudentDetailsDialog
from studium.presentation.desktop.files import FilePreviewDialog
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app
from tests.integration.test_file_desktop import image_source
from tests.unit.test_domain import instant


@pytest.fixture(autouse=True)
def fail_unexpected_message(monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *_: pytest.fail("Unexpected modal warning"))


def test_new_question_clipboard_multiline_context_and_global_page(desktop):
    window, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    course = s.list_courses()[0]
    topic = s.create_topic(course.id, "Эпюра M")
    skill = s.create_skill(course.id, "Определяет знак M")
    dialog = QuestionCaptureDialog(s, student_id=student.id, offering_id=offering.id)
    body = "  Первая строка\n\nВторая строка с отступом  "
    QApplication.clipboard().setText(body)
    QTest.mouseClick(dialog.paste_button, Qt.MouseButton.LeftButton)
    assert dialog.body.toPlainText() == body
    dialog.channel.setCurrentIndex(dialog.channel.findData(CommunicationChannel.TELEGRAM))
    dialog.sent_at.setDateTime(QDateTime.fromMSecsSinceEpoch(instant().epoch_microseconds // 1000))
    for kind in ("assessment", "topic", "skill"):
        dialog.context_fields[kind].item(0).setCheckState(Qt.CheckState.Checked)
    dialog.submit()
    assert dialog.result() == QDialog.DialogCode.Accepted
    case = dialog.saved_case
    context = s.list_question_context(case.id)
    assert context["assessment"][0][1].id == assessment.id
    assert context["topic"][0][1] == topic and context["skill"][0][1] == skill
    assert s.list_messages(case.id)[0].body == body
    window.refresh()
    window.navigation.setCurrentRow(1)
    window.groups_page.open_group(window.service.list_offerings()[0].group)
    window.groups_page.tabs.setCurrentWidget(window.questions_page)
    assert window.questions_page.model.rowCount() == 1
    assert not hasattr(window.questions_page.model.rows[0].case, "_sa_instance_state")
    window.questions_page.search.setText("вТОРАя")
    QTest.qWait(220)
    assert window.questions_page.model.rowCount() == 1
    window.questions_page.search.setText("несуществующий")
    QTest.qWait(220)
    assert window.questions_page.model.rowCount() == 0
    dialog.close()


def test_question_dialog_teacher_capture_state_filters_and_student_tab(desktop):
    window, runtime, _, offering, student, _ = desktop
    s = runtime.service
    case = s.create_question_case(student.id, "Вопрос", instant(), course_offering_id=offering.id)
    dialog = QuestionCaseDialog(s, case.id)
    assert dialog.body.toPlainText() == "Вопрос"
    answer = MessageCaptureDialog(
        s, case.id, AuthorRole.TEACHER, channel=CommunicationChannel.EMAIL
    )
    answer.sent_at.setDateTime(
        QDateTime.fromMSecsSinceEpoch(instant().epoch_microseconds // 1000 + 1000)
    )
    answer.body.setPlainText("Ответ\nпреподавателя")
    answer.submit()
    assert answer.result() == QDialog.DialogCode.Accepted
    dialog.refresh()
    assert (
        len(dialog.message_model.rows) == 2 and dialog.body.toPlainText() == "Ответ\nпреподавателя"
    )
    assert dialog.message_model.rows[1].author_role == AuthorRole.TEACHER
    assert dialog.message_model.data(
        dialog.message_model.index(0, 0), Qt.ItemDataRole.BackgroundRole
    ) != dialog.message_model.data(dialog.message_model.index(1, 0), Qt.ItemDataRole.BackgroundRole)
    page = window.questions_page
    page.state.setCurrentIndex(page.state.findData(CommunicationState.WAITING))
    assert page.model.rowCount() == 0
    page.state.setCurrentIndex(page.state.findData(CommunicationState.ANSWERED))
    assert page.model.rowCount() == 1
    dialog.toggle_closed()
    assert dialog.case.closed_at is not None
    dialog.toggle_closed()
    assert dialog.case.closed_at is None
    context = s.list_offerings()[0]
    roster = s.list_students_for_offering(offering.id)[0]
    card = StudentDetailsDialog(s, context, roster)
    card.tabs.setCurrentWidget(card.questions)
    assert card.tabs.tabText(4) == "Вопросы" and card.questions.model.rowCount() == 1
    card.close()
    answer.close()
    dialog.close()


def test_message_image_preview_uses_existing_file_services(desktop, tmp_path):
    _, runtime, _, offering, student, _ = desktop
    s = runtime.service
    case = s.create_question_case(
        student.id, "Исходное сообщение", instant(), course_offering_id=offering.id
    )
    dialog = QuestionCaseDialog(s, case.id)
    source = image_source(tmp_path / "synthetic-question.jpg")
    dialog.import_paths([str(source)])
    assert dialog.attachment_model.rowCount() == 1
    entry = dialog.attachment_model.rows[0]
    preview = FilePreviewDialog(s, entry)
    preview.show()
    QTest.qWait(10)
    assert not preview.image.pixmap().isNull()
    assert student.full_name in preview.context.text()
    assert s.get_thumbnail(entry.asset.id).exists()
    preview.close()
    dialog.close()


def test_capture_empty_message_and_dialog_context_detach(desktop):
    _, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    capture = QuestionCaptureDialog(s, student_id=student.id, offering_id=offering.id)
    capture.submit()
    assert capture.result() != QDialog.DialogCode.Accepted
    # FormDialog reports validation errors inline; no case has committed.
    assert not s.list_question_cases()
    capture.close()
    case = s.create_question_case(student.id, "Вопрос", instant(), course_offering_id=offering.id)
    dialog = QuestionCaseDialog(s, case.id)
    dialog.attach_context()
    assert dialog.context_model.rows[0][2].id == assessment.id
    dialog.context_view.selectRow(0)
    dialog.detach_context()
    assert not dialog.context_model.rows
    dialog.close()


def test_question_remains_readable_after_student_and_assessment_archiving(desktop):
    _, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    case = s.create_question_case(
        student.id,
        "Сохранённый вопрос",
        instant(),
        course_offering_id=offering.id,
        context={"assessment": [assessment.id]},
    )
    work = s.get_or_create_work(student.id, assessment.id)
    s.hide("student", student)
    s.hide("assessment", assessment)
    dialog = QuestionCaseDialog(s, case.id)
    assert dialog.body.toPlainText() == "Сохранённый вопрос"
    assert dialog.context_model.rows[0][2].deleted_at is not None
    assert s.question_work_for_assessment(case.id, assessment.id) == work
    assert s.list_question_cases()[0].student.deleted_at is not None
    dialog.close()


def test_capture_without_available_student_reports_ownership_requirement(desktop):
    _, runtime, _, _, student, _ = desktop
    s = runtime.service
    s.hide("student", student)
    capture = QuestionCaptureDialog(s)
    capture.body.setPlainText("Вопрос требует известного владельца")
    capture.submit()
    assert capture.result() != QDialog.DialogCode.Accepted
    assert "Выберите студента" in capture.error_label.text()
    assert not s.list_question_cases()
    capture.close()
