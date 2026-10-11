"""Upgrade an actual populated synthetic Phase 3 DB copy; no production paths."""

import shutil
from pathlib import Path

from alembic import command
from sqlalchemy import inspect

from studium.application.services import GradeInput
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, GradeKind
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure.database.migrations import migration_config, upgrade_database
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.user_data import JsonPreferences
from tests.legacy_schema import HistoricalStudiumService as StudiumService
from tests.legacy_schema import (
    preserved_objects,
    preserved_rows,
    repository_set,
    transaction_factory,
)


def snapshot(connection):
    tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
    rows = {
        table: connection.exec_driver_sql(f"SELECT * FROM {table} ORDER BY id").fetchall()
        for table in tables
    }
    objects = connection.exec_driver_sql(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND name != 'alembic_version' ORDER BY name"
    ).fetchall()
    return rows, objects


def test_populated_phase3_v2_copy_upgrade_preserves_every_fact_and_schema(tmp_path):
    original = tmp_path / "original-v2.sqlite"
    engine = create_database_engine(original, wal=False)
    with engine.begin() as c:
        config = migration_config()
        config.attributes["connection"] = c
        command.upgrade(config, "0002_learning_model")
    sessions = create_session_factory(engine)
    s = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(tmp_path / "preferences.json"),
    )
    term = s.create_term("Synthetic term", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Synthetic course")
    group = s.create_group("TEST")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic student")
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    assessment = s.create_assessment(
        offering.id, "Synthetic work", AssessmentType.HOMEWORK, max_score=10
    )
    work = s.get_or_create_work(student.id, assessment.id)
    topic = s.create_topic(course.id, "Synthetic topic")
    child = s.create_topic(course.id, "Synthetic child", parent_topic_id=topic.id)
    skill = s.create_skill(course.id, "Synthetic skill")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 9, 30), title="Synthetic lesson")
    item = s.create_assessment_item(assessment.id, "Synthetic item")
    for kind, owner, target in [
        ("topic_skills", topic, skill),
        ("lesson_topics", lesson, topic),
        ("assessment_topics", assessment, topic),
        ("assessment_skills", assessment, skill),
        ("item_topics", item, child),
        ("item_skills", item, skill),
    ]:
        s.attach_learning_link(kind, owner.id, target.id)
    s.mark_attendance(
        lesson.id, enrollment.id, AttendanceStatus.PRESENT, comment="Synthetic attendance"
    )
    s.archive_topic(child)
    for result in (
        AttemptResult.NEEDS_REVISION,
        AttemptResult.NEEDS_REVISION,
        AttemptResult.ACCEPTED,
    ):
        attempt = s.add_attempt(
            work.id,
            UtcInstant.now(),
            result,
            score=8 if result == AttemptResult.ACCEPTED else None,
            grade=GradeInput(GradeKind.NUMERIC) if result == AttemptResult.ACCEPTED else None,
        )
    history = s.history(work.id)
    s._r.attempts.soft_delete(
        history.entries[1].attempt.id, expected_revision=1, at=UtcInstant.now()
    )
    with engine.connect() as c:
        before, schema = snapshot(c)
        assert len(before) == 21 and all(before.values())
    engine.dispose()
    original_bytes = original.read_bytes()
    copy = tmp_path / "copy-v2.sqlite"
    shutil.copy2(original, copy)
    migrated = create_database_engine(copy)
    try:
        upgrade_database(migrated)
        upgrade_database(migrated)
        with migrated.connect() as c:
            after, new_schema = snapshot(c)
            assert (
                c.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0010_qa_package"
            )
            assert (
                len(after) == 100
            )  # v10 adds 21 concrete QA tables; every old row is compared below.
            assert preserved_rows(before, after)
            assert preserved_objects(schema, new_schema)
            assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        repositories = repository_set(create_session_factory(migrated))
        assert repositories.attempts.find_by_id(attempt.id).result == AttemptResult.ACCEPTED
        assert repositories.topics.find_by_id(child.id, include_deleted=True).deleted_at is not None
    finally:
        migrated.dispose()
    assert original.read_bytes() == original_bytes


def test_historical_migrations_unchanged_in_git():
    import hashlib
    import json

    root = Path(__file__).resolve().parents[2]
    expected = json.loads((root / "tests/fixtures/migration_hashes.json").read_text())
    for version in range(1, 3):
        for suffix in ("py", "sql"):
            relative = (
                f"src/studium/infrastructure/database/migrations/versions/v000{version}.{suffix}"
            )
            current = (root / relative).read_bytes()
            assert hashlib.sha256(current).hexdigest() == expected[relative]
