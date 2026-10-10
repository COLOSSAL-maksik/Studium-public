"""Synthetic payload safety checks; these are never native installer acceptance."""

import hashlib
import importlib.util
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check_windows_bundle.py"
spec = importlib.util.spec_from_file_location("windows_bundle_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
smoke_spec = importlib.util.spec_from_file_location(
    "windows_installer_smoke", SCRIPT.with_name("smoke_installer_windows.py")
)
smoke = importlib.util.module_from_spec(smoke_spec)
smoke_spec.loader.exec_module(smoke)


def test_database_comparison_closes_its_windows_file_handle(tmp_path, monkeypatch):
    database = tmp_path / "synthetic.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE synthetic (value TEXT)")
    connection.execute("INSERT INTO synthetic VALUES ('Synthetic row')")
    connection.commit()
    connection.close()
    original_connect, opened = sqlite3.connect, []

    def track_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(smoke.sqlite3, "connect", track_connect)
    assert smoke.database_facts(database) == {"synthetic": [("Synthetic row",)]}
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")


def test_closed_wal_database_comparison_preserves_the_entire_root(tmp_path):
    database = tmp_path / "synthetic.sqlite"
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE synthetic (value TEXT)")
        connection.execute("INSERT INTO synthetic VALUES ('Synthetic row')")
        connection.commit()
    finally:
        connection.close()
    before = smoke.file_hashes(tmp_path)
    assert smoke.database_facts(database) == {"synthetic": [("Synthetic row",)]}
    assert smoke.file_hashes(tmp_path) == before
    assert not database.with_name(database.name + "-wal").exists()
    assert not database.with_name(database.name + "-shm").exists()


def test_database_comparison_cannot_ignore_uncheckpointed_wal(tmp_path):
    database = tmp_path / "synthetic.sqlite"
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE synthetic (value TEXT)")
        connection.commit()
        with pytest.raises(RuntimeError, match="Close and checkpoint"):
            smoke.database_facts(database)
    finally:
        connection.close()


def test_recovery_compares_asset_bytes_separately_from_operational_journal(tmp_path):
    files = tmp_path / "files"
    (files / ".imports").mkdir(parents=True)
    (files / ".imports/lock").write_bytes(b"\0")
    attachment = files / "synthetic.txt"
    contents = b"Synthetic immutable attachment"
    attachment.write_bytes(contents)
    digest = hashlib.sha256(contents).hexdigest()
    connection = sqlite3.connect(tmp_path / "studium.sqlite")
    try:
        connection.execute(
            "CREATE TABLE file_assets(storage_key TEXT, size_bytes INTEGER, sha256 TEXT)"
        )
        connection.execute(
            "INSERT INTO file_assets VALUES (?, ?, ?)",
            ("files/synthetic.txt", len(contents), digest),
        )
        connection.commit()
    finally:
        connection.close()
    before = smoke.file_hashes(tmp_path)
    assert smoke.asset_hashes(tmp_path) == {"files/synthetic.txt": digest}
    assert smoke.file_hashes(tmp_path) == before
    attachment.write_bytes(b"Synthetic corruption")
    with pytest.raises(AssertionError):
        smoke.asset_hashes(tmp_path)


@pytest.fixture
def bundle(tmp_path):
    project, payload = tmp_path / "source", tmp_path / "onedir"
    (project / "src/studium").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf8")
    (project / "src/studium/__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf8")
    for root, name, value in (
        (audit.RESOURCE_ROOTS[0], "versions/v0001.py", b"# Synthetic migration\n"),
        (audit.RESOURCE_ROOTS[0], "versions/v0001.sql", b"-- Synthetic schema\n"),
        (audit.RESOURCE_ROOTS[0], "script.py.mako", b"# Synthetic template\n"),
        (audit.RESOURCE_ROOTS[1], "index.json", b"[]\n"),
        (audit.RESOURCE_ROOTS[1], "getting-started.md", b"# Synthetic help\n"),
    ):
        source = project / "src" / root / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(value)
        target = payload / "_internal" / root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in (
        "Studium.exe",
        "_internal/python312.dll",
        "_internal/_sqlite3.pyd",
        "_internal/PySide6/Qt6Core.dll",
        "_internal/PySide6/Qt6Gui.dll",
        "_internal/PySide6/Qt6Widgets.dll",
        "_internal/PySide6/Qt6Pdf.dll",
        "_internal/PySide6/Qt6PdfWidgets.dll",
        "_internal/PySide6/Qt6Charts.dll",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
    ):
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"MZ synthetic test placeholder, not an executable")
    with zipfile.ZipFile(payload / "_internal/base_library.zip", "w") as archive:
        archive.writestr("encodings/__init__.pyc", b"Synthetic placeholder, not Python bytecode")
    return project, payload


