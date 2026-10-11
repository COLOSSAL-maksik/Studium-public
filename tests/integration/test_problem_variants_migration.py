"""Fresh and populated v7 upgrade keeps every historical value and original byte."""

import shutil

from alembic import command

from studium.composition import create_runtime
from studium.domain.content import GenerationCriteria
from studium.domain.enums import AssessmentType, AttemptResult
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


def test_populated_v7_upgrade_preserves_problems_tickets_assignments_files(tmp_path):
    original = tmp_path / "v7"
    original.mkdir()
    engine = create_database_engine(original / "studium.sqlite", wal=False)
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0007_work_programs")
    sessions = create_session_factory(engine)
    s = HistoricalStudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(original / "preferences.json"),
        file_storage=LocalFileStorage(original),
    )
    term = s.create_term("Synthetic v7", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Synthetic course")
    group = s.create_group("V7-TEST")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic Student")
    work = s.create_assessment(offering.id, "Original RK", AssessmentType.CONTROL_WORK)
    s.record_attempt(
        student.id, work.id, occurred_at=UtcInstant.now(), result=AttemptResult.PRESENTED
    )
    problem = s.create_material(
        "problems", course_id=course.id, title="Original", statement="Keep", correct_answer="Answer"
    )
    path = original / "synthetic.txt"
    path.write_bytes(b"immutable v7 original")
    file = s.import_file_for_material("problems", problem.id, path)
    saved = s.save_ticket_set(
        offering.id,
        s.generate_ticket_draft(GenerationCriteria(course.id, 1)),
        assessment_id=work.id,
        assign_students=True,
    )
    with engine.connect() as connection:
        before, objects = snapshot(connection)
    engine.dispose()
    original_bytes = (original / "studium.sqlite").read_bytes()
    destination = tmp_path / "copy"
    shutil.copytree(original, destination)
    for _ in range(2):
        runtime = create_runtime(destination)
        with runtime._engine.connect() as connection:
            after, new_objects = snapshot(connection)
            assert preserved_rows(before, after)
            assert preserved_objects(objects, new_objects)
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        migrated = runtime.service.get_material("problems", problem.id)
        assert migrated.statement == "Keep" and migrated.purposes == () and not migrated.is_family
        assert runtime.service.ticket_set_details(saved.id)[0].assignments
        assert (
            runtime.service.accessible_file_path(file.file_asset_id).read_bytes()
            == b"immutable v7 original"
        )
        assert runtime.diagnostics.schema_version == "0010_qa_package"
        runtime.close()
    assert (original / "studium.sqlite").read_bytes() == original_bytes


def test_empty_v7_upgrade_and_fresh_schema(tmp_path):
    engine = create_database_engine(tmp_path / "empty.sqlite")
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0007_work_programs")
        command.upgrade(config, "head")
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == "0010_qa_package"
        )
        assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    engine.dispose()
    runtime = create_runtime(tmp_path / "fresh")
    assert runtime.diagnostics.schema_version == "0010_qa_package"
    runtime.close()
