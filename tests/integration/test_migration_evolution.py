"""Migrate a populated synthetic Phase 2 database copy, never the user's DB."""

import shutil
from uuid import uuid4

from alembic import command
from sqlalchemy import inspect

from studium.infrastructure.database.migrations import migration_config, upgrade_database
from studium.infrastructure.database.session import create_database_engine
from tests.legacy_schema import preserved_objects


def test_v1_database_copy_preserves_all_phase2_rows_and_schema(tmp_path):
    original = tmp_path / "phase2.sqlite"
    engine = create_database_engine(original, wal=False)
    with engine.begin() as c:
        config = migration_config()
        config.attributes["connection"] = c
        command.upgrade(config, "0001_local_core")
        ids = {}
        rows = [
            (
                "academic_terms",
                dict(name="Synthetic", starts_on="2026-09-01", ends_on="2027-01-01"),
            ),
            ("courses", dict(name="Synthetic")),
            ("student_groups", dict(number="TEST-01")),
            ("students", dict(full_name="Synthetic Student")),
            (
                "course_offerings",
                lambda: dict(
                    term_id=ids["academic_terms"],
                    course_id=ids["courses"],
                    group_id=ids["student_groups"],
                ),
            ),
            (
                "enrollments",
                lambda: dict(
                    student_id=ids["students"],
                    offering_id=ids["course_offerings"],
                    enrolled_at=1,
                    status="ACTIVE",
                ),
            ),
            (
                "assessments",
                lambda: dict(
                    offering_id=ids["course_offerings"],
                    type="HOMEWORK",
                    title="Synthetic",
                    issued_at=1,
                ),
            ),
            (
                "student_works",
                lambda: dict(student_id=ids["students"], assessment_id=ids["assessments"]),
            ),
            (
                "attempts",
                lambda: dict(
                    student_work_id=ids["student_works"],
                    attempt_no=1,
                    occurred_at=2,
                    result="ACCEPTED",
                    score=8,
                    max_score=10,
                    comment="Synthetic",
                ),
            ),
            (
                "grades",
                lambda: dict(attempt_id=ids["attempts"], kind="NUMERIC", score=8, max_score=10),
            ),
        ]
        for table, fields in rows:
            values = dict(
                id=str(uuid4()),
                created_at=1,
                updated_at=1,
                revision=1,
                **(fields() if callable(fields) else fields),
            )
            ids[table] = values["id"]
            c.exec_driver_sql(
                f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})",
                tuple(values.values()),
            )
        for number, result in [(2, "NEEDS_REVISION"), (3, "ACCEPTED")]:
            c.exec_driver_sql(
                "INSERT INTO attempts(id,student_work_id,attempt_no,occurred_at,result,comment,created_at,updated_at,revision) VALUES(?,?,?,?,?,?,1,1,1)",
                (str(uuid4()), ids["student_works"], number, number, result, "Synthetic history"),
            )
        c.exec_driver_sql(
            "UPDATE attempts SET deleted_at=4,updated_at=4,revision=2 WHERE attempt_no=2"
        )
        before = {table: c.exec_driver_sql(f"SELECT * FROM {table}").fetchall() for table in ids}
        schema = c.exec_driver_sql(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND name != 'alembic_version' ORDER BY name"
        ).fetchall()
    engine.dispose()
    copy = tmp_path / "phase2-copy.sqlite"
    shutil.copy2(original, copy)
    migrated = create_database_engine(copy)
    try:
        upgrade_database(migrated)
        upgrade_database(migrated)
        with migrated.connect() as c:
            assert (
                c.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0010_qa_package"
            )
            for table, facts in before.items():
                assert [
                    tuple(row)[: len(facts[0])]
                    for row in c.exec_driver_sql(f"SELECT * FROM {table}").fetchall()
                ] == [tuple(row) for row in facts]
            after = c.exec_driver_sql(
                "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND name != 'alembic_version' ORDER BY name"
            ).fetchall()
            assert preserved_objects(schema, after)
            assert len(inspect(c).get_table_names()) == 101
            assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        migrated.dispose()
    original_engine = create_database_engine(original, wal=False)
    try:
        with original_engine.connect() as c:
            assert (
                c.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == "0001_local_core"
            )
    finally:
        original_engine.dispose()


def test_fresh_database_to_latest_and_reopen(tmp_path):
    path = tmp_path / "fresh.sqlite"
    for _ in range(2):
        engine = create_database_engine(path)
        try:
            upgrade_database(engine)
            with engine.connect() as c:
                assert (
                    c.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                    == "0010_qa_package"
                )
                assert len(inspect(c).get_table_names()) == 101
                assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        finally:
            engine.dispose()
