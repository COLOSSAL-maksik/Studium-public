"""v8 upgrade retains all facts, concrete links, file UUIDs, bytes and guards."""

import shutil

import pytest
from alembic import command

from studium.application.services import StudiumService
from studium.composition import create_runtime
from studium.domain.content import GenerationCriteria
from studium.domain.enums import AssessmentType, AttemptResult
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.database.migrations import migration_config
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.database.unit_of_work import repository_set, transaction_factory
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import JsonPreferences
from tests.integration.test_file_migrations import snapshot


def test_populated_v8_upgrade_preserves_every_old_row_and_guard(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    engine = create_database_engine(original / "studium.sqlite", wal=False)
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0008_problem_variants")
    sessions = create_session_factory(engine)
    s = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(original / "preferences.json"),
        file_storage=LocalFileStorage(original),
    )
    term = s.create_term("Synthetic v8", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Synthetic")
    group = s.create_group("V8")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic Student")
    assessment = s.create_assessment(offering.id, "History", AssessmentType.CONTROL_WORK)
    work = s.get_or_create_work(student.id, assessment.id)
    attempt = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    family = s.create_material("problems", course_id=course.id, title="Family", is_family=True)
    variant = s.create_material(
        "problems", course_id=course.id, title="Variant", family_id=family.id, variant_code="1"
    )
    source = original / "Учебный файл.txt"
    source.write_bytes(b"Synthetic v8 bytes")
    links = [
        s.import_file_for_attempt(attempt.id, source),
        s.import_file_for_material("problems", variant.id, source),
    ]
    for kind in ("literature", "homework", "methodical", "seminars", "packs"):
        material = s.create_material(kind, course_id=course.id, title=kind)
        links.append(s.import_file_for_material(kind, material.id, source))
    case = s.create_question_case(student.id, "Synthetic", UtcInstant.now())
    message = next(m for m in s._r.messages.list() if m.question_case_id == case.id)
    links.append(s.import_file_for_message(message.id, source))
    saved = s.save_ticket_set(
        offering.id,
        s.generate_ticket_draft(GenerationCriteria(course.id, 1)),
        assessment_id=assessment.id,
        assign_students=True,
    )
    with engine.connect() as connection:
        before, objects = snapshot(connection)
    engine.dispose()
    original_bytes = (original / "studium.sqlite").read_bytes()
    destination = tmp_path / "copy"
    shutil.copytree(original, destination)
    (destination / source.name).unlink()
    for _ in range(2):
        runtime = create_runtime(destination)
        try:
            with runtime._engine.connect() as connection:
                after, new_objects = snapshot(connection)
                for table, rows in before.items():
                    if table != "alembic_version":
                        assert after[table] == rows, table
                object_map = {name: sql for _, name, sql in new_objects}
                for _, name, sql in objects:
                    expected = (
                        sql.replace("'docx'", "'doc','docx'") if name == "file_assets" else sql
                    )
                    assert object_map[name] == expected, name
                assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
                assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
                assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
            assert runtime.diagnostics.schema_version == "0010_qa_package"
            assert runtime.service.ticket_set_details(saved.id)[0].assignments
            for link in links:
                assert (
                    runtime.service.accessible_file_path(link.file_asset_id).read_bytes()
                    == b"Synthetic v8 bytes"
                )
        finally:
            runtime.close()
    assert (original / "studium.sqlite").read_bytes() == original_bytes


def test_fresh_doc_import_retains_extension_and_internal_copy(tmp_path):
    runtime = create_runtime(tmp_path / "data")
    try:
        s = runtime.service
        material = s.create_material("literature", course_id=None, title="Legacy document")
        source = tmp_path / "Старый документ.doc"
        source.write_bytes(b"Synthetic DOC content")
        link = s.import_file_for_material("literature", material.id, source)
        source.unlink()
        asset = s.get_file_asset(link.file_asset_id)
        assert asset.mime_type == "application/msword"
        assert s.accessible_file_path(asset.id).suffix == ".doc"
        assert s.accessible_file_path(asset.id).read_bytes() == b"Synthetic DOC content"
    finally:
        runtime.close()


def test_doc_table_rebuild_rolls_back_with_later_migration_failure(tmp_path, monkeypatch):
    from alembic import op

    from studium.infrastructure.database.migrations import upgrade_database

    engine = create_database_engine(tmp_path / "rollback.sqlite", wal=False)
    try:
        with engine.begin() as connection:
            config = migration_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "0008_problem_variants")
        sessions = create_session_factory(engine)
        s = StudiumService(
            repository_set(sessions),
            transaction_factory(sessions),
            JsonPreferences(tmp_path / "preferences.json"),
            file_storage=LocalFileStorage(tmp_path),
        )
        material = s.create_material("literature", title="Synthetic", course_id=None)
        source = tmp_path / "synthetic.txt"
        source.write_bytes(b"keep after rollback")
        link = s.import_file_for_material("literature", material.id, source)
        with engine.connect() as connection:
            before, objects = snapshot(connection)

        def fail(_statement, *_args, **_kwargs):
            raise RuntimeError("Injected late migration failure")

        with monkeypatch.context() as patch:
            patch.setattr(op, "execute", fail)
            with pytest.raises(RuntimeError, match="Injected late"):
                upgrade_database(engine)
        with engine.connect() as connection:
            after, new_objects = snapshot(connection)
            assert after == before and new_objects == objects
            assert (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0008_problem_variants"
            )
            assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        assert s.accessible_file_path(link.file_asset_id).read_bytes() == b"keep after rollback"
        upgrade_database(engine)
    finally:
        engine.dispose()
