"""Direct SQL cannot rewrite historical item or classification facts."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from studium.domain.enums import ItemOutcome
from studium.domain.value_objects import EntityId
from tests.integration.test_analytics_facts import attempt
from tests.integration.test_analytics_facts import locked as locked
from tests.integration.test_learning import learning as learning


@pytest.fixture
def evaluated(locked):
    f = locked
    work = f.s.get_or_create_work(f.student.id, f.assessment.id)
    first = f.s._r.attempts.history(work.id)[0]
    value = f.s.create_attempt_item_result(
        first.id, f.item.id, score=1, max_score=3, outcome=ItemOutcome.PARTIAL
    )
    return f, value


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE attempt_item_results SET score=2,revision=revision+1",
        "UPDATE attempt_item_results SET outcome='CORRECT',revision=revision+1",
        "UPDATE attempt_item_results SET max_score=5,revision=revision+1",
        "UPDATE attempt_item_results SET teacher_comment='Changed',revision=revision+1",
        "UPDATE attempt_item_results SET attempt_id='00000000-0000-0000-0000-000000000000',revision=revision+1",
        "UPDATE attempt_item_results SET assessment_item_id='00000000-0000-0000-0000-000000000000',revision=revision+1",
        "UPDATE attempt_item_results SET revision=revision+2",
        "UPDATE attempt_item_results SET created_at=created_at+1,updated_at=updated_at+1,revision=revision+1",
        "DELETE FROM attempt_item_results",
    ],
)
def test_raw_result_immutability(evaluated, sql):
    f, value = evaluated
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql(sql)
    assert f.s._r.item_results.find_by_id(value.id) == value


def test_raw_active_pair_unique_and_tombstone_cannot_resurrect(evaluated):
    f, value = evaluated
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql(
            "INSERT INTO attempt_item_results SELECT ?,attempt_id,assessment_item_id,outcome,score,max_score,teacher_comment,created_at,updated_at,1,NULL FROM attempt_item_results",
            (EntityId.generate().value,),
        )
    f.s.archive_attempt_item_result(value)
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql("UPDATE attempt_item_results SET deleted_at=NULL,revision=revision+1")
    archived = f.s._r.item_results.find_by_id(value.id, include_deleted=True)
    assert archived.deleted_at is not None and archived.score == value.score


@pytest.mark.parametrize(
    "outcome,score,maximum",
    [
        (None, None, None),
        ("UNKNOWN", None, None),
        (None, -1, None),
        (None, 1, 0),
        (None, 4, 3),
        (None, "bad", None),
        (None, 1, "bad"),
        (None, float("inf"), None),
    ],
)
def test_raw_item_result_checks(learning, outcome, score, maximum):
    f = learning
    first = attempt(f)
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql(
            "INSERT INTO attempt_item_results(id,attempt_id,assessment_item_id,outcome,score,max_score,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                EntityId.generate().value,
                first.id.value,
                f.item.id.value,
                outcome,
                score,
                maximum,
                first.created_at.epoch_microseconds,
                first.updated_at.epoch_microseconds,
            ),
        )


def test_raw_cross_assessment_item_rejected(learning):
    f = learning
    other = f.s.create_assessment(f.offering.id, "Other", f.assessment.type)
    item = f.s.create_assessment_item(other.id, "Other item")
    first = attempt(f)
    with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
        c.exec_driver_sql(
            "INSERT INTO attempt_item_results(id,attempt_id,assessment_item_id,outcome,created_at,updated_at) VALUES(?,?,?,'CORRECT',?,?)",
            (
                EntityId.generate().value,
                first.id.value,
                item.id.value,
                first.created_at.epoch_microseconds,
                first.updated_at.epoch_microseconds,
            ),
        )


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("assessments", "title", "Changed"),
        ("assessments", "description", "Changed"),
        ("assessments", "max_score", 10),
        ("assessments", "number", "Changed"),
        ("assessments", "type", "TEST"),
        ("assessment_items", "title", "Changed"),
        ("assessment_items", "description", "Changed"),
        ("assessment_items", "max_score", 10),
        ("topics", "title", "Changed"),
        ("topics", "description", "Changed"),
        ("skills", "title", "Changed"),
        ("skills", "description", "Changed"),
    ],
)
def test_raw_semantic_edits_rejected(locked, table, field, value):
    with pytest.raises(IntegrityError), locked.runtime._engine.begin() as c:
        c.exec_driver_sql(f"UPDATE {table} SET {field}=?,revision=revision+1", (value,))


@pytest.mark.parametrize(
    "table",
    [
        "assessment_items",
        "assessment_topics",
        "assessment_skills",
        "assessment_item_topics",
        "assessment_item_skills",
        "topics",
        "skills",
    ],
)
def test_raw_semantic_archive_rejected(locked, table):
    with pytest.raises(IntegrityError), locked.runtime._engine.begin() as c:
        c.exec_driver_sql(f"UPDATE {table} SET deleted_at=updated_at,revision=revision+1")


@pytest.mark.parametrize(
    "table",
    [
        "assessment_items",
        "assessment_topics",
        "assessment_skills",
        "assessment_item_topics",
        "assessment_item_skills",
    ],
)
def test_raw_semantic_addition_rejected(locked, table):
    with pytest.raises(IntegrityError), locked.runtime._engine.begin() as c:
        fields = inspect(c).get_columns(table)
        names = [column["name"] for column in fields]
        selected = ["?" if name == "id" else name for name in names]
        c.exec_driver_sql(
            f"INSERT INTO {table} ({','.join(names)}) SELECT {','.join(selected)} FROM {table}",
            (EntityId.generate().value,),
        )


def test_lock_views_match_repository_after_archived_attempt(locked):
    f = locked
    assert f.s._r.content_locks.assessment_locked(f.assessment.id)
    assert f.s._r.content_locks.topic_locked(f.topic.id)
    assert f.s._r.content_locks.skill_locked(f.skill.id)
    with f.runtime._engine.connect() as c:
        assert set(c.exec_driver_sql("SELECT id FROM analytics_locked_assessments").scalars()) == {
            f.assessment.id.value
        }
        assert set(c.exec_driver_sql("SELECT id FROM analytics_locked_topics").scalars()) == {
            f.topic.id.value
        }
        assert set(c.exec_driver_sql("SELECT id FROM analytics_locked_skills").scalars()) == {
            f.skill.id.value
        }
        assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        assert inspect(c).get_foreign_keys("attempt_item_results")
        assert len(inspect(c).get_indexes("attempt_item_results")) == 2


def test_raw_topic_ancestor_and_reparent_lock(learning):
    f = learning
    child = f.s.create_topic(f.course.id, "Child", parent_topic_id=f.topic.id)
    other = f.s.create_topic(f.course.id, "Other parent")
    f.s.attach_item_topic(f.item.id, child.id)
    first = attempt(f)
    f.s._r.attempts.soft_delete(first.id, expected_revision=first.revision, at=f.s._clock())
    for sql, params in [
        (
            "UPDATE topics SET parent_topic_id=?,revision=revision+1 WHERE id=?",
            (other.id.value, child.id.value),
        ),
        ("UPDATE topics SET title='Changed',revision=revision+1 WHERE id=?", (f.topic.id.value,)),
    ]:
        with pytest.raises(IntegrityError), f.runtime._engine.begin() as c:
            c.exec_driver_sql(sql, params)
    assert f.s._r.content_locks.topic_locked(child.id)
    assert f.s._r.content_locks.topic_locked(f.topic.id)
    assert not f.s._r.content_locks.topic_locked(other.id)
