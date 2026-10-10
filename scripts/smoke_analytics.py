"""Two native Windows launches verify Phase 6 with a temporary synthetic profile."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

CHILD_CHECK = """
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from studium.domain.enums import AssessmentType, AttemptResult, ItemOutcome
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.analytics import AttemptItemResultForm, EvidenceDialog
from studium.presentation.desktop.dialogs import StudentDetailsDialog, HistoryDialog
from studium.presentation.desktop.pages import AssessmentStudentsDialog
original_exec = QApplication.exec

def smoke_exec(self):
    def verify():
        try:
            assert QApplication.platformName() == 'windows'
            window = next(w for w in self.topLevelWidgets() if w.windowTitle() == 'Studium')
            assert window.isVisible() and window.windowHandle().isVisible()
            s = window.service
            first_run = not s.list_terms()
            if first_run:
                term=s.create_term('Synthetic',LocalDate(2026,9,1),LocalDate(2027,1,1))
                course=s.create_course('Synthetic course')
                group=s.create_group('TEST')
                offering=s.create_offering(term.id,course.id,group.id)
                student=s.create_student(offering.id,'Synthetic Student')
                assessment=s.create_assessment(offering.id,'Synthetic Work',AssessmentType.CONTROL_WORK,max_score=10)
                topic=s.create_topic(course.id,'Synthetic topic')
                skill=s.create_skill(course.id,'Synthetic skill')
                item=s.create_assessment_item(assessment.id,'Synthetic part',max_score=5)
                s.set_assessment_content(item.id,[topic.id],[skill.id],item=True)
                work=s.get_or_create_work(student.id,assessment.id)
                attempt=s.add_attempt(work.id,UtcInstant.now(),AttemptResult.ACCEPTED,score=8,max_score=10)
                assert s.topic_evidence(topic.id).item_result_count == 0
                form=AttemptItemResultForm(s,attempt,item)
                form.show()
                QTest.qWait(100)
                form.outcome.setCurrentIndex(form.outcome.findData(ItemOutcome.PARTIAL))
                form.score.setText('3')
                form.submit()
                assert form.result()==QDialog.DialogCode.Accepted
                form.close()
                s.create_question_case(student.id,'Synthetic unanswered question',UtcInstant.now(),course_offering_id=offering.id,context={'topic':[topic.id],'skill':[skill.id]})
            context=s.list_offerings()[0]
            offering=context.offering
            student=s.list_students_for_offering(offering.id)[0]
            assessment=s.list_assessments(offering.id)[0]
            item=s.list_assessment_items(assessment.id)[0]
            topic=s.list_course_topics(context.course.id)[0]
            skill=s.list_course_skills(context.course.id)[0]
            window.refresh()
            window.navigation.setCurrentRow(1)
            window.groups_page.open_group(context.group)
            window.groups_page.tabs.setCurrentWidget(window.groups_page.analytics)
            QTest.qWait(100)
            assert window.groups_page.analytics.metrics.summary.student_count==1
            card=StudentDetailsDialog(s,context,student)
            card.tabs.setCurrentWidget(card.progress)
            card.show()
            QTest.qWait(100)
            assert card.progress.metrics.summary.assessments_completed==1
            assert card.progress.metrics.summary.questions.questions_waiting_for_teacher==1
            card.close()
            results=AssessmentStudentsDialog(s,context,assessment)
            results.tabs.setCurrentIndex(1)
            results.show()
            QTest.qWait(100)
            assert results.results.item_model.rows[0].partial==1
            results.close()
            work=s.get_or_create_work(student.student.id,assessment.id)
            history=HistoryDialog(s,work.id)
            history.detail_tabs.setCurrentIndex(1)
            history.show()
            QTest.qWait(100)
            assert history.item_results.model.rows[0][1].score==3
            assert not history.item_results.add_button.isEnabled()
            history.close()
            for entity,is_skill in [(topic,False),(skill,True)]:
                evidence=EvidenceDialog(s,entity,skill=is_skill,offering_id=offering.id)
                evidence.show()
                QTest.qWait(100)
                assert evidence.summary.item_result_count==1
                assert evidence.summary.question_cases_linked==1
                evidence.close()
            print('NATIVE_ANALYTICS_RECORD_PASS' if first_run else 'NATIVE_ANALYTICS_REOPEN_PASS',flush=True)
            window.close()
            self.quit()
        except Exception:
            import traceback
            traceback.print_exc()
            self.exit(1)
    QTimer.singleShot(500,verify)
    return original_exec()
QApplication.exec=smoke_exec
"""


def main():
    if os.name != "nt":
        raise RuntimeError("Native Windows smoke required")
    with TemporaryDirectory(prefix="studium-analytics-smoke-") as directory:
        root = Path(directory)
        (root / "sitecustomize.py").write_text(CHILD_CHECK, encoding="utf-8")
        env = dict(os.environ, LOCALAPPDATA=str(root / "profile"), QT_QPA_PLATFORM="windows")
        env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
        for marker in ("NATIVE_ANALYTICS_RECORD_PASS", "NATIVE_ANALYTICS_REOPEN_PASS"):
            result = subprocess.run(
                [sys.executable, "-m", "studium"],
                env=env,
                capture_output=True,
                text=True,
                timeout=35,
            )
            if result.returncode != 0 or marker not in result.stdout:
                raise RuntimeError(
                    f"Native analytics smoke failed: {result.returncode}\n{result.stdout}\n{result.stderr}"
                )
            print(result.stdout.strip())
        print(
            "Phase 6 native progress/group/results/item recording/evidence/questions/reopen PASS; temporary data only"
        )


if __name__ == "__main__":
    main()
