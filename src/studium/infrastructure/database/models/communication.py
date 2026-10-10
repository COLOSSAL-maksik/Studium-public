"""Additive v4 communication mappings; migration snapshot owns production DDL."""

from sqlalchemy import CheckConstraint, Column, Index, Integer, Text, UniqueConstraint

from studium.infrastructure.database.models.base import Base
from studium.infrastructure.database.models.learning import order, record, reference


class QuestionCaseRow(Base):
    __table__ = record(
        "question_cases",
        reference("student_id", "students"),
        reference("course_offering_id", "course_offerings", nullable=True),
        Column("title", Text),
        Column("opened_at", Integer, nullable=False),
        Column("closed_at", Integer),
        CheckConstraint("title IS NULL OR length(trim(title)) > 0"),
        CheckConstraint("typeof(opened_at) = 'integer'"),
        CheckConstraint(
            "closed_at IS NULL OR (typeof(closed_at) = 'integer' AND closed_at >= opened_at)"
        ),
    )


class MessageRow(Base):
    __table__ = record(
        "messages",
        reference("question_case_id", "question_cases"),
        Column("author_role", Text, nullable=False),
        Column("channel", Text, nullable=False),
        Column("sent_at", Integer, nullable=False),
        Column("body", Text, nullable=False),
        Column("external_system", Text),
        Column("external_account_key", Text),
        Column("external_thread_id", Text),
        Column("external_message_id", Text),
        CheckConstraint("author_role IN ('STUDENT', 'TEACHER')"),
        CheckConstraint("channel IN ('MANUAL', 'EMAIL', 'TELEGRAM', 'OTHER')"),
        CheckConstraint("typeof(sent_at) = 'integer'"),
        CheckConstraint("length(trim(body, char(9) || char(10) || char(13) || ' ')) > 0"),
        CheckConstraint(
            "(external_system IS NULL AND external_account_key IS NULL AND external_thread_id IS NULL AND external_message_id IS NULL) OR (channel != 'MANUAL' AND external_system IS NOT NULL AND length(trim(external_system)) > 0 AND external_account_key IS NOT NULL AND length(trim(external_account_key)) > 0 AND external_thread_id IS NOT NULL AND length(trim(external_thread_id)) > 0 AND external_message_id IS NOT NULL AND length(trim(external_message_id)) > 0)"
        ),
        UniqueConstraint(
            "external_system", "external_account_key", "external_thread_id", "external_message_id"
        ),
    )


class MessageAttachmentRow(Base):
    __table__ = record(
        "message_attachments",
        reference("message_id", "messages"),
        reference("file_asset_id", "file_assets"),
        Column("caption", Text),
        *order(),
        UniqueConstraint("message_id", "file_asset_id"),
    )


class QuestionCaseAssessmentRow(Base):
    __table__ = record(
        "question_case_assessments",
        reference("question_case_id", "question_cases"),
        reference("assessment_id", "assessments"),
        UniqueConstraint("question_case_id", "assessment_id"),
    )


class QuestionCaseAttemptRow(Base):
    __table__ = record(
        "question_case_attempts",
        reference("question_case_id", "question_cases"),
        reference("attempt_id", "attempts"),
        UniqueConstraint("question_case_id", "attempt_id"),
    )


class QuestionCaseTopicRow(Base):
    __table__ = record(
        "question_case_topics",
        reference("question_case_id", "question_cases"),
        reference("topic_id", "topics"),
        UniqueConstraint("question_case_id", "topic_id"),
    )


class QuestionCaseSkillRow(Base):
    __table__ = record(
        "question_case_skills",
        reference("question_case_id", "question_cases"),
        reference("skill_id", "skills"),
        UniqueConstraint("question_case_id", "skill_id"),
    )


Index("question_cases_student", QuestionCaseRow.student_id, QuestionCaseRow.opened_at)
Index("question_cases_offering", QuestionCaseRow.course_offering_id)
Index(
    "messages_history",
    MessageRow.question_case_id,
    MessageRow.sent_at,
    MessageRow.created_at,
    MessageRow.id,
)
Index("message_attachments_asset", MessageAttachmentRow.file_asset_id)
Index("message_attachments_order", MessageAttachmentRow.message_id, MessageAttachmentRow.sort_order)
for cls, target in [
    (QuestionCaseAssessmentRow, "assessment_id"),
    (QuestionCaseAttemptRow, "attempt_id"),
    (QuestionCaseTopicRow, "topic_id"),
    (QuestionCaseSkillRow, "skill_id"),
]:
    Index(cls.__table__.name + "_target", getattr(cls, target))
