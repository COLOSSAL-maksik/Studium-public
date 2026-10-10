"""Local recovery commands and immutable results; no Qt, SQL or archive dependencies."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Protocol

from studium.application.errors import ApplicationError


@dataclass(frozen=True)
class BackupEntry:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class BackupPreview:
    created_utc: str
    app_version: str
    schema_revision: str
    database_size: int
    files: tuple[BackupEntry, ...]
    archive_sha256: str

    @property
    def file_count(self) -> int:
        return len(self.files) - 1

    @property
    def total_size(self) -> int:
        return sum(entry.size for entry in self.files)


@dataclass(frozen=True)
class StorageHealth:
    data_root: str
    schema_revision: str
    database_size: int
    file_count: int
    file_size: int
    database_ok: bool
    missing_files: int
    damaged_files: int
    free_bytes: int | None


class BackupControl:
    """Cooperative cancellation and progress safe to use from a worker thread."""

    def __init__(self, progress: Callable[[str, int, int], None] | None = None):
        self._cancelled = Event()
        self._progress = progress

    def cancel(self) -> None:
        self._cancelled.set()

    def check(self) -> None:
        if self._cancelled.is_set():
            raise ApplicationError("backup_cancelled")

    def report(self, phase: str, completed: int = 0, total: int = 0) -> None:
        self.check()
        if self._progress:
            self._progress(phase, completed, total)
        self.check()


class BackupPort(Protocol):
    def create(self, destination: Path, control: BackupControl) -> BackupPreview: ...

    def verify(self, archive: Path, control: BackupControl) -> BackupPreview: ...

    def restore(
        self, archive: Path, destination: Path, preview: BackupPreview, control: BackupControl
    ) -> Path: ...

    def diagnose(self, control: BackupControl) -> StorageHealth: ...


class BackupService:
    def __init__(self, port: BackupPort):
        self._port = port

    def create(self, destination: Path, control: BackupControl) -> BackupPreview:
        return self._port.create(destination, control)

    def verify(self, archive: Path, control: BackupControl) -> BackupPreview:
        return self._port.verify(archive, control)

    def restore(
        self, archive: Path, destination: Path, preview: BackupPreview, control: BackupControl
    ) -> Path:
        return self._port.restore(archive, destination, preview, control)

    def diagnose(self, control: BackupControl) -> StorageHealth:
        return self._port.diagnose(control)
