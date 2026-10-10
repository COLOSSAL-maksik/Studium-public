"""Synthetic Iteration 1 acceptance dataset, only for an isolated application root."""

from pathlib import Path

from phase65_scenario import seed as seed_existing
from PySide6.QtGui import QFont, QPainter, QPdfWriter

from studium.domain.content import GenerationCriteria, LiteratureType, MaterialFileRole
from studium.domain.enums import AssessmentType, AttendanceStatus, LessonType
from studium.domain.value_objects import AcademicWeekNumber, LocalDate


def seed(service, directory):
    directory = Path(directory)
    data = seed_existing(service, directory)
    image = directory / "synthetic-work.png"
    pdf = directory / "Синтетическое методическое пособие — длинное название файла.pdf"
    writer = QPdfWriter(str(pdf))
    writer.setTitle("Синтетический учебный пример")
    painter = QPainter(writer)
    painter.setFont(QFont("Segoe UI", 20))
    painter.drawText(350, 700, "Studium · синтетический пример")
    painter.drawText(350, 1100, "Учебная схема. Только placeholder content.")
    painter.drawLine(500, 2000, 5500, 2000)
    painter.drawLine(500, 2000, 3000, 1300)
    painter.drawLine(3000, 1300, 5500, 2000)
    painter.end()
    del painter
    del writer
    collection = service.create_problem_collection(data.course.id, "как в ДЗ")
    advanced = service.create_problem_collection(data.course.id, "РК1 · повышенная сложность")
    data.problems = []
    for category in ("балки", "рамы"):
        for i in range(22):
            problem = service.create_material(
                "problems",
                course_id=data.course.id,
                title=f"{'Балка' if category == 'балки' else 'Рама'} {i + 1:02d} · эпюры Q и M",
                statement=f"Синтетическое условие №{i + 1}. Постройте эпюры Q и M; проверьте равновесие.\n\nL = {2 + i % 5} м, F = {10 + i} кН. Схема приложена.",
                correct_answer=f"Синтетический эталон: реакция A = {5 + i} кН; момент M = {10 + 2 * i} кН·м.",
                solution="1. Записать равновесие.\n2. Разбить на участки.\n3. Проверить знаки. Только пример для QA.",
                tags=(category, "изгиб"),
                difficulty="Базовая",
                notes="Placeholder: не учебник и не реальная работа.",
            )
            service.set_problem_collection(collection.id, problem.id, included=True)
            if i % 2 == 0:
                service.set_problem_collection(advanced.id, problem.id, included=True)
            service.import_file_for_material("problems", problem.id, image)
            service.import_file_for_material(
                "problems", problem.id, image, role=MaterialFileRole.REFERENCE
            )
            if i == 0:
                service.import_file_for_material(
                    "problems", problem.id, pdf, role=MaterialFileRole.REFERENCE
                )
            data.problems.append(problem)
    data.homework, data.seminars, data.literature, data.lectures = [], [], [], []
    for number in range(1, 6):
        homework = service.create_material(
            "homework",
            course_id=data.course.id,
            title=f"ДЗ №{number} · Построение эпюр Q и M",
            label=str(number),
            description=f"Синтетическое ДЗ №{number}. Рассчитать реакции опор и построить эпюры.\n\nПроверьте размерности.",
            tags=("балки", "изгиб"),
        )
        service.import_file_for_material("homework", homework.id, image)
        data.homework.append(homework)
        seminar = service.create_material(
            "seminars",
            course_id=data.course.id,
            title=f"Семинар {number} · Эпюры и метод сечений",
            planned_week=AcademicWeekNumber(number),
            topic_ids=(data.topic.id,),
            plan_text="1. Обсуждение вопросов (10 мин).\n2. Синтетический пример (40 мин).\n3. Самостоятельная проверка (20 мин).",
            full_text=f"# Неделя {number}\n\nСинтетический конспект в переносимом Markdown.\n\nОпределяем знаки Q и M методом сечений.",
            tags=("балки",),
        )
        service.import_file_for_material("seminars", seminar.id, image)
        data.seminars.append(seminar)
        lecture = service.create_lesson(
            data.offerings[0].id,
            LocalDate(2026, 9, 1 + (number - 1) * 7),
            type=LessonType.LECTURE,
            title=f"Лекция {number} · Изгиб и внутренние силовые факторы",
            notes="Синтетическая посещаемость, вручную со слов лектора.",
        )
        for i, entry in enumerate(service.list_students_for_offering(data.offerings[0].id)):
            service.mark_attendance(
                lecture.id,
                entry.enrollment.id,
                AttendanceStatus.PRESENT if i % 4 else AttendanceStatus.ABSENT,
            )
        data.lectures.append(lecture)
    for title, kind in [
        ("Синтетический учебник по сопротивлению материалов", LiteratureType.TEXTBOOK),
        ("Методические указания: эпюры Q и M", LiteratureType.METHOD_GUIDE),
        ("Синтетическая статья: метод сечений", LiteratureType.ARTICLE),
    ]:
        item = service.create_material(
            "literature",
            course_id=data.course.id,
            title=title,
            type=kind,
            authors="Автор синтетического примера",
            year=2026,
            tags=("изгиб",),
            notes="Только placeholder, без copyrighted textbook content.",
        )
        service.import_file_for_material("literature", item.id, pdf)
        data.literature.append(item)
    definition = data.homework[0]
    data.planned = service.create_assessment(
        data.offerings[0].id,
        "ДЗ из библиотеки · недели 5–7",
        AssessmentType.HOMEWORK,
        description=definition.description,
        homework_definition_id=definition.id,
        planned_issue_week=AcademicWeekNumber(5),
        planned_due_week=AcademicWeekNumber(7),
    )
    criteria = GenerationCriteria(data.course.id, 20, 1, ("балки",), collection.id, 66)
    data.ticket_set = service.save_ticket_set(
        data.offerings[0].id,
        service.generate_ticket_draft(criteria),
        title="МТ5-31 · 20 вариантов · балки · как в ДЗ",
        assessment_id=data.assessments[0][8].id,
        assign_students=True,
    )
    data.collection, data.image, data.pdf = collection, image, pdf
    return data
