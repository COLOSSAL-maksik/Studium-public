"""Item evaluation history and semantic lock use only synthetic temporary data."""

from dataclasses import replace
from pathlib import Path

import pytest

from studium.application.errors import ApplicationError
from studium.composition import create_runtime
from studium.domain.enums import AttemptResult, ItemOutcome
from studium.domain.repositories import RepositoryError, RepositoryFailure
from tests.integration.test_learning import learning as learning


def attempt(f, result=AttemptResult.NEEDS_REVISION):
    work = f.s.get_or_create_work(f.student.id, f.assessment.id)
    return f.s.add_attempt(work.id, f.s._clock(), result)


@pytest.mark.parametrize(
    "values",
    [
        {"outcome": ItemOutcome.CORRECT},
        {"score": 0},
        {"score": 1.5, "max_score": 3},
        {"outcome": ItemOutcome.PARTIAL, "score": 1, "max_score": 3},
    ],
)
def test_item_result_roundtrip_and_reopen(learning, values):
    f = learning
    first = attempt(f)
    value = f.s.create_attempt_item_result(
        first.id, f.item.id, teacher_comment="Original", **values
    )
    assert f.s.list_attempt_item_results(first.id) == (value,)
    assert f.s._r.item_results.find_by_id(value.id) == value
    assert f.s._r.item_results.for_attempts([first.id, first.id]) == [value]
    reopened = create_runtime(Path(f.runtime.diagnostics.database_path).parent)
    try:
        assert reopened.service.list_attempt_item_results(first.id) == (value,)
    finally:
        reopened.close()


def test_multiple_items_separate_attempts_preserve_history(learning):
    f = learning
    second_item = f.s.create_assessment_item(f.assessment.id, "Second item")
    first = attempt(f)
    one = f.s.create_attempt_item_result(first.id, f.item.id, outcome=ItemOutcome.INCORRECT)
    two = f.s.create_attempt_item_result(first.id, second_item.id, outcome=ItemOutcome.CORRECT)
    second = attempt(f, AttemptResult.ACCEPTED)
    corrected = f.s.create_attempt_item_result(second.id, f.item.id, outcome=ItemOutcome.CORRECT)
    assert set(f.s.list_attempt_item_results(first.id)) == {one, two}
    assert f.s.list_attempt_item_results(second.id) == (corrected,)
    assert f.s._r.item_results.find_by_id(one.id) == one


def test_explicit_archive_then_replacement_keeps_old_fact(learning):
    f = learning
    first = attempt(f)
    original = f.s.create_attempt_item_result(first.id, f.item.id, score=1, max_score=3)
    with pytest.raises(ApplicationError, match="item_result_exists"):
        f.s.create_attempt_item_result(first.id, f.item.id, score=2, max_score=3)
    f.s.archive_attempt_item_result(original)
    corrected = f.s.create_attempt_item_result(first.id, f.item.id, score=2, max_score=3)
    history = f.s.list_attempt_item_results(first.id, include_deleted=True)
    old = next(value for value in history if value.id == original.id)
    assert old.score == original.score and old.max_score == original.max_score
    assert old.deleted_at is not None and old.revision == original.revision + 1
    assert corrected.id != old.id and f.s.list_attempt_item_results(first.id) == (corrected,)


def test_item_result_empty_and_foreign_item_rejected(learning):
    f = learning
    other = f.s.create_assessment(f.offering.id, "Other", f.assessment.type)
    foreign_item = f.s.create_assessment_item(other.id, "Other item")
    first = attempt(f)
    with pytest.raises(ApplicationError, match="item_result_empty"):
        f.s.create_attempt_item_result(first.id, f.item.id, teacher_comment="No evaluation")
    with pytest.raises(ApplicationError, match="item_result_context_mismatch"):
        f.s.create_attempt_item_result(first.id, foreign_item.id, outcome=ItemOutcome.CORRECT)
    assert f.s.list_attempt_item_results(first.id) == ()


@pytest.fixture
def locked(learning):
    f = learning
    f.s.set_assessment_content(f.assessment.id, [f.topic.id], [f.skill.id])
    f.s.set_assessment_content(f.item.id, [f.topic.id], [f.skill.id], item=True)
    attempt(f)
    return f


