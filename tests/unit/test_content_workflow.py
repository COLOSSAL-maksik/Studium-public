import json
from dataclasses import replace

import pytest

from studium.domain.content import (
    FAQDraftContract,
    GenerationCriteria,
    LiteratureItem,
    LiteratureType,
    Problem,
    generate_variants,
    tag_document,
)
from studium.domain.value_objects import (
    AcademicWeekNumber,
    EntityId,
    EntityMetadata,
    LocalDate,
    UtcInstant,
)


@pytest.mark.parametrize(
    "number,numerator", [(1, True), (2, False), (5, True), (6, False), (101, True)]
)
def test_academic_week_parity(number, numerator):
    assert AcademicWeekNumber(number).numerator is numerator


@pytest.mark.parametrize("number", [0, -1, True, 1.5, "2", None])
def test_week_rejects_nonpositive_or_noninteger(number):
    with pytest.raises(ValueError):
        AcademicWeekNumber(number)


@pytest.mark.parametrize("day,expected", [(1, 1), (7, 1), (8, 2), (14, 2), (15, 3)])
def test_week_counts_from_term_start(day, expected):
    assert (
        AcademicWeekNumber.for_date(LocalDate(2026, 9, 1), LocalDate(2026, 9, day)).value
        == expected
    )


def test_before_term_has_no_academic_week():
    assert AcademicWeekNumber.for_date(LocalDate(2026, 9, 1), LocalDate(2026, 8, 31)) is None


def test_shared_tags_normalize_without_losing_cyrillic():
    assert json.loads(tag_document([" Балки ", "балки", "рамы"])) == ["Балки", "рамы"]


def problem(number, course):
    return Problem(
        metadata=EntityMetadata.create(UtcInstant.now()),
        course_id=course,
        title=f"Problem {number}",
        statement="Synthetic",
        correct_answer="Teacher answer",
    )


@pytest.mark.parametrize("size,count", [(1, 20), (2, 30), (3, 30), (10, 5)])
def test_generator_is_deterministic_unique_and_bounded(size, count):
    course = EntityId.generate()
    pool = [problem(i, course) for i in range(30)]
    criteria = GenerationCriteria(course, count, size, seed=7)
    first = generate_variants(pool, criteria)
    assert first == generate_variants(reversed(pool), criteria)
    assert len(first) == count and all(len(v) == size for v in first)
    assert len({tuple(sorted(p.id for p in v)) for v in first}) == count
    assert first != generate_variants(pool, replace(criteria, seed=8))


@pytest.mark.parametrize("size,count", [(3, 1), (1, 3), (2, 2)])
def test_insufficient_unique_combinations_explicit(size, count):
    course = EntityId.generate()
    with pytest.raises(ValueError, match="insufficient_problem_pool"):
        generate_variants(
            [problem(1, course), problem(2, course)], GenerationCriteria(course, count, size)
        )


@pytest.mark.parametrize("year", [0, 10000, True, 2.5])
def test_literature_year_validation(year):
    with pytest.raises(ValueError):
        LiteratureItem(
            metadata=EntityMetadata.create(UtcInstant.now()),
            course_id=None,
            title="Synthetic",
            year=year,
        )


@pytest.mark.parametrize("type", list(LiteratureType))
def test_literature_type_contract(type):
    assert (
        LiteratureItem(
            metadata=EntityMetadata.create(UtcInstant.now()),
            course_id=None,
            title="Synthetic",
            type=type,
        ).type
        == type
    )


def test_faq_contract_is_reviewed_manual_and_inactive_by_default():
    value = FAQDraftContract("Question", "Reviewed answer", EntityId.generate())
    assert not value.active
    with pytest.raises(ValueError):
        FAQDraftContract("", "Answer")
