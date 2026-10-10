"""Upgrade a populated v6 copy including files/tickets; retain original bytes."""

import shutil
from datetime import UTC, datetime

from alembic import command

from studium.composition import create_runtime
from studium.domain.content import GenerationCriteria
from studium.domain.enums import AssessmentType, AttemptResult, ItemOutcome
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.database.migrations import migration_config
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import JsonPreferences
from tests.integration.test_file_migrations import snapshot
from tests.legacy_schema import (
    HistoricalStudiumService,
    preserved_objects,
    preserved_rows,
    repository_set,
    transaction_factory,
)


def test_populated_v6_copy_program_mapping_files_tickets_reopen(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    engine = create_database_engine(original / "studium.sqlite", wal=False)
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0006_content_workflow")
    sessions = create_session_factory(engine)
    at = UtcInstant(datetime(2026, 9, 1, tzinfo=UTC))
    service = HistoricalStudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(original / "preferences.json"),
        file_storage=LocalFileStorage(original),
        clock=lambda: at,
    )
    term = service.create_term("Synthetic", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = service.create_course("Synthetic course")
    definition = service.create_material(
        "homework", course_id=course.id, title="Shared original homework"
    )
    source = original / "synthetic.txt"
    source.write_text("Immutable synthetic bytes", encoding="utf8")
    link = service.import_file_for_material("homework", definition.id, source)
    topic = service.create_topic(course.id, "Original topic")
    skill = service.create_skill(course.id, "Original skill")
    service.attach_topic_skill(topic.id, skill.id)
    problem = service.create_material(
        "problems", course_id=course.id, title="Original problem", statement="Original statement"
    )
    assessments = []
    offerings = []
    for i in range(2):
        group = service.create_group(f"LEGACY-{i}")
        offering = service.create_offering(term.id, course.id, group.id)
        offerings.append(offering)
        student = service.create_student(offering.id, f"Synthetic student {i}")
        assessment = service.create_assessment(
            offering.id,
            "Original homework",
            AssessmentType.HOMEWORK,
            homework_definition_id=definition.id,
        )
        assessments.append(assessment)
        attempt = service.record_attempt(
            student.id, assessment.id, occurred_at=at, result=AttemptResult.ACCEPTED
        )
        service.import_file_for_attempt(attempt.id, source)
        control = service.create_assessment(offering.id, "Original RK", AssessmentType.CONTROL_WORK)
        item = service.create_assessment_item(control.id, "Original task")
        task_attempt = service.record_attempt(
            student.id, control.id, occurred_at=at, result=AttemptResult.REJECTED
        )
        service.create_attempt_item_result(task_attempt.id, item.id, outcome=ItemOutcome.INCORRECT)
        service.create_question_case(
            student.id, "Original question", at, course_offering_id=offering.id
        )
        draft = service.generate_ticket_draft(GenerationCriteria(course.id, 1, 1))
        service.save_ticket_set(offering.id, draft, assessment_id=control.id, assign_students=True)
    with engine.connect() as connection:
        before, objects = snapshot(connection)
    engine.dispose()
    original_bytes = (original / "studium.sqlite").read_bytes()
    copy = tmp_path / "copy"
    shutil.copytree(original, copy)
    for _ in range(2):
        current = create_runtime(copy)
        try:
            with current._engine.connect() as connection:
                after, new_objects = snapshot(connection)
                assert preserved_rows(before, after)
                assert preserved_objects(objects, new_objects)
                assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
            s = current.service
            assert len(s.list_work_programs(course.id)) == 2
            assert all(s.program_for_offering(o.id).weeks == 17 for o in offerings)
            for assessment in assessments:
                assert (
                    s.definition_for_assessment(s._r.assessments.find_by_id(assessment.id)).id
                    == definition.id
                )
                assert s.assessment_shared_files(assessment)[0].asset.id == link.file_asset_id
            assert (
                s.accessible_file_path(link.file_asset_id).read_text("utf8")
                == "Immutable synthetic bytes"
            )
            assert s.get_material("problems", problem.id).statement == "Original statement"
        finally:
            current.close()
    assert (original / "studium.sqlite").read_bytes() == original_bytes
