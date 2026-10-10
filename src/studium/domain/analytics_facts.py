"""Recorded evaluation of one assessment item in one immutable Attempt."""

from dataclasses import dataclass

from studium.domain.entities import StudiumEntity
from studium.domain.enums import ItemOutcome
from studium.domain.value_objects import EntityId, validate_score


@dataclass(frozen=True, kw_only=True)
class AttemptItemResult(StudiumEntity):
    attempt_id: EntityId
    assessment_item_id: EntityId
    outcome: ItemOutcome | None = None
    score: float | None = None
    max_score: float | None = None
    teacher_comment: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is not None and not isinstance(self.outcome, ItemOutcome):
            raise ValueError("Item result requires a known outcome")
        validate_score(self.score, self.max_score)
        if self.outcome is None and self.score is None:
            raise ValueError("Item result requires outcome or score")
        if self.teacher_comment is not None and not isinstance(self.teacher_comment, str):
            raise ValueError("Teacher comment must be text")
