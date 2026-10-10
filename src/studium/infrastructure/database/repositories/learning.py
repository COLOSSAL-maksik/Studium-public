"""Adapters using the same transaction and revision policy as the local core."""

from sqlalchemy import select

from studium.domain import entities as e
from studium.infrastructure.database.models import learning as m
from studium.infrastructure.database.repositories import SqlAlchemyMutableRepository, domain_value


class TopicRepository(SqlAlchemyMutableRepository[e.Topic]):
    entity_type, row_type = e.Topic, m.TopicRow

    def for_course(self, course_id):
        return sorted(
            self._matching(self.row_type.course_id, course_id),
            key=lambda x: (x.sort_order, x.title, x.id),
        )


class SkillRepository(SqlAlchemyMutableRepository[e.Skill]):
    entity_type, row_type = e.Skill, m.SkillRow

    def for_course(self, course_id):
        return sorted(
            self._matching(self.row_type.course_id, course_id),
            key=lambda x: (x.sort_order, x.title, x.id),
        )


class LessonRepository(SqlAlchemyMutableRepository[e.Lesson]):
    entity_type, row_type = e.Lesson, m.LessonRow

    def for_offering(self, offering_id):
        return sorted(
            self._matching(self.row_type.course_offering_id, offering_id),
            key=lambda x: (x.lesson_date, x.created_at, x.id),
            reverse=True,
        )


class AttendanceRepository(SqlAlchemyMutableRepository[e.Attendance]):
    entity_type, row_type = e.Attendance, m.AttendanceRow

    def for_lesson(self, lesson_id):
        return self._matching(self.row_type.lesson_id, lesson_id)


class AssessmentItemRepository(SqlAlchemyMutableRepository[e.AssessmentItem]):
    entity_type, row_type = e.AssessmentItem, m.AssessmentItemRow

    def for_assessment(self, assessment_id):
        return sorted(
            self._matching(self.row_type.assessment_id, assessment_id),
            key=lambda x: (x.sort_order, x.created_at, x.id),
        )


class LinkRepository(SqlAlchemyMutableRepository):
    owner_field: str
    target_field: str

    def for_owner(self, owner_id, *, include_deleted=False):
        query = (
            select(self.row_type)
            .where(getattr(self.row_type, self.owner_field) == owner_id.value)
            .order_by(self.row_type.created_at, self.row_type.id)
        )
        if not include_deleted:
            query = query.where(self.row_type.deleted_at.is_(None))
        with self._transaction() as session:
            return [domain_value(self.entity_type, row) for row in session.scalars(query)]

    def find_pair(self, owner_id, target_id):
        with self._transaction() as session:
            row = session.scalar(
                select(self.row_type).where(
                    getattr(self.row_type, self.owner_field) == owner_id.value,
                    getattr(self.row_type, self.target_field) == target_id.value,
                )
            )
            return domain_value(self.entity_type, row) if row else None


class TopicSkillRepository(LinkRepository):
    entity_type, row_type = e.TopicSkill, m.TopicSkillRow
    owner_field, target_field = "topic_id", "skill_id"


class LessonTopicRepository(LinkRepository):
    entity_type, row_type = e.LessonTopic, m.LessonTopicRow
    owner_field, target_field = "lesson_id", "topic_id"


class AssessmentTopicRepository(LinkRepository):
    entity_type, row_type = e.AssessmentTopic, m.AssessmentTopicRow
    owner_field, target_field = "assessment_id", "topic_id"


class AssessmentSkillRepository(LinkRepository):
    entity_type, row_type = e.AssessmentSkill, m.AssessmentSkillRow
    owner_field, target_field = "assessment_id", "skill_id"


class AssessmentItemTopicRepository(LinkRepository):
    entity_type, row_type = e.AssessmentItemTopic, m.AssessmentItemTopicRow
    owner_field, target_field = "assessment_item_id", "topic_id"


class AssessmentItemSkillRepository(LinkRepository):
    entity_type, row_type = e.AssessmentItemSkill, m.AssessmentItemSkillRow
    owner_field, target_field = "assessment_item_id", "skill_id"


ADAPTERS = {
    "topics": TopicRepository,
    "skills": SkillRepository,
    "lessons": LessonRepository,
    "attendance": AttendanceRepository,
    "items": AssessmentItemRepository,
    "topic_skills": TopicSkillRepository,
    "lesson_topics": LessonTopicRepository,
    "assessment_topics": AssessmentTopicRepository,
    "assessment_skills": AssessmentSkillRepository,
    "item_topics": AssessmentItemTopicRepository,
    "item_skills": AssessmentItemSkillRepository,
}
