"""Only synthetic facts and external temporary roots; hostile ZIPs never touch production."""

import errno
import hashlib
import json
import os
import sqlite3
import stat
import struct
import tempfile
import warnings
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from studium.application.backup import BackupControl, BackupEntry
from studium.application.errors import ApplicationError
from studium.application.services import GradeInput
from studium.composition import create_runtime
from studium.domain.enums import AssessmentType, AttemptResult, AttendanceStatus, GradeKind
from studium.domain.value_objects import LocalDate, UtcInstant
from studium.infrastructure import backup as implementation
from studium.infrastructure.backup import DATABASE, MANIFEST, LocalBackup
from studium.infrastructure.backup_paths import file_identity
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.user_data import AppPaths
from tests.integration.test_reporting import database_facts


def tree_bytes(root):
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode))
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.fixture
def backup_data(tmp_path):
    root = tmp_path / "active"
    runtime = create_runtime(root)
    s = runtime.service
    term = s.create_term("Synthetic term", LocalDate(2026, 9, 1), LocalDate(2027, 1, 31))
    course, group = s.create_course("Synthetic course"), s.create_group("Synthetic group")
    offering = s.create_offering(term.id, course.id, group.id)
    student = s.create_student(offering.id, "Synthetic Student", "Synthetic private note")
    assessment = s.create_assessment(offering.id, "Synthetic assessment", AssessmentType.HOMEWORK)
    work = s.get_or_create_work(student.id, assessment.id)
    attempt = s.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
    s.add_attempt(
        work.id,
        UtcInstant.now(),
        AttemptResult.ACCEPTED,
        score=7,
        max_score=10,
        grade=GradeInput(GradeKind.NUMERIC),
    )
    s.update_student(student, full_name="Synthetic revised name")
    lesson = s.create_lesson(offering.id, LocalDate(2026, 9, 1))
    enrollment = s._r.enrollments.for_offering(offering.id)[0]
    attendance = s.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.LATE)
    s.mark_attendance(lesson.id, enrollment.id, AttendanceStatus.PRESENT, original=attendance)
    case = s.create_question_case(student.id, "Synthetic question", UtcInstant.now())
    message = s.list_messages(case.id)[0]
    assets = []
    for number in range(3):
        source = tmp_path / f"synthetic-{number}.txt"
        source.write_bytes((f"Synthetic immutable bytes {number}\n" * 500).encode())
        link = s.import_file_for_attempt(attempt.id, source)
        assets.append(s.get_file_asset(link.file_asset_id))
        if number == 0:
            s.attach_file_asset_to_message(message.id, link.file_asset_id)
        if number == 2:
            s.detach_attachment(link.id, expected_revision=link.revision)
            s.archive_file_asset(link.file_asset_id, expected_revision=1)
            assets[-1] = s.get_file_asset(link.file_asset_id, include_deleted=True)
    for name in ("cache/thumbnail.txt", "logs/synthetic.log", "temp/partial.tmp"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic excluded bytes")
    backend = LocalBackup(AppPaths(root))
    archive = tmp_path / "synthetic-backup.zip"
    yield SimpleNamespace(
        runtime=runtime,
        s=s,
        root=root,
        backend=backend,
        archive=archive,
        assets=assets,
        destination=tmp_path / "restored",
        offering_id=offering.id.value,
    )
    runtime.close()


@pytest.fixture(autouse=True)
def scratch_cleanup():
    root = Path(tempfile.gettempdir())
    before = set(root.glob(".studium-recovery-*")) | set(root.glob("studium-schema-*"))
    yield
    assert (set(root.glob(".studium-recovery-*")) | set(root.glob("studium-schema-*"))) == before


def create(data):
    return data.backend.create(data.archive, BackupControl())


@pytest.mark.parametrize("operation", ["file", "archive"])
def test_windows_creation_and_change_times_are_distinct_without_source_change(
    tmp_path, monkeypatch, operation
):
    """CPython Windows stat uses creation time; fstat uses metadata change time."""
    path = tmp_path / "synthetic.txt"
    raw = b"Synthetic stable bytes"
    path.write_bytes(raw)
    backend = LocalBackup(AppPaths(tmp_path / "active"))
    path_stat, descriptor_stat = Path.stat, os.fstat

    def timestamps(info, ctime):
        return SimpleNamespace(
            **{
                name: getattr(info, name)
                for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
            },
            st_birthtime_ns=100,
            st_ctime_ns=ctime,
        )

    def by_path(value, *args, **kwargs):
        info = path_stat(value, *args, **kwargs)
        return timestamps(info, 100) if value == path else info

    monkeypatch.setattr(Path, "stat", by_path)
    monkeypatch.setattr(os, "fstat", lambda fd: timestamps(descriptor_stat(fd), 200))
    if operation == "file":
        backend._file(
            path,
            BackupEntry("synthetic.txt", len(raw), hashlib.sha256(raw).hexdigest()),
            BackupControl(),
        )
    else:
        with backend._archive_stream(path) as stream:
            assert stream.read() == raw
    assert path.read_bytes() == raw


def test_native_file_path_and_descriptor_timestamps_remain_compatible(tmp_path):
    path = tmp_path / "synthetic.txt"
    path.write_bytes(b"Synthetic bytes")
    # Ensure metadata change time differs from creation on Windows NTFS.
    os.utime(path, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    backend = LocalBackup(AppPaths(tmp_path / "active"))
    before = file_identity(path)
    with backend._archive_stream(path) as stream:
        assert stream.read() == b"Synthetic bytes"
    assert file_identity(path) == before


def test_descriptor_metadata_change_is_still_rejected_with_stable_creation_time(
    tmp_path, monkeypatch
):
    path = tmp_path / "synthetic.txt"
    raw = b"Synthetic bytes"
    path.write_bytes(raw)
    backend = LocalBackup(AppPaths(tmp_path / "active"))
    descriptor_stat = os.fstat
    changed = False

    def by_descriptor(fd):
        info = descriptor_stat(fd)
        return SimpleNamespace(
            **{
                name: getattr(info, name)
                for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
            },
            st_birthtime_ns=file_identity(path)[-1],
            st_ctime_ns=200 if changed else 100,
        )

    def metadata_change(*_):
        nonlocal changed
        changed = True

    monkeypatch.setattr(os, "fstat", by_descriptor)
    with pytest.raises(ApplicationError, match="backup_source_changed"):
        backend._file(
            path,
            BackupEntry("synthetic.txt", len(raw), hashlib.sha256(raw).hexdigest()),
            BackupControl(metadata_change),
        )
    assert changed and path.read_bytes() == raw


def rewrite(data, mutate):
    create(data)
    with zipfile.ZipFile(data.archive) as archive:
        entries = [(i, archive.read(i)) for i in archive.infolist()]
    changed = mutate(entries)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(data.archive, "w") as archive:
            for info, raw in changed:
                archive.writestr(info, raw)


def change_manifest(entries, mutate):
    result = []
    for info, raw in entries:
        if info.filename == MANIFEST:
            values = json.loads(raw)
            mutate(values)
            raw = json.dumps(values).encode()
        result.append((info, raw))
    return result


def assert_rejected_unchanged(data):
    before = tree_bytes(data.root)
    facts = database_facts(data.runtime._engine)
    with pytest.raises(ApplicationError):
        data.backend.verify(data.archive, BackupControl())
    assert tree_bytes(data.root) == before
    assert database_facts(data.runtime._engine) == facts
    assert not data.destination.exists()
    assert not list(data.archive.parent.glob(".studium-*"))


def test_complete_backup_verify_restore_preserves_every_fact_schema_and_byte(backup_data):
    d = backup_data
    facts = database_facts(d.runtime._engine)
    before = tree_bytes(d.root)
    preview = create(d)
    assert tree_bytes(d.root) == before
    assert d.backend.verify(d.archive, BackupControl()) == preview
    assert tree_bytes(d.root) == before
    assert preview.file_count == 3 and preview.database_size > 0
    assert preview.total_size == preview.database_size + sum(a.size_bytes for a in d.assets)
    assert preview.created_utc.endswith("+00:00")
    with zipfile.ZipFile(d.archive) as archive:
        assert set(archive.namelist()) == {MANIFEST, DATABASE, *(a.storage_key for a in d.assets)}
        manifest = archive.read(MANIFEST).decode()
        for private in (
            "Synthetic Student",
            "Synthetic revised name",
            "Synthetic private note",
            "Synthetic group",
            "Synthetic course",
        ):
            assert private not in manifest
        assert all(a.original_filename not in manifest for a in d.assets)
    d.destination.mkdir()
    assert d.backend.restore(d.archive, d.destination, preview, BackupControl()) == d.destination
    assert tree_bytes(d.root) == before
    assert database_facts(d.runtime._engine) == facts
    recovered = create_runtime(d.destination)
    try:
        assert database_facts(recovered._engine) == facts
        assert recovered.diagnostics.schema_version == d.runtime.diagnostics.schema_version
        for asset in d.assets:
            assert recovered.service.get_file_asset(asset.id, include_deleted=True) == asset
            path = d.destination / asset.storage_key
            assert path.read_bytes() == (d.root / asset.storage_key).read_bytes()
            assert not path.stat().st_mode & stat.S_IWRITE
        assert not (d.destination / "cache").exists()
        assert not (d.destination / MANIFEST).exists()
    finally:
        recovered.close()


def test_pinned_wal_snapshot_allows_concurrent_fact_commit(backup_data):
    d = backup_data
    with sqlite3.connect(d.root / DATABASE) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert (d.root / (DATABASE + "-wal")).stat().st_size > 0
    old = database_facts(d.runtime._engine)
    changed = False

    def progress(phase, *_):
        nonlocal changed
        if phase == "snapshot" and not changed:
            changed = True
            d.s.create_course("Synthetic concurrent fact")

    preview = d.backend.create(d.archive, BackupControl(progress))
    assert changed and database_facts(d.runtime._engine) != old
    d.backend.restore(d.archive, d.destination, preview, BackupControl())
    restored = create_runtime(d.destination)
    try:
        assert database_facts(restored._engine) == old
    finally:
        restored.close()


@pytest.mark.parametrize("fault", ["missing", "damaged", "symlink"])
def test_managed_file_faults_do_not_publish_or_modify_source(backup_data, fault):
    d = backup_data
    path = d.root / d.assets[0].storage_key
    path.chmod(stat.S_IREAD | stat.S_IWRITE)
    if fault == "missing":
        path.unlink()
    elif fault == "damaged":
        path.write_bytes(b"Synthetic damage")
    else:
        path.unlink()
        path.symlink_to(d.archive.parent / "synthetic-0.txt")
    before = tree_bytes(d.root)
    d.archive.write_bytes(b"Previous synthetic backup sentinel")
    with pytest.raises(ApplicationError):
        create(d)
    assert d.archive.read_bytes() == b"Previous synthetic backup sentinel"
    assert tree_bytes(d.root) == before
    assert not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.parametrize("phase", ["files", "verify", "publish"])
def test_external_file_mutation_during_backup_is_rejected(backup_data, phase):
    d = backup_data
    changed = False

    def mutate(current, *_):
        nonlocal changed
        if current == phase and not changed:
            changed = True
            path = d.root / d.assets[0].storage_key
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
            path.write_bytes(b"Synthetic mutation")

    with pytest.raises(ApplicationError):
        d.backend.create(d.archive, BackupControl(mutate))
    assert not d.archive.exists() and not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.parametrize("name", ["unfinished.json", "unfinished.tmp", "unexpected"])
def test_pending_import_is_refused_without_recovery_or_cleanup(backup_data, name):
    d = backup_data
    (d.root / "files/.imports" / name).write_text("Synthetic pending journal")
    before = tree_bytes(d.root)
    with pytest.raises(ApplicationError, match="backup_pending_import"):
        create(d)
    assert tree_bytes(d.root) == before and not d.archive.exists()


def test_concurrent_import_uses_same_lock_and_is_refused(backup_data):
    d = backup_data
    with d.backend.storage.backup_guard():
        with pytest.raises(ApplicationError, match="file_storage_busy"):
            d.backend.storage.backup_guard().__enter__()
        with pytest.raises(ApplicationError, match="file_storage_busy"):
            with LocalFileStorage(d.root)._lock():
                pytest.fail("import acquired a held backup lock")


@pytest.mark.windows
@pytest.mark.skipif(os.name != "nt", reason="Native Windows sharing lock")
def test_windows_locked_destination_preserves_previous_backup_and_source(backup_data):
    import ctypes
    from ctypes import wintypes

    d = backup_data
    create(d)
    previous, before = d.archive.read_bytes(), tree_bytes(d.root)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    open_file = kernel.CreateFileW
    open_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    open_file.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes, close.restype = (wintypes.HANDLE,), wintypes.BOOL
    # Allow readers/writers but deny FILE_SHARE_DELETE, preventing atomic replace.
    handle = open_file(str(d.archive), 0x80000000, 0x3, None, 3, 0x80, None)
    assert handle != wintypes.HANDLE(-1).value, "Synthetic sharing lock could not be acquired"
    try:
        with pytest.raises(ApplicationError, match="file_permission"):
            create(d)
    finally:
        assert close(handle), "Synthetic sharing lock could not be released"
    assert d.archive.read_bytes() == previous and tree_bytes(d.root) == before
    assert not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("format", "unknown"),
        ("version", 99),
        ("version", True),
        ("schema_revision", "9999_unknown"),
        ("schema_sha256", "0" * 64),
        ("app_version", "99.0.0"),
        ("created_utc", "2026-10-08"),
        ("database_size", 0),
    ],
)
def test_unknown_or_incompatible_manifest_is_rejected(backup_data, field, value):
    rewrite(
        backup_data, lambda entries: change_manifest(entries, lambda v: v.update({field: value}))
    )
    assert_rejected_unchanged(backup_data)


