"""Compact acceptance set; native DPI geometry uses temporary synthetic profiles."""

import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from iteration2_scenario import seed
from PySide6.QtCore import QEvent, QLocale, QThreadPool
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from studium.composition import create_runtime
from studium.domain.content import GenerationCriteria, ProblemPurpose
from studium.presentation.desktop.learning import CatalogueForm
from studium.presentation.desktop.library import ContentEditor
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.programs import ModuleForm, ProgramForm, ProgramWorkForm
from studium.presentation.desktop.quick_attempt import QuickAttemptDialog
from studium.presentation.desktop.theme import apply_theme
from studium.presentation.desktop.visuals import Disclosure


def add_family(service, data):
    family = service.create_material(
        "problems",
        course_id=data.course.id,
        title="Равновесие балки · общее условие",
        identifier="Б-01",
        is_family=True,
        statement="Для показанной схемы определить опорные реакции, построить эпюры Q и M.\nПроверить равновесие и размерности.",
        purposes=(ProblemPurpose.SEMINAR, ProblemPurpose.CONTROL),
        tags=("балки", "равновесие"),
    )
    service.set_content_links("problem_topics", family.id, (data.topic.id,))
    service.set_content_links("problem_skills", family.id, (data.skill.id,))
    variants = []
    for i in range(1, 4):
        variant = service.create_material(
            "problems",
            course_id=data.course.id,
            family_id=family.id,
            title=f"Вариант {i}",
            variant_code=str(i),
            parameters=f"L = {3 + i} м; F = {10 * i} кН",
            correct_answer=f"Синтетический эталон {i}",
        )
        image = QImage(480, 180, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        painter.setPen(QPen(QColor("#263953"), 3))
        painter.drawLine(40, 100, 440, 100)
        painter.drawLine(60, 100, 45, 125)
        painter.drawLine(60, 100, 75, 125)
        painter.drawLine(45, 125, 75, 125)
        painter.drawEllipse(410, 110, 14, 14)
        x = 100 + i * 70
        painter.drawLine(x, 40, x, 95)
        painter.drawLine(x, 95, x - 7, 82)
        painter.drawLine(x, 95, x + 7, 82)
        painter.drawText(30, 25, f"Synthetic scheme {i}: F={10 * i} kN; L={3 + i} m")
        painter.end()
        scheme = data.image.parent / f"iteration3-scheme-{i}.png"
        assert image.save(str(scheme))
        service.import_file_for_material("problems", variant.id, scheme)
        variants.append(variant)
    return family, variants


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--native-base-scale", type=float, default=2)
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("docs/screenshots/iteration3"))
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ["QT_SCALE_FACTOR"] = str(args.scale / args.native_base_scale)
    os.environ.pop("QT_SCREEN_SCALE_FACTORS", None)
    app = QApplication([])
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    report = {"dpr": app.primaryScreen().devicePixelRatio(), "geometry": [], "screenshots": []}
    assert abs(report["dpr"] - args.scale) < 0.02

    def fail(*values):
        raise RuntimeError(values[-1])

    QMessageBox.warning = fail

    def settle():
        for _ in range(5):
            app.processEvents()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    with TemporaryDirectory(prefix="studium-iteration3-qa-") as temporary:
        runtime = create_runtime(Path(temporary))
        window = MainWindow()
        window.initialize(runtime.service, runtime.diagnostics)
        window.resize(1240, 780)
        window.show()
        data = seed(runtime.service, Path(temporary))
        s = runtime.service
        family, _ = add_family(s, data)
        for context in reversed(s.list_offerings()):
            s.remember_offering(context.offering.id)
        window.refresh()

        def capture(name):
            settle()
            if not args.geometry_only:
                assert window.grab().save(str(output / (name + ".png")))
                report["screenshots"].append(name)

        def push(page, title):
            window.router.push(page, title)
            settle()
            return page

        def journal():
            window.open_sidebar_group(s.list_offerings()[0])
            settle()
            return window.groups_page.matrix_view

        def verify_form(form, size):
            push(form, form.windowTitle() or "Новый материал")
            settle()
            # Fractional native DPI rounds the client rectangle by one logical pixel.
            assert abs(window.width() - size[0]) <= 1 and abs(window.height() - size[1]) <= 1, (
                form,
                window.size(),
                size,
            )
            for disclosure in form.findChildren(Disclosure):
                disclosure.toggle.setChecked(True)
            settle()
            if isinstance(form, QuickAttemptDialog):
                form.details_button.setChecked(True)
                settle()
            saves = [b for b in form.findChildren(QPushButton) if b.text() == "Сохранить"]
            assert saves
            for save in saves:
                assert save.isVisibleTo(window)
                assert window.rect().contains(save.mapTo(window, save.rect().bottomRight())), (
                    form,
                    save.geometry(),
                )
            scroll = form.scroll
            assert scroll.widget().minimumSizeHint().width() <= scroll.viewport().width(), (
                form,
                scroll.widget().minimumSizeHint(),
                scroll.viewport().size(),
            )
            report["geometry"].append(
                {
                    "form": type(form).__name__,
                    "size": list(size),
                    "vertical_scroll": scroll.verticalScrollBar().maximum(),
                    "save_visible": True,
                }
            )
            window.router.back()
            settle()

        try:
            capture("01-home")
            window.navigation.topLevelItem(1).setExpanded(True)
            capture("02-sidebar-work")
            window.navigation.topLevelItem(1).setExpanded(False)
            window.navigation.topLevelItem(3).setExpanded(True)
            capture("03-sidebar-library")
            window.navigation.topLevelItem(3).setExpanded(False)
            view = journal()
            capture("04-journal")
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().maximum())
            settle()
            assert view.frozen.y() + view.frozen.viewport().y() == view.viewport().y()
            capture("05-journal-scrolled")
            window.navigation.setCurrentRow(3)
            for kind, name in (("homework", "06-homework"), ("problems", "07-problem-bank")):
                window.library_page.select_section(kind)
                capture(name)
            editor = push(ContentEditor(window, "problems", family), family.title)
            editor.tabs.setCurrentWidget(editor.variant_page)
            capture("08-problem-family")
            window.router.back()
            s.save_ticket_set(
                data.offerings[0].id,
                s.generate_ticket_draft(
                    GenerationCriteria(
                        data.course.id, 3, purpose=ProblemPurpose.CONTROL, problem_ids=(family.id,)
                    )
                ),
                title="Рубежный контроль · три варианта",
            )
            for kind, name in (
                ("control", "09-control-sets"),
                ("seminars", "10-seminars"),
                ("lectures", "11-lectures"),
            ):
                window.library_page.select_section(kind)
                capture(name)
            window.resize(960, 620)
            editor = push(ContentEditor(window, "problems"), "Новый материал")
            capture("12-new-material")
            next(
                d for d in editor.findChildren(Disclosure) if d.toggle.text() == "Дополнительно"
            ).toggle.setChecked(True)
            settle()
            editor.scroll.ensureWidgetVisible(editor.fields["difficulty"])
            capture("13-new-material-advanced")
            window.router.back()
            window.resize(1240, 780)
            journal()
            apply_theme("dark")
            capture("14-dark-journal")
            window.navigation.setCurrentRow(3)
            window.library_page.select_section("problems")
            capture("15-dark-library")
            apply_theme("light")
            window.resize(960, 620)
            journal()
            capture("16-narrow-journal")
            for theme in ("light", "dark"):
                apply_theme(theme)
                for size in ((960, 620), (1240, 780)):
                    window.resize(*size)
                    settle()
                    program = data.programs[0]
                    factories = [
                        lambda: ContentEditor(window, "problems"),
                        lambda: ContentEditor(window, "homework"),
                        lambda: ProgramForm(s, data.course),
                        lambda: ModuleForm(s, program),
                        lambda: ProgramWorkForm(s, program),
                        lambda: CatalogueForm(s, data.course),
                        lambda: CatalogueForm(s, data.course, skill=True),
                        lambda: QuickAttemptDialog(
                            s, data.students[0][0], data.homework_assessments[0]
                        ),
                    ]
                    for factory in factories:
                        verify_form(factory(), size)
                    view = journal()
                    view.horizontalScrollBar().setValue(view.horizontalScrollBar().maximum())
                    settle()
                    assert view.frozen.y() + view.frozen.viewport().y() == view.viewport().y()
                    assert (
                        view.frozen.horizontalHeader().height() == view.horizontalHeader().height()
                    )
                    assert view.frozen.horizontalHeader().isVisibleTo(window)
                    report["geometry"].append(
                        {
                            "form": "Journal",
                            "theme": theme,
                            "size": list(size),
                            "frozen_aligned": True,
                        }
                    )
                window.showMaximized()
                settle()
                verify_form(ContentEditor(window, "problems"), (window.width(), window.height()))
                window.showNormal()
            report["schema"] = runtime.diagnostics.schema_version
        finally:
            window.close()
            QThreadPool.globalInstance().waitForDone()
            settle()
            runtime.close()
    path = output / f"geometry-{int(args.scale * 100)}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(
        json.dumps(
            {
                "dpr": report["dpr"],
                "geometry_checks": len(report["geometry"]),
                "screenshots": len(report["screenshots"]),
                "report": str(path),
            }
        )
    )


if __name__ == "__main__":
    main()