def test_snapshot_contains_only_audited_entries_and_matches_hashes(bundle, tmp_path):
    project, payload = bundle
    before = audit.validate_bundle(payload, project)
    stage = tmp_path / "unique-stage"
    audit.stage_bundle(payload, stage, project)
    manifest = json.loads((stage / "payload-manifest.json").read_text(encoding="utf8"))
    assert manifest == {"version": "1.2.3", "files": before}
    assert audit.validate_bundle(stage / "payload", project) == before
    include = (stage / "payload.iss").read_text(encoding="utf-8-sig")
    assert "*" not in include and include.count("Source:") == len(before) + 1
    receipt = (stage / audit.RECEIPT_NAME).read_text(encoding="ascii").splitlines()
    assert receipt == [
        audit.RECEIPT_HEADER,
        *(entry["sha256"] + " " + entry["path"].replace("/", "\\") for entry in before),
    ]
    assert audit.digest(stage / audit.RECEIPT_NAME) in include
    with pytest.raises(FileExistsError):
        audit.stage_bundle(payload, stage, project)


@pytest.mark.parametrize("name", ["Qt6Core.dll.", "Qt6Core.dll ", "CON.dll", "lpt1.pyd"])
def test_ambiguous_windows_names_cannot_be_payload_targets(name):
    # Win32 normalizes these at creation; test raw names without creating device files.
    with pytest.raises(ValueError, match="path syntax"):
        audit.validate_relative_path("_internal/" + name)


@pytest.mark.parametrize(
    "name",
    [
        "studium.sqlite",
        "_internal/studium.sqlite-wal",
        "_internal/demo.db-shm",
        "_internal/preferences.json",
        "_internal/settings.json",
        "_internal/.env",
        "_internal/FILES/00000000.synthetic.txt",
        "_internal/FileAsset/synthetic.pdf",
        "_internal/backups/synthetic.zip",
        "_internal/exports/report.csv",
        "_internal/logs/synthetic.log",
        "_internal/.imports/lock",
        "_internal/secrets/fixture.json",
        "_internal/credentials-test.json",
        "_internal/synthetic.pdf",
        "_internal/synthetic.png",
        "_internal/synthetic.docx",
        "_internal/extra.json",
        "_internal/source.py",
        "_internal/user.zip",
        "_internal/studium/presentation/desktop/help_articles/unreviewed.md",
    ],
)
def test_contaminated_payload_is_refused_before_staging(bundle, tmp_path, name):
    project, payload = bundle
    extra = payload / name
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"Synthetic sensitive-data stand-in")
    stage = tmp_path / "stage"
    with pytest.raises(ValueError):
        audit.stage_bundle(payload, stage, project)
    assert not stage.exists()


@pytest.mark.parametrize(
    "resource",
    [
        "_internal/studium/infrastructure/database/migrations/versions/v0001.sql",
        "_internal/studium/presentation/desktop/help_articles/index.json",
    ],
)
def test_stale_or_modified_resources_are_refused(bundle, resource):
    project, payload = bundle
    (payload / resource).write_bytes(b"Synthetic substituted content")
    with pytest.raises(ValueError, match="differs from source"):
        audit.validate_bundle(payload, project)


def test_help_package_python_is_compiled_code_not_resource_data(bundle):
    project, payload = bundle
    code = project / "src" / audit.RESOURCE_ROOTS[1] / "__init__.py"
    code.write_text('"""Synthetic package marker."""\n', encoding="utf8")
    audit.validate_bundle(payload, project)
    # PyInstaller includes this module in PYZ, not as a loose data file.
    copied = payload / "_internal" / audit.RESOURCE_ROOTS[1] / "__init__.py"
    shutil.copyfile(code, copied)
    with pytest.raises(ValueError, match="Unapproved"):
        audit.validate_bundle(payload, project)


