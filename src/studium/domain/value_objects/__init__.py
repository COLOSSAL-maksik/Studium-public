"""Identity, absolute time, calendar dates and local revisions."""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from math import isfinite
from uuid import UUID, uuid4


@dataclass(frozen=True, order=True)
class EntityId:
    value: str

    def __post_init__(self) -> None:
        canonical = str(UUID(self.value))
        if canonical != self.value.lower():
            raise ValueError("Expected a canonical UUID")
        object.__setattr__(self, "value", canonical)

    @classmethod
    def generate(cls) -> "EntityId":
        return cls(str(uuid4()))

    def __str__(self) -> str:
        return self.value


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, order=True)
class UtcInstant:
    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None or self.value.utcoffset() != timedelta(0):
            raise ValueError("UTC is required explicitly")
        object.__setattr__(self, "value", self.value.astimezone(UTC))

    @classmethod
    def now(cls) -> "UtcInstant":
        return cls(datetime.now(UTC))

    @classmethod
    def from_epoch_microseconds(cls, value: int) -> "UtcInstant":
        if type(value) is not int:
            raise ValueError("Epoch microseconds must be an integer")
        return cls(EPOCH + timedelta(microseconds=value))

    @property
    def epoch_microseconds(self) -> int:
        delta = self.value - EPOCH
        return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


@dataclass(frozen=True, order=True)
class LocalDate:
    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        date(self.year, self.month, self.day)

    @classmethod
    def parse(cls, value: str) -> "LocalDate":
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("Expected YYYY-MM-DD")
        return cls(parsed.year, parsed.month, parsed.day)

    def __str__(self) -> str:
        return date(self.year, self.month, self.day).isoformat()


@dataclass(frozen=True, kw_only=True)
class EntityMetadata:
    id: EntityId
    created_at: UtcInstant
    updated_at: UtcInstant | None = None
    revision: int = 1
    deleted_at: UtcInstant | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, EntityId) or not isinstance(self.created_at, UtcInstant):
            raise ValueError("Metadata requires a UUID and UTC instant")
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision must be an integer >= 1")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at precedes created_at")
        if (
            self.deleted_at is not None
            and not self.created_at <= self.deleted_at <= self.updated_at
        ):
            raise ValueError("deleted_at must be between created_at and updated_at")

    @classmethod
    def create(cls, at: UtcInstant) -> "EntityMetadata":
        return cls(id=EntityId.generate(), created_at=at)

    def touch(self, at: UtcInstant) -> "EntityMetadata":
        if at < self.updated_at:
            raise ValueError("updated_at cannot move backwards")
        return replace(self, updated_at=at, revision=self.revision + 1)

    def soft_delete(self, at: UtcInstant) -> "EntityMetadata":
        if self.deleted_at is not None:
            return self
        return replace(self.touch(at), deleted_at=at)


def require_text(value: str, field: str) -> None:
    if not value.strip():
        raise ValueError(f"{field} must not be blank")


@dataclass(frozen=True, order=True)
class AcademicWeekNumber:
    value: int

    def __post_init__(self):
        if type(self.value) is not int or self.value < 1:
            raise ValueError("Academic week must be an integer >= 1")

    @property
    def numerator(self):
        return self.value % 2 == 1

    @classmethod
    def for_date(cls, starts_on: LocalDate, on: LocalDate):
        days = (
            date(on.year, on.month, on.day) - date(starts_on.year, starts_on.month, starts_on.day)
        ).days
        return cls(days // 7 + 1) if days >= 0 else None


def validate_score(score: float | None, maximum: float | None) -> None:
    if score is not None and (not isfinite(score) or score < 0):
        raise ValueError("score must be finite and nonnegative")
    if maximum is not None and (not isfinite(maximum) or maximum <= 0):
        raise ValueError("max_score must be finite and positive")
    if score is not None and maximum is not None and score > maximum:
        raise ValueError("score cannot exceed max_score")
