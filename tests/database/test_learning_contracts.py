import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from studium.domain.enums import AttendanceStatus
from studium.domain.value_objects import EntityId
from tests.integration.test_learning import learning as learning


@pytest.fixture
def facts(learning):
    f = learning
    for kind, owner, target in [
        ("topic_skills", f.topic, f.skill),
        ("lesson_topics", f.lesson, f.topic),
        ("assessment_topics", f.assessment, f.topic),
        ("assessment_skills", f.assessment, f.skill),
        ("item_topics", f.item, f.topic),
        ("item_skills", f.item, f.skill),
    ]:
        f.s.attach_learning_link(kind, owner.id, target.id)
    f.s.mark_attendance(f.lesson.id, f.enrollment.id, AttendanceStatus.PRESENT)
    return f


TABLES = [
    "topics",
    "skills",
    "lessons",
    "attendance",
    "assessment_items",
    "topic_skills",
    "lesson_topics",
    "assessment_topics",
    "assessment_skills",
    "assessment_item_topics",
    "assessment_item_skills",
]


@pytest.mark.parametrize("table", TABLES)
def test_v2_fk_metadata_indexes_and_no_physical_delete(facts, table):
    engine = facts.runtime._engine
    with engine.connect() as c:
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert inspect(c).get_foreign_keys(table)
        assert inspect(c).get_indexes(table)
        assert c.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one() == 1
    for sql in [
        f"DELETE FROM {table}",
        f"UPDATE {table} SET revision=revision+2",
        f"UPDATE {table} SET created_at=created_at+1,updated_at=updated_at+1,revision=revision+1",
        f"UPDATE {table} SET updated_at=updated_at-1,revision=revision+1",
    ]:
        with pytest.raises(IntegrityError), engine.begin() as c:
            c.exec_driver_sql(sql)
    with engine.connect() as c:
        assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []


def test_raw_sql_cycle_and_cross_course_parent(facts):
    f = facts
    child = f.s.create_topic(f.course.id, "Child", parent_topic_id=f.topic.id)
    other = f.s.create_course("Other")
    foreign = f.s.create_topic(other.id, "Foreign")
    for id in [child.id, foreign.id, f.topic.id]:
        with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
            c.exec_driver_sql(
                "UPDATE topics SET parent_topic_id=?,revision=revision+1 WHERE id=?",
                (id.value, f.topic.id.value),
            )


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("topics", "title", " "),
        ("topics", "sort_order", -1),
        ("skills", "sort_order", 1.5),
        ("lessons", "lesson_date", "2026-02-30"),
        ("attendance", "status", "other"),
        ("assessment_items", "max_score", -1),
        ("assessment_items", "max_score", float("inf")),
    ],
)
def test_raw_invalid_learning_values(facts, table, field, value):
    with pytest.raises(IntegrityError), facts.runtime._engine.begin() as c:
        c.exec_driver_sql(f"UPDATE {table} SET {field}=?,revision=revision+1", (value,))


@pytest.mark.parametrize(
    "table,field",
    [
        ("topics", "course_id"),
        ("skills", "course_id"),
        ("lessons", "course_offering_id"),
        ("assessment_items", "assessment_id"),
        ("attendance", "enrollment_id"),
        ("topic_skills", "skill_id"),
        ("lesson_topics", "topic_id"),
        ("assessment_topics", "topic_id"),
        ("assessment_skills", "skill_id"),
        ("assessment_item_topics", "topic_id"),
        ("assessment_item_skills", "skill_id"),
    ],
)
def test_raw_reference_identity_changes_rejected(facts, table, field):
    with pytest.raises(IntegrityError), facts.runtime._engine.begin() as c:
        c.exec_driver_sql(
            f"UPDATE {table} SET {field}=?,revision=revision+1", (EntityId.generate().value,)
        )


def test_lesson_attendance_fk_same_offering_and_unique_pair(facts):
    f = facts
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql(
            "INSERT INTO attendance SELECT ?,lesson_id,enrollment_id,status,comment,created_at,updated_at,revision,deleted_at FROM attendance",
            (EntityId.generate().value,),
        )
