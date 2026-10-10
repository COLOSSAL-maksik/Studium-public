"""Program repositories reuse the existing transaction and revision policy."""

from studium.infrastructure.database.models.program import SPECS
from studium.infrastructure.database.repositories import SqlAlchemyMutableRepository
from studium.infrastructure.database.repositories.learning import LinkRepository

ADAPTERS = {
    name: type(
        entity.__name__ + "Repository",
        (LinkRepository if owner else SqlAlchemyMutableRepository,),
        {"entity_type": entity, "row_type": row, "owner_field": owner, "target_field": target},
    )
    for name, (entity, row, owner, target) in SPECS.items()
}
