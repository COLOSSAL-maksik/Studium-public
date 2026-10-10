"""Reproducible source UI acceptance; native Windows or offscreen, isolated facts only."""

import argparse
import json
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import perf_counter

from phase66_scenario import seed
from PySide6.QtCore import QEvent, QLocale, QMimeData, QPoint, QPointF, Qt, QThreadPool, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from studium.composition import create_runtime
from studium.presentation.desktop.dialogs import AssessmentDialog, TermDialog
from studium.presentation.desktop.learning import LessonDialog
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.workflow_widgets import data_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--native-base-scale", type=float, default=1)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.pop("QT_SCREEN_SCALE_FACTORS", None)
    os.environ["QT_SCALE_FACTOR"] = str(args.scale / args.native_base_scale)
    app = QApplication([])
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    for name in ["segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"]:
        QFontDatabase.addApplicationFont(
            str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name)
        )
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "platform": app.platformName(),
        "scale": args.scale,
        "dpr": app.primaryScreen().devicePixelRatio(),
        "resize": [],
        "checks": [],
        "performance": {},
    }
    assert abs(report["dpr"] - args.scale) < 0.01

    def wait(predicate, seconds=8):
        start = perf_counter()
        while not predicate() and perf_counter() - start < seconds:
            app.processEvents()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            Event().wait(0.015)
        assert predicate(), "UI worker timeout"

    def settle():
        app.processEvents()
        Event().wait(0.04)
        app.processEvents()

    with TemporaryDirectory(prefix="studium-phase66-qa-") as temp:
        root = Path(temp)
        runtime = create_runtime(root)
        try:
            s = runtime.service
            window = MainWindow()
            window.initialize(s, runtime.diagnostics)
            window.resize(1240, 780)
            window.setScreen(app.primaryScreen())
            window.move(app.primaryScreen().availableGeometry().topLeft() + QPoint(20, 20))
            window.show()
            settle()
            report["window_dpr"] = window.devicePixelRatioF()
            assert abs(report["window_dpr"] - args.scale) < 0.01

            def capture(name):
                settle()
                assert window.grab().save(str(args.output / f"phase66-{name}.png"))
                assert QWidget.window(window.pages.currentWidget()) is window

            data = seed(s, root)
            window.refresh()
            capture("01-navigation")
            window.navigation.topLevelItem(1).setExpanded(True)
            window.navigation.setCurrentItem(window.navigation.topLevelItem(1).child(0))
            page = window.groups_page
            capture("02-sidebar-groups")
            page.open_matrix_student(0)
            card = window.pages.currentWidget()
            capture("03-student-back")
            QTest.keyClick(window, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
            settle()
            assert window.pages.currentWidget() is page
            report["checks"].append("Alt+Left / internal Student / Back")
            window.navigate(3)
            capture("04-add")

            def library(kind):
                window.navigate(2)
                value = window.library_page.lists[kind]
                window.library_page.tabs.setCurrentWidget(value)
                value.refresh()
                return value

            library("homework")
            capture("05-homework")
            bank = library("problems")
            bank.tags.setText("балки")
            bank.collection.setCurrentIndex(data_index(bank.collection, data.collection.id))
            bank.load()
            assert bank.model.rowCount() == 22
            capture("06-problem-bank")
            bank.edit(data.problems[0])
            editor = window.pages.currentWidget()
            assert editor.course.currentData() == data.course.id
            editor.tabs.setCurrentIndex(1)
            capture("07-problem-answer")
            editor.tabs.setCurrentIndex(2)
            references = editor.file_widgets[1]
            wait(lambda: references.model.rowCount() == 2)
            capture("07b-problem-epures")
            references.view.selectRow(0)
            references.preview()
            preview = window.pages.currentWidget()
            wait(lambda: not preview.preview_pixmap.isNull())
            capture("07c-image-preview")
            window.router.back()
            references.view.selectRow(1)
            references.preview()
            preview = window.pages.currentWidget()
            wait(lambda: hasattr(preview, "pdf_view"))
            assert preview.pdf_document.pageCount() == 1
            settle()
            Event().wait(0.5)
            settle()
            capture("07d-pdf-preview")
            window.router.back()
            window.router.back()

            window.open_sidebar_group(s.list_offerings()[0])
            page.tabs.setCurrentWidget(page.tickets)
            tickets = page.tickets
            tickets.tags.setText("балки")
            tickets.collection.setCurrentIndex(data_index(tickets.collection, data.collection.id))
            tickets.count.setValue(20)
            tickets.tabs.setCurrentIndex(0)
            capture("08-ticket-criteria")
            tickets.generate()
            wait(lambda: tickets.draft is not None)
            assert tickets.model.rowCount() == 20
            capture("09-generated-20")
            tickets.save()
            assert sum(len(v.assignments) for v in tickets.saved_views) == 20
            capture("09b-saved-assignments")
            tickets.unassign()
            tickets.assign()
            assert sum(len(v.assignments) for v in tickets.saved_views) == 20
            report["checks"].append("Generate20 / save snapshots / assign / unassign / restore")
            for width, height in [(960, 620), (1240, 780), (1600, 900)]:
                window.resize(width, height)
                settle()
                for tab in range(3):
                    tickets.tabs.setCurrentIndex(tab)
                    settle()
                    for button in tickets.tabs.currentWidget().findChildren(QPushButton):
                        if button.isVisible():
                            p = button.mapTo(window, button.rect().bottomRight())
                            assert p.x() <= window.width() and p.y() <= window.height(), (
                                button.text()
                            )
                report["resize"].append([window.width(), window.height()])
            window.resize(1240, 780)
            library("seminars")
            capture("10-seminars")
            library("literature")
            capture("11-literature")
            editor = ContentEditor(window, "literature", data.literature[0])
            window.router.push(editor, "Литература · файлы")
            files = editor.file_widgets[0]
            wait(lambda: files.model.rowCount() == 1)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(data.image)), QUrl.fromLocalFile(str(data.pdf))])
            enter = QDragEnterEvent(
                files.drop_zone.rect().center(),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            files.drop_zone.dragEnterEvent(enter)
            assert enter.isAccepted()
            capture("12-drag-drop")
            drop = QDropEvent(
                QPointF(10, 10),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            files.drop_zone.dropEvent(drop)
            wait(lambda: files.model.rowCount() == 3)
            report["checks"].append("Qt multi-file drop / integrity / image and PDF preview")
            window.router.back()
            form = AssessmentDialog(lambda _: None, data.planned, window)
            present_detail(form, window, title="Учебные недели")
            assert form.issue_week.currentData().value == 5
            capture("13-week-selector")
            form.issue_week.showPopup()
            settle()
            assert (
                form.issue_week.view().grab().save(str(args.output / "phase66-13b-combo-popup.png"))
            )
            form.issue_week.hidePopup()
            window.router.back()
            window.open_sidebar_group(s.list_offerings()[0])
            context = page.context()
            lesson = LessonDialog(s, context, data.lectures[0], page)
            present_detail(lesson, page, title="Лекция · посещаемость")
            capture("14-lecture-attendance")
            window.router.back()
            page.open_matrix_student(0)
            card = window.pages.currentWidget()
            card.tabs.setCurrentWidget(card.progress)
            card.progress.tabs.setCurrentWidget(card.progress.charts)
            capture("15-student-charts")
            window.router.back()
            page.tabs.setCurrentWidget(page.analytics)
            start = perf_counter()
            page.analytics.refresh()
            report["performance"]["group_analytics_seconds"] = round(perf_counter() - start, 4)
            page.analytics.tabs.setCurrentWidget(page.analytics.charts)
            page.analytics.charts.tabs.setCurrentIndex(1)
            capture("16-group-charts")
            page.analytics.charts.tabs.setCurrentIndex(2)
            capture("16b-lecture-seminar-charts")
            window.open_sidebar_group(s.list_offerings()[1])
            page.tabs.setCurrentIndex(0)
            capture("17-long-names")
            term_form = TermDialog(lambda _: None, parent=window)
            term_form.show()
            calendar = term_form.start.calendarWidget()
            target = term_form.start.date().addDays(10)
            calendar.clicked.emit(target)
            assert term_form.start.date() == target
            term_form.close()
            term_form.deleteLater()
            visible = [w for w in app.topLevelWidgets() if w.isVisible() and w.isWindow()]
            assert visible == [window], [w.windowTitle() for w in visible]
            report["checks"].append(
                "One MainWindow / long Russian FIO and filenames / Combo / direct calendar"
            )
            window.close()
            QThreadPool.globalInstance().waitForDone()
            app.processEvents()
        finally:
            runtime.close()
            for path in root.rglob("*"):
                if path.is_file():
                    path.chmod(stat.S_IWRITE | stat.S_IREAD)
    (args.output / f"phase66-qa-{args.scale:g}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
