"""Immutable reporting projections; no persistence, IO or presentation dependencies."""

from dataclasses import dataclass
from enum import StrEnum

from studium.domain.entities import Grade
from studium.domain.value_objects import EntityId, UtcInstant


class ReportKind(StrEnum):
    STUDENT = "student"
    GROUP = "group"
    ASSESSMENT = "assessment"


type ReportCell = str | int | float | StrEnum | UtcInstant | Grade | None


@dataclass(frozen=True)
class ReportTable:
    key: str
    title: str
    columns: tuple[tuple[str, str | StrEnum], ...]
    rows: tuple[tuple[ReportCell, ...], ...]


@dataclass(frozen=True)
class Report:
    kind: ReportKind
    title: str
    offering_id: EntityId
    generated_at: UtcInstant
    metadata: tuple[tuple[str, ReportCell], ...]
    tables: tuple[ReportTable, ...]


@dataclass(frozen=True)
class ReportChoices:
    students: tuple[tuple[EntityId, str], ...]
    assessments: tuple[tuple[EntityId, str], ...]
