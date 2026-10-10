"""Explicit content tables, extended additively through v8 production migrations."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)

from studium.infrastructure.database.models.base import Base
from studium.infrastructure.database.models.learning import record, reference, title


def prose(name):
    return Column(name, Text, nullable=False, server_default=text("''"))


def content(name, *fields, optional_course=False):
    return record(
        name,
        reference("course_id", "courses", nullable=optional_course),
        *title(),
        prose("notes"),
        Column("tags_json", Text, nullable=False, server_default=text("'[]'")),
        Column("details_json", Text, nullable=False, server_default=text("'{}'")),
        CheckConstraint("json_valid(tags_json) AND json_type(tags_json) = 'array'"),
        CheckConstraint("json_valid(details_json) AND json_type(details_json) = 'object'"),
        *fields,
    )


class HomeworkDefinitionRow(Base):
    __table__ = content(
        "homework_definitions",
        prose("label"),
        prose("description"),
        Column("type", Text, nullable=False, server_default=text("'HOMEWORK'")),
        CheckConstraint(
            "type IN ('HOMEWORK','CONTROL_WORK','LAB','DEFENSE','EXAM','TEST','OTHER')"
        ),
    )


class ProblemRow(Base):
    __table__ = content(
        "problems",
        prose("statement"),
        prose("correct_answer"),
        prose("solution"),
        prose("difficulty"),
        prose("identifier"),
        Column("purposes_json", Text, nullable=False, server_default=text("'[]'")),
        Column("is_family", Boolean, nullable=False, server_default=text("0")),
        # SQLite ADD COLUMN keeps this as an inline FK, as with v7 additions.
        Column("family_id", Text, ForeignKey("problems.id"), nullable=True),
        prose("variant_code"),
        prose("parameters"),
        CheckConstraint("json_valid(purposes_json) AND json_type(purposes_json) = 'array'"),
        CheckConstraint("is_family IN (0,1)"),
    )


class ProblemCollectionRow(Base):
    __table__ = record(
        "problem_collections", reference("course_id", "courses"), *title(), prose("notes")
    )


class ProblemCollectionMemberRow(Base):
    __table__ = record(
        "problem_collection_members",
        reference("collection_id", "problem_collections"),
        reference("problem_id", "problems"),
        UniqueConstraint("collection_id", "problem_id"),
    )


class SeminarMaterialRow(Base):
    __table__ = content(
        "seminar_materials",
        Column("planned_week", Integer),
        CheckConstraint(
            "planned_week IS NULL OR (typeof(planned_week) = 'integer' AND planned_week >= 1)"
        ),
        prose("plan_text"),
        prose("full_text"),
        Column("type", Text, nullable=False, server_default=text("'SEMINAR'")),
        CheckConstraint("type IN ('SEMINAR','LECTURE')"),
    )


class SeminarMaterialTopicRow(Base):
    __table__ = record(
        "seminar_material_topics",
        reference("seminar_material_id", "seminar_materials"),
        reference("topic_id", "topics"),
        UniqueConstraint("seminar_material_id", "topic_id"),
    )


class LiteratureItemRow(Base):
    __table__ = content(
        "literature_items",
        prose("authors"),
        Column("year", Integer),
        Column("type", Text, nullable=False, server_default=text("'OTHER'")),
        CheckConstraint("year IS NULL OR (typeof(year) = 'integer' AND year BETWEEN 1 AND 9999)"),
        CheckConstraint("type IN ('TEXTBOOK','STUDY_GUIDE','METHOD_GUIDE','ARTICLE','OTHER')"),
        optional_course=True,
    )


def attachment(name, owner, target):
    return record(
        name,
        reference(owner, target),
        reference("file_asset_id", "file_assets"),
        prose("caption"),
        Column("sort_order", Integer, nullable=False, server_default=text("0")),
        Column("role", Text, nullable=False, server_default=text("'STATEMENT'")),
        CheckConstraint("typeof(sort_order) = 'integer' AND sort_order >= 0"),
        CheckConstraint("role IN ('STATEMENT','REFERENCE','SOLUTION')"),
        UniqueConstraint(owner, "file_asset_id"),
    )


class HomeworkAttachmentRow(Base):
    __table__ = attachment("homework_attachments", "homework_definition_id", "homework_definitions")


class ProblemAttachmentRow(Base):
    __table__ = attachment("problem_attachments", "problem_id", "problems")


class SeminarAttachmentRow(Base):
    __table__ = attachment("seminar_attachments", "seminar_material_id", "seminar_materials")


class LiteratureAttachmentRow(Base):
    __table__ = attachment("literature_attachments", "literature_item_id", "literature_items")


class TicketSetRow(Base):
    __table__ = record(
        "ticket_sets",
        reference("course_offering_id", "course_offerings"),
        reference("assessment_id", "assessments", nullable=True),
        *title(),
        Column("criteria_json", Text, nullable=False),
        CheckConstraint("json_valid(criteria_json) AND json_type(criteria_json) = 'object'"),
    )


class TicketRow(Base):
    __table__ = record(
        "tickets",
        reference("ticket_set_id", "ticket_sets"),
        Column("number", Integer, nullable=False),
        CheckConstraint("typeof(number) = 'integer' AND number >= 1"),
        UniqueConstraint("ticket_set_id", "number"),
    )


class TicketProblemRow(Base):
    __table__ = record(
        "ticket_problems",
        reference("ticket_id", "tickets"),
        reference("problem_id", "problems"),
        Column("position", Integer, nullable=False),
        Column("source_revision", Integer, nullable=False),
        prose("title_snapshot"),
        prose("statement_snapshot"),
        Column("teacher_snapshot_json", Text, nullable=False),
        CheckConstraint("typeof(position) = 'integer' AND position >= 1"),
        CheckConstraint("typeof(source_revision) = 'integer' AND source_revision >= 1"),
        CheckConstraint("length(trim(title_snapshot)) > 0"),
        CheckConstraint(
            "json_valid(teacher_snapshot_json) AND json_type(teacher_snapshot_json) = 'object'"
        ),
        UniqueConstraint("ticket_id", "position"),
        UniqueConstraint("ticket_id", "problem_id"),
    )


class TicketProblemFileRow(Base):
    __table__ = record(
        "ticket_problem_files",
        reference("ticket_problem_id", "ticket_problems"),
        reference("file_asset_id", "file_assets"),
        Column("role", Text, nullable=False),
        Column("sort_order", Integer, nullable=False),
        CheckConstraint("role IN ('STATEMENT','REFERENCE','SOLUTION')"),
        CheckConstraint("typeof(sort_order) = 'integer' AND sort_order >= 0"),
        UniqueConstraint("ticket_problem_id", "file_asset_id"),
    )


class TicketAssignmentRow(Base):
    __table__ = record(
        "ticket_assignments",
        reference("ticket_set_id", "ticket_sets"),
        reference("ticket_id", "tickets"),
        reference("enrollment_id", "enrollments"),
        UniqueConstraint("ticket_set_id", "enrollment_id"),
    )


ROWS = (
    HomeworkDefinitionRow,
    ProblemRow,
    ProblemCollectionRow,
    ProblemCollectionMemberRow,
    SeminarMaterialRow,
    SeminarMaterialTopicRow,
    LiteratureItemRow,
    HomeworkAttachmentRow,
    ProblemAttachmentRow,
    SeminarAttachmentRow,
    LiteratureAttachmentRow,
    TicketSetRow,
    TicketRow,
    TicketProblemRow,
    TicketProblemFileRow,
    TicketAssignmentRow,
)
for row in ROWS:
    for column in row.__table__.columns:
        if column.foreign_keys:
            Index(row.__table__.name + "_" + column.name, column)

Index(
    "uq_problem_variant_code",
    ProblemRow.__table__.c.family_id,
    ProblemRow.__table__.c.variant_code,
    unique=True,
    sqlite_where=ProblemRow.__table__.c.family_id.is_not(None),
)

Index(
    "problems_identifier_active",
    ProblemRow.__table__.c.course_id,
    ProblemRow.__table__.c.identifier,
    unique=True,
    sqlite_where=(
        ProblemRow.__table__.c.deleted_at.is_(None) & (ProblemRow.__table__.c.identifier != "")
    ),
)
