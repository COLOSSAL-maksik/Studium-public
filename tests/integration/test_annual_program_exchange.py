"""Hostile program containers, read-only preview and real import recovery."""

import hashlib
import json
import stat
import warnings
import zipfile

import pytest

from studium.application.qa_services import document
from studium.domain import annual_program as a
from studium.domain.value_objects import EntityId
from tests.integration.test_annual_program import filled
from tests.integration.test_application import runtime as runtime


def rewrite(
    source, destination, *, mutate_content=None, mutate_manifest=None, extra=None, duplicate=False
):
    with zipfile.ZipFile(source) as old:
        entries = {v.filename: old.read(v.filename) for v in old.infolist()}
    manifest = json.loads(entries["manifest.json"])
    payload = json.loads(entries["program.json"])
    if mutate_content:
        mutate_content(payload)
    raw = document(payload).encode()
    manifest["content_hash"] = hashlib.sha256(raw).hexdigest()
    if mutate_manifest:
        mutate_manifest(manifest)
    entries.update({"program.json": raw, "manifest.json": document(manifest).encode()})
    with warnings.catch_warnings(), zipfile.ZipFile(destination, "w") as out:
        warnings.simplefilter("ignore", UserWarning)
        for name, data in entries.items():
            out.writestr(name, data)
        if extra:
            out.writestr(*extra)
        if duplicate:
            out.writestr("program.json", raw)


@pytest.mark.parametrize(
    "mutation",
    [
        "traversal",
        "absolute",
        "backslash",
        "symlink",
        "reparse",
        "duplicate",
        "future",
        "bad_json",
        "reference",
        "cycle",
        "hash",
        "huge",
        "extra_field",
        "bad_library",
    ],
)
def test_invalid_package_refused_before_preview_without_writes(runtime, tmp_path, mutation):
    from tests.integration.test_file_migrations import snapshot

    s = runtime.service
    _, draft = filled(s)
    version = s.publish_program_draft(draft)
    valid = tmp_path / "valid.studium-program"
    s.export_program(version.id, valid)
    bad = tmp_path / "bad.studium-program"
    kwargs = {}
    if mutation in {"traversal", "absolute", "backslash"}:
        kwargs["extra"] = (
            {"traversal": "../escape", "absolute": "/escape", "backslash": "files\\escape"}[
                mutation
            ],
            b"x",
        )
    elif mutation in {"symlink", "reparse"}:
        info = zipfile.ZipInfo("files/" + a.key())
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16 if mutation == "symlink" else 0x400
        kwargs["extra"] = (info, b"x")
    elif mutation == "duplicate":
        kwargs["duplicate"] = True
    elif mutation == "future":
        kwargs["mutate_manifest"] = lambda m: m.update(version=900)
    elif mutation == "reference":
        kwargs["mutate_content"] = lambda p: p["content"]["annual"]["semesters"][0]["modules"][0][
            "lessons"
        ][0].update(topic_ids=[a.key()])
    elif mutation == "cycle":
        kwargs["mutate_content"] = lambda p: p["content"]["topic_ids_snapshots"][0].update(
            parent_topic_id=p["content"]["topic_ids_snapshots"][0]["id"]
        )
    elif mutation == "hash":
        kwargs["mutate_manifest"] = lambda m: m.update(content_hash="0" * 64)
    elif mutation == "bad_library":
        kwargs["mutate_content"] = lambda payload: payload["content"]["definitions"][0].update(
            title=""
        )
    elif mutation == "extra_field":
        kwargs["mutate_content"] = lambda p: p["content"].update(students=[{"name": "Secret"}])
    rewrite(valid, bad, **kwargs)
    if mutation == "bad_json":
        with zipfile.ZipFile(bad, "w") as out:
            out.writestr("manifest.json", b"{malformed")
            out.writestr("program.json", b"{}")
    if mutation == "huge":
        with zipfile.ZipFile(bad, "w", compression=zipfile.ZIP_DEFLATED) as out:
            out.writestr("manifest.json", b" " * (2 * 1024**2))
            out.writestr("program.json", b"{}")
    with runtime._engine.connect() as connection:
        before = snapshot(connection)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        s.preview_program_import(bad)
    with runtime._engine.connect() as connection:
        assert snapshot(connection) == before
    assert not (tmp_path / "escape").exists()


