"""Synthetic Qt analytics views preserve facts and record immutable item results."""

from datetime import timedelta

import pytest
from PySide6.QtCore import QDateTime, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from sqlalchemy import event

from studium.domain.enums import AttemptResult, ItemOutcome
from studium.domain.value_objects import UtcInstant
from studium.presentation.desktop.analytics import (
    AssessmentAnalyticsWidget,
    AttemptItemResultForm,
    EvidenceDialog,
    metric,
)
from studium.presentation.desktop.communication import QuestionCaseDialog
from studium.presentation.desktop.dialogs import HistoryDialog, StudentDetailsDialog
from studium.presentation.desktop.learning import LearningCatalogueDialog
from studium.presentation.desktop.pages import AssessmentStudentsDialog
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app
from tests.unit.test_domain import instant


@pytest.fixture(autouse=True)
def fail_unexpected_message(monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *_: pytest.fail("Unexpected modal warning"))


def learning_facts(desktop, *, add_unrecorded_item=False):
    _, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    topic = s.create_topic(s.list_courses()[0].id, "Эпюра M")
    skill = s.create_skill(topic.course_id, "Определяет знак M")
    item = s.create_assessment_item(assessment.id, "Задача 1", max_score=5)
    s.set_assessment_content(item.id, [topic.id], [skill.id], item=True)
    if add_unrecorded_item:
        s.create_assessment_item(assessment.id, "Задача 2", sort_order=1)
    work = s.get_or_create_work(student.id, assessment.id)
    attempt = s.add_attempt(work.id, instant(), AttemptResult.ACCEPTED, score=8, max_score=10)
    return topic, skill, item, work, attempt


def test_student_progress_tab_readonly_metrics_and_evidence(desktop):
    _, runtime, _, offering, student, _ = desktop
    topic, _, item, _, attempt = learning_facts(desktop)
    s = runtime.service
    s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    s.create_question_case(
        student.id,
        "Вопрос",
        instant(),
        course_offering_id=offering.id,
        context={"topic": [topic.id]},
    )
    card = StudentDetailsDialog(
        s, s.list_offerings()[0], s.list_students_for_offering(offering.id)[0]
    )
    card.tabs.setCurrentWidget(card.progress)
    summary = card.progress.metrics.summary
    assert summary.assessments_completed == 1 and summary.questions.open_questions == 1
    assert card.progress.evidence_model.rowCount() == 2
    assert card.progress.evidence_model.rows[0].correct == 1
    assert not hasattr(summary, "_sa_instance_state")
    card.close()


def test_group_analytics_tab_without_ranking_or_work_creation(desktop):
    window, runtime, group, offering, _, _ = desktop
    s = runtime.service
    s.create_student(offering.id, "Второй Тестовый")
    before = s.matrix(offering.id)
    assert all(cell.work is None for cell in before.cells.values())
    window.groups_page.open_group(group)
    window.groups_page.tabs.setCurrentWidget(window.groups_page.analytics)
    summary = window.groups_page.analytics.metrics.summary
    assert summary.student_count == 2 and summary.assessments_completed == 0
    assert summary.average_completion_rate == 0
    after = s.matrix(offering.id)
    assert all(cell.work is None for cell in after.cells.values())
    assert window.groups_page.analytics.metrics.view.model().columnCount() == 3
    assert not hasattr(summary, "ranking")


def test_assessment_results_tab_shows_outcomes_and_no_score_na(desktop):
    _, runtime, _, offering, _, assessment = desktop
    s = runtime.service
    _, _, item, _, attempt = learning_facts(desktop)
    s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.PARTIAL)
    dialog = AssessmentStudentsDialog(s, s.list_offerings()[0], assessment)
    dialog.tabs.setCurrentIndex(1)
    assert dialog.results.summary.passed == 1
    assert dialog.results.item_model.rows[0].partial == 1
    cell = dialog.results.item_model.index(0, 4)
    assert dialog.results.item_model.data(cell) == "Нет данных"
    assert dialog.results.summary.average_normalized_score == 0.8
    assert not dialog.results.item_model.flags(cell) & Qt.ItemFlag.ItemIsEditable
    assert s.list_students_for_offering(offering.id)
    dialog.close()


