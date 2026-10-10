"""Version 1 recovery packages: pinned WAL snapshots, bounded ZIP IO and staged restore."""

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import struct
import tempfile
import time
import zipfile
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from studium import __version__
from studium.application.backup import BackupControl, BackupEntry, BackupPreview, StorageHealth
from studium.application.errors import ApplicationError
from studium.domain.file_contract import validate_storage_key
from studium.infrastructure.backup_paths import (
    empty_destination,
    external_path,
    file_identity,
    identity,
    path_identity,
    unlinked_path,
)
from studium.infrastructure.database.migrations import SCHEMA_REVISION, upgrade_database
from studium.infrastructure.database.session import create_database_engine
from studium.infrastructure.file_storage import (
    CHUNK_BYTES,
    MAX_FILE_BYTES,
    LocalFileStorage,
    file_error,
)
from studium.infrastructure.user_data import AppPaths

FORMAT = "studium-local-backup"
FORMAT_VERSION = 1
DATABASE = "studium.sqlite"
MANIFEST = "manifest.json"
HASH = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class BackupLimits:
    entries: int = 100_000
    total_bytes: int = 64 * 1024**3
    database_bytes: int = 4 * 1024**3
    manifest_bytes: int = 16 * 1024**2
    directory_bytes: int = 32 * 1024**2
    compression_ratio: int = 200
    snapshot_seconds: int = 60


def _schema_hash(connection: sqlite3.Connection) -> str:
    count, size = connection.execute(
        "SELECT count(*), coalesce(sum(length(sql)), 0) FROM sqlite_master"
    ).fetchone()
    if count > 4096 or size > 4 * 1024**2:
        raise ApplicationError("backup_limits")
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
    ).fetchall()
    return hashlib.sha256(json.dumps(rows, ensure_ascii=True).encode()).hexdigest()


@lru_cache(maxsize=1)
def _supported_schema_hash() -> str:
    # Build only a synthetic reference in scratch, never open the live Runtime.
    with tempfile.TemporaryDirectory(prefix="studium-schema-") as folder:
        path = Path(folder) / DATABASE
        engine = create_database_engine(path, wal=False)
        try:
            upgrade_database(engine)
            with closing(sqlite3.connect(path)) as connection:
                return _schema_hash(connection)
        finally:
            engine.dispose()


@contextmanager
def _readonly(path: Path, control: BackupControl, *, immutable=False):
    uri = path.as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    with closing(sqlite3.connect(uri, uri=True, timeout=0.1)) as connection:
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 4 * 1024**2)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")

        def interrupted():
            try:
                control.check()
                return 0
            except ApplicationError:
                return 1

        connection.set_progress_handler(interrupted, 1000)
        try:
            yield connection
        except sqlite3.Error:
            control.check()
            raise ApplicationError("backup_database_invalid") from None


def _check_database(connection: sqlite3.Connection, control: BackupControl) -> None:
    control.report("database_check")
    revisions = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    if revisions != [(SCHEMA_REVISION,)]:
        raise ApplicationError("backup_schema_unsupported")
    if _schema_hash(connection) != _supported_schema_hash():
        raise ApplicationError("backup_schema_unsupported")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ApplicationError("backup_database_invalid")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ApplicationError("backup_database_invalid")
    control.check()


def _assets(connection: sqlite3.Connection, limits: BackupLimits) -> tuple[BackupEntry, ...]:
    # Include soft-deleted assets: immutable historical facts still reference them.
    count, key_length, id_length, hash_length = connection.execute(
        "SELECT count(*), max(length(storage_key)), max(length(id)), max(length(sha256)) "
        "FROM file_assets"
    ).fetchone()
    if count + 2 > limits.entries:
        raise ApplicationError("backup_limits")
    if count and (key_length > 64 or id_length != 36 or hash_length != 64):
        raise ApplicationError("backup_file_invalid")
    rows = connection.execute(
        "SELECT id, storage_key, size_bytes, sha256 FROM file_assets ORDER BY storage_key"
    )
    result = []
    for id, key, size, digest in rows:
        validate_storage_key(key)
        if key[9:45] != id or key[6:8] != id[:2]:
            raise ApplicationError("backup_file_invalid")
        if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES or not HASH.fullmatch(digest):
            raise ApplicationError("backup_file_invalid")
        result.append(BackupEntry(key, size, digest))
        if len(result) + 2 > limits.entries:
            raise ApplicationError("backup_limits")
    return tuple(result)


