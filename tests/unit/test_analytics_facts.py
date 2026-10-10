from dataclasses import FrozenInstanceError

import pytest

from studium.domain.analytics_facts import AttemptItemResult
from studium.domain.enums import ItemOutcome
from studium.domain.value_objects import EntityId
from tests.unit.test_domain import metadata


def result(**values):
    return AttemptItemResult(
        metadata=metadata(),
        attempt_id=EntityId.generate(),
        assessment_item_id=EntityId.generate(),
        **values,
    )


@pytest.mark.parametrize(
    "values",
    [
        {"outcome": ItemOutcome.CORRECT},
        {"outcome": ItemOutcome.PARTIAL},
        {"outcome": ItemOutcome.INCORRECT},
        {"outcome": ItemOutcome.NOT_EVALUATED},
        {"outcome": ItemOutcome.NOT_EVALUATED, "max_score": 3},
        {"score": 0},
        {"score": 2.5},
        {"score": 2, "max_score": 4},
        {"outcome": ItemOutcome.PARTIAL, "score": 2, "max_score": 4},
    ],
)
def test_item_result_outcome_score_combinations(values):
    value = result(teacher_comment="  Original\ncomment  ", **values)
    assert value.teacher_comment == "  Original\ncomment  "
    assert value.revision == 1 and value.deleted_at is None
    with pytest.raises(FrozenInstanceError):
        value.score = 0


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"teacher_comment": "Only comment"},
        {"max_score": 5},
        {"outcome": "CORRECT"},
        {"score": -1},
        {"score": float("nan")},
        {"score": float("inf")},
        {"score": 1, "max_score": 0},
        {"score": 1, "max_score": float("inf")},
        {"score": 4, "max_score": 3},
        {"outcome": ItemOutcome.CORRECT, "teacher_comment": 5},
    ],
)
def test_item_result_invalid_values(values):
    with pytest.raises(ValueError):
        result(**values)
