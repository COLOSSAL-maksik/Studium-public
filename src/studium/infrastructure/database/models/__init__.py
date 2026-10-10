"""Explicit SQLAlchemy mappings for the Alembic-managed local schema."""

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

from studium.infrastructure.database.models import analytics_facts as analytics_facts
from studium.infrastructure.database.models import communication as communication
from studium.infrastructure.database.models import files as files
from studium.infrastructure.database.models import learning as learning
from studium.infrastructure.database.models import program as program
from studium.infrastructure.database.models.base import Base


class AcademicTermRow(Base):
    __table__ = Table(
        "academic_terms",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column("name", Text, nullable=False),
        Column("starts_on", Text, nullable=False),
        Column("ends_on", Text, nullable=False),
        Column("archived", Integer, nullable=False, server_default=text("0")),
        Column("week_utc_offset_minutes", Integer, nullable=False, server_default=text("180")),
        CheckConstraint(
            "typeof(week_utc_offset_minutes) = 'integer' AND week_utc_offset_minutes BETWEEN -840 AND 840"
        ),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("length(trim(name)) > 0"),
        CheckConstraint(
            "length(starts_on) = 10 AND starts_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND substr(starts_on, 1, 4) != '0000' AND date(starts_on, '+0 days') IS NOT NULL AND date(starts_on, '+0 days') = starts_on"
        ),
        CheckConstraint(
            "length(ends_on) = 10 AND ends_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND substr(ends_on, 1, 4) != '0000' AND date(ends_on, '+0 days') IS NOT NULL AND date(ends_on, '+0 days') = ends_on"
        ),
        CheckConstraint("archived IN (0, 1)"),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
        CheckConstraint("ends_on >= starts_on"),
    )


class CourseRow(Base):
    __table__ = Table(
        "courses",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column("name", Text, nullable=False),
        Column("short_name", Text, nullable=False, server_default=text("''")),
        Column("description", Text, nullable=False, server_default=text("''")),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("length(trim(name)) > 0"),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
    )


class StudentGroupRow(Base):
    __table__ = Table(
        "student_groups",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column("number", Text, nullable=False),
        Column("department", Text, nullable=False, server_default=text("''")),
        Column("faculty", Text, nullable=False, server_default=text("''")),
        Column("faculty_short", Text, nullable=False, server_default=text("''")),
        Column("notes", Text, nullable=False, server_default=text("''")),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("length(trim(number)) > 0"),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
    )


class CourseOfferingRow(Base):
    __table__ = Table(
        "course_offerings",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column(
            "term_id", Text, ForeignKey("academic_terms.id", ondelete="RESTRICT"), nullable=False
        ),
        Column("course_id", Text, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False),
        Column("work_program_id", Text, ForeignKey("work_programs.id")),
        Column(
            "group_id", Text, ForeignKey("student_groups.id", ondelete="RESTRICT"), nullable=False
        ),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
    )


class StudentRow(Base):
    __table__ = Table(
        "students",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column("full_name", Text, nullable=False),
        Column("preferred_name", Text, nullable=True),
        Column("notes", Text, nullable=False, server_default=text("''")),
        Column("active", Integer, nullable=False, server_default=text("1")),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("length(trim(full_name)) > 0"),
        CheckConstraint("preferred_name IS NULL OR length(trim(preferred_name)) > 0"),
        CheckConstraint("active IN (0, 1)"),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
    )