def _stream(source, target, control: BackupControl, *, limit: int, phase: str) -> tuple[int, str]:
    digest, size = hashlib.sha256(), 0
    while chunk := source.read(CHUNK_BYTES):
        size += len(chunk)
        if size > limit:
            raise ApplicationError("backup_limits")
        control.report(phase, size, limit)
        digest.update(chunk)
        if target is not None:
            target.write(chunk)
    control.check()
    return size, digest.hexdigest()


def _matches(entry: BackupEntry, measured: tuple[int, str]) -> None:
    if measured != (entry.size, entry.sha256):
        raise ApplicationError("backup_checksum")


def _zip_name(name: str) -> None:
    if name in (MANIFEST, DATABASE):
        return
    # Exact existing portable FileAsset grammar also excludes drives, UNC, ADS,
    # backslashes, NUL, dot segments, Windows device names and trailing dots.
    validate_storage_key(name)


def _zip_preflight(stream, limits: BackupLimits) -> None:
    """Bound the central directory before ZipFile allocates its list of entries."""
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    if size > limits.total_bytes + limits.directory_bytes + limits.manifest_bytes:
        raise ApplicationError("backup_limits")
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise ApplicationError("backup_archive_invalid")
    record = struct.unpack_from("<4s4H2IH", tail, offset)
    _, disk, directory_disk, disk_count, count, directory_size, directory_offset, comment = record
    if disk or directory_disk or len(tail) - offset != 22 + comment:
        raise ApplicationError("backup_archive_invalid")
    eocd_position = size - len(tail) + offset
    if count == 65535 or directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF:
        stream.seek(eocd_position - 20)
        locator = stream.read(20)
        if len(locator) != 20:
            raise ApplicationError("backup_archive_invalid")
        signature, disk64, position64, disks = struct.unpack("<4sIQI", locator)
        if signature != b"PK\x06\x07" or disk64 or disks != 1 or position64 >= eocd_position:
            raise ApplicationError("backup_archive_invalid")
        stream.seek(position64)
        raw = stream.read(56)
        if len(raw) != 56:
            raise ApplicationError("backup_archive_invalid")
        (
            signature,
            length,
            _,
            _,
            disk,
            directory_disk,
            disk_count,
            count,
            directory_size,
            directory_offset,
        ) = struct.unpack("<4sQ2H2I4Q", raw)
        if signature != b"PK\x06\x06" or length != 44 or disk or directory_disk:
            raise ApplicationError("backup_archive_invalid")
    if disk_count != count or count > limits.entries or directory_size > limits.directory_bytes:
        raise ApplicationError("backup_limits")
    if directory_offset + directory_size > eocd_position:
        raise ApplicationError("backup_archive_invalid")
    # Do not trust a forged EOCD count. Count bounded central records before
    # ZipFile constructs Python objects (and reject prepended/concatenated ZIPs).
    stream.seek(directory_offset)
    consumed = actual_count = 0
    while consumed < directory_size:
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise ApplicationError("backup_archive_invalid")
        name_length, extra_length, comment_length = struct.unpack_from("<3H", header, 28)
        if not 0 < name_length <= 256:
            raise ApplicationError("backup_archive_unsafe")
        consumed += 46 + name_length + extra_length + comment_length
        actual_count += 1
        if actual_count > limits.entries or consumed > directory_size:
            raise ApplicationError("backup_limits")
        stream.seek(name_length + extra_length + comment_length, os.SEEK_CUR)
    if consumed != directory_size or actual_count != count:
        raise ApplicationError("backup_archive_invalid")
    stream.seek(0)


