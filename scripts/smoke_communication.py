"""Two real Windows entry-point launches with synthetic correspondence only."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

CHILD_CHECK = """
import os
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from studium.domain.communication import AuthorRole, CommunicationChannel
from studium.domain.enums import AssessmentType, AttemptResult
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.communication import QuestionCaptureDialog, QuestionCaseDialog, MessageCaptureDialog
from studium.presentation.desktop.dialogs import StudentDetailsDialog
from studium.presentation.desktop.files import FilePreviewDialog
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
                term = s.create_term('Synthetic', LocalDate(2026,9,1), LocalDate(2027,1,1))
                course = s.create_course('Synthetic course')
                group = s.create_group('TEST')
                offering = s.create_offering(term.id, course.id, group.id)
                student = s.create_student(offering.id, 'Synthetic Student')
                assessment = s.create_assessment(offering.id, 'Synthetic Work', AssessmentType.HOMEWORK)
                work = s.get_or_create_work(student.id, assessment.id)
                attempt = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
                topic = s.create_topic(course.id, 'Synthetic topic')
                skill = s.create_skill(course.id, 'Synthetic skill')
                capture = QuestionCaptureDialog(s, student_id=student.id, offering_id=offering.id)
                capture.show()
                QTest.qWait(100)
                capture.body.setPlainText('Synthetic student question\\nSecond line preserved')
                capture.channel.setCurrentIndex(capture.channel.findData(CommunicationChannel.TELEGRAM))
                capture.title.setText('Synthetic question subject')
                capture.submit()
                case = capture.saved_case
                capture.close()
                for kind, target in [('assessment',assessment),('attempt',attempt),('topic',topic),('skill',skill)]:
                    s.attach_question_context(case.id, kind, target.id)
                answer = MessageCaptureDialog(s, case.id, AuthorRole.TEACHER, channel=CommunicationChannel.TELEGRAM)
                answer.show()
                QTest.qWait(100)
                answer.body.setPlainText('Synthetic teacher response')
                answer.submit()
                answer.close()
                source = Path(os.environ['STUDIUM_SMOKE_ROOT'])/'synthetic.png'
                image=QImage(800,600,QImage.Format.Format_RGB32)
                image.fill(QColor('#d9e9f8'))
                assert image.save(str(source),'PNG')
                s.import_file_for_message(s.list_messages(case.id)[0].id,source)
            window.refresh()
            window.navigation.setCurrentRow(2)
            assert window.questions_page.model.rowCount() == 1
            entry = window.questions_page.model.rows[0]
            messages = s.list_messages(entry.case.id)
            assert len(messages) == 2 and '\\n' in messages[0].body
            assert all(len(v)==1 for v in s.list_question_context(entry.case.id).values())
            files=s.list_message_attachments(messages[0].id)
            assert len(files)==1 and files[0].integrity.value=='available'
            preview=FilePreviewDialog(s,files[0])
            preview.show()
            QTest.qWait(100)
            assert preview.isVisible() and not preview.image.pixmap().isNull()
            preview.close()
            context=s.list_offerings()[0]
            roster=s.list_students_for_offering(context.offering.id)[0]
            card=StudentDetailsDialog(s,context,roster)
            card.tabs.setCurrentWidget(card.questions)
            card.show()
            QTest.qWait(100)
            assert card.questions.model.rowCount()==1
            card.questions.view.selectRow(0)
            opened=[]
            def finish_dialog():
                detail=next(w for w in self.topLevelWidgets() if isinstance(w,QuestionCaseDialog))
                assert detail.isVisible() and detail.case_id==entry.case.id
                opened.append(detail.case_id)
                detail.accept()
            QTimer.singleShot(100,finish_dialog)
            card.questions.open_question()
            assert opened==[entry.case.id]
            card.close()
            print('NATIVE_COMMUNICATION_CAPTURE_PASS' if first_run else 'NATIVE_COMMUNICATION_REOPEN_PASS',flush=True)
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
    with TemporaryDirectory(prefix="studium-communication-smoke-") as directory:
        root = Path(directory)
        (root / "sitecustomize.py").write_text(CHILD_CHECK, encoding="utf-8")
        env = dict(
            os.environ,
            LOCALAPPDATA=str(root / "profile"),
            QT_QPA_PLATFORM="windows",
            STUDIUM_SMOKE_ROOT=str(root),
        )
        env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
        for marker in ("NATIVE_COMMUNICATION_CAPTURE_PASS", "NATIVE_COMMUNICATION_REOPEN_PASS"):
            result = subprocess.run(
                [sys.executable, "-m", "studium"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0 or marker not in result.stdout:
                raise RuntimeError(
                    f"Native communication smoke failed: {result.returncode}\n{result.stdout}\n{result.stderr}"
                )
            print(result.stdout.strip())
        print(
            "Phase 5 native capture/response/context/image/reopen/global/student PASS; temporary data only"
        )


if __name__ == "__main__":
    main()