def test_export_allowlist_excludes_facts_paths_and_unknown_extensions(runtime, tmp_path):
    s = runtime.service
    _, draft = filled(s)
    data = json.loads(draft.content_json)
    data["unrecognized_extension"] = {
        "student_name": "Synthetic private name",
        "path": "C:\\private\\local",
    }
    data["annual"]["passport"]["unrecognized_extension"] = "DO-NOT-TRANSFER"
    draft = s.save_program_draft(draft, data)
    version = s.publish_program_draft(draft)
    # Local extensions survive draft->V1->draft, but are not transferable program data.
    next_draft = s.create_program_draft(
        s.get_course_program(version.course_program_id).course_id, previous=version
    )
    assert (
        json.loads(next_draft.content_json)["unrecognized_extension"]
        == data["unrecognized_extension"]
    )
    path = tmp_path / "allowlist.studium-program"
    s.export_program(version.id, path)
    with zipfile.ZipFile(path) as archive:
        raw = archive.read("program.json").decode()
        assert (
            "Synthetic private name" not in raw
            and "C:\\private" not in raw
            and "DO-NOT-TRANSFER" not in raw
        )
        assert set(archive.namelist()) == {"manifest.json", "program.json"}
        assert not any(
            word in json.loads(raw)["content"]
            for word in ("students", "groups", "assessments", "lessons", "attempts", "storage_key")
        )


def test_preview_stale_source_and_file_integrity(runtime, tmp_path):
    s = runtime.service
    _, draft = filled(s)
    source = tmp_path / "synthetic-file.txt"
    source.write_text("Synthetic file")
    draft = s.attach_program_documents(draft, [source])
    version = s.publish_program_draft(draft)
    path = tmp_path / "stale.studium-program"
    s.export_program(version.id, path, include_files=True)
    preview = s.preview_program_import(path)
    with zipfile.ZipFile(path) as archive:
        entries = {v.filename: archive.read(v.filename) for v in archive.infolist()}
    with zipfile.ZipFile(path, "w") as archive:
        for name, raw in entries.items():
            archive.writestr(name, raw + b"corruption" if name.startswith("files/") else raw)
    before = len(s.list_course_programs())
    with pytest.raises(ValueError):
        s.commit_program_import(preview)
    assert len(s.list_course_programs()) == before


def test_unfinished_file_commit_reconciled_on_reopen(runtime, tmp_path):
    from studium.composition import create_runtime
    from studium.domain.entities import FileAsset
    from studium.infrastructure.file_storage import LocalFileStorage

    root = tmp_path / "recovery"
    local = create_runtime(root)
    source = tmp_path / "synthetic-recovery.txt"
    source.write_text("Synthetic committed bytes")
    storage = LocalFileStorage(root)
    meta = local.service._meta()
    from dataclasses import asdict

    with storage.import_file(source, meta.id) as imported:
        asset = FileAsset(metadata=meta, **asdict(imported))
        local.service._r.file_assets.insert(asset)
    # Reproduce durable markers remaining after process termination on either side of SQL commit.
    journal = root / "files" / ".imports"
    (journal / f"{meta.id}.json").write_text(json.dumps({"storage_key": asset.storage_key}))
    orphan = EntityId(a.key())
    orphan_key = f"files/{str(orphan)[:2]}/{orphan}.txt"
    path = root / orphan_key
    path.parent.mkdir(exist_ok=True)
    path.write_text("Synthetic uncommitted bytes")
    (journal / f"{orphan}.json").write_text(json.dumps({"storage_key": orphan_key}))
    local.close()
    reopened = create_runtime(root)
    try:
        assert reopened.service.accessible_file_path(meta.id).read_bytes() == source.read_bytes()
        assert not path.exists() and not list(journal.glob("*.json"))
    finally:
        reopened.close()
