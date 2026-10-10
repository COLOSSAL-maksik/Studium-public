import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDialog

from studium.domain.enums import AssessmentType, AttemptResult, GradeKind, ItemOutcome
from studium.presentation.desktop.analytics import AttemptItemResultForm
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.programs import OfferingProgramForm, ProgramForm, ProgramWorkForm
from studium.presentation.desktop.quick_attempt import QuickAttemptDialog
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


def test_program_create_explicit_offering_and_enum_values(desktop):
    window, runtime, _, _, _, _ = desktop
    service = runtime.service
    course = service.list_courses()[0]
    form = ProgramForm(service, course)
    form.title.setText("Other work program")
    form.direction.setText("Other direction")
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    program = next(
        p for p in service.list_work_programs(course.id) if p.title == "Other work program"
    )
    group = service.create_group("OTHER")
    offering_form = OfferingProgramForm(service, service.active_term(), group)
    offering_form.program.setCurrentIndex(
        next(
            i
            for i in range(offering_form.program.count())
            if offering_form.program.itemData(i) == program.id
        )
    )
    offering_form.submit()
    assert offering_form.result() == QDialog.DialogCode.Accepted
    assert (
        next(c for c in service.list_offerings() if c.group.id == group.id).offering.work_program_id
        == program.id
    )
    editor = ContentEditor(window, "homework")
    editor.title.setText("Reusable control")
    editor.work_type.setCurrentIndex(editor.work_type.findData(AssessmentType.CONTROL_WORK))
    editor.save()
    assert editor.original.type == AssessmentType.CONTROL_WORK
    for widget in (form, offering_form, editor):
        widget.close()
        widget.deleteLater()


def test_work_schedule_week_constrains_date_and_updates(desktop):
    _, runtime, _, offering, *_ = desktop
    service = runtime.service
    program = service.program_for_offering(offering.id)
    service.create_work_definition(offering.course_id, "Planned")
    form = ProgramWorkForm(service, program)
    assert form.due.count() == 18
    form.due.setCurrentIndex(6)
    form.due_enabled.setChecked(True)
    first, last = program.week_dates(6)
    assert form.due_date.minimumDate() == QDate(first.year, first.month, first.day)
    assert form.due_date.maximumDate() == QDate(last.year, last.month, last.day)
    form.due.setCurrentIndex(7)
    assert form.due_date.date() >= form.due_date.minimumDate()
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    form.deleteLater()


@pytest.mark.windows
def test_homework_quick_status_grade_fields_and_theme_persistence(desktop):
    window, runtime, _, offering, student, assessment = desktop
    form = QuickAttemptDialog(runtime.service, student, assessment)
    assert form.result_combo.findData(AttemptResult.REJECTED) == -1
    form.details_button.setChecked(True)
    form.grade_kind.setCurrentIndex(form.grade_kind.findData(GradeKind.PASS_FAIL))
    assert not form.passed.isHidden() and form.label.isHidden()
    form.grade_kind.setCurrentIndex(form.grade_kind.findData(GradeKind.TRADITIONAL))
    assert form.passed.isHidden() and not form.label.isHidden()
    window.theme_combo.setCurrentIndex(1)
    assert runtime.service.preferred_theme() == "dark"
    runtime.service.select_term(offering.term_id)
    runtime.service.remember_offering(offering.id)
    assert runtime.service.preferred_theme() == "dark"
    assert runtime.service.recent_offering_ids()[0] == offering.id
    window.theme_combo.setCurrentIndex(0)
    form.deleteLater()


def test_control_skill_form_persists_actual_qt_enum_selection(desktop, monkeypatch):
    import pytest
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *values: pytest.fail(str(values[-1])))
    _, runtime, _, offering, student, assessment = desktop
    s = runtime.service
    assessment = s.update_assessment(assessment, type=AssessmentType.CONTROL_WORK)
    skill = s.create_skill(offering.course_id, "Shared skill")
    problem = s.create_material(
        "problems", course_id=offering.course_id, title="Bank task", statement="Statement"
    )
    s.set_content_links("problem_skills", problem.id, (skill.id,))
    item = s.add_control_problem(assessment.id, problem.id)
    s.assign_student_problem(student.id, item.id, problem.id)
    attempt = s.record_attempt(
        student.id, assessment.id, occurred_at=s._clock(), result=AttemptResult.PRESENTED
    )
    form = AttemptItemResultForm(s, attempt, item)
    form.outcome.setCurrentIndex(form.outcome.findData(ItemOutcome.CORRECT))
    form.skill_fields[skill.id].setCurrentIndex(
        form.skill_fields[skill.id].findData(ItemOutcome.INCORRECT)
    )
    form.submit()
    assert form.result() == QDialog.DialogCode.Accepted
    assert s.skill_outcome_counts(offering.id, student.id)[skill.id][ItemOutcome.INCORRECT] == 1
    form.deleteLater()
