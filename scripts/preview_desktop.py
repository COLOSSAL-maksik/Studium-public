"""Render desktop screenshots using only synthetic data in a temporary database."""

import argparse
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDateTime, QLocale
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPdfWriter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from studium.application.services import GradeInput
from studium.composition import create_runtime
from studium.domain.communication import CommunicationChannel, CommunicationState
from studium.domain.enums import (
    AssessmentType,
    AttemptResult,
    AttendanceStatus,
    GradeKind,
    ItemOutcome,
)
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.presentation.desktop.analytics import EvidenceDialog
from studium.presentation.desktop.communication import QuestionCaseDialog
from studium.presentation.desktop.dialogs import HistoryDialog, StudentDetailsDialog
from studium.presentation.desktop.files import FilePreviewDialog
from studium.presentation.desktop.learning import (
    AssessmentContentDialog,
    LearningCatalogueDialog,
    LessonDialog,
    LessonForm,
)
from studium.presentation.desktop.main_window import MainWindow
from studium.presentation.desktop.pages import AssessmentStudentsDialog


def analytics_preview(s, window, course, group, offering, students, assessments, capture):
    """All item structure is recorded before presentations lock the semantics."""
    now = UtcInstant.now()

    def past(days):
        return UtcInstant(now.value - timedelta(days=days))

    topic = s.create_topic(course.id, "Построение эпюр")
    child = s.create_topic(course.id, "Эпюра M", parent_topic_id=topic.id)
    skill = s.create_skill(course.id, "Определяет знак изгибающего момента")
    s.attach_topic_skill(child.id, skill.id)
    revised = []
    for assessment in assessments:
        revised.append(s.update_assessment(assessment, issued_at=past(8), due_at=past(2)))
    assessments = revised
    s.set_assessment_content(assessments[0].id, [topic.id, child.id], [skill.id])
    items = []
    for i, title in enumerate(
        ["Задача 1 — реакции опор", "Задача 2 — знак M", "Задача 3 — эпюра M"]
    ):
        item = s.create_assessment_item(
            assessments[0].id, title, max_score=[3, 4, 3][i], sort_order=i
        )
        s.set_assessment_content(item.id, [topic.id, child.id], [skill.id], item=True)
        items.append(item)
    work = s.get_or_create_work(students[0].id, assessments[0].id)
    first = s.add_attempt(
        work.id,
        past(4),
        AttemptResult.NEEDS_REVISION,
        comment="Проверить знак момента на втором участке.",
    )
    for item, outcome, score in zip(
        items,
        [ItemOutcome.CORRECT, ItemOutcome.PARTIAL, ItemOutcome.INCORRECT],
        [3, 2, 0],
        strict=True,
    ):
        s.create_attempt_item_result(
            first.id,
            item.id,
            outcome=outcome,
            score=score,
            max_score=item.max_score,
            teacher_comment="Синтетический пример",
        )
    second = s.add_attempt(
        work.id,
        past(1),
        AttemptResult.ACCEPTED,
        score=9,
        max_score=10,
        comment="Исправление проверено.",
    )
    for item in items:
        s.create_attempt_item_result(
            second.id,
            item.id,
            outcome=ItemOutcome.CORRECT,
            score=item.max_score,
            max_score=item.max_score,
        )
    for index, student in enumerate(students[1:]):
        other = s.get_or_create_work(student.id, assessments[0].id)
        attempt = s.add_attempt(
            other.id,
            past(3 - index),
            [AttemptResult.ACCEPTED, AttemptResult.NEEDS_REVISION, AttemptResult.PRESENTED][index],
            score=[7, 4, None][index],
            max_score=10,
        )
        s.create_attempt_item_result(
            attempt.id,
            items[1].id,
            outcome=[ItemOutcome.CORRECT, ItemOutcome.PARTIAL, ItemOutcome.NOT_EVALUATED][index],
        )
    done = s.get_or_create_work(students[0].id, assessments[1].id)
    s.add_attempt(done.id, past(3), AttemptResult.ACCEPTED, score=8, max_score=10)
    for day, statuses in [
        (
            1,
            [
                AttendanceStatus.PRESENT,
                AttendanceStatus.PRESENT,
                AttendanceStatus.ABSENT,
                AttendanceStatus.UNKNOWN,
            ],
        ),
        (
            2,
            [
                AttendanceStatus.LATE,
                AttendanceStatus.EXCUSED,
                AttendanceStatus.PRESENT,
                AttendanceStatus.PRESENT,
            ],
        ),
    ]:
        lesson = s.create_lesson(
            offering.id,
            LocalDate(2026, 10, day),
            title="Метод сечений и эпюры",
            topic_ids=[child.id],
        )
        for entry, status in zip(s.list_students_for_offering(offering.id), statuses, strict=True):
            s.mark_attendance(lesson.id, entry.enrollment.id, status)
    case = s.create_question_case(
        students[0].id,
        "Как проверить знак M?",
        past(2),
        course_offering_id=offering.id,
        context={"topic": [child.id], "skill": [skill.id], "assessment": [assessments[0].id]},
    )
    s.add_teacher_message(
        case.id,
        "Проверьте направление момента в методе сечений.",
        UtcInstant(past(2).value + timedelta(hours=3)),
    )
    s.create_question_case(
        students[2].id,
        "Почему эпюра меняет знак?",
        past(1),
        course_offering_id=offering.id,
        context={"topic": [child.id], "skill": [skill.id]},
    )
    context = s.list_offerings()[0]
    entry = next(
        r for r in s.list_students_for_offering(offering.id) if r.student.id == students[0].id
    )
    window.refresh()
    window.navigation.setCurrentRow(1)
    window.groups_page.open_group(group)
    window.groups_page.tabs.setCurrentWidget(window.groups_page.analytics)
    capture(window, "phase6-group-analytics.png")
    student = StudentDetailsDialog(s, context, entry, window)
    student.resize(1100, 800)
    student.tabs.setCurrentWidget(student.progress)
    student.progress.metrics.enabled.setChecked(True)
    student.progress.metrics.cutoff.setDateTime(
        QDateTime.fromMSecsSinceEpoch(past(2).epoch_microseconds // 1000)
    )
    student.progress.refresh()
    capture(student, "phase6-student-progress.png")
    student.close()
    assessment = AssessmentStudentsDialog(s, context, assessments[0], window)
    assessment.resize(1080, 780)
    assessment.tabs.setCurrentIndex(1)
    capture(assessment, "phase6-assessment-analytics.png")
    assessment.close()
    history = HistoryDialog(s, work.id, parent=window)
    history.detail_tabs.setCurrentIndex(1)
    capture(history, "phase6-attempt-item-results.png")
    history.close()
    for entity, is_skill, name in [
        (child, False, "phase6-topic-evidence.png"),
        (skill, True, "phase6-skill-evidence.png"),
    ]:
        dialog = EvidenceDialog(s, entity, skill=is_skill, offering_id=offering.id, parent=window)
        capture(dialog, name)
        dialog.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", choices=(2, 3, 4, 5, 6), default=2, type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setApplicationName("Studium")
    # Windows offscreen has no system font database. Load existing fonts into this
    # process only; normal desktop launch uses Qt's native Windows font discovery.
    if os.name == "nt" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        fonts = Path(os.environ["WINDIR"]) / "Fonts"
        for filename in ("segoeui.ttf", "seguisym.ttf"):
            if QFontDatabase.addApplicationFont(str(fonts / filename)) < 0:
                raise RuntimeError("Existing Windows preview font could not be loaded")
        font = QFont("Segoe UI", 10)
        font.setFamilies(["Segoe UI", "Segoe UI Symbol"])
        app.setFont(font)
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))

    def capture(widget, name):
        if not name.startswith(f"phase{args.phase}-"):
            return
        widget.show()
        QTest.qWait(100)
        if not widget.grab().save(str(args.output / name)):
            raise RuntimeError("Screenshot could not be saved")

    with TemporaryDirectory(prefix="studium-preview-") as temporary:
        runtime = create_runtime(Path(temporary))
        try:
            s = runtime.service
            window = MainWindow()
            window.initialize(s, runtime.diagnostics)
            capture(window, "phase2-first-run.png")
            term = s.create_term("2026/2027 — Осень", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
            course = s.create_course("Сопротивление материалов", "Сопромат")
            group = s.create_group("ТЕСТ-31", "Тестовая кафедра")
            offering = s.create_offering(term.id, course.id, group.id)
            students = [
                s.create_student(offering.id, name, notes)
                for name, notes in [
                    ("Тестовый Александр", "Уверенно решает задачи; нужно внимание к знакам."),
                    ("Тестовая Мария", "Аккуратное оформление, задаёт уточняющие вопросы."),
                    ("Тестовый Николай", "Полезно повторить построение эпюр."),
                    ("Тестовая Ольга", "Самостоятельно проверяет промежуточные результаты."),
                ]
            ]
            assessments = [
                s.create_assessment(offering.id, title, kind, number=str(i + 1), max_score=10)
                for i, (title, kind) in enumerate(
                    [
                        ("ДЗ №1", AssessmentType.HOMEWORK),
                        ("ДЗ №2", AssessmentType.HOMEWORK),
                        ("ДЗ №3", AssessmentType.HOMEWORK),
                        ("КР №1", AssessmentType.CONTROL_WORK),
                    ]
                )
            ]
            if args.phase == 6:
                analytics_preview(
                    s, window, course, group, offering, students, assessments, capture
                )
                window.close()
                app.processEvents()
                return
            work = s.get_or_create_work(students[0].id, assessments[0].id)
            s.add_attempt(
                work.id,
                UtcInstant(datetime(2026, 10, 3, 9, 30, tzinfo=UTC)),
                AttemptResult.NEEDS_REVISION,
                comment="Ошибка знака M на втором участке; проверить направление момента.",
            )
            s.add_attempt(
                work.id,
                UtcInstant(datetime(2026, 10, 5, 10, tzinfo=UTC)),
                AttemptResult.ACCEPTED,
                comment="Исправление проверено.",
                score=9,
                max_score=10,
                grade=GradeInput(GradeKind.PASS_FAIL, passed=True),
            )
            other = s.get_or_create_work(students[1].id, assessments[0].id)
            s.add_attempt(other.id, UtcInstant.now(), AttemptResult.ACCEPTED)
            other = s.get_or_create_work(students[2].id, assessments[1].id)
            s.add_attempt(
                other.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION, comment="Повторить эпюры."
            )
            window.refresh()
            window.navigation.setCurrentRow(1)
            window.groups_page.open_group(group)
            window.groups_page.tabs.setCurrentIndex(1)
            capture(window, "phase2-students.png")
            window.groups_page.tabs.setCurrentIndex(0)
            capture(window, "phase2-matrix.png")
            history = HistoryDialog(s, work.id, parent=window)
            history.view.setCurrentIndex(history.model.index(0, 0))
            capture(history, "phase2-attempts.png")
            history.close()
            context = s.list_offerings()[0]
            entry = next(
                x
                for x in s.list_students_for_offering(offering.id)
                if x.student.id == students[0].id
            )
            student = StudentDetailsDialog(s, context, entry, window)
            capture(student, "phase2-student-card.png")
            student.close()
            if args.phase == 5:
                topic = s.create_topic(course.id, "Эпюра M")
                skill = s.create_skill(course.id, "Определяет знак изгибающего момента")
                question_work = s.get_or_create_work(students[0].id, assessments[2].id)
                first = s.add_attempt(
                    question_work.id,
                    UtcInstant(datetime(2026, 10, 1, 15, 30, tzinfo=UTC)),
                    AttemptResult.NEEDS_REVISION,
                    comment="Проверьте знаки на втором участке.",
                )
                case = s.create_question_case(
                    students[0].id,
                    "Не понимаю, почему момент на втором участке отрицательный.\n\nПрикладываю свой расчёт и схему балки.",
                    UtcInstant(datetime(2026, 10, 1, 15, 42, tzinfo=UTC)),
                    course_offering_id=offering.id,
                    title="Знак момента на втором участке",
                    channel=CommunicationChannel.TELEGRAM,
                    context={
                        "assessment": [assessments[2].id],
                        "topic": [topic.id],
                        "skill": [skill.id],
                    },
                )
                # The recorded attempt belongs to ДЗ №3 and the same student.
                s.attach_question_context(case.id, "attempt", first.id)
                s.add_teacher_message(
                    case.id,
                    "Проверьте направление отсечённой части.\nЗнак M определяется выбранной стороной сечения.\n\nПокажите положительное направление на своей схеме.",
                    UtcInstant(datetime(2026, 10, 1, 16, 10, tzinfo=UTC)),
                    channel=CommunicationChannel.TELEGRAM,
                )
                s.create_question_case(
                    students[1].id,
                    "Как выбрать отсечённую часть для метода сечений?",
                    UtcInstant(datetime(2026, 10, 1, 16, 30, tzinfo=UTC)),
                    course_offering_id=offering.id,
                    channel=CommunicationChannel.EMAIL,
                    title="Метод сечений",
                )
                closed = s.create_question_case(
                    students[2].id,
                    "Нужно ли указывать единицы на эпюре?",
                    UtcInstant(datetime(2026, 9, 29, 12, tzinfo=UTC)),
                    course_offering_id=offering.id,
                    title="Единицы измерения",
                )
                s.add_teacher_message(
                    closed.id,
                    "Да, подпишите оси и единицы измерения.",
                    UtcInstant(datetime(2026, 9, 29, 13, tzinfo=UTC)),
                )
                s.close_question_case(closed)
                window.refresh()
                window.navigation.setCurrentRow(2)
                capture(window, "phase5-questions.png")
                dialog = QuestionCaseDialog(s, case.id, window)
                capture(dialog, "phase5-correspondence.png")
                message = s.list_messages(case.id)[0]
                source = Path(temporary) / "synthetic-question.png"
                image = QImage(800, 600, QImage.Format.Format_RGB32)
                image.fill(QColor("white"))
                painter = QPainter(image)
                painter.setFont(QFont("Segoe UI", 20))
                painter.setPen(QColor("#26384b"))
                painter.drawText(50, 65, "Синтетический пример · эпюра M")
                painter.drawLine(100, 240, 700, 240)
                painter.drawLine(100, 240, 100, 360)
                painter.drawLine(100, 360, 700, 240)
                painter.drawText(120, 410, "M < 0 · второй участок")
                painter.end()
                assert image.save(str(source), "PNG")
                s.import_file_for_message(message.id, source)
                dialog.refresh()
                dialog.message_view.selectRow(0)
                capture(dialog, "phase5-message-attachment.png")
                preview = FilePreviewDialog(s, s.list_message_attachments(message.id)[0], dialog)
                capture(preview, "phase5-image-preview.png")
                preview.close()
                dialog.close()
                card = StudentDetailsDialog(s, context, entry, window)
                card.tabs.setCurrentWidget(card.questions)
                capture(card, "phase5-student-questions.png")
                card.close()
                window.questions_page.state.setCurrentIndex(
                    window.questions_page.state.findData(CommunicationState.WAITING)
                )
                capture(window, "phase5-waiting.png")
            if args.phase == 4:
                history_entries = s.history(work.id).entries
                sources = Path(temporary) / "synthetic-sources"
                sources.mkdir()
                for page in (1, 2):
                    image = QImage(900, 1150, QImage.Format.Format_RGB32)
                    image.fill(QColor("white"))
                    painter = QPainter(image)
                    painter.setFont(QFont("Segoe UI", 24))
                    painter.setPen(QColor("#26384b"))
                    painter.drawText(70, 100, f"Синтетическая работа · страница {page}")
                    painter.setFont(QFont("Segoe UI", 18))
                    painter.drawText(70, 170, "Учебный пример. Реальные данные не используются.")
                    painter.drawLine(100, 400, 800, 400)
                    painter.drawLine(100, 420, 100, 500)
                    painter.drawLine(800, 420, 800, 500)
                    painter.drawText(330, 470, "Схема балки")
                    painter.drawText(70, 660, "Расчёт реакций опор и эпюр")
                    painter.drawText(70, 730, "Rₐ + Rᵦ = F")
                    painter.end()
                    path = sources / f"page{page}.jpg"
                    assert image.save(str(path), "JPEG")
                    s.import_file_for_attempt(history_entries[0].attempt.id, path)
                pdf = sources / "corrected.pdf"
                writer = QPdfWriter(str(pdf))
                painter = QPainter(writer)
                painter.drawText(300, 500, "Synthetic corrected work")
                painter.end()
                del painter, writer
                s.import_file_for_attempt(history_entries[1].attempt.id, pdf)
                history = HistoryDialog(s, work.id, parent=window)
                history.files.view.selectRow(0)
                capture(history, "phase4-attempt-files.png")
                history.close()
                entries = s.list_attempt_attachments(history_entries[0].attempt.id)
                preview = FilePreviewDialog(s, entries[0], window)
                capture(preview, "phase4-image-preview.png")
                preview.close()
                student = StudentDetailsDialog(s, context, entry, window)
                student.tabs.setCurrentWidget(student.files)
                for _ in range(100):
                    if student.files.model.rowCount():
                        break
                    QTest.qWait(20)
                capture(student, "phase4-student-files.png")
                student.close()
                missing = s.accessible_file_path(entries[1].asset.id)
                missing.chmod(stat.S_IREAD | stat.S_IWRITE)
                missing.unlink()
                history = HistoryDialog(s, work.id, parent=window)
                capture(history, "phase4-missing-file.png")
                history.close()
            if args.phase == 3:
                topic = s.create_topic(
                    course.id, "Построение эпюр", description="Синтетический учебный пример"
                )
                topics = [
                    s.create_topic(course.id, title, parent_topic_id=topic.id, sort_order=i)
                    for i, title in enumerate(["Эпюра N", "Эпюра Q", "Эпюра M"])
                ]
                skill = s.create_skill(
                    course.id, "Определяет знак Q", description="Синтетический проверяемый навык"
                )
                s.attach_topic_skill(topics[1].id, skill.id)
                lesson = s.create_lesson(
                    offering.id,
                    LocalDate(2026, 10, 1),
                    title="Метод сечений и эпюры",
                    notes="Разобрали реакции опор, метод сечений и эпюру Q. Начали эпюру M.",
                    topic_ids=[topics[1].id, topics[2].id],
                )
                for entry, status in zip(
                    s.list_students_for_offering(offering.id),
                    [
                        AttendanceStatus.PRESENT,
                        AttendanceStatus.LATE,
                        AttendanceStatus.ABSENT,
                        AttendanceStatus.UNKNOWN,
                    ],
                    strict=True,
                ):
                    s.mark_attendance(lesson.id, entry.enrollment.id, status)
                s.set_assessment_content(
                    assessments[2].id, [topics[1].id, topics[2].id], [skill.id]
                )
                item = s.create_assessment_item(
                    assessments[2].id, "Задание 1 — эпюра Q", max_score=5
                )
                s.set_assessment_content(item.id, [topics[1].id], [skill.id], item=True)
                s.create_assessment_item(
                    assessments[2].id, "Задание 2 — эпюра M", max_score=5, sort_order=1
                )
                window.refresh()
                window.groups_page.tabs.setCurrentWidget(window.groups_page.lessons_page)
                capture(window, "phase3-lessons.png")
                for dialog, name in [
                    (LearningCatalogueDialog(s, course, window), "phase3-catalogue.png"),
                    (LessonDialog(s, context, lesson, window), "phase3-lesson.png"),
                    (
                        AssessmentContentDialog(s, context, assessments[2], window),
                        "phase3-assessment.png",
                    ),
                    (LessonForm(s, context, lesson, window), "phase3-lesson-form.png"),
                ]:
                    capture(dialog, name)
                    dialog.close()
            window.close()
            app.processEvents()
        finally:
            runtime.close()


if __name__ == "__main__":
    main()