def test_reviewed_settings_help_is_not_a_user_preferences_file(bundle):
    project, payload = bundle
    source = project / "src" / audit.RESOURCE_ROOTS[1] / "settings.md"
    source.write_bytes(b"# Synthetic reviewed settings help\n")
    target = payload / "_internal" / audit.RESOURCE_ROOTS[1] / "settings.md"
    shutil.copyfile(source, target)
    audit.validate_bundle(payload, project)
    target.write_bytes(b"Synthetic substituted personal settings")
    with pytest.raises(ValueError, match="differs from source"):
        audit.validate_bundle(payload, project)


def test_preferences_are_forbidden_even_inside_source_resource_directory(bundle):
    project, payload = bundle
    source = project / "src" / audit.RESOURCE_ROOTS[1] / "preferences.json"
    source.write_bytes(b'{"synthetic_personal_setting": true}\n')
    target = payload / "_internal" / audit.RESOURCE_ROOTS[1] / "preferences.json"
    shutil.copyfile(source, target)
    with pytest.raises(ValueError, match="Private/runtime"):
        audit.validate_bundle(payload, project)


def test_only_exact_pinned_vendor_resource_bytes_are_accepted(bundle, tmp_path, monkeypatch):
    project, payload = bundle
    relative = "_internal/setuptools/_vendor/jaraco/text/Lorem ipsum.txt"
    source = tmp_path / "synthetic-vendor-resource.txt"
    source.write_bytes(b"Synthetic vendor fixture")
    monkeypatch.setattr(audit, "dependency_resources", lambda _: {relative: source})
    target = payload / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    audit.validate_bundle(payload, project)
    target.write_bytes(b"Synthetic substituted personal text")
    with pytest.raises(ValueError, match="differs from source"):
        audit.validate_bundle(payload, project)


@pytest.fixture
def pinned_dependency_resources(bundle, tmp_path, monkeypatch):
    project, payload = bundle
    installed = tmp_path / "synthetic-installed-packages"
    (project / "requirements-build.lock").write_text("setuptools==84.0.0\n", encoding="utf8")
    (project / "requirements-dev.lock").write_text("MarkupSafe==3.0.3\n", encoding="utf8")
    names = (
        "INSTALLER",
        "METADATA",
        "RECORD",
        "REQUESTED",
        "WHEEL",
        "top_level.txt",
        "licenses/LICENSE.txt",
    )
    for relative in (
        "setuptools/_vendor/jaraco/text/Lorem ipsum.txt",
        *(f"markupsafe-3.0.3.dist-info/{name}" for name in names),
    ):
        source = installed / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"Synthetic pinned package resource")
        target = payload / "_internal" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    monkeypatch.setattr(
        audit.importlib.metadata,
        "distribution",
        lambda name: SimpleNamespace(
            version="84.0.0" if name == "setuptools" else "3.0.3",
            locate_file=lambda path: installed / path,
        ),
    )
    return project, payload


@pytest.mark.parametrize(
    "name",
    [
        "INSTALLER",
        "METADATA",
        "RECORD",
        "REQUESTED",
        "WHEEL",
        "top_level.txt",
        "licenses/LICENSE.txt",
    ],
)
def test_pinned_wheel_metadata_must_match_exact_source(pinned_dependency_resources, name):
    project, payload = pinned_dependency_resources
    audit.validate_bundle(payload, project)
    (payload / "_internal/markupsafe-3.0.3.dist-info" / name).write_bytes(
        b"Synthetic substituted private metadata"
    )
    with pytest.raises(ValueError, match="differs from source"):
        audit.validate_bundle(payload, project)


def test_unknown_wheel_metadata_and_wrong_version_are_refused(pinned_dependency_resources):
    project, payload = pinned_dependency_resources
    extra = payload / "_internal/markupsafe-3.0.3.dist-info/extra.txt"
    extra.write_bytes(b"Synthetic personal data")
    with pytest.raises(ValueError, match="Unapproved"):
        audit.validate_bundle(payload, project)
    extra.unlink()
    (project / "requirements-dev.lock").write_text("MarkupSafe==0.0.0\n", encoding="utf8")
    with pytest.raises(ValueError, match="differs from its lock"):
        audit.validate_bundle(payload, project)


