"""Synthetic local learning workflows and persistence risks."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from studium.application.services import ApplicationError
from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttendanceStatus
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId, EntityMetadata, LocalDate, UtcInstant


@pytest.fixture
def learning(tmp_path):
    runtime = create_runtime(tmp_path)
    s = runtime.service
    term = s.create_term("Synthetic term", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course = s.create_course("Synthetic course")
    group = s.create_group("TEST-01")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic Student")
    enrollment = s.list_students_for_offering(offering.id)[0].enrollment
    assessment = s.create_assessment(offering.id, "Synthetic Assessment", AssessmentType.HOMEWORK)
    topic = s.create_topic(course.id, "Synthetic Topic")
    skill = s.create_skill(course.id, "Synthetic Skill")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 9, 29), title="Synthetic Lesson")
    item = s.create_assessment_item(assessment.id, "Synthetic Item")
    yield SimpleNamespace(
        runtime=runtime,
        s=s,
        term=term,
        course=course,
        group=group,
        offering=offering,
        student=student,
        enrollment=enrollment,
        assessment=assessment,
        topic=topic,
        skill=skill,
        lesson=lesson,
        item=item,
    )
    runtime.close()


def test_topic_hierarchy_order_update_and_cycle(learning):
    f, s = learning, learning.s
    child = s.create_topic(f.course.id, "Child", parent_topic_id=f.topic.id, sort_order=2)
    first = s.create_topic(f.course.id, "First", parent_topic_id=f.topic.id, sort_order=1)
    tree = s.topic_hierarchy(f.course.id)
    assert tree[0].topic == f.topic
    assert [node.topic for node in tree[0].children] == [first, child]
    with pytest.raises(ApplicationError, match="topic_cycle"):
        s.update_topic(f.topic, parent_topic_id=child.id)
    assert s.topic_hierarchy(f.course.id) == tree
    edited = s.update_topic(child, title="Renamed", parent_topic_id=None)
    assert edited.revision == child.revision + 1
    with pytest.raises(RepositoryError) as failure:
        s.update_topic(child, title="Stale")
    assert failure.value.failure == RepositoryFailure.REVISION_CONFLICT


def test_skill_update_and_catalogue_shared_by_groups(learning):
    f = learning
    edited = f.s.update_skill(f.skill, description="Synthetic description", sort_order=3)
    group2 = f.s.create_group("TEST-02")
    other = f.s.create_offering(f.term.id, f.course.id, group2.id)
    lesson2 = f.s.create_lesson(other.id, LocalDate(2026, 9, 30), topic_ids=[f.topic.id])
    assert f.s.list_course_skills(f.course.id) == [edited]
    assert f.s.learning_targets("lesson_topics", lesson2.id) == (f.topic,)


@pytest.mark.parametrize(
    "kind,owner,target",
    [
        ("topic_skills", "topic", "skill"),
        ("lesson_topics", "lesson", "topic"),
        ("assessment_topics", "assessment", "topic"),
        ("assessment_skills", "assessment", "skill"),
        ("item_topics", "item", "topic"),
        ("item_skills", "item", "skill"),
    ],
)
def test_normalized_link_idempotency_detach_restore_and_unique(learning, kind, owner, target):
    f = learning
    owner_id, target_id = getattr(f, owner).id, getattr(f, target).id
    first = f.s.attach_learning_link(kind, owner_id, target_id)
    assert f.s.attach_learning_link(kind, owner_id, target_id) == first
    repository = getattr(f.s._r, kind)
    with pytest.raises(RepositoryError) as error:
        repository.insert(replace(first, metadata=EntityMetadata.create(UtcInstant.now())))
    assert error.value.failure == RepositoryFailure.DUPLICATE
    f.s.detach_learning_link(kind, owner_id, target_id)
    assert f.s.learning_links(kind, owner_id) == ()
    hidden = f.s.learning_links(kind, owner_id, include_deleted=True)[0]
    assert hidden.id == first.id and hidden.deleted_at is not None
    restored = f.s.attach_learning_link(kind, owner_id, target_id)
    assert restored.id == first.id and restored.revision == 3
    assert f.s.learning_targets(kind, owner_id) == (getattr(f, target),)


@pytest.mark.parametrize(
    "kind,owner,target",
    [
        ("topic_skills", "topic", "skill"),
        ("lesson_topics", "lesson", "topic"),
        ("assessment_topics", "assessment", "topic"),
        ("assessment_skills", "assessment", "skill"),
        ("item_topics", "item", "topic"),
        ("item_skills", "item", "skill"),
    ],
)
def test_cross_course_links_rejected_in_service_and_database(learning, kind, owner, target):
    from studium.application.learning_services import LINKS

    f = learning
    course2 = f.s.create_course("Other synthetic course")
    foreign = (f.s.create_topic if target == "topic" else f.s.create_skill)(course2.id, "Foreign")
    owner_id = getattr(f, owner).id
    with pytest.raises(ApplicationError, match="learning_course_mismatch"):
        f.s.attach_learning_link(kind, owner_id, foreign.id)
    cls, _, _, owner_field, target_field = LINKS[kind]
    with pytest.raises(RepositoryError) as error:
        getattr(f.s._r, kind).insert(
            cls(
                metadata=EntityMetadata.create(UtcInstant.now()),
                **{owner_field: owner_id, target_field: foreign.id},
            )
        )
    assert error.value.failure == RepositoryFailure.INVALID_REFERENCE
    assert f.s.learning_links(kind, owner_id) == ()


def test_lesson_atomic_create_edit_and_detach(learning):
    f = learning
    before = f.s.list_lessons(f.offering.id)
    with pytest.raises(RepositoryError):
        f.s.create_lesson(
            f.offering.id, LocalDate(2026, 10, 1), topic_ids=[f.topic.id, EntityId.generate()]
        )
    assert f.s.list_lessons(f.offering.id) == before
    assert f.lesson.course_offering_id == f.offering.id
    value = f.s.update_lesson(
        f.lesson, title="Edited", notes="Synthetic notes", topic_ids=[f.topic.id]
    )
    assert f.s.learning_targets("lesson_topics", value.id) == (f.topic,)
    with pytest.raises(RepositoryError):
        f.s.update_lesson(value, notes="Must roll back", topic_ids=[EntityId.generate()])
    assert f.s.list_lessons(f.offering.id)[0] == value
    f.s.detach_lesson_topic(value.id, f.topic.id)
    assert f.s.learning_targets("lesson_topics", value.id) == ()


@pytest.mark.parametrize("status", list(AttendanceStatus))
def test_attendance_mark_update_stale_and_history_after_withdrawal(learning, status):
    f = learning
    row = f.s.list_lesson_attendance(f.lesson.id)[0]
    assert row.attendance is None
    first = f.s.mark_attendance(f.lesson.id, f.enrollment.id, status, comment="Synthetic")
    edited = f.s.mark_attendance(
        f.lesson.id, f.enrollment.id, AttendanceStatus.EXCUSED, comment="Edited", original=first
    )
    with pytest.raises(RepositoryError) as error:
        f.s.mark_attendance(f.lesson.id, f.enrollment.id, AttendanceStatus.ABSENT, original=first)
    assert error.value.failure == RepositoryFailure.REVISION_CONFLICT
    f.s.withdraw_student(f.enrollment)
    assert f.s.list_lesson_attendance(f.lesson.id)[0].attendance == edited
    assert f.s.list_lesson_attendance(f.lesson.id)[0].student.id == f.student.id


def test_attendance_rejects_other_offering_and_duplicate_student_membership(learning):
    f = learning
    group2 = f.s.create_group("TEST-02")
    other = f.s.create_offering(f.term.id, f.course.id, group2.id)
    foreign = f.s.enroll_student(other.id, f.student.id)
    with pytest.raises(ApplicationError, match="attendance_context_mismatch"):
        f.s.mark_attendance(f.lesson.id, foreign.id, AttendanceStatus.PRESENT)
    f.s.mark_attendance(f.lesson.id, f.enrollment.id, AttendanceStatus.PRESENT)
    f.s.withdraw_student(f.enrollment)
    repeated = f.s.enroll_student(f.offering.id, f.student.id)
    with pytest.raises(RepositoryError) as error:
        f.s.mark_attendance(f.lesson.id, repeated.id, AttendanceStatus.PRESENT)
    assert error.value.failure == RepositoryFailure.DUPLICATE


def test_assessment_item_crud_order_and_stale_atomic_rollback(learning):
    f = learning
    second = f.s.create_assessment_item(f.assessment.id, "Second", max_score=10, sort_order=1)
    f.s.reorder_assessment_items(f.assessment.id, [second, f.item])
    items = f.s.list_assessment_items(f.assessment.id)
    assert [i.id for i in items] == [second.id, f.item.id]
    assert [i.sort_order for i in items] == [0, 1]
    with pytest.raises(RepositoryError):
        f.s.reorder_assessment_items(f.assessment.id, [f.item, items[0]])
    assert f.s.list_assessment_items(f.assessment.id) == items
    with pytest.raises(ApplicationError, match="item_order_incomplete"):
        f.s.reorder_assessment_items(f.assessment.id, [items[0]])
    changed = f.s.update_assessment_item(items[0], title="Edited", description="Synthetic")
    f.s.attach_item_topic(changed.id, f.topic.id)
    f.s.archive_assessment_item(changed)
    assert [i.id for i in f.s.list_assessment_items(f.assessment.id)] == [f.item.id]
    assert f.s._r.item_topics.for_owner(changed.id)[0].topic_id == f.topic.id


def test_content_replacement_is_atomic_across_topics_and_skills(learning):
    f = learning
    f.s.set_assessment_content(f.assessment.id, [f.topic.id], [f.skill.id])
    with pytest.raises(RepositoryError):
        f.s.set_assessment_content(f.assessment.id, [], [EntityId.generate()])
    assert f.s.learning_targets("assessment_topics", f.assessment.id) == (f.topic,)
    assert f.s.learning_targets("assessment_skills", f.assessment.id) == (f.skill,)


def test_archive_subtree_retains_factual_links_and_reopen(learning, tmp_path):
    f = learning
    child = f.s.create_topic(f.course.id, "Child", parent_topic_id=f.topic.id)
    f.s.attach_lesson_topic(f.lesson.id, child.id)
    f.s.attach_assessment_skill(f.assessment.id, f.skill.id)
    f.s.archive_topic(f.topic)
    f.s.archive_skill(f.skill)
    assert f.s.topic_hierarchy(f.course.id) == ()
    assert f.s.list_course_skills(f.course.id) == []
    assert f.s.learning_targets("lesson_topics", f.lesson.id)[0].deleted_at is not None
    f.runtime.close()
    runtime = create_runtime(tmp_path)
    try:
        assert runtime.service.learning_targets("lesson_topics", f.lesson.id)[0].id == child.id
        assert (
            runtime.service.learning_targets("assessment_skills", f.assessment.id)[0].id
            == f.skill.id
        )
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "entity,method,field",
    [
        ("topic", "update_topic", "course_id"),
        ("skill", "update_skill", "course_id"),
        ("lesson", "update_lesson", "course_offering_id"),
        ("item", "update_assessment_item", "assessment_id"),
    ],
)
def test_learning_context_is_immutable(learning, entity, method, field):
    f = learning
    with pytest.raises(ApplicationError, match="learning_context_immutable"):
        getattr(f.s, method)(getattr(f, entity), **{field: EntityId.generate()})


def test_archive_lesson_preserves_topics_and_attendance(learning):
    f = learning
    link = f.s.attach_lesson_topic(f.lesson.id, f.topic.id)
    attendance = f.s.mark_attendance(f.lesson.id, f.enrollment.id, AttendanceStatus.PRESENT)
    f.s.archive_lesson(f.lesson)
    assert f.s.list_lessons(f.offering.id) == []
    assert f.s._r.lesson_topics.for_owner(f.lesson.id) == [link]
    assert f.s._r.attendance.for_lesson(f.lesson.id) == [attendance]
    assert f.s._r.lessons.find_by_id(f.lesson.id, include_deleted=True).deleted_at is not None


def test_stale_root_archive_rolls_back_descendant_changes(learning):
    f = learning
    child = f.s.create_topic(f.course.id, "Child", parent_topic_id=f.topic.id)
    changed = f.s.update_topic(f.topic, title="Changed externally")
    with pytest.raises(RepositoryError):
        f.s.archive_topic(f.topic)
    assert f.s._r.topics.find_by_id(child.id) == child
    assert f.s._r.topics.find_by_id(f.topic.id) == changed


def test_topic_skill_many_to_many_has_independent_explicit_links(learning):
    f = learning
    second_topic = f.s.create_topic(f.course.id, "Other topic")
    second_skill = f.s.create_skill(f.course.id, "Other skill")
    f.s.attach_topic_skill(f.topic.id, f.skill.id)
    f.s.attach_topic_skill(f.topic.id, second_skill.id)
    f.s.attach_topic_skill(second_topic.id, f.skill.id)
    assert {s.id for s in f.s.learning_targets("topic_skills", f.topic.id)} == {
        f.skill.id,
        second_skill.id,
    }
    assert f.s.learning_targets("topic_skills", second_topic.id) == (f.skill,)
    assert f.s.learning_targets("lesson_topics", f.lesson.id) == ()
