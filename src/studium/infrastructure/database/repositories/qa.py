"""QA repositories retain the standard transaction/CAS policy and concrete owner queries."""

from studium.domain import qa
from studium.domain.enums import AssessmentType, AttemptResult, GradeKind
from studium.infrastructure.database.models.qa import SPECS
from studium.infrastructure.database.repositories import (
    BOOLEAN_FIELDS,
    ENUM_FIELDS,
    TIME_FIELDS,
    SqlAlchemyMutableRepository,
)
from studium.infrastructure.database.repositories.learning import LinkRepository

ENUM_FIELDS.update(
    {
        qa.PlannedWork: {"type": AssessmentType},
        qa.Review: {"result": AttemptResult},
        qa.ReviewGrade: {"kind": GradeKind},
    }
)
BOOLEAN_FIELDS.add("configured")
TIME_FIELDS.update(
    {"exact_due_at", "actual_issued_at", "received_at", "reviewed_at", "returned_at"}
)

ADAPTERS = {
    name: type(
        entity.__name__ + "Repository",
        (LinkRepository if owner else SqlAlchemyMutableRepository,),
        {"entity_type": entity, "row_type": row, "owner_field": owner, "target_field": target},
    )
    for name, (entity, row, owner, target) in SPECS.items()
}
