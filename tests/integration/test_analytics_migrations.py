"""Upgrade populated historical copies; no production database or originals touched."""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect

from studium.application.errors import ApplicationError
from studium.application.services import GradeInput
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, GradeKind
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.database.migrations import migration_config, upgrade_database
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import JsonPreferences
from tests.integration.test_file_migrations import snapshot
from tests.legacy_schema import HistoricalStudiumService as StudiumService
from tests.legacy_schema import (
    preserved_objects,
    preserved_rows,
    repository_set,
    transaction_factory,
)


@pytest.mark.parametrize(
    "revision",
    [
        "0001_local_core",
        "0002_learning_model",
        "0003_attachments",
        "0004_communication",
        "0005_analytics_foundation",
    ],
)
def test_populated_v1_v2_v3_v4_copies_to_analytics_preserve_rows_schema_and_files(
    tmp_path, revision
):
    original = tmp_path / "original.sqlite"
    engine = create_database_engine(original, wal=False)
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
    sessions = create_session_factory(engine)
    service = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(tmp_path / "preferences.json"),
        file_storage=LocalFileStorage(tmp_path),
    )
    term = service.create_term("Synthetic term", LocalDate(2026, 9, 1), LocalDate(2027, 1, 1))
    course = service.create_course("Synthetic course")
    group = service.create_group("TEST")
    offering = service.create_offering(term.id, course.id, group.id)
    student = service.create_student(offering.id, "Synthetic Student")
    assessment = service.create_assessment(
        offering.id, "Synthetic work", AssessmentType.CONTROL_WORK, max_score=10
    )
    work = service.get_or_create_work(student.id, assessment.id)
    if revision != "0001_local_core":
        topic = service.create_topic(course.id, "Synthetic topic")
        child = service.create_topic(course.id, "Synthetic child", parent_topic_id=topic.id)
        skill = service.create_skill(course.id, "Synthetic skill")
        item = service.create_assessment_item(assessment.id, "Synthetic part", max_score=5)
        lesson = service.create_lesson(offering.id, LocalDate(2026, 10, 1))
        for kind, owner, target in (
            ("assessment_topics", assessment, topic),
            ("assessment_skills", assessment, skill),
            ("item_topics", item, child),
            ("item_skills", item, skill),
            ("lesson_topics", lesson, child),
            ("topic_skills", child, skill),
        ):
            service.attach_learning_link(kind, owner.id, target.id)
        enrollment = service.list_students_for_offering(offering.id)[0].enrollment
        service.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.PRESENT)
    first = service.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
    second = service.add_attempt(
        work.id,
        UtcInstant.now(),
        AttemptResult.ACCEPTED,
        score=8,
        max_score=10,
        grade=GradeInput(GradeKind.NUMERIC),
    )
    stored = None
    if revision in {"0003_attachments", "0004_communication", "0005_analytics_foundation"}:
        source = tmp_path / "synthetic.txt"
        source.write_text("Synthetic immutable original", encoding="utf-8")
        attachment = service.import_file_for_attempt(second.id, source)
        stored = service.accessible_file_path(attachment.file_asset_id)
        stored_bytes = stored.read_bytes()
    if revision in {"0004_communication", "0005_analytics_foundation"}:
        at = UtcInstant.now()
        case = service.create_question_case(
            student.id,
            "Synthetic question\noriginal body",
            at,
            course_offering_id=offering.id,
            context={
                "assessment": [assessment.id],
                "attempt": [first.id],
                "topic": [child.id],
                "skill": [skill.id],
            },
        )
        response = service.add_teacher_message(
            case.id, "Synthetic response", UtcInstant(at.value + timedelta(seconds=1))
        )
        service.attach_file_asset_to_message(response.id, attachment.file_asset_id)
        service.archive_message(response)
    service._r.attempts.soft_delete(first.id, expected_revision=first.revision, at=UtcInstant.now())
    with engine.connect() as connection:
        before, objects = snapshot(connection)
    engine.dispose()
    original_bytes = original.read_bytes()
    copied = tmp_path / "copy.sqlite"
    shutil.copy2(original, copied)
    migrated = create_database_engine(copied, wal=False)
    try:
        upgrade_database(migrated)
        upgrade_database(migrated)
        with migrated.connect() as connection:
            after, new_objects = snapshot(connection)
            assert (
                len(after) == 100
            )  # v10 adds 21 concrete QA tables; every old row is compared below.
            assert preserved_rows(before, after)
            assert preserved_objects(objects, new_objects)
            assert after["attempt_item_results"] == []
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
            assert (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0010_qa_package"
            )
        repositories = repository_set(create_session_factory(migrated))
        assert repositories.content_locks.assessment_locked(assessment.id)
        current = StudiumService(
            repositories,
            transaction_factory(create_session_factory(migrated)),
            JsonPreferences(tmp_path / "copy-preferences.json"),
        )
        assert current.history(work.id).entries[0].attempt == second
        with pytest.raises(ApplicationError, match="content_semantic_locked"):
            current.update_assessment(assessment, title="Changed historical meaning")
        if revision in {"0004_communication", "0005_analytics_foundation"}:
            messages = current.list_messages(case.id, include_deleted=True)
            assert len(messages) == 2
            assert messages[0].body == "Synthetic question\noriginal body"
            assert messages[1].body == "Synthetic response" and messages[1].deleted_at is not None
    finally:
        migrated.dispose()
    assert original.read_bytes() == original_bytes
    if stored is not None:
        assert stored.read_bytes() == stored_bytes


def test_fresh_analytics_database_reopens_with_unchanged_schema(tmp_path):
    path = tmp_path / "fresh.sqlite"
    for _ in range(2):
        engine = create_database_engine(path, wal=False)
        try:
            upgrade_database(engine)
            with engine.connect() as connection:
                assert len(inspect(connection).get_table_names()) == 101
                assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
                assert (
                    connection.exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    ).scalar_one()
                    == "0010_qa_package"
                )
        finally:
            engine.dispose()


def test_all_four_historical_migration_snapshots_unchanged():
    import hashlib
    import json

    root = Path(__file__).resolve().parents[2]
    expected = json.loads((root / "tests/fixtures/migration_hashes.json").read_text())
    for version in range(1, 6):
        for suffix in ("py", "sql"):
            relative = (
                f"src/studium/infrastructure/database/migrations/versions/v000{version}.{suffix}"
            )
            current = (root / relative).read_bytes()
            assert hashlib.sha256(current).hexdigest() == expected[relative]
