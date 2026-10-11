"""Actual v9 DDL/backfill preservation, transactional failure and new-head recovery."""

import pytest
from alembic import command
from sqlalchemy import event

from studium.application.services import StudiumService
from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult
from studium.domain.value_objects import AcademicWeekNumber, LocalDate, UtcInstant
from studium.infrastructure.database.migrations import migration_config, upgrade_database
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.database.unit_of_work import repository_set, transaction_factory
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import JsonPreferences
from tests.integration.test_file_migrations import snapshot


def legacy(tmp_path):
    root = tmp_path / "legacy"
    root.mkdir()
    engine = create_database_engine(root / "studium.sqlite", wal=False)
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0009_daily_workflow")
    sessions = create_session_factory(engine)
    service = StudiumService(
        repository_set(sessions),
        transaction_factory(sessions),
        JsonPreferences(root / "preferences.json"),
        file_storage=LocalFileStorage(root),
    )
    term = service.create_term("Synthetic legacy T1", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = service.create_course("Synthetic")
    program = service.create_work_program(
        course.id, term.id, "Same title", term.starts_on, direction=" 15.15.03 "
    )
    module = service.create_program_module(program.id, "Legacy M", 1, 6)
    definition = service.create_work_definition(course.id, "Legacy H1", AssessmentType.HOMEWORK)
    service.add_program_work(
        program.id,
        definition.id,
        module_id=module.id,
        planned_issue_week=AcademicWeekNumber(1),
        issue_date=LocalDate(2026, 9, 1),
        planned_due_week=AcademicWeekNumber(6),
        due_date=LocalDate(2026, 10, 10),
    )
    for index in range(2):
        group = service.create_group(f"SYN-{index}")
        offering = service.create_offering(term.id, course.id, group.id, program.id)
        planned = service.planned_works(offering.id)[0]
        assessment = service.issue_program_work(offering.id, planned.link.id)
        student = service.create_student(offering.id, f"Synthetic {index}")
        work = service.get_or_create_work(student.id, assessment.id)
        service.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
        attempt = service.add_attempt(
            work.id,
            UtcInstant.now(),
            AttemptResult.SCORED,
            score=24.123456789,
            max_score=30.987654321,
        )
        source = root / f"synthetic-{index}.pdf"
        source.write_bytes(b"synthetic legacy immutable bytes")
        service.import_file_for_attempt(attempt.id, source)
        if index:
            service.withdraw_student(service.list_students_for_offering(offering.id)[0].enrollment)
    with engine.connect() as connection:
        before, objects = snapshot(connection)
    return root, engine, before, objects


def test_populated_legacy_maps_preserve_every_row_object_real_and_reopen(tmp_path):
    root, engine, before, objects = legacy(tmp_path)
    upgrade_database(engine)
    with engine.connect() as connection:
        after, new_objects = snapshot(connection)
        for table, rows in before.items():
            assert after[table] == rows, table
        assert set(objects).issubset(set(new_objects))
        assert len(after["course_programs"]) == 1
        assert len(after["semester_plans"]) == 2
        assert len(after["plan_modules"]) == 2
        assert len(after["issued_works"]) == 2
        assert not after["submissions"] and not after["reviews"] and not after["required_work_sets"]
        assert connection.exec_driver_sql("SELECT code FROM directions").scalar_one() == "15.15.03"
        assert connection.exec_driver_sql("SELECT actual_issued_at FROM issued_works").all() == [
            (None,),
            (None,),
        ]
        assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    upgrade_database(engine)
    with engine.connect() as connection:
        assert snapshot(connection) == (after, new_objects)
    engine.dispose()
    runtime = create_runtime(root)
    try:
        for work in runtime.service._r.works.list():
            result = runtime.service.work_result(work.id)
            assert result.score.hex() == (24.123456789).hex()
            assert not result.exact
        assert runtime.diagnostics.schema_version == "0010_qa_package"
    finally:
        runtime.close()


def test_real_ddl_and_backfill_late_failure_rolls_back_all(tmp_path, monkeypatch):
    _, engine, before, objects = legacy(tmp_path)
    writes = 0

    def fail_after_backfill(connection, cursor, statement, parameters, context, executemany):
        nonlocal writes
        if statement.startswith("INSERT INTO plan_history"):
            writes += 1
            if writes == 2:
                raise RuntimeError("synthetic late DDL/backfill failure")

    event.listen(engine, "after_cursor_execute", fail_after_backfill)
    with pytest.raises(RuntimeError, match="late DDL/backfill"):
        upgrade_database(engine)
    with engine.connect() as connection:
        assert snapshot(connection) == (before, objects)
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == "0009_daily_workflow"
        )
        assert not connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    event.remove(engine, "after_cursor_execute", fail_after_backfill)
    upgrade_database(engine)
    engine.dispose()


def test_new_head_backup_restore_roundtrip_with_exact_reviews_and_files(tmp_path):
    from studium.application.backup import BackupControl
    from studium.infrastructure.backup import LocalBackup
    from studium.infrastructure.user_data import AppPaths

    root, engine, _, _ = legacy(tmp_path)
    engine.dispose()
    runtime = create_runtime(root)
    s = runtime.service
    try:
        work = s._r.works.list()[0]
        s.change_scoring_rule(work.assessment_id, "18", "30")
        paths = [root / "synthetic-0.pdf", root / "synthetic-1.pdf"]
        submission = s.register_submission(work.id, UtcInstant.now(), paths=paths)
        review = s.review_submission(submission.id, AttemptResult.ACCEPTED, score="24", paths=paths)
        s.record_review_return(review.id, UtcInstant.now())
        with runtime._engine.connect() as connection:
            before = snapshot(connection)
        backend = LocalBackup(AppPaths(root))
        archive = tmp_path / "qa.zip"
        backend.create(archive, BackupControl())
        destination = tmp_path / "restored"
        backend.restore(
            archive, destination, backend.verify(archive, BackupControl()), BackupControl()
        )
    finally:
        runtime.close()
    restored = create_runtime(destination)
    try:
        with restored._engine.connect() as connection:
            assert snapshot(connection) == before
        assert not restored.service.fractional_scores_enabled()
        assert restored.service.work_result(work.id).score == 2400
        for asset in restored.service._r.file_assets.list(include_deleted=True):
            assert (
                restored.service.accessible_file_path(asset.id).read_bytes()
                == b"synthetic legacy immutable bytes"
            )
    finally:
        restored.close()
