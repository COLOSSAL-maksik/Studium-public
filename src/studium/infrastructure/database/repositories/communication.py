"""Communication adapters reuse local CAS, errors and transaction policy."""

from sqlalchemy import select

from studium.domain import communication as e
from studium.infrastructure.database.models import communication as m
from studium.infrastructure.database.repositories import (
    SqlAlchemyMutableRepository,
    SqlAlchemySoftDeleteRepository,
    domain_value,
)
from studium.infrastructure.database.repositories.learning import LinkRepository


class QuestionCaseRepository(SqlAlchemyMutableRepository):
    entity_type, row_type = e.QuestionCase, m.QuestionCaseRow


class MessageRepository(SqlAlchemySoftDeleteRepository):
    entity_type, row_type = e.Message, m.MessageRow

    def insert(self, entity):
        with self._transaction() as session:
            self._insert(session, entity)

    def for_case(self, case_id, *, include_deleted=False):
        query = (
            select(self.row_type)
            .where(self.row_type.question_case_id == case_id.value)
            .order_by(self.row_type.sent_at, self.row_type.created_at, self.row_type.id)
        )
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]

    def find_external(self, key):
        query = select(self.row_type).where(
            *(
                getattr(self.row_type, field) == value
                for field, value in zip(
                    (
                        "external_system",
                        "external_account_key",
                        "external_thread_id",
                        "external_message_id",
                    ),
                    key,
                    strict=True,
                )
            )
        )
        with self._transaction() as session:
            row = session.scalar(query)
            return domain_value(self.entity_type, row) if row else None


class MessageAttachmentRepository(LinkRepository):
    entity_type, row_type = e.MessageAttachment, m.MessageAttachmentRow
    owner_field, target_field = "message_id", "file_asset_id"

    def for_asset(self, asset_id):
        return self._matching(self.row_type.file_asset_id, asset_id)


class QuestionCaseAssessmentRepository(LinkRepository):
    entity_type, row_type = e.QuestionCaseAssessment, m.QuestionCaseAssessmentRow
    owner_field, target_field = "question_case_id", "assessment_id"


class QuestionCaseAttemptRepository(LinkRepository):
    entity_type, row_type = e.QuestionCaseAttempt, m.QuestionCaseAttemptRow
    owner_field, target_field = "question_case_id", "attempt_id"


class QuestionCaseTopicRepository(LinkRepository):
    entity_type, row_type = e.QuestionCaseTopic, m.QuestionCaseTopicRow
    owner_field, target_field = "question_case_id", "topic_id"


class QuestionCaseSkillRepository(LinkRepository):
    entity_type, row_type = e.QuestionCaseSkill, m.QuestionCaseSkillRow
    owner_field, target_field = "question_case_id", "skill_id"


ADAPTERS = {
    "question_cases": QuestionCaseRepository,
    "messages": MessageRepository,
    "message_attachments": MessageAttachmentRepository,
    "question_case_assessments": QuestionCaseAssessmentRepository,
    "question_case_attempts": QuestionCaseAttemptRepository,
    "question_case_topics": QuestionCaseTopicRepository,
    "question_case_skills": QuestionCaseSkillRepository,
}
