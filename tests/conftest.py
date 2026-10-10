import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from studium.domain.entities import (
    AcademicTerm,
    Assessment,
    Course,
    CourseOffering,
    Enrollment,
    Student,
    StudentGroup,
    StudentWork,
)
from studium.domain.enums import AssessmentType
from studium.domain.value_objects import EntityMetadata, LocalDate
from studium.infrastructure.database import repositories as repo
from studium.infrastructure.database.migrations import upgrade_database
from studium.infrastructure.database.repositories.learning import ADAPTERS
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from tests.unit.test_domain import instant

_production_root = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Studium"
).resolve()
_isolation = None
_original_localappdata = None


def _protect_production(event, args):
    """Refuse direct reads/writes too, even when a future test bypasses AppPaths."""
    if _isolation is None:
        return
    if event in {"open", "os.listdir", "os.scandir", "sqlite3.connect"} and args:
        value = args[0]
        if isinstance(value, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(value)).resolve()
            if path.is_relative_to(_production_root):
                raise RuntimeError("Tests cannot access production Studium storage")


sys.addaudithook(_protect_production)


def pytest_configure(config):
    # Before collection, also inherited by child processes. Never inspect production.
    global _isolation, _original_localappdata
    _original_localappdata = os.environ.get("LOCALAPPDATA")
    _isolation = TemporaryDirectory(prefix="studium-pytest-profile-")
    os.environ["LOCALAPPDATA"] = _isolation.name


def pytest_unconfigure(config):
    global _isolation
    isolated = _isolation
    _isolation = None
    if _original_localappdata is None:
        os.environ.pop("LOCALAPPDATA", None)
    else:
        os.environ["LOCALAPPDATA"] = _original_localappdata
    if isolated is not None:
        isolated.cleanup()


@pytest.fixture(autouse=True)
def isolated_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "profile"))


@pytest.fixture
def foundation(tmp_path):
    path = tmp_path / "integration.sqlite"
    engine = create_database_engine(path)
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    repositories = {}
    for name, cls in {
        "terms": repo.SqlAlchemyAcademicTermRepository,
        "courses": repo.SqlAlchemyCourseRepository,
        "groups": repo.SqlAlchemyStudentGroupRepository,
        "students": repo.SqlAlchemyStudentRepository,
        "offerings": repo.SqlAlchemyCourseOfferingRepository,
        "enrollments": repo.SqlAlchemyEnrollmentRepository,
        "assessments": repo.SqlAlchemyAssessmentRepository,
        "works": repo.SqlAlchemyStudentWorkRepository,
        "attempts": repo.SqlAlchemyAttemptRepository,
        "grades": repo.SqlAlchemyGradeRepository,
        **ADAPTERS,
    }.items():
        repositories[name] = cls(sessions)
    r = SimpleNamespace(**repositories)

    def meta() -> EntityMetadata:
        return EntityMetadata.create(instant())

    term = AcademicTerm(
        metadata=meta(),
        name="Synthetic term",
        starts_on=LocalDate(2026, 9, 1),
        ends_on=LocalDate(2027, 1, 31),
    )
    course = Course(
        metadata=meta(), name="Synthetic course", short_name="TEST", description="Synthetic"
    )
    group = StudentGroup(
        metadata=meta(), number="TEST-01", department="Test", faculty="Test", notes="Synthetic"
    )
    student = Student(
        metadata=meta(), full_name="Synthetic Student", preferred_name="Test", notes="Synthetic"
    )
    offering = CourseOffering(
        metadata=meta(), term_id=term.id, course_id=course.id, group_id=group.id
    )
    enrollment = Enrollment(
        metadata=meta(), student_id=student.id, offering_id=offering.id, enrolled_at=instant()
    )
    assessment = Assessment(
        metadata=meta(),
        offering_id=offering.id,
        type=AssessmentType.HOMEWORK,
        title="Test",
        number="1",
        description="Synthetic",
        issued_at=instant(),
        due_at=instant(2),
        max_score=10,
    )
    work = StudentWork(metadata=meta(), assessment_id=assessment.id, student_id=student.id)
    entities = dict(
        terms=term,
        courses=course,
        groups=group,
        students=student,
        offerings=offering,
        enrollments=enrollment,
        assessments=assessment,
        works=work,
    )
    for name, entity in entities.items():
        repositories[name].insert(entity)
    yield SimpleNamespace(
        path=path,
        engine=engine,
        repositories=r,
        entities=entities,
        work=work,
        student=student,
        enrollment=enrollment,
        assessment=assessment,
        offering=offering,
    )
    engine.dispose()
