from dataclasses import replace

import pytest
from sqlalchemy import event, inspect, text

from studium.application.commands import RecordAttempt
from studium.application.queries import GetStudentWorkProgress
from studium.domain.entities import Grade
from studium.domain.enums import AttemptResult, EnrollmentStatus, StudentWorkStatus
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId
from studium.infrastructure.database.migrations import upgrade_database
from studium.infrastructure.database.repositories import SqlAlchemyAttemptRepository
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from tests.unit.test_domain import attempt, instant, metadata


@pytest.mark.parametrize(
    "name",
    ["terms", "courses", "groups", "students", "offerings", "enrollments", "assessments", "works"],
)
def test_domain_database_domain_roundtrip(foundation, name):
    entity = foundation.entities[name]
    repository = getattr(foundation.repositories, name)
    assert repository.find_by_id(entity.id) == entity
    assert repository.list() == [entity]


def test_two_attempts_preserve_first_and_projection(foundation):
    r = foundation.repositories
    first = attempt(foundation.work.id, 1, AttemptResult.NEEDS_REVISION, day=5)
    second = attempt(foundation.work.id, 2, AttemptResult.ACCEPTED, day=1)
    RecordAttempt(r.attempts).execute(first)
    RecordAttempt(r.attempts).execute(second)
    assert r.attempts.find_by_id(first.id) == first
    assert r.attempts.find_by_id(second.id) == second
    assert r.attempts.history(foundation.work.id) == [first, second]
    assert (
        GetStudentWorkProgress(r.works).execute(foundation.work.id).status
        == StudentWorkStatus.ACCEPTED
    )
    with pytest.raises(RepositoryError) as error:
        r.attempts.append(replace(first, metadata=metadata()))
    assert error.value.failure == RepositoryFailure.DUPLICATE


@pytest.mark.parametrize("variant", ["pass", "fail", "numeric", "bounded", "traditional"])
def test_grade_repository_roundtrip(foundation, variant):
    result = AttemptResult.NEEDS_REVISION if variant == "fail" else AttemptResult.ACCEPTED
    score = 7 if variant in {"numeric", "bounded"} else None
    fact = attempt(foundation.work.id, 1, result, score=score)
    if variant == "bounded":
        fact = replace(fact, max_score=10)
    values = dict(metadata=metadata(), attempt_id=fact.id)
    if variant in {"pass", "fail"}:
        grade = Grade.pass_fail(**values, passed=variant == "pass")
    elif variant in {"numeric", "bounded"}:
        grade = Grade.numeric(**values, score=score, max_score=fact.max_score)
    else:
        grade = Grade.traditional(**values, label="Excellent")
    foundation.repositories.attempts.append(fact, grade=grade)
    assert foundation.repositories.grades.for_attempt(fact.id) == grade
    assert foundation.repositories.grades.find_by_id(grade.id) == grade
    assert foundation.repositories.attempts.find_by_id(fact.id) == fact


def test_failed_grade_rolls_back_entire_attempt(foundation):
    fact = attempt(foundation.work.id, 1, AttemptResult.ACCEPTED, score=7)
    grade = Grade.numeric(metadata=metadata(), attempt_id=fact.id, score=8)
    with pytest.raises(RepositoryError):
        foundation.repositories.attempts.append(fact, grade=grade)
    assert foundation.repositories.attempts.find_by_id(fact.id) is None
    assert foundation.repositories.grades.list() == []
    foundation.repositories.attempts.append(fact)


def test_soft_delete_revision_projection_and_reserved_number(foundation):
    r = foundation.repositories
    first = attempt(foundation.work.id, 1, AttemptResult.NEEDS_REVISION)
    second = attempt(foundation.work.id, 2, AttemptResult.ACCEPTED)
    r.attempts.append(first)
    r.attempts.append(second)
    r.attempts.soft_delete(second.id, expected_revision=1, at=instant(3))
    assert r.attempts.find_by_id(second.id) is None
    preserved = r.attempts.find_by_id(second.id, include_deleted=True)
    assert preserved.result == second.result and preserved.revision == 2
    assert r.attempts.history(foundation.work.id) == [first]
    assert len(r.attempts.history(foundation.work.id, include_deleted=True)) == 2
    assert r.works.progress(foundation.work.id).status == StudentWorkStatus.REVISION_REQUIRED
    with pytest.raises(RepositoryError):
        r.attempts.append(replace(second, metadata=metadata()))
    r.attempts.append(attempt(foundation.work.id, 3, AttemptResult.ACCEPTED))


def test_stale_update_cannot_overwrite_new_revision(foundation):
    repository = foundation.repositories.students
    original = foundation.student
    edited = replace(original, metadata=original.metadata.touch(instant(2)), notes="New")
    repository.update(edited, expected_revision=1)
    with pytest.raises(RepositoryError) as error:
        repository.update(replace(edited, notes="Stale"), expected_revision=1)
    assert error.value.failure == RepositoryFailure.REVISION_CONFLICT
    assert repository.find_by_id(original.id) == edited
    repository.soft_delete(original.id, expected_revision=2, at=instant(3))
    assert repository.list() == []
    assert repository.find_by_id(original.id, include_deleted=True).revision == 3


