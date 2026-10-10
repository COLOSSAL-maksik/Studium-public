"""Explicit v2 mappings. Production DDL lives in the immutable v0002.sql snapshot."""

from sqlalchemy import (
    REAL,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    text,
)

from studium.infrastructure.database.models.base import Base


def reference(name, table, *, nullable=False):
    return Column(name, Text, ForeignKey(table + ".id", ondelete="RESTRICT"), nullable=nullable)


def record(name, *content):
    return Table(
        name,
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        *content,
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer' AND updated_at >= created_at"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint(
            "deleted_at IS NULL OR (typeof(deleted_at) = 'integer' AND deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
    )


def title():
    return Column("title", Text, nullable=False), CheckConstraint("length(trim(title)) > 0")


def description():
    return Column("description", Text, nullable=False, server_default=text("''"))


def order():
    return (
        Column("sort_order", Integer, nullable=False, server_default=text("0")),
        CheckConstraint("typeof(sort_order) = 'integer' AND sort_order >= 0"),
    )


class TopicRow(Base):
    __table__ = record(
        "topics",
        reference("course_id", "courses"),
        reference("parent_topic_id", "topics", nullable=True),
        *title(),
        description(),
        *order(),
        CheckConstraint("parent_topic_id IS NULL OR parent_topic_id != id"),
    )


class SkillRow(Base):
    __table__ = record(
        "skills", reference("course_id", "courses"), *title(), description(), *order()
    )


class LessonRow(Base):
    __table__ = record(
        "lessons",
        reference("course_offering_id", "course_offerings"),
        Column("lesson_date", Text, nullable=False),
        Column("planned_date", Text),
        Column("planned_week", Integer),
        Column("module_id", Text, ForeignKey("program_modules.id")),
        Column("cancelled", Integer, nullable=False, server_default=text("0")),
        Column("cancellation_reason", Text, nullable=False, server_default=text("''")),
        CheckConstraint("cancelled IN (0,1)"),
        CheckConstraint(
            "planned_week IS NULL OR (typeof(planned_week) = 'integer' AND planned_week >= 1)"
        ),
        CheckConstraint(
            "planned_date IS NULL OR (date(planned_date, '+0 days') IS NOT NULL AND date(planned_date, '+0 days') = planned_date)"
        ),
        Column("title", Text, nullable=False, server_default=text("''")),
        Column("notes", Text, nullable=False, server_default=text("''")),
        Column("type", Text, nullable=False, server_default=text("'SEMINAR'")),
        CheckConstraint("type IN ('SEMINAR','LECTURE')"),
        CheckConstraint(
            "length(lesson_date) = 10 AND lesson_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND substr(lesson_date, 1, 4) != '0000' AND date(lesson_date, '+0 days') IS NOT NULL AND date(lesson_date, '+0 days') = lesson_date"
        ),
    )


class AttendanceRow(Base):
    __table__ = record(
        "attendance",
        reference("lesson_id", "lessons"),
        reference("enrollment_id", "enrollments"),
        Column("status", Text, nullable=False),
        Column("comment", Text, nullable=False, server_default=text("''")),
        UniqueConstraint("lesson_id", "enrollment_id"),
        CheckConstraint("status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED', 'UNKNOWN')"),
    )


class AssessmentItemRow(Base):
    __table__ = record(
        "assessment_items",
        reference("assessment_id", "assessments"),
        *title(),
        description(),
        *order(),
        Column("max_score", REAL),
        CheckConstraint(
            "max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)"
        ),
    )


def link(name, owner, owner_table, target, target_table):
    return record(
        name,
        reference(owner, owner_table),
        reference(target, target_table),
        UniqueConstraint(owner, target),
    )


class TopicSkillRow(Base):
    __table__ = link("topic_skills", "topic_id", "topics", "skill_id", "skills")


class LessonTopicRow(Base):
    __table__ = link("lesson_topics", "lesson_id", "lessons", "topic_id", "topics")


class AssessmentTopicRow(Base):
    __table__ = link("assessment_topics", "assessment_id", "assessments", "topic_id", "topics")


class AssessmentSkillRow(Base):
    __table__ = link("assessment_skills", "assessment_id", "assessments", "skill_id", "skills")


class AssessmentItemTopicRow(Base):
    __table__ = link(
        "assessment_item_topics", "assessment_item_id", "assessment_items", "topic_id", "topics"
    )


class AssessmentItemSkillRow(Base):
    __table__ = link(
        "assessment_item_skills", "assessment_item_id", "assessment_items", "skill_id", "skills"
    )


for row, columns in [
    (TopicRow, ("course_id", "parent_topic_id", "sort_order")),
    (SkillRow, ("course_id", "sort_order")),
    (LessonRow, ("course_offering_id", "lesson_date")),
    (AttendanceRow, ("enrollment_id",)),
    (AssessmentItemRow, ("assessment_id", "sort_order")),
    (TopicSkillRow, ("skill_id",)),
    (LessonTopicRow, ("topic_id",)),
    (AssessmentTopicRow, ("topic_id",)),
    (AssessmentSkillRow, ("skill_id",)),
    (AssessmentItemTopicRow, ("topic_id",)),
    (AssessmentItemSkillRow, ("skill_id",)),
]:
    Index(row.__table__.name + "_lookup", *(row.__table__.c[c] for c in columns))
