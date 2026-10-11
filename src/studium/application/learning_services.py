"""Learning use cases composed into StudiumService, independent of UI and ORM."""

from collections import Counter
from dataclasses import dataclass, replace

from studium.application.errors import ApplicationError
from studium.domain import entities as e
from studium.domain.enums import AttendanceStatus, LessonType
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId, LocalDate


@dataclass(frozen=True)
class TopicNode:
    topic: e.Topic
    children: tuple["TopicNode", ...]


@dataclass(frozen=True)
class AttendanceEntry:
    student: e.Student
    enrollment: e.Enrollment
    attendance: e.Attendance | None


@dataclass(frozen=True)
class LessonListEntry:
    lesson: e.Lesson
    topics: tuple[e.Topic, ...]
    attendance_counts: tuple[tuple[AttendanceStatus, int], ...]


# Typed entity and explicit relation endpoints; no polymorphic persistence.
LINKS = {
    "topic_skills": (e.TopicSkill, "topics", "skills", "topic_id", "skill_id"),
    "lesson_topics": (e.LessonTopic, "lessons", "topics", "lesson_id", "topic_id"),
    "assessment_topics": (e.AssessmentTopic, "assessments", "topics", "assessment_id", "topic_id"),
    "assessment_skills": (e.AssessmentSkill, "assessments", "skills", "assessment_id", "skill_id"),
    "item_topics": (e.AssessmentItemTopic, "items", "topics", "assessment_item_id", "topic_id"),
    "item_skills": (e.AssessmentItemSkill, "items", "skills", "assessment_item_id", "skill_id"),
}