@pytest.mark.parametrize(
    "fault", ["hash", "size", "duplicate", "unexpected", "no_sqlite", "db_metadata"]
)
def test_manifest_tampering_and_missing_required_entries(backup_data, fault):
    def mutate(entries):
        if fault == "unexpected":
            return entries + [(zipfile.ZipInfo("unexpected.txt"), b"Synthetic")]
        if fault == "no_sqlite":
            return [(i, b) for i, b in entries if i.filename != DATABASE]

        def alter(values):
            if fault == "hash":
                values["files"][0]["sha256"] = "0" * 64
            elif fault == "size":
                values["files"][0]["size"] += 1
            elif fault == "duplicate":
                values["files"][1] = values["files"][0]
            else:
                values["files"][1]["sha256"] = "0" * 64

        return change_manifest(entries, alter)

    rewrite(backup_data, mutate)
    assert_rejected_unchanged(backup_data)


@pytest.mark.parametrize("fault", ["truncated", "garbage", "crc", "sqlite"])
def test_corrupt_zip_and_database_are_rejected(backup_data, fault):
    d = backup_data
    create(d)
    if fault in {"truncated", "garbage"}:
        raw = d.archive.read_bytes()
        d.archive.write_bytes(
            raw[: len(raw) // 2] if fault == "truncated" else b"Synthetic garbage"
        )
    elif fault == "crc":
        raw = bytearray(d.archive.read_bytes())
        raw[100] ^= 0xFF
        d.archive.write_bytes(raw)
    else:

        def corrupt(entries):
            changed = [
                (i, b"Synthetic invalid SQLite" if i.filename == DATABASE else b)
                for i, b in entries
            ]
            return change_manifest(
                changed,
                lambda m: (
                    m.update(database_size=24),
                    m["files"][0].update(
                        size=24, sha256=hashlib.sha256(b"Synthetic invalid SQLite").hexdigest()
                    ),
                ),
            )

        rewrite(d, corrupt)
    assert_rejected_unchanged(d)


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "C:/drive",
        "C:\\drive",
        "//server/share",
        "files/../escape",
        "files/device:ads",
        "files/NUL",
        "studium.sqlite/child",
    ],
)
def test_zip_slip_absolute_drive_unc_and_windows_names(backup_data, name):
    rewrite(backup_data, lambda entries: entries + [(zipfile.ZipInfo(name), b"Synthetic unsafe")])
    assert_rejected_unchanged(backup_data)


