from datetime import UTC, datetime, timedelta

import pytest

from studium.domain import qa as q
from studium.domain.value_objects import LocalDate, UtcInstant


@pytest.mark.parametrize(
    "value,expected",
    [("0", 0), ("18", 1800), ("24,75", 2475), ("92233720368547758.07", q.MAX_CENTS)],
)
def test_exact_cents(value, expected):
    assert q.score_cents(value, fractional=True) == expected


@pytest.mark.parametrize(
    "value", ["NaN", "inf", "-1", "1,234", "1.2,3", "1e2", "92233720368547758.08"]
)
def test_invalid_exact_input(value):
    with pytest.raises(ValueError):
        q.score_cents(value, fractional=True)


@pytest.mark.parametrize(
    "start", [datetime(2026, 12, 28, 23, 0, tzinfo=UTC), datetime(2027, 1, 28, 23, 0, tzinfo=UTC)]
)
def test_sla_calendar_boundary_equality_and_microseconds(start):
    received = UtcInstant(start)
    due = UtcInstant(start + timedelta(days=7))
    assert q.deadline_state(received, due)[1] == "near_due"
    assert (
        q.deadline_state(received, UtcInstant(due.value + timedelta(microseconds=1)))[1]
        == "overdue"
    )
    assert (
        q.deadline_state(received, UtcInstant(due.value - timedelta(microseconds=1)))[1]
        == "near_due"
    )
    assert (
        q.deadline_state(received, UtcInstant(due.value - timedelta(hours=24, microseconds=1)))[1]
        == "waiting"
    )


def test_date_only_explicit_exclusive_boundary():
    assert q.day_boundary(LocalDate(2026, 10, 14)) == UtcInstant(
        datetime(2026, 10, 14, 21, tzinfo=UTC)
    )


def test_structured_physical_answers_do_not_use_score_precision():
    values = '[{"name":"Reaction","symbol":"A","kind":"numeric","value":"-1.23456789","units":"N","formula":"text only"}]'
    assert q.validate_answers(values)[0]["value"] == "-1.23456789"
