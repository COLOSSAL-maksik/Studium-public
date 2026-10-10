from dataclasses import replace

import pytest

from studium.domain.program import ProgramModule, WorkProgram
from studium.domain.value_objects import AcademicWeekNumber, EntityId, LocalDate
from tests.unit.test_domain import metadata


@pytest.fixture
def program():
    return WorkProgram(
        metadata=metadata(),
        course_id=EntityId.generate(),
        term_id=EntityId.generate(),
        title="Synthetic 17 weeks",
        first_week_start=LocalDate(2026, 9, 1),
    )


def test_semester_bounds_and_odd_even_first_date_mapping(program):
    assert program.weeks == 17
    assert program.week_dates(1) == (LocalDate(2026, 9, 1), LocalDate(2026, 9, 7))
    assert program.week_dates(17) == (LocalDate(2026, 12, 22), LocalDate(2026, 12, 28))
    assert program.week_for_date(LocalDate(2026, 9, 7)) == AcademicWeekNumber(1)
    assert program.week_for_date(LocalDate(2026, 9, 8)) == AcademicWeekNumber(2)
    assert program.week_for_date(LocalDate(2026, 12, 29)) is None
    assert AcademicWeekNumber(5).numerator
    assert not AcademicWeekNumber(6).numerator
    for week in (0, 18):
        with pytest.raises(ValueError):
            program.week_dates(week)


def test_week_exact_date_consistency(program):
    program.validate_week_date(AcademicWeekNumber(2), LocalDate(2026, 9, 8))
    with pytest.raises(ValueError):
        program.validate_week_date(AcademicWeekNumber(1), LocalDate(2026, 9, 8))
    with pytest.raises(ValueError):
        program.validate_week_date(None, LocalDate(2026, 9, 8))


@pytest.mark.parametrize("weeks", [0, 105, 1.5, True])
def test_duration_is_explicit_integer(program, weeks):
    with pytest.raises(ValueError):
        replace(program, weeks=weeks)


def test_module_ranges(program):
    with pytest.raises(ValueError):
        ProgramModule(
            metadata=metadata(),
            work_program_id=program.id,
            title="Invalid",
            start_week=7,
            end_week=6,
        )