def test_attempt_item_editor_records_then_protects_history(desktop):
    _, runtime, _, _, _, _ = desktop
    s = runtime.service
    _, _, item, work, attempt = learning_facts(desktop)
    history = HistoryDialog(s, work.id)
    assert history.item_results.add_button.isEnabled()
    submitted = []
    callback_errors = []

    def fill():
        form = next(
            w for w in QApplication.topLevelWidgets() if isinstance(w, AttemptItemResultForm)
        )
        try:
            form.outcome.setCurrentIndex(form.outcome.findData(ItemOutcome.PARTIAL))
            form.score.setText("3")
            form.teacher_comment.setPlainText("Проверить знак")
            form.submit()
            submitted.append(form.result())
        except BaseException as error:
            callback_errors.append(error)
        finally:
            if form.result() != QDialog.DialogCode.Accepted:
                form.reject()

    QTimer.singleShot(20, fill)
    history.item_results.record()
    assert not callback_errors
    assert submitted == [QDialog.DialogCode.Accepted]
    result = history.item_results.model.rows[0][1]
    assert result.attempt_id == attempt.id and result.teacher_comment == "Проверить знак"
    assert history.item_results.model.data(history.item_results.model.index(0, 2)) == "3 / 5"
    assert not history.item_results.add_button.isEnabled()
    history.close()
    readonly = HistoryDialog(s, work.id, editable=False)
    assert not readonly.item_results.add_button.isEnabled()
    readonly.close()


def test_empty_item_result_form_does_not_save(desktop, monkeypatch):
    _, runtime, *_ = desktop
    _, _, item, _, attempt = learning_facts(desktop)
    errors = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda _parent, _title, message: errors.append(message)
    )
    form = AttemptItemResultForm(runtime.service, attempt, item)
    form.submit()
    assert form.result() != QDialog.DialogCode.Accepted
    assert errors == ["Укажите результат части или балл."]
    assert not runtime.service.list_attempt_item_results(attempt.id)
    form.close()


@pytest.mark.parametrize(
    "outcome,score", [(ItemOutcome.CORRECT, None), (None, 2), (ItemOutcome.PARTIAL, 3)]
)
def test_item_result_form_optional_outcome_and_prefilled_maximum(desktop, outcome, score):
    _, runtime, *_ = desktop
    _, _, item, _, attempt = learning_facts(desktop)
    form = AttemptItemResultForm(runtime.service, attempt, item)
    form.outcome.setCurrentIndex(form.outcome.findData(outcome))
    if score is not None:
        form.score.setText(str(score))
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    result = runtime.service.list_attempt_item_results(attempt.id)[0]
    assert result.outcome == outcome and result.score == score
    assert result.max_score == (5 if score is not None else None)
    form.close()


def test_topic_and_skill_evidence_catalogue_navigation(desktop):
    _, runtime, *_ = desktop
    topic, skill, item, _, attempt = learning_facts(desktop)
    s = runtime.service
    s.create_attempt_item_result(attempt.id, item.id, score=0, max_score=5)
    catalogue = LearningCatalogueDialog(s, s.list_courses()[0])
    catalogue.tree.setCurrentItem(catalogue.tree.topLevelItem(0).child(0))
    opened = []
    callback_errors = []

    def close_evidence():
        dialog = next(
            w
            for w in QApplication.topLevelWidgets()
            if isinstance(w, EvidenceDialog) and w.isVisible()
        )
        try:
            assert dialog.summary.item_result_count == 1
            assert dialog.summary.average_normalized_item_score == 0
            opened.append(dialog.entity.id)
        except BaseException as error:
            callback_errors.append(error)
        finally:
            dialog.accept()

    QTimer.singleShot(20, close_evidence)
    catalogue.topic_evidence()
    catalogue.skill_view.selectRow(0)
    QTimer.singleShot(20, close_evidence)
    catalogue.skill_evidence()
    assert not callback_errors
    assert opened == [topic.id, skill.id]
    catalogue.close()