class LearningService:
    """Uses StudiumService's repositories, transaction, clock and context helpers."""

    @staticmethod
    def _fixed(original, values, *fields):
        if any(field in values and values[field] != getattr(original, field) for field in fields):
            raise ApplicationError("learning_context_immutable")

    def assessment_content_locked(self, assessment_id):
        with self._transaction() as r:
            self._require(r.assessments, assessment_id, historical=True)
            return r.content_locks.assessment_locked(assessment_id)

    @staticmethod
    def _assert_assessment_unlocked(r, assessment_id):
        if r.content_locks.assessment_locked(assessment_id):
            raise ApplicationError("content_semantic_locked")

    def _assert_assessment_content_edit(self, r, original, values):
        fields = (
            "offering_id",
            "type",
            "number",
            "title",
            "description",
            "max_score",
            "homework_definition_id",
        )
        if any(field in values and values[field] != getattr(original, field) for field in fields):
            self._assert_assessment_unlocked(r, original.id)

    @staticmethod
    def _assert_taxonomy_edit(r, kind, original, values):
        fields = (
            ("course_id", "title", "description", "parent_topic_id")
            if kind == "topics"
            else ("course_id", "title", "description")
        )
        changed = any(
            field in values and values[field] != getattr(original, field) for field in fields
        )
        locked = r.content_locks.topic_locked if kind == "topics" else r.content_locks.skill_locked
        if changed and locked(original.id):
            raise ApplicationError("content_semantic_locked")

    def _assert_link_unlocked(self, r, kind, owner_id):
        if kind in {"assessment_topics", "assessment_skills"}:
            self._assert_assessment_unlocked(r, owner_id)
        elif kind in {"item_topics", "item_skills"}:
            item = self._require(r.items, owner_id)
            self._assert_assessment_unlocked(r, item.assessment_id)

    def list_course_topics(self, course_id):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            return r.topics.for_course(course_id)

    def topic_hierarchy(self, course_id):
        topics = self.list_course_topics(course_id)
        children = {}
        for topic in topics:
            children.setdefault(topic.parent_topic_id, []).append(topic)

        def build(topic, path):
            if topic.id in path:
                raise ApplicationError("topic_cycle")
            return TopicNode(
                topic, tuple(build(c, path | {topic.id}) for c in children.get(topic.id, []))
            )

        return tuple(build(t, set()) for t in children.get(None, []))

    def _topic_parent(self, r, course_id, parent_id, id=None):
        seen = set()
        while parent_id is not None:
            if parent_id == id or parent_id in seen:
                raise ApplicationError("topic_cycle")
            seen.add(parent_id)
            parent = self._require(r.topics, parent_id)
            if parent.course_id != course_id:
                raise ApplicationError("learning_course_mismatch")
            parent_id = parent.parent_topic_id

    def create_topic(
        self,
        course_id: EntityId,
        title: str,
        *,
        parent_topic_id=None,
        description="",
        sort_order=0,
        skill_ids=(),
    ):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            self._topic_parent(r, course_id, parent_topic_id)
            value = e.Topic(
                metadata=self._meta(),
                course_id=course_id,
                title=title.strip(),
                parent_topic_id=parent_topic_id,
                description=description,
                sort_order=sort_order,
            )
            r.topics.insert(value)
            self._set_links(r, "topic_skills", value.id, skill_ids)
            return value

    def update_topic(self, original, *, skill_ids=None, expected_skills=None, **values):
        self._fixed(original, values, "course_id")
        with self._transaction() as r:
            self._require(r.topics, original.id)
            self._assert_taxonomy_edit(r, "topics", original, values)
            self._require(r.courses, original.course_id)
            self._topic_parent(
                r,
                original.course_id,
                values.get("parent_topic_id", original.parent_topic_id),
                original.id,
            )
            updated = self._update(r.topics, original, **values)
            if skill_ids is not None:
                self._set_links(r, "topic_skills", original.id, skill_ids, expected=expected_skills)
            return updated

    def archive_topic(self, original):
        with self._transaction() as r:
            topics = r.topics.for_course(original.course_id)
            pending = [original]
            subtree = []
            while pending:
                value = pending.pop()
                subtree.append(value)
                pending.extend(t for t in topics if t.parent_topic_id == value.id)
            self._assert_frozen_taxonomy_archive(r, "topic", [v.id for v in subtree])
            for value in reversed(subtree):
                if r.content_locks.topic_locked(value.id):
                    raise ApplicationError("content_semantic_locked")
                r.topics.soft_delete(value.id, expected_revision=value.revision, at=self._clock())

    def list_course_skills(self, course_id):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            return r.skills.for_course(course_id)

    def create_skill(self, course_id, title, *, description="", sort_order=0):
        with self._transaction() as r:
            self._require(r.courses, course_id)
            value = e.Skill(
                metadata=self._meta(),
                course_id=course_id,
                title=title.strip(),
                description=description,
                sort_order=sort_order,
            )
            r.skills.insert(value)
            return value

    def update_skill(self, original, **values):
        self._fixed(original, values, "course_id")
        with self._transaction() as r:
            self._require(r.skills, original.id)
            self._assert_taxonomy_edit(r, "skills", original, values)
            self._require(r.courses, original.course_id)
            return self._update(r.skills, original, **values)

    def archive_skill(self, original):
        with self._transaction() as r:
            self._assert_frozen_taxonomy_archive(r, "skill", [original.id])
            if r.content_locks.skill_locked(original.id):
                raise ApplicationError("content_semantic_locked")
            r.skills.soft_delete(original.id, expected_revision=original.revision, at=self._clock())

    def list_lessons(self, offering_id):
        with self._transaction() as r:
            self._context(r, offering_id)
            return r.lessons.for_offering(offering_id)

    def create_lesson(
        self,
        course_offering_id,
        lesson_date: LocalDate,
        *,
        title="",
        notes="",
        topic_ids=(),
        type=LessonType.SEMINAR,
        planned_date=None,
        planned_week=None,
        module_id=None,
    ):
        with self._transaction() as r:
            self._context(r, course_offering_id)
            value = e.Lesson(
                metadata=self._meta(),
                course_offering_id=course_offering_id,
                lesson_date=lesson_date,
                title=title.strip(),
                notes=notes,
                type=type,
                planned_date=planned_date or lesson_date,
                planned_week=planned_week,
                module_id=module_id,
            )
            r.lessons.insert(value)
            self._set_links(r, "lesson_topics", value.id, topic_ids)
            return value

    def update_lesson(self, original, *, topic_ids=None, expected_topics=None, **values):
        self._fixed(original, values, "course_offering_id")
        with self._transaction() as r:
            self._require(r.lessons, original.id)
            self._context(r, original.course_offering_id)
            value = self._update(r.lessons, original, **values)
            if topic_ids is not None:
                self._set_links(r, "lesson_topics", value.id, topic_ids, expected=expected_topics)
            return value

    def archive_lesson(self, original):
        self._r.lessons.soft_delete(
            original.id, expected_revision=original.revision, at=self._clock()
        )

    def _learning_owner(self, r, kind, id):
        value = self._require(getattr(r, kind), id)
        if kind in {"topics", "skills"}:
            self._require(r.courses, value.course_id)
            return value, value.course_id
        if kind == "items":
            _, course_id = self._learning_owner(r, "assessments", value.assessment_id)
            return value, course_id
        offering_id = value.course_offering_id if kind == "lessons" else value.offering_id
        return value, self._context(r, offering_id).course.id

    def learning_links(self, kind, owner_id, *, include_deleted=False):
        with self._transaction() as r:
            self._learning_owner(r, LINKS[kind][1], owner_id)
            return tuple(getattr(r, kind).for_owner(owner_id, include_deleted=include_deleted))

    def learning_targets(self, kind, owner_id):
        """Includes archived linked catalogue entries to retain historical meaning in UI."""
        with self._transaction() as r:
            _, owner_kind, target_kind, _, target_field = LINKS[kind]
            self._learning_owner(r, owner_kind, owner_id)
            return tuple(
                self._require(getattr(r, target_kind), getattr(link, target_field), historical=True)
                for link in getattr(r, kind).for_owner(owner_id)
            )

    def _attach(self, r, kind, owner_id, target_id):
        cls, owner_kind, target_kind, owner_field, target_field = LINKS[kind]
        _, course_id = self._learning_owner(r, owner_kind, owner_id)
        target = self._require(getattr(r, target_kind), target_id)
        if target.course_id != course_id:
            raise ApplicationError("learning_course_mismatch")
        repository = getattr(r, kind)
        existing = repository.find_pair(owner_id, target_id)
        if existing:
            if existing.deleted_at:
                self._assert_link_unlocked(r, kind, owner_id)
                value = replace(
                    existing,
                    metadata=replace(existing.metadata.touch(self._clock()), deleted_at=None),
                )
                repository.update(value, expected_revision=existing.revision)
                return value
            return existing
        self._assert_link_unlocked(r, kind, owner_id)
        value = cls(metadata=self._meta(), **{owner_field: owner_id, target_field: target_id})
        repository.insert(value)
        return value

    def attach_learning_link(self, kind, owner_id, target_id):
        with self._transaction() as r:
            return self._attach(r, kind, owner_id, target_id)

    def detach_learning_link(self, kind, owner_id, target_id):
        with self._transaction() as r:
            self._learning_owner(r, LINKS[kind][1], owner_id)
            existing = getattr(r, kind).find_pair(owner_id, target_id)
            if existing and existing.deleted_at is None:
                self._assert_link_unlocked(r, kind, owner_id)
                getattr(r, kind).soft_delete(
                    existing.id, expected_revision=existing.revision, at=self._clock()
                )

    def _set_links(self, r, kind, owner_id, target_ids, *, expected=None):
        self._learning_owner(r, LINKS[kind][1], owner_id)
        selected = set(target_ids)
        repository = getattr(r, kind)
        current = {getattr(link, LINKS[kind][4]): link for link in repository.for_owner(owner_id)}
        if expected is not None and {link.id: link for link in expected} != {
            link.id: link for link in current.values()
        }:
            raise RepositoryError(
                RepositoryFailure.REVISION_CONFLICT, "Learning links changed since read"
            )
        if selected != current.keys():
            self._assert_link_unlocked(r, kind, owner_id)
        for target_id in selected - current.keys():
            self._attach(r, kind, owner_id, target_id)
        for target_id in current.keys() - selected:
            link = current[target_id]
            repository.soft_delete(link.id, expected_revision=link.revision, at=self._clock())

    def set_learning_links(self, kind, owner_id, target_ids, *, expected=None):
        with self._transaction() as r:
            self._set_links(r, kind, owner_id, target_ids, expected=expected)

    def set_assessment_content(
        self,
        assessment_id,
        topic_ids,
        skill_ids,
        *,
        item=False,
        expected_topics=None,
        expected_skills=None,
    ):
        with self._transaction() as r:
            self._set_links(
                r,
                "item_topics" if item else "assessment_topics",
                assessment_id,
                topic_ids,
                expected=expected_topics,
            )
            self._set_links(
                r,
                "item_skills" if item else "assessment_skills",
                assessment_id,
                skill_ids,
                expected=expected_skills,
            )

    def attach_topic_skill(self, topic_id, skill_id):
        return self.attach_learning_link("topic_skills", topic_id, skill_id)

    def detach_topic_skill(self, topic_id, skill_id):
        self.detach_learning_link("topic_skills", topic_id, skill_id)

    def attach_lesson_topic(self, lesson_id, topic_id):
        return self.attach_learning_link("lesson_topics", lesson_id, topic_id)

    def detach_lesson_topic(self, lesson_id, topic_id):
        self.detach_learning_link("lesson_topics", lesson_id, topic_id)

    def attach_assessment_topic(self, assessment_id, topic_id):
        return self.attach_learning_link("assessment_topics", assessment_id, topic_id)

    def detach_assessment_topic(self, assessment_id, topic_id):
        self.detach_learning_link("assessment_topics", assessment_id, topic_id)

    def attach_assessment_skill(self, assessment_id, skill_id):
        return self.attach_learning_link("assessment_skills", assessment_id, skill_id)

    def detach_assessment_skill(self, assessment_id, skill_id):
        self.detach_learning_link("assessment_skills", assessment_id, skill_id)

    def attach_item_topic(self, item_id, topic_id):
        return self.attach_learning_link("item_topics", item_id, topic_id)

    def detach_item_topic(self, item_id, topic_id):
        self.detach_learning_link("item_topics", item_id, topic_id)

    def attach_item_skill(self, item_id, skill_id):
        return self.attach_learning_link("item_skills", item_id, skill_id)

    def detach_item_skill(self, item_id, skill_id):
        self.detach_learning_link("item_skills", item_id, skill_id)

    def list_assessment_items(self, assessment_id, *, historical=False):
        """Historical read retains archived items and academic parents for Attempt history."""
        with self._transaction() as r:
            if historical:
                assessment = self._require(r.assessments, assessment_id, historical=True)
                self._context(r, assessment.offering_id, historical=True)
                return sorted(
                    (
                        item
                        for item in r.items.list(include_deleted=True)
                        if item.assessment_id == assessment_id
                    ),
                    key=lambda item: (item.sort_order, item.created_at, item.id),
                )
            self._learning_owner(r, "assessments", assessment_id)
            return r.items.for_assessment(assessment_id)

    def create_assessment_item(
        self, assessment_id, title, *, description="", max_score=None, sort_order=0
    ):
        with self._transaction() as r:
            self._learning_owner(r, "assessments", assessment_id)
            self._assert_assessment_unlocked(r, assessment_id)
            value = e.AssessmentItem(
                metadata=self._meta(),
                assessment_id=assessment_id,
                title=title.strip(),
                description=description,
                max_score=max_score,
                sort_order=sort_order,
            )
            r.items.insert(value)
            return value

    def update_assessment_item(self, original, **values):
        self._fixed(original, values, "assessment_id")
        with self._transaction() as r:
            self._learning_owner(r, "items", original.id)
            fields = ("title", "description", "max_score")
            if any(
                field in values and values[field] != getattr(original, field) for field in fields
            ):
                self._assert_assessment_unlocked(r, original.assessment_id)
            return self._update(r.items, original, **values)

    def archive_assessment_item(self, original):
        with self._transaction() as r:
            self._assert_assessment_unlocked(r, original.assessment_id)
            r.items.soft_delete(original.id, expected_revision=original.revision, at=self._clock())

    def reorder_assessment_items(self, assessment_id, items):
        """A complete ordered snapshot; stale revisions roll back the whole reorder."""
        with self._transaction() as r:
            self._learning_owner(r, "assessments", assessment_id)
            current = r.items.for_assessment(assessment_id)
            if len({item.id for item in items}) != len(current) or {item.id for item in items} != {
                item.id for item in current
            }:
                raise ApplicationError("item_order_incomplete")
            for order, original in enumerate(items):
                self._fixed(original, {"assessment_id": assessment_id}, "assessment_id")
                self._update(r.items, original, sort_order=order)

    def mark_attendance(self, lesson_id, enrollment_id, status, *, comment="", original=None):
        with self._transaction() as r:
            return self._mark_attendance(r, lesson_id, enrollment_id, status, comment, original)

    def _mark_attendance(self, r, lesson_id, enrollment_id, status, comment, original):
        lesson, _ = self._learning_owner(r, "lessons", lesson_id)
        if lesson.cancelled:
            raise ApplicationError("lesson_cancelled")
        enrollment = self._require(r.enrollments, enrollment_id)
        self._require(r.students, enrollment.student_id)
        if enrollment.offering_id != lesson.course_offering_id:
            raise ApplicationError("attendance_context_mismatch")
        existing = next(
            (a for a in r.attendance.for_lesson(lesson_id) if a.enrollment_id == enrollment_id),
            None,
        )
        if existing:
            if original is None:
                raise ApplicationError("attendance_snapshot_required")
            if original.id != existing.id:
                raise ApplicationError("attendance_context_mismatch")
            return self._update(r.attendance, original, status=status, comment=comment)
        if original is not None:
            raise RepositoryError(RepositoryFailure.REVISION_CONFLICT, "Attendance changed")
        value = e.Attendance(
            metadata=self._meta(),
            lesson_id=lesson_id,
            enrollment_id=enrollment_id,
            status=status,
            comment=comment,
        )
        r.attendance.insert(value)
        return value

    def mark_attendance_many(self, lesson_id, entries, status):
        """Explicitly selected participation snapshots, one atomic batch."""
        with self._transaction() as r:
            seen = set()
            result = []
            for entry in entries:
                if entry.student.id in seen:
                    raise ApplicationError("attendance_context_mismatch")
                seen.add(entry.student.id)
                result.append(
                    self._mark_attendance(
                        r,
                        lesson_id,
                        entry.enrollment.id,
                        status,
                        entry.attendance.comment if entry.attendance else "",
                        entry.attendance,
                    )
                )
            return tuple(result)

    def lesson_list(self, offering_id):
        """Bulk list context and raw attendance counts, no query per lesson."""
        with self._transaction() as r:
            self._context(r, offering_id)
            lessons = r.lessons.for_offering(offering_id)
            topics = {t.id: t for t in r.topics.list(include_deleted=True)}
            links = r.lesson_topics.list()
            attendance = r.attendance.list()
            return tuple(
                LessonListEntry(
                    lesson,
                    tuple(topics[link.topic_id] for link in links if link.lesson_id == lesson.id),
                    tuple(
                        Counter(a.status for a in attendance if a.lesson_id == lesson.id).items()
                    ),
                )
                for lesson in lessons
            )

    def list_lesson_attendance(self, lesson_id):
        with self._transaction() as r:
            lesson, _ = self._learning_owner(r, "lessons", lesson_id)
            facts = {a.enrollment_id: a for a in r.attendance.for_lesson(lesson_id)}
            enrollments = r.enrollments.for_offering(lesson.course_offering_id)
            by_id = {en.id: en for en in enrollments}
            # Preserve previously marked, now archived enrollments and students.
            historical = {en.id: en for en in r.enrollments.list(include_deleted=True)}
            students = {s.id: s for s in r.students.list(include_deleted=True)}
            for id in facts:
                by_id[id] = historical[id]
            result = [
                AttendanceEntry(students[en.student_id], en, facts.get(en.id))
                for en in by_id.values()
            ]
            return tuple(
                sorted(
                    result,
                    key=lambda row: (
                        row.student.full_name.casefold(),
                        row.enrollment.enrolled_at,
                        row.enrollment.id,
                    ),
                )
            )
