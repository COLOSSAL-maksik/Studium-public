"""Local immutable bytes, bounded streaming copy and recoverable import journal."""

import errno
import hashlib
import json
import os
import shutil
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity, ImportedFile
from studium.domain.file_contract import FILE_EXTENSIONS, validate_filename, validate_storage_key
from studium.domain.value_objects import EntityId
from studium.infrastructure.user_data import AppPaths

MAX_FILE_BYTES = 1024 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".rtf": "application/rtf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".zip": "application/zip",
    ".7z": "application/x-7z-compressed",
    ".bin": "application/octet-stream",
}


def file_error(error: OSError) -> ApplicationError:
    key = {
        errno.ENOENT: "file_missing",
        errno.EACCES: "file_permission",
        errno.EPERM: "file_permission",
        errno.ENOSPC: "file_disk_full",
    }.get(error.errno, "file_io_error")
    return ApplicationError(key)


class LocalFileStorage:
    def __init__(self, root: Path):
        self.paths = AppPaths(root)
        self.root = self.paths.root

    def controlled_path(self, relative: str) -> Path:
        path = self.root / relative
        if path.is_absolute() and not path.is_relative_to(self.root):
            raise ApplicationError("file_unsafe_path")
        if any(part in ("..", ".") for part in Path(relative).parts):
            raise ApplicationError("file_unsafe_path")
        # Reject symlinks and Windows junctions, even when they point inside root.
        for component in (self.root, *reversed(path.parents), path):
            if component.is_relative_to(self.root) and (
                component.is_symlink() or component.is_junction()
            ):
                raise ApplicationError("file_unsafe_path")
        if not path.resolve().is_relative_to(self.root):
            raise ApplicationError("file_unsafe_path")
        return path

    def working_copy(self, asset):
        from uuid import uuid4

        if self.verify(asset) != FileIntegrity.AVAILABLE:
            raise ApplicationError("file_missing")
        target = self.controlled_path(
            "cache/working-copies/" + str(uuid4()) + "/" + asset.original_filename
        )
        target.parent.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copyfile(self.path(asset), target)
        except OSError as error:
            shutil.rmtree(target.parent)
            raise file_error(error) from error
        return target

    def path(self, asset):
        validate_storage_key(asset.storage_key)
        return self.controlled_path(asset.storage_key)

    @contextmanager
    def _lock(self):
        journal = self.controlled_path("files/.imports")
        journal.mkdir(parents=True, exist_ok=True)
        lock_path = self.controlled_path("files/.imports/lock")
        with lock_path.open("a+b") as handle:
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise ApplicationError("file_storage_busy") from None
            try:
                yield journal
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _publish(temporary: Path, final: Path):
        # Windows rename fails if the destination exists. POSIX link has the same
        # no-overwrite guarantee; both publish complete bytes atomically.
        if os.name == "nt":
            os.rename(temporary, final)
        else:
            os.link(temporary, final)
            temporary.unlink()

    @contextmanager
    def backup_guard(self):
        """Reuse the import lock without creating/changing the production journal."""
        journal = self.controlled_path("files/.imports")
        lock_path = self.controlled_path("files/.imports/lock")
        try:
            with lock_path.open("rb") as handle:
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise ApplicationError("file_storage_busy") from None
                try:
                    if any(path.name != "lock" for path in journal.iterdir()):
                        raise ApplicationError("backup_pending_import")
                    yield
                finally:
                    if os.name == "nt":
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as error:
            raise file_error(error) from None

    @staticmethod
    def _remove_uncommitted(path: Path):
        # Windows read-only originals need their attribute cleared for rollback;
        # this is used only for journal entries proven absent from the database.
        if path.exists():
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
        path.unlink(missing_ok=True)

    @contextmanager
    def import_file(self, source: Path, id: EntityId):
        try:
            with self._lock(), self._import_unlocked(source, id) as imported:
                yield imported
        except OSError as error:
            raise file_error(error) from None

    @contextmanager
    def import_files(self, sources):
        """One lock/publication boundary; DB failure rolls back every new asset."""
        try:
            committed_batch = {"committed": False}
            with self._lock(), ExitStack() as stack:
                imported = [
                    stack.enter_context(self._import_unlocked(Path(path), id, committed_batch))
                    for path, id in sources
                ]
                yield tuple(imported)
                committed_batch["committed"] = True
        except OSError as error:
            raise file_error(error) from None

    @contextmanager
    def _import_unlocked(self, source, id, committed_batch=None):
        source = Path(source)
        validate_filename(source.name)
        extension = source.suffix.lower()
        if extension not in FILE_EXTENSIONS:
            raise ApplicationError("file_type_blocked")
        if source.is_symlink() or source.is_junction():
            raise ApplicationError("file_invalid_source")
        if not stat.S_ISREG(source.stat().st_mode):
            raise ApplicationError("file_invalid_source")
        key = f"files/{id.value[:2]}/{id.value}{extension}"
        final = self.controlled_path(key)
        final.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.controlled_path(f"files/.imports/{id.value}.tmp")
        marker = self.controlled_path(f"files/.imports/{id.value}.json")
        published = False
        committed = False
        marker_created = False
        try:
            with marker.open("x", encoding="utf-8") as record:
                marker_created = True
                json.dump({"storage_key": key}, record)
                record.flush()
                os.fsync(record.fileno())
            digest = hashlib.sha256()
            count = 0
            with source.open("rb") as original, temporary.open("xb") as target:
                before = os.fstat(original.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ApplicationError("file_invalid_source")
                if before.st_size > MAX_FILE_BYTES:
                    raise ApplicationError("file_too_large")
                header = original.read(16)
                if header.startswith((b"MZ", b"\x7fELF", b"#!")):
                    raise ApplicationError("file_type_blocked")
                original.seek(0)
                while chunk := original.read(CHUNK_BYTES):
                    count += len(chunk)
                    if count > MAX_FILE_BYTES:
                        raise ApplicationError("file_too_large")
                    target.write(chunk)
                    digest.update(chunk)
                target.flush()
                os.fsync(target.fileno())
                after = os.fstat(original.fileno())
                if (before.st_size, before.st_mtime_ns) != (
                    after.st_size,
                    after.st_mtime_ns,
                ) or count != before.st_size:
                    raise ApplicationError("file_source_changed")
            # Windows registry MIME settings vary, notably for WebP.
            mime = MIME_TYPES[extension]
            self._publish(temporary, final)
            published = True
            final.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            yield ImportedFile(source.name, key, mime, count, digest.hexdigest())
            # The caller's DB transaction has committed before resuming.
            committed = True
        finally:
            committed = committed or bool(committed_batch and committed_batch["committed"])
            if marker_created:
                try:
                    if published and not committed:
                        self._remove_uncommitted(final)
                    temporary.unlink(missing_ok=True)
                    marker.unlink(missing_ok=True)
                except OSError:
                    # Keep the marker for startup reconciliation. Never
                    # remove a committed original after finalization fails.
                    raise ApplicationError(
                        "file_finalize_pending" if committed else "file_rollback_pending"
                    ) from None

    def recover_pending(self, find_asset):
        """Reconcile only our journal, never scan/delete arbitrary stored originals."""
        recovered = 0
        try:
            with self._lock() as journal:
                for marker in sorted(journal.glob("*.json")):
                    marker = self.controlled_path(marker.relative_to(self.root).as_posix())
                    try:
                        id = EntityId(marker.stem)
                        record = json.loads(marker.read_text(encoding="utf-8"))
                        key = record["storage_key"]
                        validate_storage_key(key)
                        if key[9:45] != id.value or key[6:8] != id.value[:2]:
                            raise ValueError("Journal identity mismatch")
                    except (ValueError, KeyError, TypeError):
                        raise ApplicationError("file_journal_invalid") from None
                    asset = find_asset(id)
                    if asset is not None and asset.storage_key != key:
                        raise ApplicationError("file_journal_invalid")
                    if asset is None:
                        self._remove_uncommitted(self.controlled_path(key))
                    self.controlled_path(f"files/.imports/{id.value}.tmp").unlink(missing_ok=True)
                    marker.unlink()
                    recovered += 1
            return recovered
        except OSError as error:
            raise file_error(error) from None

    def verify(self, asset):
        try:
            path = self.path(asset)
            with path.open("rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ApplicationError("file_invalid_source")
                if os.fstat(stream.fileno()).st_size != asset.size_bytes:
                    return FileIntegrity.CORRUPTED
                digest = hashlib.sha256()
                while chunk := stream.read(CHUNK_BYTES):
                    digest.update(chunk)
            return (
                FileIntegrity.AVAILABLE
                if digest.hexdigest() == asset.sha256
                else FileIntegrity.CORRUPTED
            )
        except FileNotFoundError:
            return FileIntegrity.MISSING
        except OSError as error:
            raise file_error(error) from None
