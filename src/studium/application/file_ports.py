"""File side effects behind ports; query integrity is derived, never persisted."""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from studium.domain.entities import FileAsset
from studium.domain.value_objects import EntityId


class FileIntegrity(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    CORRUPTED = "corrupted"


@dataclass(frozen=True)
class ImportedFile:
    original_filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
    sha256: str


class FileStorage(Protocol):
    def import_file(self, source: Path, id: EntityId) -> AbstractContextManager[ImportedFile]: ...
    def import_files(self, sources) -> AbstractContextManager[tuple[ImportedFile, ...]]: ...
    def verify(self, asset: FileAsset) -> FileIntegrity: ...
    def path(self, asset: FileAsset) -> Path: ...
    def working_copy(self, asset: FileAsset) -> Path: ...


class FileOpener(Protocol):
    def open(self, path: Path) -> None: ...


class ThumbnailCache(Protocol):
    def image(self, asset: FileAsset, source: Path, *, maximum: int) -> Path: ...
