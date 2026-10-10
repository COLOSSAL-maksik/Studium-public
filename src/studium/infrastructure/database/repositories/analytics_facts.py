"""Immutable item facts and semantic-lock queries in the shared transaction."""

from sqlalchemy import select, text

from studium.domain.analytics_facts import AttemptItemResult
from studium.infrastructure.database.models.analytics_facts import AttemptItemResultRow
from studium.infrastructure.database.repositories import (
    SqlAlchemySoftDeleteRepository,
    domain_value,
)


class AttemptItemResultRepository(SqlAlchemySoftDeleteRepository[AttemptItemResult]):
    entity_type, row_type = AttemptItemResult, AttemptItemResultRow

    def insert(self, entity):
        with self._transaction() as session:
            self._insert(session, entity)

    def for_attempt(self, attempt_id, *, include_deleted=False):
        query = (
            select(self.row_type)
            .where(self.row_type.attempt_id == attempt_id.value)
            .order_by(self.row_type.created_at, self.row_type.id)
        )
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]

    def for_attempts(self, ids):
        return self._many(self.row_type.attempt_id, ids)


class SemanticLockRepository(SqlAlchemySoftDeleteRepository):
    def assessment_locked(self, assessment_id):
        with self._transaction() as session:
            return bool(
                session.scalar(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM student_works w JOIN attempts a ON a.student_work_id=w.id WHERE w.assessment_id=:id)"
                    ),
                    {"id": assessment_id.value},
                )
            )

    def topic_locked(self, topic_id):
        # Inline expressions also support test fixtures deliberately populated at v2-v4.
        query = """
        WITH RECURSIVE locked_assessments(id) AS (
            SELECT DISTINCT w.assessment_id FROM student_works w JOIN attempts a ON a.student_work_id=w.id
        ), locked_topics(id) AS (
            SELECT t.topic_id FROM assessment_topics t JOIN locked_assessments a ON a.id=t.assessment_id
            UNION
            SELECT t.topic_id FROM assessment_item_topics t JOIN assessment_items i ON i.id=t.assessment_item_id
                JOIN locked_assessments a ON a.id=i.assessment_id
            UNION
            SELECT t.parent_topic_id FROM topics t JOIN locked_topics l ON l.id=t.id WHERE t.parent_topic_id IS NOT NULL
        )
        SELECT EXISTS(SELECT 1 FROM locked_topics WHERE id=:id)
        """
        with self._transaction() as session:
            return bool(session.scalar(text(query), {"id": topic_id.value}))

    def skill_locked(self, skill_id):
        query = """
        WITH locked_assessments(id) AS (
            SELECT DISTINCT w.assessment_id FROM student_works w JOIN attempts a ON a.student_work_id=w.id
        ), locked_skills(id) AS (
            SELECT s.skill_id FROM assessment_skills s JOIN locked_assessments a ON a.id=s.assessment_id
            UNION
            SELECT s.skill_id FROM assessment_item_skills s JOIN assessment_items i ON i.id=s.assessment_item_id
                JOIN locked_assessments a ON a.id=i.assessment_id
        )
        SELECT EXISTS(SELECT 1 FROM locked_skills WHERE id=:id)
        """
        with self._transaction() as session:
            return bool(session.scalar(text(query), {"id": skill_id.value}))


ADAPTERS = {
    "item_results": AttemptItemResultRepository,
    "content_locks": SemanticLockRepository,
}
