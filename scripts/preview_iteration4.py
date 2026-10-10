"""Twenty synthetic native acceptance captures plus a bounded DPI geometry matrix."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from iteration2_scenario import seed
from preview_iteration3 import add_family
from PySide6.QtCore import QEvent, QItemSelectionModel, QLocale, QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from studium.composition import create_runtime
from studium.presentation.desktop.dialogs import GroupDialog, StudentDetailsDialog
from studium.presentation.desktop.learning import CatalogueForm, LearningCatalogueDialog
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.periods import PeriodManager
from studium.presentation.desktop.problem_picker import ProblemPicker
from studium.presentation.desktop.programs import ProgramForm, WorkProgramPage
from studium.presentation.desktop.theme import apply_theme


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ["QT_SCALE_FACTOR"] = str(args.scale / 2)
    app = QApplication([])
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    output = Path("docs/screenshots/iteration4")
    output.mkdir(parents=True, exist_ok=True)
    report = dict(dpr=app.primaryScreen().devicePixelRatio(), geometry=[], screenshots=[])
    assert abs(report["dpr"] - args.scale) < 0.02

    def fail(*values):
        raise RuntimeError(str(values[-1]))

    QMessageBox.warning = fail

    def settle():
        QTest.qWait(200)
        for _ in range(5):
            app.processEvents()
            QThreadPool.globalInstance().waitForDone()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    with TemporaryDirectory(prefix="studium-iteration4-qa-") as temporary:
        runtime = create_runtime(Path(temporary))
        s = runtime.service
        data = seed(s, Path(temporary))
        family, variants = add_family(s, data)
        s.place_topic_in_module(data.topic.id, data.modules[0][0].id, data.course.id)
        s.create_topic(data.course.id, "Равновесие балки · подтема", parent_topic_id=data.topic.id)
        seminar = s.create_material(
            "seminars",
            title="Семинар · равновесие балки",
            course_id=data.course.id,
            plan_text="Проверить равновесие. Обсудить опорные реакции.",
            problem_ids=(family.id,),
        )
        s.import_file_for_material("seminars", seminar.id, data.pdf)
        window = MainWindow()
        window.initialize(s, runtime.diagnostics)
        window.resize(1240, 780)
        window.show()
        context = next(c for c in s.list_offerings() if c.offering.id == data.offerings[0].id)
        entry = next(
            e
            for e in s.list_students_for_offering(context.offering.id)
            if e.student.id == data.students[0][0].id
        )

        def capture(name, widget=None):
            settle()
            if not args.geometry_only:
                assert (widget or window).grab().save(str(output / (name + ".png")))
                report["screenshots"].append(name)

        def root_library(kind="problems"):
            window.navigation.setCurrentRow(3)
            window.library_page.select_section(kind)
            settle()

        def push(page, title):
            window.router.push(page, title)
            settle()
            return page

        def group(tab=0):
            window.open_sidebar_group(context)
            window.groups_page.tabs.setCurrentIndex(tab)
            settle()
            return window.groups_page

        def card():
            group()
            return push(StudentDetailsDialog(s, context, entry, window), entry.student.full_name)

        try:
            window.navigation.topLevelItem(3).setExpanded(True)
            root_library()
            capture("01-sidebar-selected")
            window.term_combo.showPopup()
            capture("02-period-dropdown", window.term_combo.view().window())
            window.term_combo.hidePopup()
            push(LearningCatalogueDialog(s, data.course, window), "Темы и навыки")
            capture("03-topic-hierarchy")
            page = group(1)
            page.student_view.setColumnWidth(0, 320)
            capture("04-students-columns")
            page.tabs.setCurrentIndex(0)
            capture("05-journal")
            selection = page.matrix_view.selectionModel()
            col = next(
                (
                    i
                    for i, c in enumerate(page.matrix_model.snapshot.columns, 1)
                    if c.kind == "attendance" and c.lessons
                ),
                1,
            )
            for row in (0, 1, 2):
                selection.select(
                    page.matrix_model.index(row, col), QItemSelectionModel.SelectionFlag.Select
                )
            capture("06-attendance-selection")
            root_library()
            bank = window.library_page.lists["problems"]
            bank.search.setText("Равновесие балки")
            bank.load()
            bank.view.selectRow(0)
            bank.preview_variant.setCurrentIndex(1)
            capture("07-bank-preview")
            editor = push(ContentEditor(window, "seminars", seminar), seminar.title)
            editor.tabs.setCurrentWidget(editor.seminar_problems)
            capture("08-seminar-problems")
            editor.tabs.setCurrentIndex(2)
            capture("09-seminar-files")
            window.router.back()
            editor = push(ContentEditor(window, "literature"), "Новый материал")
            editor.tabs.setCurrentIndex(1)
            capture("10-file-drop-zone")
            student = card()
            student.tabs.setCurrentWidget(student.works)
            capture("11-student-works")
            facts = student.works.work_model.rows
            row = next((i for i, f in enumerate(facts) if f.attempts >= 3), 0)
            student.works.work_view.selectRow(row)
            capture("12-student-attempts")
            student.tabs.setCurrentWidget(student.progress)
            student.progress.tabs.setCurrentIndex(0)
            capture("13-progress-homework")
            student.progress.tabs.setCurrentIndex(1)
            capture("14-progress-control")
            box = QMessageBox(
                QMessageBox.Icon.Question,
                "Подтверждение",
                f"Удалить «{data.course.name}» из активной работы?\n\nИстория и прикреплённые файлы сохранятся.\nМатериалы Библиотеки и рабочие программы не будут удалены.",
                parent=window,
            )
            box.addButton("Удалить", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
            box.show()
            capture("15-delete-confirmation", box)
            box.close()
            window.open_help()
            capture("16-help-home")
            window.open_help("attempts")
            capture("17-help-article")
            window.help_page.search.setText("перетащите")
            capture("18-help-search")
            apply_theme("dark")
            capture("19-help-dark")
            window.resize(960, 620)
            root_library()
            bank.view.selectRow(0)
            bank.preview_toggle.click()
            bank.preview_variant.setCurrentIndex(1)
            capture("20-bank-narrow-dark")
            apply_theme("light")
            factories = [
                ("Bank", lambda: (root_library(), window.library_page.lists["problems"])[1]),
                ("GroupStudents", lambda: group(1)),
                ("Journal", lambda: group()),
                ("GroupSettings", lambda: group(7)),
                ("Seminar", lambda: push(ContentEditor(window, "seminars", seminar), "Семинар")),
                ("Problem", lambda: push(ContentEditor(window, "problems", family), "Задача")),
                (
                    "StudentWorks",
                    lambda: (lambda c: (c.tabs.setCurrentWidget(c.works), c)[1])(card()),
                ),
                (
                    "StudentProgress",
                    lambda: (lambda c: (c.tabs.setCurrentWidget(c.progress), c)[1])(card()),
                ),
                ("Topics", lambda: push(LearningCatalogueDialog(s, data.course, window), "Темы")),
                ("TopicForm", lambda: push(CatalogueForm(s, data.course), "Тема")),
                ("GroupForm", lambda: push(GroupDialog(lambda _: None), "Группа")),
                ("ProgramForm", lambda: push(ProgramForm(s, data.course), "Программа")),
                ("Program", lambda: push(WorkProgramPage(window, data.programs[0]), "Программа")),
                ("Periods", lambda: push(PeriodManager(window), "Периоды")),
                ("ProblemPicker", lambda: push(ProblemPicker(s, data.course.id), "Банк")),
                ("Help", lambda: (window.open_help("files"), window.help_page)[1]),
            ]
            for size in ((960, 620), (1240, 780), "maximized"):
                window.showNormal()
                if size == "maximized":
                    window.showMaximized()
                else:
                    window.resize(*size)
                for name, factory in factories:
                    window.navigation.setCurrentRow(0)
                    page = factory()
                    settle()
                    if size != "maximized":
                        assert (
                            abs(window.width() - size[0]) <= 1
                            and abs(window.height() - size[1]) <= 1
                        ), (name, size, window.size())
                    assert page.isVisibleTo(window), name
                    for button in page.findChildren(QPushButton):
                        if button.text() == "Сохранить" and button.isVisibleTo(window):
                            assert window.rect().contains(
                                button.mapTo(window, button.rect().bottomRight())
                            ), name
                    report["geometry"].append(
                        dict(
                            page=name,
                            size=size,
                            window=[window.width(), window.height()],
                            visible=True,
                        )
                    )
            assert args.geometry_only or len(report["screenshots"]) == 20
        finally:
            window.close()
            settle()
            runtime.close()
    (output / f"geometry-{args.scale:g}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        json.dumps(
            dict(
                dpr=report["dpr"],
                geometry=len(report["geometry"]),
                screenshots=len(report["screenshots"]),
            )
        )
    )


if __name__ == "__main__":
    main()
