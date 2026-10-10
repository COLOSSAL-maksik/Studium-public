import errno
import hashlib
import json
import stat
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity
from studium.composition import create_runtime
from studium.domain.entities import AttemptAttachment
from studium.domain.enums import AttemptResult
from studium.domain.repositories import RepositoryError, RepositoryFailure
from studium.domain.value_objects import EntityId, EntityMetadata, UtcInstant
from tests.integration.test_application import runtime as runtime
from tests.integration.test_application import workflow as workflow


@pytest.fixture
def files(workflow, runtime, tmp_path):
    service, _, _, _, offering, student, assessment, work = workflow
    attempt = service.add_attempt(work.id, UtcInstant.now(), AttemptResult.NEEDS_REVISION)
    source = tmp_path / "исходник.txt"
    source.write_bytes(b"Synthetic source; never real student data\n")
    return SimpleNamespace(
        runtime=runtime,
        s=service,
        offering=offering,
        student=student,
        assessment=assessment,
        work=work,
        attempt=attempt,
        source=source,
        root=tmp_path,
    )


def imported(f):
    link = f.s.import_file_for_attempt(f.attempt.id, f.source, caption="Synthetic")
    return link, f.s.get_file_asset(link.file_asset_id)


def originals(f):
    return [
        path
        for path in (f.root / "files").rglob("*")
        if path.is_file() and ".imports" not in path.parts
    ]


def test_import_source_unchanged_hash_and_relative_uuid_key(files):
    f = files
    before = f.source.read_bytes(), f.source.stat().st_mtime_ns
    link, asset = imported(f)
    assert (f.source.read_bytes(), f.source.stat().st_mtime_ns) == before
    assert asset.sha256 == hashlib.sha256(before[0]).hexdigest()
    assert asset.size_bytes == len(before[0])
    assert not Path(asset.storage_key).is_absolute()
    assert asset.original_filename == f.source.name
    assert Path(asset.storage_key).name != f.source.name
    assert asset.id.value in asset.storage_key
    assert f.s.accessible_file_path(asset.id).read_bytes() == before[0]
    assert link.attempt_id == f.attempt.id
    assert not f.s.accessible_file_path(asset.id).stat().st_mode & stat.S_IWRITE
    assert list((f.root / "files/.imports").glob("*.json")) == []


def test_multiple_and_duplicate_imports_keep_separate_assets(files):
    f = files
    first, a = imported(f)
    second, b = imported(f)
    assert a.id != b.id and a.storage_key != b.storage_key and a.sha256 == b.sha256
    assert [entry.attachment.id for entry in f.s.list_attempt_attachments(f.attempt.id)] == [
        first.id,
        second.id,
    ]
    assert [
        entry.attachment.sort_order for entry in f.s.list_attempt_attachments(f.attempt.id)
    ] == [0, 1]