@pytest.mark.parametrize(
    "name",
    [
        "_internal/PySide6/Qt6Pdf.dll",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
        "_internal/studium/presentation/desktop/help_articles/getting-started.md",
        "_internal/studium/infrastructure/database/migrations/versions/v0001.py",
    ],
)
def test_incomplete_resource_bundle_is_refused(bundle, name):
    project, payload = bundle
    (payload / name).unlink()
    with pytest.raises(ValueError, match="Incomplete"):
        audit.validate_bundle(payload, project)


@pytest.mark.parametrize("name", ["../escape.pyc", "studium.sqlite", "private/settings.json"])
def test_hidden_documents_in_standard_library_archive_are_refused(bundle, name):
    project, payload = bundle
    with zipfile.ZipFile(payload / "_internal/base_library.zip", "a") as archive:
        archive.writestr(name, b"Synthetic stand-in")
    with pytest.raises(ValueError, match="Unexpected entry"):
        audit.validate_bundle(payload, project)


def test_links_cannot_import_external_material(bundle, tmp_path):
    project, payload = bundle
    external = tmp_path / "synthetic-private.txt"
    external.write_text("Synthetic stand-in", encoding="utf8")
    link = payload / "_internal/linked.dll"
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip("Symlink creation unavailable on this platform")
    with pytest.raises(ValueError, match="Linked"):
        audit.validate_bundle(payload, project)


def test_snapshot_race_is_refused(bundle, tmp_path, monkeypatch):
    project, payload = bundle
    original_copy = audit.shutil.copytree

    def copy_then_change(*args, **kwargs):
        result = original_copy(*args, **kwargs)
        if Path(args[1]).name == "payload":
            (Path(args[1]) / "Studium.exe").write_bytes(b"MZ changed synthetic stand-in")
        return result

    monkeypatch.setattr(audit.shutil, "copytree", copy_then_change)
    stage = tmp_path / "stage"
    with pytest.raises(ValueError, match="changed"):
        audit.stage_bundle(payload, stage, project)
    assert not (stage / "payload.iss").exists()


@pytest.mark.parametrize("version", ["1.2.4", "1.2.3-beta", "70000.2.3"])
def test_inconsistent_or_invalid_version_cannot_name_release(bundle, version):
    project, _ = bundle
    (project / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n', encoding="utf8")
    with pytest.raises(ValueError):
        audit.application_version(project)


@pytest.mark.parametrize("change", ["private_extra", "modified_resource", "manifest_escape"])
def test_extracted_installer_payload_must_match_receipt(bundle, tmp_path, change):
    project, payload = bundle
    installer = tmp_path / "Studium-Setup-1.2.3.exe"
    installer.write_bytes(b"MZ synthetic placeholder, never executable")
    manifest = {"version": "1.2.3", "files": audit.validate_bundle(payload, project)}
    receipt = installer.with_suffix(".payload.json")
    receipt.write_text(json.dumps(manifest), encoding="utf8")
    (payload / "unins000.dat").write_bytes(b"Synthetic uninstall metadata")
    (payload / audit.RECEIPT_NAME).write_text(
        audit.RECEIPT_HEADER
        + "\n"
        + "".join(
            entry["sha256"] + " " + entry["path"].replace("/", "\\") + "\n"
            for entry in manifest["files"]
        ),
        encoding="ascii",
    )
    smoke.check_installed_payload(payload, installer)
    if change == "private_extra":
        (payload / "studium.sqlite").write_bytes(b"Synthetic database stand-in")
    elif change == "modified_resource":
        (payload / "Studium.exe").write_bytes(b"MZ substituted placeholder")
    else:
        manifest["files"][0]["path"] = "../synthetic-private.txt"
        receipt.write_text(json.dumps(manifest), encoding="utf8")
    with pytest.raises((AssertionError, ValueError)):
        smoke.check_installed_payload(payload, installer)
