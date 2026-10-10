"""Local communication persistence ports."""

from typing import Protocol

from studium.domain.communication import Message, MessageAttachment, QuestionCase
from studium.domain.repositories import MutableRepository, SoftDeleteRepository
from studium.domain.repositories.learning import LearningLinkRepository
from studium.domain.value_objects import EntityId


class QuestionCaseRepository(MutableRepository[QuestionCase], Protocol): ...


class MessageRepository(SoftDeleteRepository[Message], Protocol):
    def insert(self, entity: Message) -> None: ...
    def for_case(self, case_id: EntityId, *, include_deleted=False) -> list[Message]: ...
    def find_external(self, key: tuple[str, str, str, str]) -> Message | None: ...


class MessageAttachmentRepository(LearningLinkRepository[MessageAttachment], Protocol):
    def for_asset(self, asset_id: EntityId) -> list[MessageAttachment]: ...
