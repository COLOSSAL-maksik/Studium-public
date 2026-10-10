"""Content adapters sharing core compare-and-swap and transaction policy."""

from studium.domain import content as e
from studium.infrastructure.database.models import content as m
from studium.infrastructure.database.repositories import SqlAlchemyMutableRepository
from studium.infrastructure.database.repositories.learning import LinkRepository

SPECS = {
    "homework_definitions": (e.HomeworkDefinition, m.HomeworkDefinitionRow, None, None),
    "problems": (e.Problem, m.ProblemRow, None, None),
    "problem_collections": (e.ProblemCollection, m.ProblemCollectionRow, None, None),
    "problem_collection_members": (
        e.ProblemCollectionMember,
        m.ProblemCollectionMemberRow,
        "collection_id",
        "problem_id",
    ),
    "seminar_materials": (e.SeminarMaterial, m.SeminarMaterialRow, None, None),
    "seminar_material_topics": (
        e.SeminarMaterialTopic,
        m.SeminarMaterialTopicRow,
        "seminar_material_id",
        "topic_id",
    ),
    "literature_items": (e.LiteratureItem, m.LiteratureItemRow, None, None),
    "homework_attachments": (
        e.HomeworkAttachment,
        m.HomeworkAttachmentRow,
        "homework_definition_id",
        "file_asset_id",
    ),
    "problem_attachments": (
        e.ProblemAttachment,
        m.ProblemAttachmentRow,
        "problem_id",
        "file_asset_id",
    ),
    "seminar_attachments": (
        e.SeminarAttachment,
        m.SeminarAttachmentRow,
        "seminar_material_id",
        "file_asset_id",
    ),
    "literature_attachments": (
        e.LiteratureAttachment,
        m.LiteratureAttachmentRow,
        "literature_item_id",
        "file_asset_id",
    ),
    "ticket_sets": (e.TicketSet, m.TicketSetRow, None, None),
    "tickets": (e.Ticket, m.TicketRow, "ticket_set_id", "id"),
    "ticket_problems": (e.TicketProblem, m.TicketProblemRow, "ticket_id", "problem_id"),
    "ticket_problem_files": (
        e.TicketProblemFile,
        m.TicketProblemFileRow,
        "ticket_problem_id",
        "file_asset_id",
    ),
    "ticket_assignments": (
        e.TicketAssignment,
        m.TicketAssignmentRow,
        "ticket_set_id",
        "enrollment_id",
    ),
}
ADAPTERS = {
    name: type(
        entity.__name__ + "Repository",
        (LinkRepository if owner else SqlAlchemyMutableRepository,),
        {"entity_type": entity, "row_type": row, "owner_field": owner, "target_field": target},
    )
    for name, (entity, row, owner, target) in SPECS.items()
}