class EnrollmentRow(Base):
    __table__ = Table(
        "enrollments",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column("student_id", Text, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        Column(
            "offering_id",
            Text,
            ForeignKey("course_offerings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        Column("enrolled_at", Integer, nullable=False),
        Column("status", Text, nullable=False),
        Column("ended_at", Integer, nullable=True),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("typeof(enrolled_at) = 'integer'"),
        CheckConstraint("status IN ('ACTIVE', 'WITHDRAWN', 'COMPLETED')"),
        CheckConstraint("ended_at IS NULL OR typeof(ended_at) = 'integer'"),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND ended_at IS NULL) OR (status != 'ACTIVE' AND ended_at IS NOT NULL)"
        ),
        CheckConstraint("ended_at IS NULL OR ended_at >= enrolled_at"),
    )


class AssessmentRow(Base):
    __table__ = Table(
        "assessments",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column(
            "offering_id",
            Text,
            ForeignKey("course_offerings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        Column("type", Text, nullable=False),
        Column("number", Text, nullable=True),
        Column("title", Text, nullable=False),
        Column("description", Text, nullable=False, server_default=text("''")),
        Column("issued_at", Integer, nullable=False),
        Column("due_at", Integer, nullable=True),
        Column("max_score", REAL, nullable=True),
        Column("planned_issue_week", Integer),
        Column("planned_due_week", Integer),
        Column("program_work_id", Text, ForeignKey("program_works.id")),
        Column(
            "homework_definition_id",
            Text,
            ForeignKey("homework_definitions.id"),
        ),
        CheckConstraint(
            "planned_issue_week IS NULL OR (typeof(planned_issue_week) = 'integer' AND planned_issue_week >= 1)"
        ),
        CheckConstraint(
            "planned_due_week IS NULL OR (typeof(planned_due_week) = 'integer' AND planned_due_week >= 1)"
        ),
        CheckConstraint(
            "planned_issue_week IS NULL OR planned_due_week IS NULL OR planned_due_week >= planned_issue_week"
        ),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint(
            "type IN ('HOMEWORK', 'TEST', 'CONTROL_WORK', 'DEFENSE', 'LAB', 'EXAM', 'OTHER')"
        ),
        CheckConstraint("length(trim(title)) > 0"),
        CheckConstraint("typeof(issued_at) = 'integer'"),
        CheckConstraint("due_at IS NULL OR typeof(due_at) = 'integer'"),
        CheckConstraint(
            "max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)"
        ),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
        CheckConstraint("due_at IS NULL OR due_at >= issued_at"),
    )


class StudentWorkRow(Base):
    __table__ = Table(
        "student_works",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column(
            "assessment_id", Text, ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
        ),
        Column("student_id", Text, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        UniqueConstraint("student_id", "assessment_id"),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
    )


class AttemptRow(Base):
    __table__ = Table(
        "attempts",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column(
            "student_work_id",
            Text,
            ForeignKey("student_works.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        Column("attempt_no", Integer, nullable=False),
        Column("occurred_at", Integer, nullable=False),
        Column("result", Text, nullable=False),
        Column("comment", Text, nullable=False, server_default=text("''")),
        Column("score", REAL, nullable=True),
        Column("max_score", REAL, nullable=True),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        UniqueConstraint("student_work_id", "attempt_no"),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("typeof(attempt_no) = 'integer' AND attempt_no >= 1"),
        CheckConstraint("typeof(occurred_at) = 'integer'"),
        CheckConstraint(
            "result IN ('PRESENTED', 'NEEDS_REVISION', 'ACCEPTED', 'SCORED', 'REJECTED', 'COMMENT_ONLY')"
        ),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1.7976931348623157e308)"),
        CheckConstraint(
            "max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)"
        ),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
        CheckConstraint("score IS NULL OR max_score IS NULL OR score <= max_score"),
        CheckConstraint("result != 'SCORED' OR score IS NOT NULL"),
    )


class GradeRow(Base):
    __table__ = Table(
        "grades",
        Base.metadata,
        Column("id", Text, primary_key=True, nullable=False),
        Column(
            "attempt_id",
            Text,
            ForeignKey("attempts.id", ondelete="RESTRICT"),
            unique=True,
            nullable=False,
        ),
        Column("kind", Text, nullable=False),
        Column("passed", Integer, nullable=True),
        Column("score", REAL, nullable=True),
        Column("max_score", REAL, nullable=True),
        Column("label", Text, nullable=True),
        Column("created_at", Integer, nullable=False),
        Column("updated_at", Integer, nullable=False),
        Column("revision", Integer, nullable=False, server_default=text("1")),
        Column("deleted_at", Integer, nullable=True),
        CheckConstraint(
            "length(id) = 36 AND substr(id, 9, 1) = '-' AND substr(id, 14, 1) = '-' AND substr(id, 19, 1) = '-' AND substr(id, 24, 1) = '-' AND length(replace(id, '-', '')) = 32 AND replace(id, '-', '') NOT GLOB '*[^0-9a-f]*'"
        ),
        CheckConstraint("kind IN ('PASS_FAIL', 'NUMERIC', 'TRADITIONAL')"),
        CheckConstraint("passed IS NULL OR passed IN (0, 1)"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 1.7976931348623157e308)"),
        CheckConstraint(
            "max_score IS NULL OR (max_score > 0 AND max_score <= 1.7976931348623157e308)"
        ),
        CheckConstraint("typeof(created_at) = 'integer'"),
        CheckConstraint("typeof(updated_at) = 'integer'"),
        CheckConstraint("typeof(revision) = 'integer' AND revision >= 1"),
        CheckConstraint("deleted_at IS NULL OR typeof(deleted_at) = 'integer'"),
        CheckConstraint("updated_at >= created_at"),
        CheckConstraint(
            "deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= updated_at)"
        ),
        CheckConstraint("score IS NULL OR max_score IS NULL OR score <= max_score"),
        CheckConstraint(
            "(kind = 'PASS_FAIL' AND passed IS NOT NULL AND score IS NULL AND max_score IS NULL AND label IS NULL) OR (kind = 'NUMERIC' AND passed IS NULL AND score IS NOT NULL AND label IS NULL) OR (kind = 'TRADITIONAL' AND passed IS NULL AND score IS NULL AND max_score IS NULL AND label IS NOT NULL AND length(trim(label)) > 0)"
        ),
    )


Index(
    "enrollments_active_membership",
    EnrollmentRow.__table__.c.student_id,
    EnrollmentRow.__table__.c.offering_id,
    unique=True,
    sqlite_where=text("deleted_at IS NULL AND status = 'ACTIVE'"),
)
Index("enrollments_offering", EnrollmentRow.__table__.c.offering_id)
Index("student_works_assessment", StudentWorkRow.__table__.c.assessment_id)
Index("attempts_history", AttemptRow.__table__.c.student_work_id, AttemptRow.__table__.c.attempt_no)
Index("assessments_offering", AssessmentRow.__table__.c.offering_id)
Index("assessments_homework_definition", AssessmentRow.__table__.c.homework_definition_id)
Index("assessments_program_work", AssessmentRow.__table__.c.program_work_id)
Index("course_offerings_work_program", CourseOfferingRow.__table__.c.work_program_id)
Index(
    "assessments_program_work_active",
    AssessmentRow.__table__.c.offering_id,
    AssessmentRow.__table__.c.program_work_id,
    unique=True,
    sqlite_where=(
        AssessmentRow.__table__.c.deleted_at.is_(None)
        & AssessmentRow.__table__.c.program_work_id.is_not(None)
    ),
)
