"""Explicit file ownership contracts, extendable by MessageAttachment in Phase 5."""

from typing import Protocol

from studium.domain.entities import AttemptAttachment, FileAsset
from studium.domain.repositories import MutableRepository, SoftDeleteRepository
from studium.domain.value_objects import EntityId


class FileAssetRepository(SoftDeleteRepository[FileAsset], Protocol):
    def insert(self, entity: FileAsset) -> None: ...


class AttemptAttachmentRepository(MutableRepository[AttemptAttachment], Protocol):
    def for_attempt(
        self, attempt_id: EntityId, *, include_deleted=False
    ) -> list[AttemptAttachment]: ...
    def for_student(
        self, student_id: EntityId, *, include_deleted=False
    ) -> list[AttemptAttachment]: ...
    def for_asset(self, asset_id: EntityId) -> list[AttemptAttachment]: ...