def test_attempt_versions_and_student_aggregation(files):
    f = files
    first, a = imported(f)
    attempt2 = f.s.add_attempt(f.work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    second = f.s.import_file_for_attempt(attempt2.id, f.source)
    other_assessment = f.s.create_assessment(f.offering.id, "Second work", f.assessment.type)
    other_work = f.s.get_or_create_work(f.student.id, other_assessment.id)
    attempt3 = f.s.add_attempt(other_work.id, UtcInstant.now(), AttemptResult.PRESENTED)
    f.s.import_file_for_attempt(attempt3.id, f.source)
    rows = f.s.list_student_files(f.student.id)
    assert len(rows) == 3
    assert {row.assessment.id for row in rows} == {f.assessment.id, other_assessment.id}
    assert {row.attempt.id for row in rows} == {f.attempt.id, attempt2.id, attempt3.id}
    assert all(
        row.student.id == f.student.id and row.integrity == FileIntegrity.AVAILABLE for row in rows
    )
    assert f.s.list_attempt_attachments(f.attempt.id)[0].attachment.id == first.id
    assert f.s.list_attempt_attachments(attempt2.id)[0].attachment.id == second.id
    other = f.s.create_student(f.offering.id, "Other Synthetic")
    assert f.s.list_student_files(other.id) == []
    assert f.s.get_file_asset(a.id) == a


def test_file_and_links_survive_reopen_and_root_move(files, tmp_path):
    import shutil

    f = files
    link, asset = imported(f)
    f.runtime.close()
    moved = tmp_path.parent / (tmp_path.name + "-moved")
    shutil.copytree(tmp_path, moved)
    reopened = create_runtime(moved)
    try:
        assert reopened.service.get_file_asset(asset.id) == asset
        assert reopened.service.list_attempt_attachments(f.attempt.id)[0].attachment == link
        assert reopened.service.verify_file_integrity(asset.id) == FileIntegrity.AVAILABLE
        assert reopened.service.accessible_file_path(asset.id).is_relative_to(moved)
    finally:
        reopened.close()


@pytest.mark.parametrize("state", ["available", "missing", "corrupted", "same_size_corrupted"])
def test_integrity_never_soft_deletes_metadata(files, state):
    f = files
    link, asset = imported(f)
    path = f.s.accessible_file_path(asset.id)
    path.chmod(stat.S_IREAD | stat.S_IWRITE)
    if state == "missing":
        path.unlink()
    elif state == "corrupted":
        path.write_bytes(b"changed")
    elif state == "same_size_corrupted":
        path.write_bytes(b"!" * asset.size_bytes)
    expected = FileIntegrity.CORRUPTED if "corrupted" in state else FileIntegrity(state)
    assert f.s.verify_file_integrity(asset.id) == expected
    assert f.s.get_file_asset(asset.id) == asset
    assert f.s.list_student_files(f.student.id)[0].integrity == expected
    if state != "available":
        with pytest.raises(ApplicationError, match="file_" + expected.value):
            f.s.open_file_asset(asset.id)


def test_detach_and_archive_preserve_bytes_and_history(files):
    f = files
    link, asset = imported(f)
    path = f.s.accessible_file_path(asset.id)
    with pytest.raises(ApplicationError, match="file_asset_in_use"):
        f.s.archive_file_asset(asset.id, expected_revision=asset.revision)
    f.s.detach_attachment(link.id, expected_revision=link.revision)
    assert f.s.list_attempt_attachments(f.attempt.id) == []
    assert f.s.list_student_files(f.student.id) == []
    historical = f.s.list_attempt_attachments(f.attempt.id, include_detached=True)
    assert historical[0].attachment.deleted_at is not None
    assert path.read_bytes() == f.source.read_bytes()
    f.s.archive_file_asset(asset.id, expected_revision=asset.revision)
    assert f.s.get_file_asset(asset.id, include_deleted=True).deleted_at is not None
    assert f.s.verify_file_integrity(asset.id) == FileIntegrity.AVAILABLE
    assert path.exists()


def test_shared_asset_detach_keeps_other_attempt_link(files):
    f = files
    link, asset = imported(f)
    attempt2 = f.s.add_attempt(f.work.id, UtcInstant.now(), AttemptResult.PRESENTED)
    second = AttemptAttachment(
        metadata=EntityMetadata.create(UtcInstant.now()),
        attempt_id=attempt2.id,
        file_asset_id=asset.id,
    )
    f.s._r.attempt_attachments.insert(second)
    f.s.detach_attachment(link.id, expected_revision=link.revision)
    assert f.s.list_attempt_attachments(attempt2.id)[0].asset == asset
    assert f.s.verify_file_integrity(asset.id) == FileIntegrity.AVAILABLE


def test_caption_order_details_revision_and_stale_detach(files):
    f = files
    link, asset = imported(f)
    changed = f.s.update_attachment(link, caption="page 2", sort_order=2, details_json='{"page":2}')
    assert changed.caption == "page 2" and changed.revision == 2
    assert f.s.get_file_asset(asset.id) == asset
    with pytest.raises(RepositoryError) as error:
        f.s.detach_attachment(link.id, expected_revision=link.revision)
    assert error.value.failure == RepositoryFailure.REVISION_CONFLICT


def test_database_failure_rolls_back_both_records_and_final_file(files):
    f = files
    transaction = f.s._transaction

    @contextmanager
    def fail_commit():
        with transaction() as r:
            yield r
            raise RepositoryError(RepositoryFailure.STORAGE_UNAVAILABLE, "Synthetic commit failure")

    f.s._transaction = fail_commit
    with pytest.raises(RepositoryError):
        imported(f)
    f.s._transaction = transaction
    assert f.s._r.file_assets.list() == []
    assert f.s.list_attempt_attachments(f.attempt.id) == []
    assert originals(f) == []
    assert list((f.root / "files/.imports").glob("*.json")) == []
    assert f.source.exists()


@pytest.mark.parametrize(
    "number,key", [(errno.ENOSPC, "file_disk_full"), (errno.EACCES, "file_permission")]
)
def test_file_failure_creates_no_db_record(files, monkeypatch, number, key):
    f = files

    def fail(*_):
        raise OSError(number, "Synthetic failure")

    monkeypatch.setattr(f.s._file_storage, "_publish", fail)
    with pytest.raises(ApplicationError, match=key):
        imported(f)
    assert f.s._r.file_assets.list() == [] and originals(f) == []
    assert list((f.root / "files/.imports").glob("*.tmp")) == []


@pytest.mark.parametrize(
    "kind", ["missing", "folder", "executable", "script", "shortcut", "disguised"]
)
def test_unsafe_or_invalid_sources_not_imported(files, kind):
    f = files
    source = (
        f.root
        / {
            "missing": "absent.txt",
            "folder": "folder.txt",
            "executable": "bad.exe",
            "script": "bad.ps1",
            "shortcut": "bad.lnk",
            "disguised": "bad.jpg",
        }[kind]
    )
    if kind == "folder":
        source.mkdir()
    elif kind != "missing":
        source.write_bytes(
            b"MZ synthetic executable" if kind == "disguised" else b"Synthetic blocked file"
        )
    with pytest.raises(ApplicationError):
        f.s.import_file_for_attempt(f.attempt.id, source)
    assert originals(f) == [] and f.s._r.file_assets.list() == []


def test_uuid_collision_does_not_overwrite_existing_original(files, monkeypatch):
    f = files
    link, asset = imported(f)
    monkeypatch.setattr(f.s, "_meta", lambda: asset.metadata)
    f.source.write_bytes(b"Different source")
    with pytest.raises(ApplicationError):
        imported(f)
    assert f.s.verify_file_integrity(asset.id) == FileIntegrity.AVAILABLE
    assert len(f.s._r.file_assets.list()) == 1


def test_open_uses_only_controlled_path_and_no_source_filename(files):
    f = files
    _, asset = imported(f)
    seen = []
    f.s._file_opener = SimpleNamespace(open=lambda path: seen.append(path))
    f.s.open_file_asset(asset.id)
    assert seen == [f.root / asset.storage_key]
    binary = f.root / "ordinary.bin"
    binary.write_bytes(b"Synthetic data")
    link = f.s.import_file_for_attempt(f.attempt.id, binary)
    with pytest.raises(ApplicationError, match="file_open_blocked"):
        f.s.open_file_asset(link.file_asset_id)


@pytest.mark.parametrize("committed", [False, True])
def test_startup_journal_recovery_respects_db_commit(files, committed):
    f = files
    if committed:
        _, asset = imported(f)
        id, key = asset.id, asset.storage_key
    else:
        id = EntityId.generate()
        key = f"files/{id.value[:2]}/{id.value}.txt"
    final = f.root / key
    final.parent.mkdir(parents=True, exist_ok=True)
    if not committed:
        final.write_bytes(b"Uncommitted synthetic bytes")
    journal = f.root / "files/.imports"
    (journal / f"{id.value}.json").write_text(json.dumps({"storage_key": key}), encoding="utf-8")
    (journal / f"{id.value}.tmp").write_bytes(b"Partial temporary bytes")
    f.runtime.close()
    value = create_runtime(f.root)
    try:
        assert final.exists() == committed
        assert not list(journal.glob("*.json")) and not list(journal.glob("*.tmp"))
        if committed:
            assert value.service.verify_file_integrity(id) == FileIntegrity.AVAILABLE
    finally:
        value.close()


def test_recovery_rejects_traversal_and_keeps_untracked_originals(files):
    f = files
    arbitrary = f.root / "files/arbitrary.txt"
    arbitrary.write_bytes(b"Must remain")
    assert f.s._file_storage.recover_pending(lambda _: None) == 0
    marker = f.root / f"files/.imports/{EntityId.generate().value}.json"
    marker.write_text('{"storage_key":"../outside.txt"}', encoding="utf-8")
    with pytest.raises(ApplicationError, match="file_journal_invalid"):
        f.s._file_storage.recover_pending(lambda _: None)
    assert arbitrary.read_bytes() == b"Must remain" and marker.exists()


def test_recovery_cannot_race_active_import(files):
    f = files
    with f.s._file_storage._lock():
        with pytest.raises(ApplicationError, match="file_storage_busy"):
            f.s._file_storage.recover_pending(lambda _: None)


def test_archived_academic_parent_retains_file_context(files):
    f = files
    link, _ = imported(f)
    f.s.hide("assessment", f.assessment)
    rows = f.s.list_student_files(f.student.id)
    assert rows[0].attachment == link and rows[0].assessment.deleted_at is not None


def test_import_size_limit_is_compensated(files, monkeypatch):
    from studium.infrastructure import file_storage

    f = files
    monkeypatch.setattr(file_storage, "MAX_FILE_BYTES", 4)
    with pytest.raises(ApplicationError, match="file_too_large"):
        imported(f)
    assert originals(f) == [] and f.s._r.file_assets.list() == []


def test_source_change_during_copy_is_rejected(files, monkeypatch):
    from studium.infrastructure import file_storage

    f = files
    real_stat = file_storage.os.fstat
    calls = 0

    def changed(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            f.source.write_bytes(b"External synthetic edit during copy")
        return real_stat(fd)

    monkeypatch.setattr(file_storage.os, "fstat", changed)
    with pytest.raises(ApplicationError, match="file_source_changed"):
        imported(f)
    assert originals(f) == [] and f.s._r.file_assets.list() == []


@pytest.mark.parametrize("after_commit", [False, True])
def test_real_process_crash_import_is_reconciled_on_reopen(files, after_commit):
    import os
    import subprocess
    import sys

    f = files
    code = """
import os, sys
from pathlib import Path
from studium.composition import create_runtime
from studium.domain.value_objects import EntityId
from studium.infrastructure.file_storage import LocalFileStorage
runtime = create_runtime(Path(sys.argv[1]))
if sys.argv[4] == 'before':
    original = LocalFileStorage._publish
    def crash(temporary, final):
        original(temporary, final)
        os._exit(23)
    LocalFileStorage._publish = staticmethod(crash)
else:
    original = Path.unlink
    def crash(path, *args, **kwargs):
        if path.suffix == '.json' and path.parent.name == '.imports':
            os._exit(23)
        return original(path, *args, **kwargs)
    Path.unlink = crash
runtime.service.import_file_for_attempt(EntityId(sys.argv[2]), Path(sys.argv[3]))
raise RuntimeError('Crash hook did not execute')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(f.root),
            f.attempt.id.value,
            str(f.source),
            "after" if after_commit else "before",
        ],
        env=dict(os.environ, LOCALAPPDATA=str(f.root / "profile")),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 23, result.stderr
    assert len(list((f.root / "files/.imports").glob("*.json"))) == 1
    reopened = create_runtime(f.root)
    try:
        rows = reopened.service.list_attempt_attachments(f.attempt.id)
        assert len(rows) == int(after_commit)
        assert len(originals(f)) == int(after_commit)
        assert not list((f.root / "files/.imports").glob("*.json"))
        if after_commit:
            assert (
                reopened.service.verify_file_integrity(rows[0].asset.id) == FileIntegrity.AVAILABLE
            )
    finally:
        reopened.close()


@pytest.mark.windows
def test_storage_junction_escape_is_rejected(files):
    import os

    if os.name != "nt":
        pytest.skip("Windows junction contract")
    import _winapi

    f = files
    outside = f.root / "outside"
    outside.mkdir()
    redirected = f.root / "files/aa"
    _winapi.CreateJunction(str(outside), str(redirected))
    try:
        with pytest.raises(ApplicationError, match="file_unsafe_path"):
            f.s._file_storage.controlled_path("files/aa/fake.txt")
        assert list(outside.iterdir()) == []
    finally:
        redirected.rmdir()
