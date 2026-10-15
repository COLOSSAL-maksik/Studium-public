"""Populated v12 preservation, transactional v13 DDL and new-head backup."""

import json
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import event

from studium.application.backup import BackupControl
from studium.application.services import StudiumService
from studium.composition import create_runtime
from studium.infrastructure.backup import LocalBackup
from studium.infrastructure.database.migrations import (
    SCHEMA_REVISION,
    migration_config,
    upgrade_database,
)
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.database.unit_of_work import repository_set, transaction_factory
from studium.infrastructure.user_data import AppPaths, JsonPreferences
from tests.integration.test_annual_program import filled
from tests.integration.test_file_migrations import snapshot
from tests.legacy_schema import preserved_objects


def test_populated_v12_preserves_bytes_uuid_guards_and_late_rollback(tmp_path):
    root = tmp_path / "previous"
    root.mkdir()
    engine = create_database_engine(root / "studium.sqlite", wal=False)
    with engine.begin() as conn:
        config = migration_config()
        config.attributes["connection"] = conn
        command.upgrade(config, "0012_frozen_taxonomy")
    sessions = create_session_factory(engine)
    s = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(root / "preferences.json"),
    )
    course = s.create_course("Synthetic old course")
    topic = s.create_topic(course.id, "Synthetic frozen topic")
    version = s.create_course_program(
        course.id, "Synthetic prior version", content={"topic_ids": [str(topic.id)]}
    )
    with engine.connect() as conn:
        before, objects = snapshot(conn)

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("CREATE TRIGGER plan_lessons_scope_update"):
            raise RuntimeError("Synthetic late v13 DDL failure")

    event.listen(engine, "after_cursor_execute", fail)
    with pytest.raises(RuntimeError, match="late v13"):
        upgrade_database(engine)
    with engine.connect() as conn:
        assert snapshot(conn) == (before, objects)
    event.remove(engine, "after_cursor_execute", fail)
    upgrade_database(engine)
    with engine.connect() as conn:
        after, new_objects = snapshot(conn)
        assert preserved_objects(objects, new_objects)
        for table, rows in before.items():
            assert after[table] == rows
        assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
        assert (
            conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == SCHEMA_REVISION
        )
    upgrade_database(engine)
    engine.dispose()
    reopened = create_runtime(root)
    try:
        assert reopened.service.get_program_version(version.id).content_json == version.content_json
        assert not reopened.service.list_program_drafts()
    finally:
        reopened.close()


def test_backup_restore_draft_versions_files_and_sources(tmp_path):
    runtime = create_runtime(tmp_path / "active")
    s = runtime.service
    course, draft = filled(s)
    source = tmp_path / "synthetic.txt"
    source.write_text("Synthetic annual backup content")
    draft = s.attach_program_documents(draft, [source])
    version = s.publish_program_draft(draft)
    draft = s.create_program_draft(course.id, previous=version)
    root = Path(runtime.diagnostics.database_path).parent
    backend = LocalBackup(AppPaths(root))
    path = tmp_path / "annual-backup.zip"
    backend.create(path, BackupControl())
    preview = backend.verify(path, BackupControl())
    restored = tmp_path / "restored"
    backend.restore(path, restored, preview, BackupControl())
    new = create_runtime(restored)
    try:
        assert new.service.get_program_version(version.id) == version
        assert new.service.get_program_draft(draft.id) == draft
        data = json.loads(version.content_json)
        from studium.domain.value_objects import EntityId

        assert (
            new.service.accessible_file_path(EntityId(data["file_asset_ids"][0])).read_bytes()
            == source.read_bytes()
        )
    finally:
        new.close()
        runtime.close()
