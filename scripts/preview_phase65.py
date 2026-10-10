"""Phase 6.5 screenshots, DPI/resize checks and read performance on synthetic facts."""

import argparse
import json
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from phase65_scenario import seed
from PySide6.QtCore import QLocale, QThreadPool
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sqlalchemy import event

from studium.composition import create_runtime
from studium.presentation.desktop.dialogs import StudentDetailsDialog
from studium.presentation.desktop.files import FilePreviewDialog
from studium.presentation.desktop.learning import LessonDialog
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.quick_attempt import QuickAttemptDialog


def wait_files(files):
    for _ in range(200):
        if files.model.rowCount():
            return
        QTest.qWait(20)
    raise AssertionError("Synthetic file list did not load")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--native-base-scale", type=float, default=1)
    args = parser.parse_args()
    # Test the requested DPR, independent of the host monitor's Windows scaling.
    os.environ.pop("QT_SCREEN_SCALE_FACTORS", None)
    os.environ["QT_SCALE_FACTOR"] = str(args.scale / args.native_base_scale)
    app = QApplication([])
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    for name in ["segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"]:
        QFontDatabase.addApplicationFont(
            str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name)
        )
    args.output.mkdir(parents=True, exist_ok=True)
    screen = app.primaryScreen()
    assert abs(screen.devicePixelRatio() - args.scale) < 0.01
    report = {
        "scale": args.scale,
        "native_base_scale": args.native_base_scale,
        "platform": app.platformName(),
        "device_pixel_ratio": screen.devicePixelRatio(),
        "screen_available": [
            screen.availableGeometry().width(),
            screen.availableGeometry().height(),
        ],
        "windows": [],
        "performance": {},
    }
    dialogs = []
    with TemporaryDirectory(prefix="studium-phase65-preview-") as temp:
        root = Path(temp)
        runtime = create_runtime(root)
        try:
            s = runtime.service
            window = MainWindow()
            window.initialize(s, runtime.diagnostics)

            def capture(widget, name):
                widget.show()
                app.processEvents()
                QTest.qWait(60)
                assert widget.grab().save(str(args.output / f"phase65-{name}.png"))

            capture(window, "first-run")
            data = seed(s, root)
            window.refresh()
            window.navigation.setCurrentRow(1)
            page = window.groups_page
            selects = []

            def count(_conn, _cursor, statement, *_):
                if statement.lstrip().upper().startswith("SELECT"):
                    selects.append(statement)

            event.listen(runtime._engine, "before_cursor_execute", count)
            start = perf_counter()
            page.open_group(data.groups[0])
            elapsed = perf_counter() - start
            report["performance"]["workspace"] = {
                "seconds": round(elapsed, 4),
                "selects": len(selects),
            }
            selects.clear()
            start = perf_counter()
            page.tabs.setCurrentWidget(page.analytics)
            elapsed = perf_counter() - start
            report["performance"]["analytics"] = {
                "seconds": round(elapsed, 4),
                "selects": len(selects),
            }
            event.remove(runtime._engine, "before_cursor_execute", count)
            capture(window, "group-analytics")
            page.tabs.setCurrentIndex(0)
            capture(window, "journal")
            page.tabs.setCurrentIndex(1)
            capture(window, "students")
            context = next(c for c in s.list_offerings() if c.offering.id == data.offerings[0].id)
            entry = next(
                r
                for r in s.list_students_for_offering(context.offering.id)
                if r.student.id == data.students[0][0].id
            )
            card = StudentDetailsDialog(s, context, entry, window)
            dialogs.append(card)
            capture(card, "student-card")
            card.tabs.setCurrentWidget(card.progress)
            capture(card, "student-progress")
            card.tabs.setCurrentWidget(card.files)
            wait_files(card.files)
            capture(card, "files")
            preview = FilePreviewDialog(s, card.files.model.rows[0], card, asynchronous=True)
            dialogs.append(preview)
            preview.show()
            for _ in range(200):
                if not preview.preview_pixmap.isNull():
                    break
                QTest.qWait(20)
            assert not preview.preview_pixmap.isNull()
            capture(preview, "file-preview")
            preview.hide()
            card.tabs.setCurrentWidget(card.questions)
            capture(card, "student-questions")
            card.hide()
            quick = QuickAttemptDialog(s, entry.student, data.assessments[0][0], window)
            dialogs.append(quick)
            capture(quick, "quick-attempt")
            quick.hide()
            lesson = LessonDialog(s, context, data.lessons[0][0], window)
            dialogs.append(lesson)
            capture(lesson, "lesson")
            lesson.hide()
            window.navigation.setCurrentRow(2)
            capture(window, "questions")
            for size in [(960, 620), (1240, 780), (1600, 900)]:
                window.resize(*size)
                window.navigation.setCurrentRow(1)
                page.tabs.setCurrentIndex(0)
                app.processEvents()
                QTest.qWait(40)
                assert window.width() >= 960 and window.height() >= 620
                assert page.matrix_view.viewport().width() > 450
                assert page.matrix_view.viewport().height() >= 100
                assert page.matrix_view.frozen.width() == page.matrix_view.columnWidth(0)
                report["windows"].append(
                    {
                        "requested_size": size,
                        "size": [window.width(), window.height()],
                        "journal_viewport": [
                            page.matrix_view.viewport().width(),
                            page.matrix_view.viewport().height(),
                        ],
                    }
                )
            page.open_group(data.groups[1])
            page.tabs.setCurrentIndex(0)
            s.update_course(
                data.course,
                name="Сопротивление материалов · Расчёт конструкций при сложном напряжённом состоянии и проверка устойчивости",
            )
            window.refresh()
            row = next(
                i
                for i, r in enumerate(page.matrix_model.matrix.roster)
                if "Очень-Длинный" in r.student.full_name
            )
            page.matrix_view.setCurrentIndex(page.matrix_model.index(row, 10))
            page.matrix_view.scrollTo(page.matrix_model.index(row, 10))
            assert "Сопротивление" in page.course_heading.text()
            capture(window, "long-names")
            for dialog in dialogs:
                dialog.close()
            window.close()
            QThreadPool.globalInstance().waitForDone()
            app.processEvents()
        finally:
            runtime.close()
            for path in root.rglob("*"):
                if path.is_file():
                    path.chmod(stat.S_IWRITE | stat.S_IREAD)
    (args.output / f"phase65-qa-{args.scale:g}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
