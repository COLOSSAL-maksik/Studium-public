"""Reusable, realistic synthetic teaching data. Always pass an isolated runtime."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QImage, QPainter

from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, ItemOutcome
from studium.domain.value_objects import LocalDate, UtcInstant


def seed(service, directory):
    directory = Path(directory)
    base = datetime(2026, 9, 1, 9, tzinfo=UTC)
    tick = [0]

    def clock():
        tick[0] += 1
        return UtcInstant(base + timedelta(seconds=tick[0]))

    original_clock = service._clock
    service._clock = clock
    try:
        term = service.create_term("Осень 2026", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
        course = service.create_course("Сопротивление материалов", "Сопротивление материалов")
        parent = service.create_topic(course.id, "Внутренние силовые факторы")
        topics = [
            service.create_topic(course.id, title, parent_topic_id=parent.id)
            for title in ["Эпюра Q", "Эпюра M", "Расчёт напряжений"]
        ]
        skill = service.create_skill(course.id, "Определение знака изгибающего момента")
        service.attach_topic_skill(topics[1].id, skill.id)
        groups, offerings, students, assessments, lessons = [], [], [], [], []
        surnames = [
            "Александров",
            "Белов",
            "Васильева",
            "Громов",
            "Данилова",
            "Егоров",
            "Жукова",
            "Зайцев",
            "Иванова",
            "Козлов",
            "Лебедева",
            "Морозов",
            "Никитина",
            "Орлов",
            "Павлова",
            "Романов",
            "Соколова",
            "Тихонов",
            "Уварова",
            "Фёдоров",
        ]
        for group_index in range(2):
            group = service.create_group(f"МТ5-{31 + group_index}", "Прикладная механика")
            offering = service.create_offering(term.id, course.id, group.id)
            groups.append(group)
            offerings.append(offering)
            roster = [
                service.create_student(
                    offering.id,
                    f"{name} {'Александр Сергеевич' if i % 2 == 0 else 'Мария Александровна'}",
                    notes="Самостоятельно проверяет расчёт. Обсудили оформление эпюр."
                    if i == 0
                    else "",
                )
                for i, name in enumerate(surnames)
            ]
            if group_index == 1:
                roster[-1] = service.update_student(
                    roster[-1],
                    full_name="Синтетический Очень-Длинный-Фамильный Александр Константинович",
                )
            students.append(roster)
            works = []
            for i in range(10):
                title = (
                    f"ДЗ №{i + 1}"
                    if i < 8
                    else f"КР №{i - 7} · {'Изгиб и эпюры' if i == 8 else 'Проверка расчёта напряжений и деформаций'}"
                )
                work = service.create_assessment(
                    offering.id,
                    title,
                    AssessmentType.HOMEWORK if i < 8 else AssessmentType.CONTROL_WORK,
                    number=str(i + 1 if i < 8 else i - 7),
                    max_score=10 if i < 8 else 20,
                    issued_at=UtcInstant(base + timedelta(days=3 + i)),
                    due_at=UtcInstant(base + timedelta(days=10 + i * 3)),
                )
                service.set_assessment_content(
                    work.id, [topics[i % 3].id], [skill.id] if i % 3 == 1 else []
                )
                item = service.create_assessment_item(work.id, "Построение эпюры M", max_score=5)
                service.set_assessment_content(item.id, [topics[1].id], [skill.id], item=True)
                for student_index, student in enumerate(roster):
                    marker = (student_index + i) % 5
                    if marker == 4:
                        continue
                    assigned = service.get_or_create_work(student.id, work.id)
                    first_result = [
                        AttemptResult.NEEDS_REVISION,
                        AttemptResult.ACCEPTED,
                        AttemptResult.PRESENTED,
                        AttemptResult.NEEDS_REVISION,
                    ][marker]
                    attempt = service.add_attempt(
                        assigned.id,
                        UtcInstant(base + timedelta(days=7 + i * 2, hours=student_index)),
                        first_result,
                    )
                    service.create_attempt_item_result(
                        attempt.id,
                        item.id,
                        outcome=[
                            ItemOutcome.PARTIAL,
                            ItemOutcome.CORRECT,
                            ItemOutcome.NOT_EVALUATED,
                            ItemOutcome.INCORRECT,
                        ][marker],
                    )
                    if marker == 0:
                        service.add_attempt(
                            assigned.id,
                            UtcInstant(base + timedelta(days=9 + i * 2)),
                            AttemptResult.ACCEPTED,
                            score=9,
                            max_score=work.max_score,
                            comment="Исправление проверено.",
                        )
                works.append(work)
            assessments.append(works)
            group_lessons = []
            for i in range(4):
                lesson = service.create_lesson(
                    offering.id,
                    LocalDate(2026, 9, 4 + i * 7),
                    title=["Метод сечений", "Эпюры Q и M", "Изгиб балки", "Напряжения при изгибе"][
                        i
                    ],
                    notes="Разобрали реакции опор, знак момента и оформление эпюр.",
                    topic_ids=[t.id for t in topics[:2]],
                )
                for j, entry in enumerate(service.list_students_for_offering(offering.id)):
                    service.mark_attendance(
                        lesson.id,
                        entry.enrollment.id,
                        [
                            AttendanceStatus.PRESENT,
                            AttendanceStatus.PRESENT,
                            AttendanceStatus.PRESENT,
                            AttendanceStatus.LATE,
                            AttendanceStatus.ABSENT,
                            AttendanceStatus.EXCUSED,
                            AttendanceStatus.UNKNOWN,
                        ][(i + j) % 7],
                    )
                group_lessons.append(lesson)
            lessons.append(group_lessons)
        image = QImage(1100, 1450, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        painter.setFont(QFont("Segoe UI", 22))
        painter.drawText(70, 90, "Синтетическая работа · Эпюра M")
        painter.drawText(70, 145, "Учебный пример. Реальные данные не используются.")
        painter.drawLine(100, 430, 970, 430)
        painter.drawLine(100, 430, 600, 250)
        painter.drawLine(600, 250, 970, 430)
        painter.drawText(100, 520, "M > 0 · первый участок")
        painter.end()
        source = directory / "synthetic-work.png"
        image.save(str(source))
        work = service.get_or_create_work(students[0][0].id, assessments[0][0].id)
        attempt = service.history(work.id).entries[0].attempt
        service.import_file_for_attempt(attempt.id, source)
        case = None
        for gi in range(2):
            for i in range(6):
                question = service.create_question_case(
                    students[gi][i].id,
                    [
                        "Как проверить знак момента на втором участке?",
                        "Как оформить реакцию опоры?",
                        "Можно уточнить направление силы?",
                    ][i % 3],
                    UtcInstant(base + timedelta(days=24, hours=i)),
                    title="Знак момента" if i % 3 == 0 else "Расчёт реакций",
                    course_offering_id=offerings[gi].id,
                    context={
                        "topic": [topics[1].id],
                        "skill": [skill.id],
                        "assessment": [assessments[gi][0].id],
                    },
                )
                if i % 2:
                    service.add_teacher_message(
                        question.id,
                        "Проверьте направление момента методом сечений.",
                        UtcInstant(base + timedelta(days=24, hours=i + 2)),
                    )
                if gi == 0 and i == 0:
                    case = question
                    service.import_file_for_message(service.list_messages(case.id)[0].id, source)
        return SimpleNamespace(
            term=term,
            course=course,
            groups=groups,
            offerings=offerings,
            students=students,
            assessments=assessments,
            lessons=lessons,
            topic=topics[1],
            skill=skill,
            case=case,
            work=work,
        )
    finally:
        service._clock = original_clock
