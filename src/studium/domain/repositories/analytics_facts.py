"""Ports for recorded item evaluations and derived content-lock policy."""

from collections.abc import Iterable
from typing import Protocol

from studium.domain.analytics_facts import AttemptItemResult
from studium.domain.repositories import SoftDeleteRepository
from studium.domain.value_objects import EntityId


class AttemptItemResultRepository(SoftDeleteRepository[AttemptItemResult], Protocol):
    def insert(self, entity: AttemptItemResult) -> None: ...
    def for_attempt(
        self, attempt_id: EntityId, *, include_deleted: bool = False
    ) -> list[AttemptItemResult]: ...
    def for_attempts(self, ids: Iterable[EntityId]) -> list[AttemptItemResult]: ...


class SemanticLockRepository(Protocol):
    def assessment_locked(self, assessment_id: EntityId) -> bool: ...
    def topic_locked(self, topic_id: EntityId) -> bool: ...
    def skill_locked(self, skill_id: EntityId) -> bool: ...
