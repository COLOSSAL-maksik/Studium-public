"""Actual Qt forms and stored data, including cancellation and worker completion."""

import json
import time

import pytest
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QMessageBox

from studium.domain.enums import AssessmentType, AttemptResult, StudentWorkStatus
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.qa_content import TopicTreePicker
from studium.presentation.desktop.qa_plans import (
    CourseVersionForm,
    PlanContentForm,
    PlanSetupForm,
    SemesterPlanWidget,
)
from studium.presentation.desktop.qa_workflow import (
    RequiredWorksForm,
    ReviewForm,
    SubmissionForm,
    SubmissionHistory,
)
from studium.presentation.desktop.workflow_widgets import data_index
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


def finish(app, form):
    end = time.monotonic() + 8
    while form.busy and time.monotonic() < end:
        app.processEvents()
        QTest.qWait(5)
    assert not form.busy
    assert form.result() == QDialog.DialogCode.Accepted, form.error_label.text()


@pytest.fixture(autouse=True)
def no_unexpected_dialog(monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *v: pytest.fail(str(v[-1])))


def test_course_version_plan_defer_independent_groups_and_required_ui(desktop, qt_app):
    window, runtime, group, offering, student, assessment = desktop
    s = runtime.service
    course = s.list_courses()[0]
    direction = s.create_direction("15.15.03", "Synthetic")
    form = CourseVersionForm(s, course)
    form.title.setText("Whole synthetic course")
    form.directions.item(0).setCheckState(Qt.CheckState.Checked)
    form.add_module()
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    version = s.program_versions(course.id)[0]
    assert s.version_direction_ids(version.id) == (direction.id,)
    context = s.list_offerings()[0]
    setup = PlanSetupForm(s, context)
    setup.reject()
    assert s.semester_plan(offering.id) is None
    setup = PlanSetupForm(s, context)
    setup.version.setCurrentIndex(1)
    setup.submit()
    assert setup.result() == QDialog.DialogCode.Accepted
    snapshot = s.semester_plan(offering.id)
    assert snapshot.plan.program_version_id == version.id
    assert len(snapshot.modules) == 1
    second_group = s.create_group("SYN-02")
    second = s.create_offering(
        offering.term_id,
        course.id,
        second_group.id,
        course_version_id=version.id,
        course_semester=1,
    )
    assert s.semester_plan(second.id).modules[0].id != snapshot.modules[0].id
    work = s.add_planned_work(
        offering.id, "Required", AssessmentType.HOMEWORK, module_id=snapshot.modules[0].id
    )
    s.issue_planned_work(work.id)
    required = RequiredWorksForm(s, context, s.semester_plan(offering.id))
    required.works.item(0).setCheckState(Qt.CheckState.Checked)
    required.reason.setText("Explicit requirement")
    required.submit()
    assert required.result() == QDialog.DialogCode.Accepted
    assert s.student_module_results(student.id)[0].state == "open"
    page = SemesterPlanWidget(window, lambda: context)
    page.refresh()
    assert page.model.rowCount() == 1
    for widget in (form, setup, required, page):
        widget.close()
        widget.deleteLater()


def test_reassignment_ui_preview_cancel_and_confirm(desktop, qt_app):
    window, runtime, _, offering, _, _ = desktop
    s = runtime.service
    course = s.list_courses()[0]
    version = s.create_course_program(
        course.id,
        "Preview program",
        content={
            "modules": [
                {
                    "key": "m",
                    "title": "Incoming",
                    "course_semester": 1,
                    "start_week": 1,
                    "end_week": 3,
                }
            ]
        },
    )
    s.create_semester_plan(offering.id)
    before = s.semester_plan(offering.id)
    context = s._context(s._r, offering.id)
    form = PlanContentForm(s, context, before, window)
    form.version.setCurrentIndex(data_index(form.version, version.id))
    form.submit()
    assert "Incoming: 1–3" in form.preview_text.toPlainText(), form.error_label.text()
    assert form.confirmed.isEnabled()
    assert s.semester_plan(offering.id) == before
    form.reject()
    assert s.semester_plan(offering.id) == before
    form = PlanContentForm(s, context, before, window)
    form.version.setCurrentIndex(data_index(form.version, version.id))
    form.submit()
    form.confirmed.setChecked(True)
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted, form.error_label.text()
    assert s.semester_plan(offering.id).modules[0].title == "Incoming"
    form.close()