@pytest.mark.parametrize(
    "operation",
    [
        lambda f: f.s.update_assessment(f.assessment, title="Changed"),
        lambda f: f.s.update_assessment(f.assessment, description="Changed"),
        lambda f: f.s.update_assessment(f.assessment, max_score=5),
        lambda f: f.s.update_assessment_item(f.item, title="Changed"),
        lambda f: f.s.update_assessment_item(f.item, description="Changed"),
        lambda f: f.s.update_assessment_item(f.item, max_score=5),
        lambda f: f.s.create_assessment_item(f.assessment.id, "New item"),
        lambda f: f.s.archive_assessment_item(f.item),
        lambda f: f.s.detach_assessment_topic(f.assessment.id, f.topic.id),
        lambda f: f.s.detach_assessment_skill(f.assessment.id, f.skill.id),
        lambda f: f.s.detach_item_topic(f.item.id, f.topic.id),
        lambda f: f.s.detach_item_skill(f.item.id, f.skill.id),
        lambda f: f.s.update_topic(f.topic, title="Changed"),
        lambda f: f.s.update_topic(f.topic, description="Changed"),
        lambda f: f.s.archive_topic(f.topic),
        lambda f: f.s.update_skill(f.skill, title="Changed"),
        lambda f: f.s.archive_skill(f.skill),
    ],
)
def test_semantic_structure_edits_rejected_after_attempt(locked, operation):
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        operation(locked)


def test_lock_remains_after_attempt_archive_and_allows_cosmetic_order(locked):
    f = locked
    work = f.s.get_or_create_work(f.student.id, f.assessment.id)
    first = f.s._r.attempts.history(work.id)[0]
    f.s._r.attempts.soft_delete(first.id, expected_revision=first.revision, at=f.s._clock())
    assert f.s.assessment_content_locked(f.assessment.id)
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.update_assessment_item(f.item, title="Reclassified")
    assert f.s.update_assessment_item(f.item, sort_order=2).sort_order == 2
    assert f.s.update_topic(f.topic, sort_order=2).sort_order == 2
    assert f.s.update_skill(f.skill, sort_order=2).sort_order == 2


def test_taxonomy_ancestors_locked_unrelated_nodes_editable(learning):
    f = learning
    child = f.s.create_topic(f.course.id, "Child", parent_topic_id=f.topic.id)
    f.s.attach_item_topic(f.item.id, child.id)
    attempt(f)
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.update_topic(child, parent_topic_id=None)
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.update_topic(f.topic, title="Reclassified parent")
    unrelated = f.s.create_topic(f.course.id, "Unrelated")
    assert f.s.update_topic(unrelated, title="Still editable").title == "Still editable"
    # TopicSkill is a catalogue relation, never an inferred item evaluation.
    f.s.attach_topic_skill(child.id, f.skill.id)
    f.s.detach_topic_skill(child.id, f.skill.id)
    assert f.s.update_skill(f.skill, title="Unrelated evaluation").title == "Unrelated evaluation"


def test_catalogue_link_addition_restore_and_transaction_rollback(learning):
    f = learning
    first = f.s.attach_assessment_topic(f.assessment.id, f.topic.id)
    f.s.detach_assessment_topic(f.assessment.id, f.topic.id)
    attempt(f)
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.attach_assessment_topic(f.assessment.id, f.topic.id)
    other = f.s.create_topic(f.course.id, "New tag")
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.attach_item_topic(f.item.id, other.id)
    hidden = f.s._r.assessment_topics.find_by_id(first.id, include_deleted=True)
    assert hidden.deleted_at is not None
    assert f.s.learning_links("item_topics", f.item.id) == ()


def test_repository_cannot_overwrite_result_fact(learning):
    f = learning
    first = attempt(f)
    original = f.s.create_attempt_item_result(first.id, f.item.id, score=1)
    # Port offers append/archive only; even the infrastructure compare-and-swap path is guarded.
    edited = replace(original, score=2, metadata=original.metadata.touch(f.s._clock()))
    with pytest.raises(RepositoryError) as failure:
        with f.s._transaction() as r:
            with r.item_results._transaction() as session:
                r.item_results._compare_and_swap(session, edited, original.revision)
    assert failure.value.failure == RepositoryFailure.IMMUTABLE_FACT
    assert f.s.list_attempt_item_results(first.id) == (original,)


def test_old_attempt_evidence_stays_stable_after_rejected_content_edits(locked):
    f = locked
    work = f.s.get_or_create_work(f.student.id, f.assessment.id)
    first = f.s._r.attempts.history(work.id)[0]
    f.s.create_attempt_item_result(
        first.id, f.item.id, outcome=ItemOutcome.PARTIAL, score=1, max_score=3
    )
    cutoff = f.s._clock()
    before_topic = f.s.topic_evidence(f.topic.id, offering_id=f.offering.id, as_of=cutoff)
    before_skill = f.s.skill_evidence(f.skill.id, offering_id=f.offering.id, as_of=cutoff)
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.set_assessment_content(f.item.id, [], [], item=True)
    with pytest.raises(ApplicationError, match="content_semantic_locked"):
        f.s.update_topic(f.topic, title="Reclassified")
    assert f.s.topic_evidence(f.topic.id, offering_id=f.offering.id, as_of=cutoff) == before_topic
    assert f.s.skill_evidence(f.skill.id, offering_id=f.offering.id, as_of=cutoff) == before_skill
    assert before_topic.item_result_count == before_skill.item_result_count == 1
