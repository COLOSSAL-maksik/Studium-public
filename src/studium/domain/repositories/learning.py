"""Ports for the course content catalogue and recorded lesson facts."""

from typing import Protocol

from studium.domain.entities import AssessmentItem, Attendance, Lesson, Skill, StudiumEntity, Topic
from studium.domain.repositories import MutableRepository
from studium.domain.value_objects import EntityId


class TopicRepository(MutableRepository[Topic], Protocol):
    def for_course(self, course_id: EntityId) -> list[Topic]: ...


class SkillRepository(MutableRepository[Skill], Protocol):
    def for_course(self, course_id: EntityId) -> list[Skill]: ...


class LessonRepository(MutableRepository[Lesson], Protocol):
    def for_offering(self, offering_id: EntityId) -> list[Lesson]: ...


class AttendanceRepository(MutableRepository[Attendance], Protocol):
    def for_lesson(self, lesson_id: EntityId) -> list[Attendance]: ...


class AssessmentItemRepository(MutableRepository[AssessmentItem], Protocol):
    def for_assessment(self, assessment_id: EntityId) -> list[AssessmentItem]: ...


class LearningLinkRepository[T: StudiumEntity](MutableRepository[T], Protocol):
    def for_owner(self, owner_id: EntityId, *, include_deleted: bool = False) -> list[T]: ...
    def find_pair(self, owner_id: EntityId, target_id: EntityId) -> T | None: ...
