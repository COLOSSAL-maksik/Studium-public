"""Upgrade actual copies of populated historical databases, preserving facts."""

import shutil
from pathlib import Path

import pytest
from alembic import command

from studium.domain.enums import AssessmentType, AttemptResult
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


@pytest.mark.parametrize("revision", ["0001_local_core", "0002_learning_model", "0003_attachments"])
def test_populated_historical_copy_to_v4_preserves_all_data_schema_and_original(revision, tmp_path):
    original = tmp_path / "original.sqlite"
    engine = create_database_engine(original, wal=False)
    with engine.begin() as conn:
        config = migration_config()
        config.attributes["connection"] = conn
        command.upgrade(config, revision)
    sessions = create_session_factory(engine)
    s = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(tmp_path / "preferences.json"),
        file_storage=LocalFileStorage(tmp_path),
    )
    term = s.create_term("Synthetic", LocalDate(2026, 9, 1), LocalDate(2027, 1, 1))
    course = s.create_course("Synthetic")
    group = s.create_group("TEST")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic Student")
    assessment = s.create_assessment(offering.id, "Synthetic Work", AssessmentType.HOMEWORK)
    work = s.get_or_create_work(student.id, assessment.id)
    if revision != "0001_local_core":
        topic = s.create_topic(course.id, "Synthetic Topic")
        s.attach_assessment_topic(assessment.id, topic.id)
        s.create_skill(course.id, "Synthetic Skill")
    attempt = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
    if revision == "0003_attachments":
        source = tmp_path / "synthetic.txt"
        source.write_text("Synthetic original", encoding="utf-8")
        link = s.import_file_for_attempt(attempt.id, source)
        stored = s.accessible_file_path(link.file_asset_id)
        stored_bytes = stored.read_bytes()
        s.detach_attachment(link.id, expected_revision=1)
    with engine.connect() as conn:
        before, objects = snapshot(conn)
    engine.dispose()
    original_bytes = original.read_bytes()
    copy = tmp_path / "copy.sqlite"
    shutil.copy2(original, copy)
    migrated = create_database_engine(copy, wal=False)
    try:
        upgrade_database(migrated)
        upgrade_database(migrated)
        with migrated.connect() as conn:
            after, new_objects = snapshot(conn)
            assert (
                len(after) == 100
            )  # v10 adds 21 concrete QA tables; every old row is compared below.
            assert preserved_rows(before, after)
            assert preserved_objects(objects, new_objects)
            assert (
                conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0010_qa_package"
            )
            assert conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        migrated.dispose()
    assert original.read_bytes() == original_bytes
    if revision == "0003_attachments":
        assert stored.read_bytes() == stored_bytes


def test_historical_v1_v2_v3_snapshots_unchanged():
    import hashlib
    import json

    root = Path(__file__).resolve().parents[2]
    expected = json.loads((root / "tests/fixtures/migration_hashes.json").read_text())
    for version in range(1, 4):
        for suffix in ("py", "sql"):
            relative = (
                f"src/studium/infrastructure/database/migrations/versions/v000{version}.{suffix}"
            )
            current = (root / relative).read_bytes()
            assert hashlib.sha256(current).hexdigest() == expected[relative]
