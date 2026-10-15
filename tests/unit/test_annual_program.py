"""Exact annual totals, integrity/completeness and stable fragment identities."""

from copy import deepcopy
from decimal import Decimal

import pytest

from studium.domain import annual_program as a


def content():
    value = a.new_annual("Synthetic")
    value["not_applicable"] = ["outcomes", "prerequisites", "works"]
    value["scoring"] = "NONE"
    value["semesters"][0]["modules"] = [
        dict(
            key=a.key(),
            title="M1",
            start_week=1,
            end_week=8,
            lessons=[
                dict(
                    key=a.key(),
                    kind="LECTURE",
                    title="L1",
                    hours="1.25",
                    topic_ids=[a.key()],
                    week=1,
                )
            ],
            works=[],
        )
    ]
    return value


def test_volume_counts_hours_normative_unknown_and_no_double_count():
    value = content()
    s = value["semesters"][0]
    value["loads"] = [
        dict(
            key=a.key(),
            semester_key=s["key"],
            module_key=s["modules"][0]["key"],
            kind="SELF_STUDY",
            hours="5.15",
        ),
        dict(key=a.key(), semester_key=s["key"], kind="SELF_STUDY", hours="0.15"),
    ]
    value["norms"] = [dict(key=a.key(), semester_key=s["key"], kind="LECTURE", hours="2")]
    assert not a.validate(value)
    module_rows = a.module_volume(value)
    assert module_rows[0].hours == Decimal("1.25")
    assert next(v for v in module_rows if v.kind == "SELF_STUDY").hours == Decimal("5.15")
    rows = a.volume(value)
    assert rows[0].hours == Decimal("1.25") and rows[0].count == 1
    assert rows[0].difference == Decimal("-0.75")
    assert next(
        v for v in rows if v.semester_key == s["key"] and v.kind == "SELF_STUDY"
    ).hours == Decimal("5.30")
    assert next(v for v in rows if v.semester_key is None and v.kind == "LECTURE").normative is None
    value["loads"].append(dict(key=a.key(), semester_key=s["key"], kind="LECTURE", hours="100"))
    with pytest.raises(ValueError, match="только из занятий"):
        a.validate(value)


@pytest.mark.parametrize("number", ["-1", "nan", "1.001", "1e2", 1.2, None])
def test_bad_hours_rejected_even_in_unfinished_lesson(number):
    value = content()
    lesson = value["semesters"][0]["modules"][0]["lessons"][0]
    lesson.update(title="", hours=number)
    with pytest.raises(ValueError):
        a.validate(value)


def test_incomplete_not_invalid_and_copy_identity_links():
    value = content()
    module = value["semesters"][0]["modules"][0]
    module["lessons"][0].update(hours="", topic_ids=[])
    assert a.validate(value)
    with pytest.raises(ValueError):
        a.validate(value, ready=True)
    copied = a.copy_fragment(module)
    assert copied["key"] != module["key"]
    assert copied["lessons"][0]["key"] != module["lessons"][0]["key"]
    assert copied["title"] == module["title"]


def test_reference_and_overlap_integrity_always_rejected():
    value = content()
    copy = deepcopy(value["semesters"][0]["modules"][0])
    copy = a.copy_fragment(copy)
    value["semesters"][0]["modules"].append(copy)
    with pytest.raises(ValueError, match="пересекаются"):
        a.validate(value)
    value["semesters"][0]["modules"].pop()
    value["outcomes"] = [
        dict(key=a.key(), category="COMPETENCE", text="Outcome", module_keys=[a.key()])
    ]
    with pytest.raises(ValueError, match="отсутствующий"):
        a.validate(value)


def test_budget_exact_no_100_limit_and_none_scoring():
    value = content()
    value["scoring"] = "POINTS"
    value["not_applicable"].remove("works")
    module = value["semesters"][0]["modules"][0]
    module["works"] = [
        dict(key=a.key(), title="Homework", category="HOMEWORK", min_cents=0, max_cents=3025)
    ]
    value["budgets"] = [
        dict(key=a.key(), module_key=module["key"], category="HOMEWORK", max_cents=4000),
        dict(key=a.key(), module_key=module["key"], category="*", max_cents=15000),
    ]
    assert not a.validate(value)
    totals = a.score_totals(value)
    assert (totals[0].allocated, totals[0].maximum, totals[1].allocated, totals[1].maximum) == (
        3025,
        4000,
        4000,
        15000,
    )
    value["budgets"][0]["max_cents"] = 3000
    assert "превышает" in " ".join(a.validate(value))
    with pytest.raises(ValueError):
        a.validate(value, ready=True)