def test_time_comparison_and_na_are_distinct(desktop):
    _, runtime, _, offering, student, _ = desktop
    learning_facts(desktop)
    s = runtime.service
    card = StudentDetailsDialog(
        s, s.list_offerings()[0], s.list_students_for_offering(offering.id)[0]
    )
    card.tabs.setCurrentWidget(card.progress)
    metrics = card.progress.metrics
    metrics.enabled.setChecked(True)
    metrics.cutoff.setDateTime(
        QDateTime.fromMSecsSinceEpoch(instant().epoch_microseconds // 1000 - 1000)
    )
    metrics.refresh()
    assert metrics.model.rows[0][1].startswith("1 из 1")
    assert metrics.model.rows[0][2].startswith("0 из ")
    assert metric(None, percent=True) == "Нет данных"
    assert metric(0, percent=True) == "0,0%"
    assert metrics.summary.student_id == student.id
    card.close()


def test_missing_on_time_data_differs_from_no_deadline(desktop):
    _, runtime, _, offering, _, assessment = desktop
    s = runtime.service
    widget = AssessmentAnalyticsWidget(s, assessment.id)
    widget.refresh()
    assert dict(widget.metrics.model.rows)["Доля своевременных сдач"] == "Не применимо"
    s.update_assessment(assessment, due_at=UtcInstant(UtcInstant.now().value + timedelta(days=1)))
    widget.refresh()
    assert dict(widget.metrics.model.rows)["Доля своевременных сдач"] == "Нет данных"
    assert s.group_analytics(offering.id).deadline_assessments_total == 1
    widget.close()


@pytest.mark.parametrize("archived_parent", ["assessment", "course", "offering"])
@pytest.mark.parametrize("link_kind", ["assessment", "attempt"])
def test_questions_open_readonly_item_history_after_parent_archive(
    desktop, monkeypatch, archived_parent, link_kind
):
    _, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    _, _, item, work, attempt = learning_facts(desktop, add_unrecorded_item=True)
    result = s.create_attempt_item_result(attempt.id, item.id, outcome=ItemOutcome.CORRECT)
    target = assessment if link_kind == "assessment" else attempt
    case = s.create_question_case(
        student.id,
        "Исторический вопрос",
        instant(),
        course_offering_id=offering.id,
        context={link_kind: [target.id]},
    )
    if archived_parent == "offering":
        s._r.offerings.soft_delete(
            offering.id, expected_revision=offering.revision, at=UtcInstant.now()
        )
    else:
        s.hide(
            archived_parent, assessment if archived_parent == "assessment" else s.list_courses()[0]
        )
    statements = []

    def record_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(runtime._engine, "before_cursor_execute", record_sql)
    opened = []

    def inspect_history(dialog):
        assert dialog.history.work.id == work.id
        assert dialog.item_results.model.rows == [(item, result)]
        assert not dialog.item_results.add_button.isEnabled()
        assert not dialog.item_results.item_choice.isEnabled()
        assert dialog.item_results.item_choice.count() == 1
        dialog.item_results.record()
        opened.append(dialog.history.work.id)
        dialog.close()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(HistoryDialog, "exec", inspect_history)
    monkeypatch.setattr(
        AttemptItemResultForm, "exec", lambda *_: pytest.fail("Read-only history opened an editor")
    )
    try:
        question = QuestionCaseDialog(s, case.id)
        question.context_view.selectRow(0)
        question.open_context_work()
        question.close()
    finally:
        event.remove(runtime._engine, "before_cursor_execute", record_sql)
    assert opened == [work.id]
    assert statements and all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )
    assert s.list_attempt_item_results(attempt.id) == (result,)
