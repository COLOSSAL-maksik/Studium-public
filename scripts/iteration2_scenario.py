"""Synthetic Iteration 2 program/journal/control/knowledge acceptance data."""

from datetime import UTC, datetime

from phase66_scenario import seed as previous_seed

from studium.domain.enums import AssessmentType, AttemptResult, ItemOutcome
from studium.domain.value_objects import AcademicWeekNumber, UtcInstant


def seed(service, directory):
    data = previous_seed(service, directory)
    service._clock = lambda: UtcInstant(datetime(2026, 10, 4, 9, tzinfo=UTC))
    data.programs = []
    data.modules = []
    for i, offering in enumerate(data.offerings):
        program = service.program_for_offering(offering.id)
        program = service.update_work_program(
            program,
            title=f"Сопромат · {'МТ' if i == 0 else 'Э'} · осень 2026",
            direction="Машиностроение" if i == 0 else "Энергетика",
            faculty="Машиностроительные технологии",
            version="2026 · версия 1",
        )
        data.programs.append(program)
        modules = [
            service.create_program_module(program.id, f"Модуль {j + 1}", start, end, j)
            for j, (start, end) in enumerate(((1, 6), (7, 12), (13, 17)))
        ]
        data.modules.append(modules)
        service.set_content_links("program_topics", program.id, (data.topic.id,))
        service.set_content_links("program_skills", program.id, (data.skill.id,))
        service.import_file_for_material("programs", program.id, data.pdf)
    data.pack = service.create_material(
        "packs", course_id=data.course.id, title="Общий комплект ДЗ1–ДЗ3 · варианты на семестр"
    )
    service.import_file_for_material("packs", data.pack.id, data.pdf)
    data.new_homework = []
    data.homework_assessments = []
    for i in range(3):
        definition = service.create_work_definition(
            data.course.id,
            f"ДЗ{i + 1} · расчёт балки",
            label=f"ДЗ{i + 1}",
            description="Выполните своё задание из общего PDF комплекта.",
        )
        service.set_definition_packs(definition.id, (data.pack.id,))
        service.set_content_links("definition_topics", definition.id, (data.topic.id,))
        service.set_content_links("definition_skills", definition.id, (data.skill.id,))
        link = service.add_program_work(
            data.programs[0].id,
            definition.id,
            module_id=data.modules[0][i].id,
            planned_issue_week=AcademicWeekNumber((1, 7, 13)[i]),
            planned_due_week=AcademicWeekNumber((6, 12, 17)[i]),
            sort_order=i,
        )
        data.new_homework.append(definition)
        if i == 0:
            assessment = service.issue_program_work(data.offerings[0].id, link.id)
            data.homework_assessments.append(assessment)
            student = data.students[0][0]
            for result in (
                AttemptResult.PRESENTED,
                AttemptResult.NEEDS_REVISION,
                AttemptResult.NEEDS_REVISION,
                AttemptResult.ACCEPTED,
            ):
                service.record_attempt(
                    student.id,
                    assessment.id,
                    occurred_at=service._clock(),
                    result=result,
                    comment="Синтетическая проверка доработки",
                )
    data.control_definition = service.create_work_definition(
        data.course.id, "РК1 · эпюры Q и M", AssessmentType.CONTROL_WORK, label="РК1"
    )
    for problem in data.problems[:3]:
        service.set_content_links("problem_topics", problem.id, (data.topic.id,))
        service.set_content_links("problem_skills", problem.id, (data.skill.id,))
    service.set_content_links(
        "definition_problems", data.control_definition.id, [p.id for p in data.problems[:3]]
    )
    for i, program in enumerate(data.programs):
        link = service.add_program_work(
            program.id,
            data.control_definition.id,
            module_id=data.modules[i][0].id,
            planned_issue_week=AcademicWeekNumber(1),
            planned_due_week=AcademicWeekNumber(6),
            sort_order=3,
        )
        if i == 0:
            data.control = service.issue_program_work(data.offerings[0].id, link.id)
    data.control_items = service.list_assessment_items(data.control.id)
    student = data.students[0][0]
    for item, problem in zip(data.control_items, data.problems[:3], strict=True):
        service.assign_student_problem(student.id, item.id, problem.id)
    data.control_attempt = service.record_attempt(
        student.id, data.control.id, occurred_at=service._clock(), result=AttemptResult.PRESENTED
    )
    service.create_attempt_item_result(
        data.control_attempt.id,
        data.control_items[0].id,
        outcome=ItemOutcome.CORRECT,
        skill_results=((data.skill.id, ItemOutcome.INCORRECT, "Ошибка знака"),),
    )
    case = service.create_question_case(
        student.id,
        "Синтетический исходный вопрос о знаке момента",
        service._clock(),
        course_offering_id=data.offerings[0].id,
    )
    data.knowledge = service.create_knowledge_from_case(
        case.id,
        "Как выбрать знак изгибающего момента?",
        "Согласуйте положительные направления и проверьте равновесие.",
    )
    other = service.create_question_case(
        data.students[0][1].id,
        "Другой вопрос того же вида",
        service._clock(),
        course_offering_id=data.offerings[0].id,
    )
    service.link_knowledge_case(data.knowledge.id, other.id)
    data.methodical = service.create_material(
        "methodical",
        course_id=data.course.id,
        title="Знаки Q и M · методическая памятка",
        description="Синтетическая общая памятка преподавателя.",
    )
    service.set_content_links("knowledge_materials", data.knowledge.id, (data.methodical.id,))
    return data
