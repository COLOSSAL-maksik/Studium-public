"""Test-only historical population: map only columns that existed in that revision.

Production adapters always use the latest schema. These adapters preserve the
original populated-copy scenarios after additive v6 columns, without changing
old migrations or pretending a fresh v6 database is a historical database.
"""

from contextlib import contextmanager
from dataclasses import MISSING, fields, replace
from types import SimpleNamespace
from weakref import WeakKeyDictionary

from sqlalchemy import MetaData, inspect, update
from sqlalchemy.orm import Session, registry

from studium.application.services import StudiumService
from studium.infrastructure.database.repositories import entity_values
from studium.infrastructure.database.unit_of_work import repository_set as latest_repositories


class HistoricalStudiumService(StudiumService):
    """Populate a real v1-v6 database without inventing v7 program records."""

    def _default_program(self, repositories, term, course, group):
        return SimpleNamespace(id=None)

    def _snapshot_problem_skills(self, repositories):
        return {}


_cache = WeakKeyDictionary()


def repository_set(sessions):
    result = latest_repositories(sessions)
    bind = sessions.get_bind() if isinstance(sessions, Session) else sessions.kw["bind"]
    if bind not in _cache:
        with bind.connect() as connection:
            if "problems" in inspect(connection).get_table_names() and "purposes_json" in {
                c["name"] for c in inspect(connection).get_columns("problems")
            }:
                _cache[bind] = {}
            else:
                metadata = MetaData()
                metadata.reflect(connection)
                mappings = registry(metadata=metadata)
                classes = {}
                for name in (
                    "terms",
                    "groups",
                    "offerings",
                    "assessments",
                    "lessons",
                    "homework_definitions",
                    "problems",
                    "seminar_materials",
                ):
                    repository = getattr(result, name)
                    table_name = repository.row_type.__table__.name
                    if table_name not in metadata.tables:
                        continue
                    table = metadata.tables[table_name]
                    attributes = {
                        field.name: field.default
                        for field in fields(repository.entity_type)
                        if field.name != "metadata"
                        and field.name not in table.c
                        and field.default is not MISSING
                    }
                    row = type("Historical" + repository.entity_type.__name__, (), attributes)
                    mappings.map_imperatively(row, table)

                    def insert(self, session, entity):
                        values = {
                            key: value
                            for key, value in entity_values(entity).items()
                            if key in self.row_type.__table__.c
                        }
                        session.add(self.row_type(**values))
                        session.flush()

                    def compare(self, session, entity, expected_revision):
                        from studium.domain.repositories import RepositoryError, RepositoryFailure

                        values = {
                            key: value
                            for key, value in entity_values(entity).items()
                            if key in self.row_type.__table__.c
                        }
                        changed = session.execute(
                            update(self.row_type)
                            .where(
                                self.row_type.id == str(entity.id),
                                self.row_type.revision == expected_revision,
                            )
                            .values(**values)
                        )
                        if entity.revision != expected_revision + 1 or changed.rowcount != 1:
                            raise RepositoryError(
                                RepositoryFailure.REVISION_CONFLICT,
                                "Historical test revision conflict",
                            )

                    classes[name] = type(
                        "Historical" + type(repository).__name__,
                        (type(repository),),
                        {"row_type": row, "_insert": insert, "_compare_and_swap": compare},
                    )
                _cache[bind] = classes
    return replace(result, **{name: cls(sessions) for name, cls in _cache[bind].items()})


def transaction_factory(sessions):
    @contextmanager
    def transaction():
        with sessions.begin() as session:
            yield repository_set(session)

    return transaction


def preserved_rows(before, after):
    """ALTER adds columns at the end; compare every preexisting value verbatim."""
    for table, rows in before.items():
        if table == "homework_definitions":
            if rows and not set(map(tuple, rows)).issubset(
                {tuple(row)[: len(rows[0])] for row in after[table]}
            ):
                return False
        elif rows:
            if [tuple(row)[: len(rows[0])] for row in after[table]] != list(map(tuple, rows)):
                return False
        elif after[table]:
            return False
    return True


def preserved_objects(before, after):
    def normalize(obj):
        kind, name, sql = tuple(obj)
        if kind == "table" and name == "file_assets" and sql:
            sql = sql.replace("'doc','docx'", "'docx'")
        return kind, name, sql

    altered = {
        "academic_terms",
        "student_groups",
        "course_offerings",
        "assessments",
        "lessons",
        "homework_definitions",
        "problems",
        "seminar_materials",
    }
    old = [normalize(obj) for obj in before if not (obj[0] == "table" and obj[1] in altered)]
    return set(old).issubset({normalize(obj) for obj in after})
