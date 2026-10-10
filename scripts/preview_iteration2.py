"""Isolated Iteration 2 UI screenshots and DPI/layout verification."""

import argparse
import json
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from iteration2_scenario import seed
from PySide6.QtCore import QEvent, QLocale, QPoint, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from studium.composition import create_runtime
from studium.presentation.desktop.analytics import AttemptItemResultForm
from studium.presentation.desktop.dialogs import HistoryDialog, TermDialog
from studium.presentation.desktop.learning import AssessmentContentDialog
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.programs import DisciplinePage, KnowledgeWidget, WorkProgramPage
from studium.presentation.desktop.quick_attempt import QuickAttemptDialog
from studium.presentation.desktop.theme import apply_theme


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--native-base-scale", type=float, default=2)
    parser.add_argument("--platform", default="windows")
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots/iteration2"))
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = args.platform
    os.environ["QT_SCALE_FACTOR"] = str(
        args.scale / args.native_base_scale if args.platform == "windows" else args.scale
    )
    os.environ.pop("QT_SCREEN_SCALE_FACTORS", None)
    app = QApplication([])
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))

    def fail(*values):
        raise RuntimeError(str(values[-1]))

    QMessageBox.warning = fail
    output = args.output / f"dpi-{int(args.scale * 100)}"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "platform": app.platformName(),
        "requested_scale": args.scale,
        "dpr": app.primaryScreen().devicePixelRatio(),
        "screenshots": [],
        "layout": [],
        "timing": {},
    }
    assert abs(report["dpr"] - args.scale) < 0.02, report

    def settle():
        for _ in range(4):
            app.processEvents()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    with TemporaryDirectory(prefix="studium-iteration2-preview-") as temp:
        root = Path(temp)
        runtime = create_runtime(root)
        window = MainWindow()
        window.initialize(runtime.service, runtime.diagnostics)
        window.resize(1240, 780)
        window.move(app.primaryScreen().availableGeometry().topLeft() + QPoint(20, 20))
        window.show()

        def capture(name, widget=None):
            settle()
            target = widget or window
            path = output / f"{name}.png"
            assert target.grab().save(str(path))
            report["screenshots"].append(path.name)
            report["layout"].append(
                {
                    "screen": name,
                    "size": [target.width(), target.height()],
                    "minimum": [
                        target.minimumSizeHint().width(),
                        target.minimumSizeHint().height(),
                    ],
                }
            )

        def push(page, title):
            window.router.push(page, title)
            settle()
            return page

        try:
            capture("00-empty-home")
            data = seed(runtime.service, root)
            s = runtime.service
            window.refresh()
            capture("01-home")
            window.navigation.setCurrentRow(2)
            push(DisciplinePage(window, data.course), data.course.name)
            capture("02-discipline")
            window.router.back()
            program = push(WorkProgramPage(window, data.programs[0]), data.programs[0].title)
            capture("03-program")
            program.tabs.setCurrentIndex(2)
            capture("04-modules")
            program.tabs.setCurrentIndex(3)
            capture("04b-program-works")
            window.router.back()
            window.navigation.setCurrentRow(1)
            context = next(c for c in s.list_offerings() if c.offering.id == data.offerings[0].id)
            window.open_sidebar_group(context)
            group = window.groups_page
            group.tabs.setCurrentIndex(0)
            capture("05-journal")
            start = perf_counter()
            group.analytics.refresh()
            report["timing"]["group_analytics_ui_seconds"] = perf_counter() - start
            group.tabs.setCurrentWidget(group.analytics)
            group.analytics.tabs.setCurrentWidget(group.analytics.progress_charts)
            capture("06-group-radial")
            group.analytics.progress_charts.mode.setCurrentIndex(1)
            capture("07-group-line")
            group.tabs.setCurrentIndex(0)
            group.open_matrix_student(0)
            student = window.pages.currentWidget()
            student.tabs.setCurrentWidget(student.progress)
            student.progress.tabs.setCurrentIndex(1)
            capture("08-student-progress")
            window.router.back()
            structure = push(
                AssessmentContentDialog(s, context, data.homework_assessments[0]), "Структура ДЗ"
            )
            capture("09-homework-structure")
            structure.main_tabs.setCurrentIndex(1)
            structure.sections.setCurrentIndex(1)
            capture("09b-homework-common-pdf")
            window.router.back()
            form = push(
                AttemptItemResultForm(s, data.control_attempt, data.control_items[1]),
                "РК · проверка задачи",
            )
            capture("10-control-task-skills")
            window.router.back()
            push(ContentEditor(window, "problems", data.problems[0]), "Банк задач")
            capture("11-problem-bank")
            window.router.back()
            knowledge = push(KnowledgeWidget(window, data.course.id), "База знаний")
            knowledge.view.selectRow(0)
            capture("12-knowledge-bank")
            window.router.back()
            group.tabs.setCurrentIndex(0)
            apply_theme("dark")
            capture("13-dark-journal")
            form = push(TermDialog(lambda _: None, data.term), "Календарь")
            calendar = form.start.calendarWidget()
            calendar.resize(390, 300)
            capture("14-dark-calendar", calendar)
            window.router.back()
            apply_theme("light")
            form = push(
                QuickAttemptDialog(s, data.students[0][0], data.homework_assessments[0]),
                "ДЗ · новая попытка",
            )
            capture("15-attempt-dialog")
            window.router.back()
            work = s.get_or_create_work(data.students[0][0].id, data.control.id)
            push(HistoryDialog(s, work.id), "РК · результаты задач")
            capture("16-control-history")
            window.router.back()
            program = push(WorkProgramPage(window, data.programs[0]), "Документ программы")
            program.tabs.setCurrentIndex(1)
            QThreadPool.globalInstance().waitForDone()
            settle()
            capture("17-program-pdf")
            for width, height in ((960, 620), (1240, 780)):
                window.resize(width, height)
                settle()
                report["layout"].append(
                    {
                        "screen": "resize-program",
                        "requested": [width, height],
                        "actual": [window.width(), window.height()],
                    }
                )
                assert window.width() == width and window.height() == height
        finally:
            window.close()
            QThreadPool.globalInstance().waitForDone()
            settle()
            runtime.close()
            for path in root.rglob("*"):
                if path.is_file():
                    path.chmod(stat.S_IWRITE | stat.S_IREAD)
    (output / "qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