@pytest.mark.parametrize("fault", ["duplicate", "casefold", "symlink", "directory", "reparse"])
def test_zip_aliases_symlinks_and_junction_attributes(backup_data, fault):
    def mutate(entries):
        if fault in {"duplicate", "casefold"}:
            info, raw = entries[0]
            name = info.filename if fault == "duplicate" else info.filename.upper()
            return entries + [(zipfile.ZipInfo(name), raw)]
        info, raw = entries[0]
        info.external_attr = {
            "symlink": (stat.S_IFLNK | 0o777) << 16,
            "directory": (stat.S_IFDIR | 0o700) << 16,
            "reparse": 0x400,
        }[fault]
        return entries

    rewrite(backup_data, mutate)
    assert_rejected_unchanged(backup_data)


@pytest.mark.parametrize(
    "limit", ["entries", "total_bytes", "manifest_bytes", "directory_bytes", "database_bytes"]
)
def test_zip_resource_limits_are_enforced(backup_data, limit):
    d = backup_data
    create(d)
    d.backend.limits = replace(d.backend.limits, **{limit: 1})
    assert_rejected_unchanged(d)


def test_compression_bomb_is_rejected_before_extraction(backup_data):
    d = backup_data
    create(d)
    with zipfile.ZipFile(d.archive, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("files/00/00000000-0000-0000-0000-000000000000.txt", b"0" * 2_000_000)
    assert_rejected_unchanged(d)


def test_forged_central_directory_count_is_rejected(backup_data):
    d = backup_data
    create(d)
    raw = bytearray(d.archive.read_bytes())
    end = raw.rfind(b"PK\x05\x06")
    struct.pack_into("<2H", raw, end + 8, 1, 1)
    d.archive.write_bytes(raw)
    assert_rejected_unchanged(d)


def test_zip64_directory_metadata_is_supported_without_large_allocations(backup_data):
    d = backup_data
    create(d)
    raw = bytearray(d.archive.read_bytes())
    end = raw.rfind(b"PK\x05\x06")
    _, _, _, _, count, size, offset, _ = struct.unpack_from("<4s4H2IH", raw, end)
    eocd = raw[end:]
    struct.pack_into("<2H2I", eocd, 8, 65535, 65535, 0xFFFFFFFF, 0xFFFFFFFF)
    zip64 = struct.pack("<4sQ2H2I4Q", b"PK\x06\x06", 44, 45, 45, 0, 0, count, count, size, offset)
    locator = struct.pack("<4sIQI", b"PK\x06\x07", 0, end, 1)
    d.archive.write_bytes(raw[:end] + zip64 + locator + eocd)
    assert d.backend.verify(d.archive, BackupControl()).file_count == 3


def test_duplicate_json_keys_in_manifest_are_rejected(backup_data):
    def mutate(entries):
        return [
            (
                i,
                b.replace(b'"format":', b'"format": "unknown", "format":', 1)
                if i.filename == MANIFEST
                else b,
            )
            for i, b in entries
        ]

    rewrite(backup_data, mutate)
    assert_rejected_unchanged(backup_data)


@pytest.mark.parametrize("fault", ["bytes_and_hash", "omitted_asset"])
def test_valid_zip_checksums_cannot_hide_mismatch_with_fileasset_metadata(backup_data, fault):
    d = backup_data
    asset = d.assets[0]

    def mutate(entries):
        replacement = b"Synthetic forged bytes"
        changed = [
            (i, replacement if i.filename == asset.storage_key else b)
            for i, b in entries
            if fault != "omitted_asset" or i.filename != asset.storage_key
        ]

        def manifest(values):
            if fault == "omitted_asset":
                values["files"] = [e for e in values["files"] if e["path"] != asset.storage_key]
            else:
                entry = next(e for e in values["files"] if e["path"] == asset.storage_key)
                entry.update(size=len(replacement), sha256=hashlib.sha256(replacement).hexdigest())

        return change_manifest(changed, manifest)

    rewrite(d, mutate)
    assert_rejected_unchanged(d)


def test_foreign_key_violation_is_rejected_even_with_valid_hashes_and_integrity(
    backup_data, tmp_path
):
    d = backup_data

    def mutate(entries):
        result = []
        digest = None
        for info, content in entries:
            if info.filename == DATABASE:
                isolated = tmp_path / "synthetic-fk.sqlite"
                isolated.write_bytes(content)
                with sqlite3.connect(isolated) as connection:
                    page = connection.execute(
                        "SELECT rootpage FROM sqlite_master WHERE name='enrollments'"
                    ).fetchone()[0]
                    page_size = connection.execute("PRAGMA page_size").fetchone()[0]
                # Change a fixed-width FK directly in a synthetic leaf page, keeping
                # schema/triggers unchanged. No live DB or SQL guards are bypassed.
                raw = bytearray(content)
                start = (page - 1) * page_size
                position = raw.find(d.offering_id.encode(), start, start + page_size)
                assert position >= 0
                raw[position : position + 36] = b"ffffffff-ffff-ffff-ffff-ffffffffffff"
                content = bytes(raw)
                isolated.write_bytes(content)
                with sqlite3.connect(isolated) as connection:
                    connection.execute("REINDEX enrollments")
                    assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
                    assert connection.execute("PRAGMA foreign_key_check").fetchall()
                content = isolated.read_bytes()
                digest = hashlib.sha256(content).hexdigest()
            result.append((info, content))
        return change_manifest(result, lambda m: m["files"][0].update(sha256=digest))

    rewrite(d, mutate)
    with pytest.raises(ApplicationError, match="backup_database_invalid"):
        d.backend.verify(d.archive, BackupControl())
    assert_rejected_unchanged(d)


def test_schema_spoof_with_supported_revision_is_rejected(backup_data, tmp_path):
    d = backup_data

    def mutate(entries):
        result, size, digest = [], 0, None
        for info, content in entries:
            if info.filename == DATABASE:
                path = tmp_path / "synthetic-spoof.sqlite"
                path.write_bytes(content)
                with sqlite3.connect(path) as connection:
                    connection.execute("CREATE TABLE synthetic_unexpected(value TEXT)")
                content = path.read_bytes()
                size, digest = len(content), hashlib.sha256(content).hexdigest()
            result.append((info, content))
        return change_manifest(
            result,
            lambda m: (
                m.update(database_size=size),
                m["files"][0].update(size=size, sha256=digest),
            ),
        )

    rewrite(d, mutate)
    assert_rejected_unchanged(d)


@pytest.mark.parametrize("operation", ["create", "verify", "restore"])
@pytest.mark.parametrize("phase", ["snapshot", "files", "verify", "publish"])
def test_cancellation_never_leaves_partial_structure(backup_data, operation, phase):
    d = backup_data
    preview = create(d)
    prior = d.archive.read_bytes()
    before = tree_bytes(d.root)
    control = BackupControl(lambda current, *_: control.cancel() if current == phase else None)
    # Phases that do not belong to an operation use cancellation before start.
    if operation == "verify" and phase in {"snapshot", "publish"}:
        control.cancel()
    if operation == "restore" and phase == "snapshot":
        control.cancel()
    with pytest.raises(ApplicationError, match="backup_cancelled"):
        if operation == "create":
            d.backend.create(d.archive, control)
        elif operation == "verify":
            d.backend.verify(d.archive, control)
        else:
            d.backend.restore(d.archive, d.destination, preview, control)
    assert d.archive.read_bytes() == prior
    assert tree_bytes(d.root) == before and not d.destination.exists()
    assert not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.parametrize("fault", ["permission", "disk_full", "publish", "free_space"])
def test_backup_write_failures_preserve_previous_archive(backup_data, monkeypatch, fault):
    d = backup_data
    create(d)
    prior, before = d.archive.read_bytes(), tree_bytes(d.root)
    if fault == "free_space":
        monkeypatch.setattr(implementation.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    elif fault == "publish":
        monkeypatch.setattr(
            implementation.os,
            "replace",
            lambda *_: (_ for _ in ()).throw(OSError(errno.EACCES, "Synthetic denied")),
        )
    else:
        original = zipfile.ZipFile.open

        def denied(self, name, mode="r", *args, **kwargs):
            if mode == "w":
                raise OSError(
                    errno.ENOSPC if fault == "disk_full" else errno.EACCES,
                    "Synthetic write failure",
                )
            return original(self, name, mode, *args, **kwargs)

        monkeypatch.setattr(zipfile.ZipFile, "open", denied)
    with pytest.raises(ApplicationError):
        create(d)
    assert d.archive.read_bytes() == prior and tree_bytes(d.root) == before
    assert not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.parametrize("fault", ["write", "rename", "changed_archive", "checksum"])
def test_restore_failure_has_no_partial_root(backup_data, monkeypatch, fault):
    d = backup_data
    preview = create(d)
    d.destination.mkdir()
    before = tree_bytes(d.root)
    if fault == "changed_archive":
        with zipfile.ZipFile(d.archive, "a") as archive:
            archive.comment = b"Synthetic changed after preview"
    elif fault == "rename":
        monkeypatch.setattr(
            implementation.os,
            "rename",
            lambda *_: (_ for _ in ()).throw(OSError(errno.EACCES, "Synthetic denied")),
        )
    elif fault == "write":
        original = Path.open

        def fail_stage(self, *args, **kwargs):
            if (
                self.is_relative_to(d.destination.parent)
                and ".studium-recovery-" in str(self)
                and args
                and args[0] == "xb"
            ):
                raise OSError(errno.ENOSPC, "Synthetic staging failure")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "open", fail_stage)
    else:
        original = d.backend._file

        def corrupt_stage(path, entry, control, target=None):
            if path.parent.parent.parent.parent == d.destination.parent and entry.path != DATABASE:
                path.write_bytes(b"Synthetic post-extraction damage")
            return original(path, entry, control, target)

        monkeypatch.setattr(d.backend, "_file", corrupt_stage)
    with pytest.raises(ApplicationError):
        d.backend.restore(d.archive, d.destination, preview, BackupControl())
    assert list(d.destination.iterdir()) == []
    assert tree_bytes(d.root) == before and not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.parametrize("operation", ["create", "restore"])
@pytest.mark.parametrize("target", ["git_dir", "git_file", "active", "nonempty", "symlink"])
def test_destination_guards_before_side_effects(backup_data, tmp_path, operation, target):
    d = backup_data
    preview = create(d)
    directory = tmp_path / "selected"
    directory.mkdir()
    if target.startswith("git"):
        if target == "git_dir":
            (directory / ".git").mkdir()
        else:
            (directory / ".git").write_text("gitdir: synthetic-worktree")
    elif target == "active":
        directory = d.root
    elif target == "nonempty":
        (directory / "sentinel.txt").write_text("Synthetic preserved")
        if operation == "create":
            return  # Backup replaces a file selected with Save, not a directory.
    else:
        link = tmp_path / "linked"
        link.symlink_to(directory, target_is_directory=True)
        directory = link
    before = tree_bytes(d.root), tree_bytes(directory)
    with pytest.raises(ApplicationError):
        if operation == "create":
            d.backend.create(directory / "unsafe.zip", BackupControl())
        else:
            d.backend.restore(d.archive, directory, preview, BackupControl())
    assert (tree_bytes(d.root), tree_bytes(directory)) == before


def test_diagnostics_counts_integrity_and_missing_damaged_files(backup_data):
    d = backup_data
    before = tree_bytes(d.root)
    health = d.backend.diagnose(BackupControl())
    assert tree_bytes(d.root) == before
    assert health.database_ok and health.file_count == 3
    assert health.file_size == sum(a.size_bytes for a in d.assets)
    assert health.missing_files == health.damaged_files == 0
    first, second = [d.root / a.storage_key for a in d.assets[:2]]
    first.chmod(stat.S_IREAD | stat.S_IWRITE)
    first.unlink()
    second.chmod(stat.S_IREAD | stat.S_IWRITE)
    second.write_bytes(b"Synthetic damage")
    before = tree_bytes(d.root)
    health = d.backend.diagnose(BackupControl())
    assert health.missing_files == health.damaged_files == 1
    assert tree_bytes(d.root) == before


def test_multichunk_file_roundtrip_is_streamed_and_immutable(backup_data, tmp_path):
    d = backup_data
    source = tmp_path / "synthetic-large.txt"
    block = b"Synthetic bounded block\n" * 50_000
    with source.open("wb") as stream:
        for _ in range(4):
            stream.write(block)
    attempt = d.s._r.attempts.history(d.s._r.works.list()[0].id)[0]
    link = d.s.import_file_for_attempt(attempt.id, source)
    asset = d.s.get_file_asset(link.file_asset_id)
    progress = []
    preview = d.backend.create(
        d.archive, BackupControl(lambda phase, n, total: progress.append((phase, n, total)))
    )
    assert any(
        phase == "files" and 0 < n < asset.size_bytes and total == asset.size_bytes
        for phase, n, total in progress
    )
    d.backend.restore(d.archive, d.destination, preview, BackupControl())
    with (d.destination / asset.storage_key).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert (
        digest == asset.sha256
        and (d.destination / asset.storage_key).stat().st_size == asset.size_bytes
    )


def test_archive_modified_during_verification_is_refused(backup_data):
    d = backup_data
    create(d)
    before = tree_bytes(d.root)
    changed = False

    def mutate(phase, *_):
        nonlocal changed
        if phase == "archive_check" and not changed:
            changed = True
            with d.archive.open("ab") as stream:
                stream.write(b"Synthetic concurrent archive mutation")

    with pytest.raises(ApplicationError, match="backup_source_changed"):
        d.backend.verify(d.archive, BackupControl(mutate))
    assert tree_bytes(d.root) == before


def test_snapshot_deadline_failure_preserves_active_data_and_previous_backup(backup_data):
    d = backup_data
    create(d)
    prior, before = d.archive.read_bytes(), tree_bytes(d.root)
    d.backend.limits = replace(d.backend.limits, snapshot_seconds=0)
    with pytest.raises(ApplicationError, match="backup_snapshot_busy"):
        create(d)
    assert d.archive.read_bytes() == prior and tree_bytes(d.root) == before
    assert not list(d.archive.parent.glob(".studium-*"))


@pytest.mark.windows
@pytest.mark.skipif(os.name != "nt", reason="Native Windows junction")
def test_windows_junction_destination_is_refused(backup_data, tmp_path):
    import subprocess

    d = backup_data
    selected = tmp_path / "junction"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(selected), str(d.root)], check=True, capture_output=True
    )
    try:
        with pytest.raises(ApplicationError, match="backup_unsafe_path"):
            d.backend.create(selected / "unsafe.zip", BackupControl())
    finally:
        selected.rmdir()
