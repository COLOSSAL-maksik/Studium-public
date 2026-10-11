"""One SQLAlchemy transaction for a composed application operation."""

from contextlib import contextmanager

from sqlalchemy.exc import SQLAlchemyError

from studium.application.ports import Repositories
from studium.infrastructure.database import repositories as adapters
from studium.infrastructure.database.repositories.analytics_facts import (
    ADAPTERS as ANALYTICS_FACT_ADAPTERS,
)
from studium.infrastructure.database.repositories.communication import (
    ADAPTERS as COMMUNICATION_ADAPTERS,
)
from studium.infrastructure.database.repositories.content import ADAPTERS as CONTENT_ADAPTERS
from studium.infrastructure.database.repositories.files import ADAPTERS as FILE_ADAPTERS
from studium.infrastructure.database.repositories.learning import ADAPTERS
from studium.infrastructure.database.repositories.program import ADAPTERS as PROGRAM_ADAPTERS
from studium.infrastructure.database.repositories.qa import ADAPTERS as QA_ADAPTERS


def repository_set(sessions) -> Repositories:
    return Repositories(
        **{
            name: cls(sessions)
            for name, cls in {
                "terms": adapters.SqlAlchemyAcademicTermRepository,
                "courses": adapters.SqlAlchemyCourseRepository,
                "groups": adapters.SqlAlchemyStudentGroupRepository,
                "offerings": adapters.SqlAlchemyCourseOfferingRepository,
                "students": adapters.SqlAlchemyStudentRepository,
                "enrollments": adapters.SqlAlchemyEnrollmentRepository,
                "assessments": adapters.SqlAlchemyAssessmentRepository,
                "works": adapters.SqlAlchemyStudentWorkRepository,
                "attempts": adapters.SqlAlchemyAttemptRepository,
                "grades": adapters.SqlAlchemyGradeRepository,
                **ADAPTERS,
                **FILE_ADAPTERS,
                **COMMUNICATION_ADAPTERS,
                **ANALYTICS_FACT_ADAPTERS,
                **CONTENT_ADAPTERS,
                **PROGRAM_ADAPTERS,
                **QA_ADAPTERS,
            }.items()
        }
    )


def transaction_factory(sessions):
    @contextmanager
    def transaction():
        try:
            with sessions.begin() as session:
                yield repository_set(session)
        except SQLAlchemyError as error:
            raise adapters.translate_error(error) from None

    return transaction
