"""Two native python -m studium launches with synthetic files and isolated profile."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

CHILD_CHECK = """
import os
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from studium.domain.enums import AssessmentType, AttemptResult
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.dialogs import HistoryDialog, StudentDetailsDialog
from studium.presentation.desktop.files import FilePreviewDialog
original_exec = QApplication.exec
def smoke_exec(self):
    def verify():
        try:
            assert QApplication.platformName() == 'windows'
            windows = [w for w in self.topLevelWidgets() if w.windowTitle() == 'Studium']
            assert len(windows) == 1 and windows[0].isVisible()
            window = windows[0]
            s = window.service
            first_run = not s.list_terms()
            if first_run:
                term = s.create_term('Synthetic', LocalDate(2026,9,1), LocalDate(2027,1,1))
                course = s.create_course('Synthetic')
                group = s.create_group('TEST')
                offering = s.create_offering(term.id, course.id, group.id)
                student = s.create_student(offering.id, 'Synthetic Student')
                assessment = s.create_assessment(offering.id, 'Synthetic Work', AssessmentType.HOMEWORK)
                work = s.get_or_create_work(student.id, assessment.id)
                s.add_attempt(work.id, UtcInstant.now(), AttemptResult.PRESENTED)
                sources = Path(os.environ['STUDIUM_SMOKE_ROOT']) / 'sources'
                sources.mkdir()
                paths = []
                for number in (1,2):
                    path = sources / f'page{number}.jpg'
                    image = QImage(800,600,QImage.Format.Format_RGB32)
                    image.fill(QColor('#d9e9f8'))
                    assert image.save(str(path),'JPEG')
                    paths.append(str(path))
                history = HistoryDialog(s, work.id)
                history.files.import_paths(paths)
                assert history.files.model.rowCount() == 2
                history.close()
            context = s.list_offerings()[0]
            entry = s.list_students_for_offering(context.offering.id)[0]
            rows = s.list_student_files(entry.student.id)
            assert len(rows) == 2 and all(r.integrity.value == 'available' for r in rows)
            assert all(s.accessible_file_path(r.asset.id).is_relative_to((Path(os.environ['LOCALAPPDATA'])/'Studium').resolve()) for r in rows)
            preview = FilePreviewDialog(s, rows[0])
            preview.show()
            QTest.qWait(100)
            assert preview.isVisible() and not preview.image.pixmap().isNull()
            preview.close()
            student_card = StudentDetailsDialog(s, context, entry)
            student_card.tabs.setCurrentWidget(student_card.files)
            student_card.show()
            QTest.qWait(100)
            for _ in range(100):
                if student_card.files.model.rowCount() == 2:
                    break
                QTest.qWait(20)
            assert student_card.files.model.rowCount() == 2
            student_card.close()
            if not first_run and os.environ.get('STUDIUM_OPEN_DEFAULT') == '1':
                s.open_file_asset(rows[0].asset.id)
                QTest.qWait(1000)
                print('DEFAULT_APPLICATION_OPEN_ACCEPTED', flush=True)
            print('NATIVE_FILES_IMPORT_PASS' if first_run else 'NATIVE_FILES_REOPEN_PREVIEW_AGGREGATION_PASS', flush=True)
            window.close()
            self.quit()
        except Exception as error:
            import traceback
            traceback.print_exc()
            print('NATIVE_FILES_FAILED', type(error).__name__, flush=True)
            self.exit(1)
    QTimer.singleShot(500, verify)
    return original_exec()
QApplication.exec = smoke_exec
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--open-default", action="store_true", help="Ask Windows to open one synthetic JPEG"
    )
    args = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError("Native Windows smoke required")
    with TemporaryDirectory(prefix="studium-files-smoke-") as directory:
        root = Path(directory)
        (root / "sitecustomize.py").write_text(CHILD_CHECK, encoding="utf-8")
        env = dict(
            os.environ,
            LOCALAPPDATA=str(root / "profile"),
            QT_QPA_PLATFORM="windows",
            STUDIUM_SMOKE_ROOT=str(root),
            STUDIUM_OPEN_DEFAULT="1" if args.open_default else "0",
        )
        env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
        for marker in ("NATIVE_FILES_IMPORT_PASS", "NATIVE_FILES_REOPEN_PREVIEW_AGGREGATION_PASS"):
            result = subprocess.run(
                [sys.executable, "-m", "studium"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0 or marker not in result.stdout:
                raise RuntimeError(
                    f"Native file smoke failed: {result.returncode}\n{result.stdout}\n{result.stderr}"
                )
            print(result.stdout.strip())
        print(
            "Phase 4 native import/multiple files/reopen/preview/student aggregation PASS; temporary data only"
        )


if __name__ == "__main__":
    main()