def test_membership_context_and_repeat_enrollment(foundation):
    r = foundation.repositories
    membership = foundation.enrollment
    with pytest.raises(RepositoryError) as error:
        r.enrollments.insert(replace(membership, metadata=metadata()))
    assert error.value.failure == RepositoryFailure.DUPLICATE
    ended = replace(
        membership,
        metadata=membership.metadata.touch(instant(2)),
        status=EnrollmentStatus.WITHDRAWN,
        ended_at=instant(2),
    )
    r.enrollments.update(ended, expected_revision=1)
    repeated = replace(membership, metadata=metadata(), enrolled_at=instant(2))
    r.enrollments.insert(repeated)
    assert r.enrollments.for_student(foundation.student.id) == [ended, repeated]


def test_unique_work_and_invalid_reference(foundation):
    r = foundation.repositories
    with pytest.raises(RepositoryError) as error:
        r.works.insert(replace(foundation.work, metadata=metadata()))
    assert error.value.failure == RepositoryFailure.DUPLICATE
    with pytest.raises(RepositoryError) as error:
        r.offerings.insert(
            replace(foundation.offering, metadata=metadata(), group_id=EntityId.generate())
        )
    assert error.value.failure == RepositoryFailure.INVALID_REFERENCE


def test_close_reopen_keeps_repository_data(foundation):
    fact = attempt(foundation.work.id, 1, AttemptResult.NEEDS_REVISION)
    foundation.repositories.attempts.append(fact)
    foundation.engine.dispose()
    reopened = create_database_engine(foundation.path)
    try:
        upgrade_database(reopened)
        repository = SqlAlchemyAttemptRepository(create_session_factory(reopened))
        assert repository.find_by_id(fact.id) == fact
        with reopened.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
    finally:
        reopened.dispose()


def test_fk_on_every_new_connection_and_orm_metadata(foundation):
    with foundation.engine.connect() as first, foundation.engine.connect() as second:
        for connection in [first, second]:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import CheckConstraint

    from studium.infrastructure.database.models import Base

    with foundation.engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []

    actual = inspect(foundation.engine)
    for table in Base.metadata.sorted_tables:
        assert {c.name for c in table.columns} == {
            c["name"] for c in actual.get_columns(table.name)
        }
        assert len(table.foreign_keys) == len(actual.get_foreign_keys(table.name))
        assert all(
            key["options"].get("ondelete")
            == (
                None
                if (table.name, key["constrained_columns"][0])
                in {
                    ("assessments", "homework_definition_id"),
                    ("assessments", "program_work_id"),
                    ("course_offerings", "work_program_id"),
                    ("lessons", "module_id"),
                    ("problems", "family_id"),
                }
                else "RESTRICT"
            )
            for key in actual.get_foreign_keys(table.name)
        )
        if table.name == "assessments":
            with foundation.engine.connect() as connection:
                added = next(
                    row
                    for row in connection.exec_driver_sql("PRAGMA foreign_key_list(assessments)")
                    if row[3] == "homework_definition_id"
                )
                assert added[6] == "NO ACTION"
        if table.name == "problems":
            with foundation.engine.connect() as connection:
                family_fk = next(
                    row
                    for row in connection.exec_driver_sql("PRAGMA foreign_key_list(problems)")
                    if row[3] == "family_id"
                )
                assert family_fk[6] == "NO ACTION"
        expected_checks = {
            str(c.sqltext).strip() for c in table.constraints if isinstance(c, CheckConstraint)
        }
        actual_checks = {c["sqltext"].strip() for c in actual.get_check_constraints(table.name)}
        assert actual_checks == expected_checks


def test_fresh_migration_failure_rolls_back_ddl(tmp_path):
    engine = create_database_engine(tmp_path / "failed.sqlite")

    def fail(_connection, _cursor, statement, _parameters, _context, _many):
        if "CREATE TABLE courses" in statement:
            raise RuntimeError("Simulated migration failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Simulated"):
            upgrade_database(engine)
        event.remove(engine, "before_cursor_execute", fail)
        assert inspect(engine).get_table_names() == []
        upgrade_database(engine)
        assert "attempts" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_unversioned_database_rejected_without_reset(tmp_path):
    engine = create_database_engine(tmp_path / "unversioned.sqlite")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE existing_data (value TEXT)"))
            connection.execute(text("INSERT INTO existing_data VALUES ('preserve')"))
        with pytest.raises(ValueError, match="Unversioned"):
            upgrade_database(engine)
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT value FROM existing_data")).scalar_one()
                == "preserve"
            )
    finally:
        engine.dispose()