def test_first_summary_ui_has_full_metrics_and_navigation(desktop, qt_app):
    from studium.presentation.desktop.analytics import StudentProgressWidget

    window, runtime, _, offering, student, _ = desktop
    page = StudentProgressWidget(runtime.service, student.id, offering.id, window)
    page.show()
    page.refresh()
    summary = page.package_summary
    assert page.tabs.currentWidget() is summary
    headings = [
        summary.model.headerData(i, Qt.Orientation.Horizontal)
        for i in range(summary.model.columnCount())
    ]
    for name in (
        "Всего выдано (активных)",
        "На доработке",
        "Ожидают проверки",
        "Не сдано в срок",
        "Фактические баллы",
    ):
        assert name in headings
    for name in (
        "Занятий:",
        "Посещено:",
        "Пропущено:",
        "Опоздания:",
        "Уважительные причины:",
        "Доля посещённых:",
    ):
        assert name in summary.caption.text()
    from PySide6.QtWidgets import QPushButton

    buttons = {button.text(): button for button in summary.findChildren(QPushButton)}
    buttons["Факты тем и навыков"].click()
    assert page.tabs.tabText(page.tabs.currentIndex()) == "Факты по темам и навыкам"
    buttons["Графики"].click()
    assert page.tabs.currentWidget() is page.charts
    page.close()


def test_submission_review_files_and_immutable_return_ui(desktop, qt_app, tmp_path):
    window, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    s.change_scoring_rule(assessment.id, "0", "10")
    original = tmp_path / "original.docx"
    original.write_bytes(b"Synthetic immutable original")
    teacher = tmp_path / "checked.docx"
    teacher.write_bytes(b"Synthetic checked copy")
    form = SubmissionForm(s, student.id, assessment_id=assessment.id)
    form.files.add_paths([original])
    before = len(s._r.attempts.list())
    form.reject()
    assert len(s._r.attempts.list()) == before
    form = SubmissionForm(s, student.id, assessment_id=assessment.id)
    form.files.add_paths([original])
    form.submit()
    finish(qt_app, form)
    submission = form.saved_value
    review = ReviewForm(s, submission, assessment)
    review.result_combo.setCurrentIndex(review.result_combo.findData(AttemptResult.NEEDS_REVISION))
    review.files.add_paths([teacher])
    review.submit()
    finish(qt_app, review)
    work = s._r.works.find_for_student(student.id, assessment.id)
    assert (
        s.matrix(offering.id).cells[student.id, assessment.id].progress.status
        == StudentWorkStatus.REVISION_REQUIRED
    )
    retry = ReviewForm(s, submission, assessment, sequence=1)
    retry.result_combo.setCurrentIndex(retry.result_combo.findData(AttemptResult.SCORED))
    retry.score.setText("7")
    retry.submit()
    end = time.monotonic() + 8
    while retry.busy and time.monotonic() < end:
        qt_app.processEvents()
        QTest.qWait(5)
    assert "явный зачёт" in retry.error_label.text()
    assert len(s.submission_history(work.id)[0][2]) == 1
    page = SubmissionHistory(s, work.id)
    assert page.model.rowCount() == 1
    assert page.teacher_model.rowCount() == 1
    assert original.read_bytes() == b"Synthetic immutable original"
    for widget in (form, review, retry, page):
        widget.close()
        widget.deleteLater()
    QThreadPool.globalInstance().waitForDone()


def test_topic_tree_exact_selection_and_structured_answer_snapshot(desktop):
    window, runtime, _, offering, *_ = desktop
    s = runtime.service
    root = s.create_topic(offering.course_id, "Root")
    child = s.create_topic(offering.course_id, "Child", parent_topic_id=root.id)
    picker = TopicTreePicker()
    picker.fill_topics([root, child], [root.id])
    assert picker.ids() == (root.id,)
    picker.search("Child")
    assert not picker.nodes[root.id].isHidden()
    assert not picker.nodes[child.id].isHidden()
    template = s.create_answer_template(
        "Force",
        [
            dict(
                kind="numeric",
                name="Force",
                symbol="F",
                value="-1.123456789123456789",
                units="N",
                formula="=literal",
                comment="text",
            )
        ],
    )
    editor = ContentEditor(window, "problems")
    editor.title.setText("Structured task")
    editor.answers.templates.setCurrentIndex(1)
    editor.answers.use_template()
    editor.save()
    problem = editor.original
    saved = json.loads(problem.details_json)
    assert saved["structured_answers"][0]["value"] == "-1.123456789123456789"
    assert saved["answer_template_snapshot"]["id"] == str(template.id)
    s.update_answer_template(
        template, "Changed", [dict(kind="symbolic", name="Moment", symbol="M", value="F*l")]
    )
    assert s.get_material("problems", problem.id).details_json == problem.details_json
    assert s.content_targets("problem_topics", problem.id) == ()
    editor.close()
    editor.deleteLater()
    picker.deleteLater()