def _manifest(archive: zipfile.ZipFile, limits: BackupLimits) -> dict:
    seen, total = set(), 0
    for info in archive.infolist():
        _zip_name(info.filename)
        folded = info.filename.casefold()
        mode = info.external_attr >> 16
        if (
            folded in seen
            or info.orig_filename != info.filename
            or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
            or info.external_attr & 0x410
            or info.flag_bits & 1
            or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
        ):
            raise ApplicationError("backup_archive_unsafe")
        seen.add(folded)
        bound = (
            limits.manifest_bytes
            if info.filename == MANIFEST
            else limits.database_bytes
            if info.filename == DATABASE
            else MAX_FILE_BYTES
        )
        total += info.file_size
        if (
            info.file_size > bound
            or total > limits.total_bytes
            or info.file_size > max(info.compress_size, 1) * limits.compression_ratio
        ):
            raise ApplicationError("backup_limits")
    if MANIFEST not in seen or DATABASE not in seen:
        raise ApplicationError("backup_manifest_invalid")

    def unique(pairs):
        values = {}
        for key, value in pairs:
            if key in values:
                raise ApplicationError("backup_manifest_invalid")
            values[key] = value
        return values

    with archive.open(MANIFEST) as source:
        raw = source.read(limits.manifest_bytes + 1)
    if len(raw) > limits.manifest_bytes:
        raise ApplicationError("backup_limits")
    manifest = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(manifest, dict) or set(manifest) != {
        "format",
        "version",
        "app_version",
        "schema_revision",
        "schema_sha256",
        "created_utc",
        "database_size",
        "files",
    }:
        raise ApplicationError("backup_manifest_invalid")
    if (
        manifest["format"] != FORMAT
        or type(manifest["version"]) is not int
        or manifest["version"] != FORMAT_VERSION
    ):
        raise ApplicationError("backup_format_unsupported")
    if (
        manifest["schema_revision"] != SCHEMA_REVISION
        or manifest["schema_sha256"] != _supported_schema_hash()
    ):
        raise ApplicationError("backup_schema_unsupported")
    if not isinstance(manifest["app_version"], str) or not re.fullmatch(
        r"\d+\.\d+\.\d+", manifest["app_version"]
    ):
        raise ApplicationError("backup_manifest_invalid")
    if manifest["app_version"] != __version__:
        raise ApplicationError("backup_format_unsupported")
    created = datetime.fromisoformat(manifest["created_utc"])
    if created.tzinfo is None or created.utcoffset().total_seconds() != 0:
        raise ApplicationError("backup_manifest_invalid")
    if not isinstance(manifest["files"], list) or len(manifest["files"]) + 1 != len(seen):
        raise ApplicationError("backup_manifest_invalid")
    entries = []
    for row in manifest["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "size", "sha256"}:
            raise ApplicationError("backup_manifest_invalid")
        entry = BackupEntry(**row)
        _zip_name(entry.path)
        if (
            entry.path == MANIFEST
            or type(entry.size) is not int
            or entry.size < 0
            or not HASH.fullmatch(entry.sha256)
        ):
            raise ApplicationError("backup_manifest_invalid")
        if archive.getinfo(entry.path).file_size != entry.size:
            raise ApplicationError("backup_checksum")
        entries.append(entry)
    if {e.path for e in entries} != {i.filename for i in archive.infolist()} - {MANIFEST} or len(
        {e.path for e in entries}
    ) != len(entries):
        raise ApplicationError("backup_manifest_invalid")
    database = next(e for e in entries if e.path == DATABASE)
    if type(manifest["database_size"]) is not int or manifest["database_size"] != database.size:
        raise ApplicationError("backup_manifest_invalid")
    manifest["files"] = tuple(entries)
    return manifest


class LocalBackup:
    def __init__(self, paths: AppPaths, *, limits: BackupLimits = BackupLimits()):
        self.paths, self.limits = paths, limits
        self.storage = LocalFileStorage(paths.root)

    @contextmanager
    def _errors(self):
        try:
            yield
        except OSError as error:
            raise file_error(error) from None
        except (
            sqlite3.Error,
            zipfile.BadZipFile,
            EOFError,
            ValueError,
            TypeError,
            KeyError,
            struct.error,
            RuntimeError,
            RecursionError,
        ):
            raise ApplicationError("backup_archive_invalid") from None

    @contextmanager
    def _scratch(self, *, parent: Path | None = None):
        external_path((parent or Path(tempfile.gettempdir())) / "studium-scratch", self.paths.root)
        folder = Path(tempfile.mkdtemp(prefix=".studium-recovery-", dir=parent))
        try:
            yield folder
        finally:
            if folder.exists():

                def retry(function, path, _error):
                    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
                    function(path)

                shutil.rmtree(folder, onexc=retry)

    def _snapshot(self, destination: Path, control: BackupControl) -> None:
        source_path = unlinked_path(self.paths.database_path)
        deadline = time.monotonic() + self.limits.snapshot_seconds
        with _readonly(source_path, control) as source:
            # A read transaction pins the WAL view throughout Online Backup API.
            source.execute("BEGIN")
            source.execute("SELECT count(*) FROM sqlite_master").fetchone()
            with closing(sqlite3.connect(destination)) as target:

                def progress(_status, remaining, pages):
                    control.report("snapshot", pages - remaining, pages)
                    if (
                        pages * source.execute("PRAGMA page_size").fetchone()[0]
                        > self.limits.database_bytes
                    ):
                        raise ApplicationError("backup_limits")
                    if time.monotonic() > deadline:
                        raise ApplicationError("backup_snapshot_busy")

                source.backup(target, pages=256, progress=progress, sleep=0.01)
                target.execute("PRAGMA journal_mode=DELETE")

    def _file(self, path: Path, entry: BackupEntry, control: BackupControl, target=None) -> None:
        unlinked_path(path)
        before_path = file_identity(path)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as source:
            info = os.fstat(source.fileno())
            before = identity(info)
            if not stat.S_ISREG(info.st_mode) or path_identity(info) != before_path:
                raise ApplicationError("backup_source_changed")
            _matches(entry, _stream(source, target, control, limit=entry.size, phase="files"))
            if before != identity(os.fstat(source.fileno())):
                raise ApplicationError("backup_source_changed")
        unlinked_path(path)
        if before_path != file_identity(path):
            raise ApplicationError("backup_source_changed")

    def create(self, destination: Path, control: BackupControl) -> BackupPreview:
        with self._errors():
            destination = external_path(destination, self.paths.root)
            if not destination.parent.is_dir():
                raise ApplicationError("backup_destination_parent")
            prior = file_identity(destination)
            parent_id = identity(destination.parent.stat())[:2]
            control.check()
            with self.storage.backup_guard(), self._scratch() as scratch:
                snapshot = scratch / DATABASE
                self._snapshot(snapshot, control)
                with _readonly(snapshot, control, immutable=True) as connection:
                    _check_database(connection, control)
                    assets = _assets(connection, self.limits)
                    schema_hash = _schema_hash(connection)
                size = snapshot.stat().st_size
                total = size + sum(e.size for e in assets)
                if total > self.limits.total_bytes:
                    raise ApplicationError("backup_limits")
                if shutil.disk_usage(destination.parent).free < total + self.limits.manifest_bytes:
                    raise ApplicationError("file_disk_full")
                with snapshot.open("rb") as source:
                    _, digest = _stream(source, None, control, limit=size, phase="snapshot")
                entries = (BackupEntry(DATABASE, size, digest), *assets)
                original_identities = {
                    entry.path: file_identity(self.storage.controlled_path(entry.path))
                    for entry in assets
                }
                manifest = {
                    "format": FORMAT,
                    "version": FORMAT_VERSION,
                    "app_version": __version__,
                    "schema_revision": SCHEMA_REVISION,
                    "schema_sha256": schema_hash,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "database_size": size,
                    "files": [asdict(e) for e in entries],
                }
                raw = json.dumps(manifest, ensure_ascii=True, indent=2).encode()
                if len(raw) > self.limits.manifest_bytes:
                    raise ApplicationError("backup_limits")
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(
                        prefix=".studium-backup-",
                        suffix=".tmp",
                        dir=destination.parent,
                        delete=False,
                    ) as stream:
                        temporary = Path(stream.name)
                        with zipfile.ZipFile(
                            stream, "w", compression=zipfile.ZIP_STORED, allowZip64=True
                        ) as archive:
                            archive.writestr(MANIFEST, raw)
                            for entry in entries:
                                path = (
                                    snapshot
                                    if entry.path == DATABASE
                                    else self.storage.controlled_path(entry.path)
                                )
                                with archive.open(entry.path, "w", force_zip64=True) as output:
                                    self._file(path, entry, control, output)
                        stream.flush()
                        os.fsync(stream.fileno())
                    preview = self.verify(temporary, control)
                    control.report("publish")
                    # Detect externally modified immutable bytes after packaging too.
                    for entry in assets:
                        self._file(self.storage.controlled_path(entry.path), entry, control)
                    external_path(destination, self.paths.root)
                    for entry in assets:
                        path = self.storage.controlled_path(entry.path)
                        if file_identity(path) != original_identities[entry.path]:
                            raise ApplicationError("backup_source_changed")
                    control.check()
                    if (
                        file_identity(destination) != prior
                        or identity(destination.parent.stat())[:2] != parent_id
                    ):
                        raise ApplicationError("backup_destination_changed")
                    os.replace(temporary, destination)
                    return preview
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)

    def _unpack(self, stream, folder: Path, control: BackupControl) -> BackupPreview:
        before = identity(os.fstat(stream.fileno()))
        _zip_preflight(stream, self.limits)
        with zipfile.ZipFile(stream) as archive:
            manifest = _manifest(archive, self.limits)
            entries = manifest["files"]
            if shutil.disk_usage(folder).free < sum(e.size for e in entries):
                raise ApplicationError("file_disk_full")
            for entry in entries:
                path = folder / entry.path
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry.path) as source, path.open("xb") as output:
                    _matches(
                        entry, _stream(source, output, control, limit=entry.size, phase="verify")
                    )
                    output.flush()
                    os.fsync(output.fileno())
            with _readonly(folder / DATABASE, control, immutable=True) as connection:
                _check_database(connection, control)
                if set(_assets(connection, self.limits)) != {
                    e for e in entries if e.path != DATABASE
                }:
                    raise ApplicationError("backup_file_invalid")
            # Independently check materialized bytes, not just the incoming stream.
            for entry in entries:
                self._file(folder / entry.path, entry, control)
        stream.seek(0)
        _, digest = _stream(
            stream,
            None,
            control,
            limit=self.limits.total_bytes
            + self.limits.directory_bytes
            + self.limits.manifest_bytes,
            phase="archive_check",
        )
        if before != identity(os.fstat(stream.fileno())):
            raise ApplicationError("backup_source_changed")
        return BackupPreview(
            manifest["created_utc"],
            manifest["app_version"],
            manifest["schema_revision"],
            manifest["database_size"],
            entries,
            digest,
        )

    def verify(self, archive: Path, control: BackupControl) -> BackupPreview:
        with self._errors():
            archive = external_path(archive, self.paths.root)
            control.check()
            with self._archive_stream(archive) as stream, self._scratch() as scratch:
                return self._unpack(stream, scratch, control)

    @contextmanager
    def _archive_stream(self, path: Path):
        unlinked_path(path)
        before = file_identity(path)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or path_identity(info) != before:
                raise ApplicationError("backup_source_changed")
            yield stream
        unlinked_path(path)
        if file_identity(path) != before:
            raise ApplicationError("backup_source_changed")

    def restore(
        self, archive: Path, destination: Path, preview: BackupPreview, control: BackupControl
    ) -> Path:
        with self._errors():
            destination = empty_destination(destination, self.paths.root)
            existed = destination.exists()
            destination_id = identity(destination.stat())[:2] if existed else None
            parent_id = identity(destination.parent.stat())[:2]
            archive = external_path(archive, self.paths.root)
            # Verification finishes before destination/staging writes begin.
            verified = self.verify(archive, control)
            if verified != preview:
                raise ApplicationError("backup_source_changed")
            with self._scratch(parent=destination.parent) as stage:
                with self._archive_stream(archive) as stream:
                    if self._unpack(stream, stage, control) != preview:
                        raise ApplicationError("backup_source_changed")
                for entry in preview.files:
                    if entry.path != DATABASE:
                        (stage / entry.path).chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                (stage / "files").mkdir(exist_ok=True)
                control.report("publish")
                empty_destination(destination, self.paths.root)
                current_id = identity(destination.stat())[:2] if destination.exists() else None
                if (
                    current_id != destination_id
                    or identity(destination.parent.stat())[:2] != parent_id
                ):
                    raise ApplicationError("backup_destination_changed")
                # rmdir can remove only the selected empty root; never production.
                # Windows cannot replace even an empty directory with rename.
                if existed:
                    destination.rmdir()
                try:
                    os.rename(stage, destination)
                except OSError:
                    if existed and not destination.exists():
                        destination.mkdir()
                    raise
                return destination

    def diagnose(self, control: BackupControl) -> StorageHealth:
        with self._errors(), self.storage.backup_guard(), self._scratch() as scratch:
            snapshot = scratch / DATABASE
            self._snapshot(snapshot, control)
            with _readonly(snapshot, control, immutable=True) as connection:
                schema = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                database_ok = True
                try:
                    _check_database(connection, control)
                except ApplicationError as error:
                    if str(error) == "backup_cancelled":
                        raise
                    database_ok = False
                assets = _assets(connection, self.limits)
            missing = damaged = 0
            for entry in assets:
                try:
                    self._file(self.storage.controlled_path(entry.path), entry, control)
                except FileNotFoundError:
                    missing += 1
                except ApplicationError as error:
                    if str(error) == "backup_cancelled":
                        raise
                    damaged += 1
            try:
                free = shutil.disk_usage(self.paths.root).free
            except OSError:
                free = None
            return StorageHealth(
                str(self.paths.root),
                schema,
                snapshot.stat().st_size,
                len(assets),
                sum(e.size for e in assets),
                database_ok,
                missing,
                damaged,
                free,
            )
