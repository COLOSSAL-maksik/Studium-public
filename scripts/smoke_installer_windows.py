"""Native installer lifecycle on a disposable Windows account; synthetic data only."""

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

PROJECT = Path(__file__).resolve().parents[1]
APP_ID = "{B724B6D6-9F24-49D0-9A0B-49BF455BE744}_is1"
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}"


def fresh_database_facts(path):
    from studium.infrastructure.database.migrations import SCHEMA_REVISION
    from studium.infrastructure.database.models import Base

    facts = database_facts(path)
    if facts.get("alembic_version") != [(SCHEMA_REVISION,)]:
        raise RuntimeError("Installed database schema differs from candidate")
    if set(facts) != set(Base.metadata.tables) | {"alembic_version"}:
        raise RuntimeError("Installed database tables differ from candidate")
    return facts


def registered_install():
    import winreg

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, UNINSTALL_KEY, 0, winreg.KEY_READ | view):
                    return True
            except FileNotFoundError:
                pass
    return False


def file_hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def database_facts(path):
    # sqlite3's transaction context manager does not close its Windows file handle.
    # A mode=ro reader of a WAL database can itself create WAL/SHM sidecars.
    # Only compare a closed, checkpointed database; immutable keeps validation read-only.
    wal = path.with_name(path.name + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise RuntimeError("Close and checkpoint the synthetic database before comparing facts")
    with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        return {
            name: sorted(connection.execute(f'SELECT * FROM "{name}"').fetchall(), key=repr)
            for name in tables
        }


def asset_hashes(root):
    """Compare every DB-referenced attachment, not the operational import journal."""
    database = root / "studium.sqlite"
    database_facts(database)  # Closed/checkpointed, integrity and foreign keys first.
    with closing(
        sqlite3.connect(f"{database.as_uri()}?mode=ro&immutable=1", uri=True)
    ) as connection:
        assets = connection.execute(
            "SELECT storage_key, size_bytes, sha256 FROM file_assets ORDER BY storage_key"
        ).fetchall()
    result = {}
    for key, size, expected_hash in assets:
        relative = Path(key)
        assert not relative.is_absolute() and relative.parts[0] == "files"
        assert not {".", ".."} & set(relative.parts)
        path = root / relative
        assert path.resolve().is_relative_to((root / "files").resolve())
        contents = path.read_bytes()
        assert len(contents) == size
        actual_hash = hashlib.sha256(contents).hexdigest()
        assert actual_hash == expected_hash
        assert key not in result
        result[key] = actual_hash
    return result


def launch(exe, profile, workspace, while_running=None):
    env = dict(os.environ, LOCALAPPDATA=str(profile), QT_QPA_PLATFORM="windows")
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PATH"] = str(Path(os.environ["WINDIR"]) / "System32") + ";" + os.environ["WINDIR"]
    powershell = Path(os.environ["WINDIR"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    process = subprocess.Popen([str(exe)], cwd=workspace, env=env)
    try:
        command = [
            str(powershell),
            "-NoProfile",
            "-File",
            str(PROJECT / "scripts/smoke_installer_ui.ps1"),
            "-OwnProcessId",
            str(process.pid),
        ]
        if while_running:
            subprocess.run([*command, "-LeaveOpen"], env=env, check=True, timeout=90)
            assert process.poll() is None
            while_running()
        subprocess.run(
            [*command, "-CloseOnly"] if while_running else command, env=env, check=True, timeout=90
        )
        assert process.wait(timeout=20) == 0
    finally:
        if process.poll() is None:
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
            process.wait(timeout=20)


def install(installer, program, workspace, desktop=False):
    result = subprocess.run(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/SP-",
            "/LANG=russian",
            "/TASKS=desktopicon" if desktop else "/TASKS=",
            f"/DIR={program}",
            f"/LOG={workspace / 'setup.log'}",
        ],
        check=False,
        timeout=180,
    )
    if result.returncode:
        log = workspace / "setup.log"
        if log.exists():
            # Print only fixed guard diagnostics, never raw installer/account paths.
            raw = log.read_bytes()
            text = raw.decode(
                "utf16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig",
                errors="replace",
            )
            for line in text.splitlines():
                if "STUDIUM_GUARD_" in line:
                    print(line[line.index("STUDIUM_GUARD_") :])
        raise RuntimeError(f"Native installer failed with exit {result.returncode}")
    assert (program / "Studium.exe").is_file()


def product_version(executable):
    library = ctypes.WinDLL("version", use_last_error=True)
    library.GetFileVersionInfoSizeW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
    library.GetFileVersionInfoSizeW.restype = ctypes.c_uint32
    ignored = ctypes.c_uint32()
    size = library.GetFileVersionInfoSizeW(str(executable), ctypes.byref(ignored))
    assert size
    buffer = ctypes.create_string_buffer(size)
    library.GetFileVersionInfoW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    assert library.GetFileVersionInfoW(str(executable), 0, size, buffer)
    pointer, length = ctypes.c_void_p(), ctypes.c_uint32()
    library.VerQueryValueW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_uint32),
    ]
    assert library.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length))
    assert length.value >= 52
    fixed = (ctypes.c_uint32 * 13).from_address(pointer.value)
    assert fixed[0] == 0xFEEF04BD and fixed[5] & 0xFFFF == 0
    return ".".join(map(str, (fixed[4] >> 16, fixed[4] & 0xFFFF, fixed[5] >> 16)))


def shortcuts():
    library = ctypes.WinDLL("shell32")
    library.SHGetFolderPathW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_wchar_p,
    ]
    paths = []
    for folder in (2, 0x10):  # CSIDL_PROGRAMS and DESKTOPDIRECTORY, not environment overrides
        buffer = ctypes.create_unicode_buffer(260)
        assert library.SHGetFolderPathW(None, folder, None, 0, buffer) == 0
        paths.append(Path(buffer.value) / "Studium.lnk")
    return paths


def registration_snapshot():
    import winreg

    result = {}
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, UNINSTALL_KEY, 0, winreg.KEY_READ | view) as key:
                    count = winreg.QueryInfoKey(key)[1]
                    result[(hive, view)] = [winreg.EnumValue(key, index) for index in range(count)]
            except FileNotFoundError:
                pass
    return result


def refuse_install(installer, program, workspace, data):
    before_program, before_registration = file_hashes(program), registration_snapshot()
    before_data = file_hashes(data)
    outcome = subprocess.run(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/SP-",
            f"/DIR={program}",
            f"/LOG={workspace / 'refusal.log'}",
        ],
        check=False,
        timeout=180,
    )
    assert outcome.returncode == 7
    assert file_hashes(program) == before_program
    assert registration_snapshot() == before_registration
    assert file_hashes(data) == before_data


def uninstall(program):
    uninstaller = program / "unins000.exe"
    subprocess.run(
        [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        check=True,
        timeout=180,
    )
    # Inno's helper removes its own executable after the main process exits.
    deadline = time.monotonic() + 10
    while uninstaller.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if uninstaller.exists():
        raise TimeoutError("Native uninstaller self-cleanup did not complete")


def check_installed_payload(program, installer):
    manifest_path = installer.with_suffix(".payload.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    assert manifest["version"] == installer_version(installer)
    expected = set()
    for entry in manifest["files"]:
        relative = PurePosixPath(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in entry["path"]:
            raise ValueError("Invalid payload manifest path")
        target = program / relative
        if not target.resolve().is_relative_to(program.resolve()):
            raise ValueError("Installed payload escaped the program directory")
        assert target.stat().st_size == entry["size"]
        with target.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == entry["sha256"]
        expected.add(relative.as_posix())
    actual = {p.relative_to(program).as_posix() for p in program.rglob("*") if p.is_file()}
    ownership = program / "studium-payload.txt"
    assert ownership.read_text(encoding="ascii").splitlines() == [
        "STUDIUM-PAYLOAD-1",
        *(entry["sha256"] + " " + entry["path"].replace("/", "\\") for entry in manifest["files"]),
    ]
    assert actual - expected <= {
        "unins000.exe",
        "unins000.dat",
        "unins000.msg",
        "studium-payload.txt",
    }
    assert expected <= actual


def check_registration(program, expected_version):
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
    ) as key:
        assert winreg.QueryValueEx(key, "DisplayName")[0] == "Studium"
        assert winreg.QueryValueEx(key, "Publisher")[0] == "COLOSSAL-maksik"
        assert winreg.QueryValueEx(key, "DisplayVersion")[0] == expected_version
        assert Path(winreg.QueryValueEx(key, "InstallLocation")[0]).resolve() == program.resolve()
        assert (
            winreg.QueryValueEx(key, "StudiumPayloadSHA256")[0]
            == hashlib.sha256((program / "studium-payload.txt").read_bytes()).hexdigest()
        )
    views = registration_snapshot()
    assert not any(hive == winreg.HKEY_LOCAL_MACHINE for hive, _ in views)
    # HKCU views may refer to the same shared key. Distinct stale records must not remain.
    identities = [
        {name: (value, kind) for name, value, kind in values} for values in views.values()
    ]
    assert identities and all(identity == identities[0] for identity in identities)


def installer_version(installer):
    import re

    match = re.fullmatch(r"Studium-Setup-(\d+\.\d+\.\d+)\.exe", installer.name)
    if not match or not installer.is_file():
        raise ValueError("Expected an existing Studium-Setup-major.minor.patch.exe")
    return match[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--upgrade-installer", type=Path, help="Actual newer build (optional)")
    parser.add_argument(
        "--disposable-account",
        action="store_true",
        help="Required: this test modifies HKCU and Start menu shortcuts",
    )
    args = parser.parse_args()
    if sys.platform != "win32" or not args.disposable_account:
        parser.error("Requires native Windows and an explicitly disposable test account")
    installer = args.installer.resolve()
    version = installer_version(installer)
    upgrade = args.upgrade_installer.resolve() if args.upgrade_installer else installer
    upgrade_version = installer_version(upgrade)
    assert product_version(installer) == version
    assert product_version(upgrade) == upgrade_version
    if args.upgrade_installer and tuple(map(int, upgrade_version.split("."))) <= tuple(
        map(int, version.split("."))
    ):
        parser.error("Upgrade installer must have a strictly newer application version")
    if registered_install():
        parser.error("Existing Studium registration detected; nothing was changed")
    start_menu, desktop = shortcuts()
    if start_menu.exists() or desktop.exists():
        parser.error("Existing Studium shortcut; nothing was changed")
    # Python is used only by the developer's harness, never by the installed application.
    from create_demo_data import create_demo

    from studium.infrastructure.user_data import ensure_outside_repository

    original_local = os.environ.get("LOCALAPPDATA")
    with TemporaryDirectory(prefix="studium-installer-synthetic-") as temporary:
        root = Path(temporary).resolve()
        ensure_outside_repository(root)
        program, profile = root / "Programs с пробелами/Studium", root / "profile"
        data = profile / "Studium"
        try:
            install(installer, program, root)
            check_installed_payload(program, installer)
            check_registration(program, version)
            assert product_version(program / "Studium.exe") == version
            assert start_menu.is_file() and not desktop.exists()
            # Fresh default AppPaths initialization, without --data-dir.
            launch(program / "Studium.exe", root / "fresh-profile", root)
            fresh_database_facts(root / "fresh-profile/Studium/studium.sqlite")
            os.environ["LOCALAPPDATA"] = str(root / "harness-profile")
            create_demo(data)
            before_facts = database_facts(data / "studium.sqlite")
            managed_before = file_hashes(data / "files")
            assets_before = asset_hashes(data)
            assert assets_before
            assert managed_before and len(before_facts["students"]) == 3
            prefs_before = (data / "preferences.json").read_bytes()
            for _ in range(2):
                launch(program / "Studium.exe", profile, root)
                assert database_facts(data / "studium.sqlite") == before_facts
                assert file_hashes(data / "files") == managed_before
                assert (data / "preferences.json").read_bytes() == prefs_before
            # Keep only audited program bytes for compatible-version archive recovery.
            # Never let this older EXE open the active data after the upgrade.
            compatible_program = root / "compatible-program"
            old_manifest = json.loads(
                installer.with_suffix(".payload.json").read_text(encoding="utf8")
            )
            for entry in old_manifest["files"]:
                copied = compatible_program / entry["path"]
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(program / entry["path"], copied)
                assert hashlib.sha256(copied.read_bytes()).hexdigest() == entry["sha256"]
            backup_result = "NOT RUN (developer source version differs from old installer)"
            from studium import __version__

            if __version__ == version:
                from studium.application.backup import BackupControl
                from studium.infrastructure.backup import LocalBackup
                from studium.infrastructure.user_data import AppPaths

                backend = LocalBackup(AppPaths(data))
                archive = root / "synthetic-before-upgrade.zip"
                before_backup = file_hashes(data)
                preview = backend.create(archive, BackupControl())
                assert preview.app_version == version
                assert backend.verify(archive, BackupControl()) == preview
                after_backup = file_hashes(data)
                assert {name: after_backup.get(name) for name in before_backup} == before_backup
                # The application's read-only backup API may create empty SQLite sidecars.
                # Preserve every previous byte; allow no other additions, nor pending WAL pages.
                assert after_backup.keys() - before_backup.keys() <= {
                    "studium.sqlite-wal",
                    "studium.sqlite-shm",
                }
                assert database_facts(data / "studium.sqlite") == before_facts
            launch(
                program / "Studium.exe",
                profile,
                root,
                while_running=lambda: refuse_install(installer, program, root, data),
            )
            assert database_facts(data / "studium.sqlite") == before_facts
            assert file_hashes(data / "files") == managed_before
            assert (data / "preferences.json").read_bytes() == prefs_before
            # From here all installer operations compare the entire closed data root.
            # Do not compare SQLite's live sidecars across opening/closing the application.
            before_install = file_hashes(data)
            for fault in ("deleted", "corrupted"):
                target = program / "_internal/PySide6/Qt6Core.dll"
                if fault == "deleted":
                    target.unlink()
                else:
                    target.write_bytes(b"Synthetic corruption of installer-owned library")
                install(installer, program, root)
                check_installed_payload(program, installer)
                assert file_hashes(data) == before_install
                assert database_facts(data / "studium.sqlite") == before_facts
                assert file_hashes(data / "files") == managed_before
            install(upgrade, program, root)
            check_installed_payload(program, upgrade)
            check_registration(program, upgrade_version)
            assert product_version(program / "Studium.exe") == upgrade_version
            assert file_hashes(data) == before_install
            if args.upgrade_installer:
                refuse_install(installer, program, root, data)
                assert file_hashes(data) == before_install
                assert database_facts(data / "studium.sqlite") == before_facts
            # Test explicitly opted-in desktop shortcut, then removal on uninstall.
            install(upgrade, program, root, desktop=True)
            assert start_menu.is_file() and desktop.is_file()
            assert file_hashes(data) == before_install
            launch(program / "Studium.exe", profile, root)
            assert database_facts(data / "studium.sqlite") == before_facts
            assert file_hashes(data / "files") == managed_before
            assert (data / "preferences.json").read_bytes() == prefs_before
            assert file_hashes(data) == before_install
            if __version__ == version:
                recovered = root / "recovered-profile/Studium"
                recovered.mkdir(parents=True)
                assert backend.restore(archive, recovered, preview, BackupControl()) == recovered
                assert database_facts(recovered / "studium.sqlite") == before_facts
                assert asset_hashes(recovered) == assets_before
                assert file_hashes(recovered / "files") == {
                    key.removeprefix("files/"): digest for key, digest in assets_before.items()
                }
                assert file_hashes(data) == before_install
                assert product_version(compatible_program / "Studium.exe") == version
                launch(compatible_program / "Studium.exe", recovered.parent, root)
                assert database_facts(recovered / "studium.sqlite") == before_facts
                assert asset_hashes(recovered) == assets_before
                assert file_hashes(data) == before_install
                backup_result = "PASS (matching-version API backup/verify/restore and packaged older EXE; only restored root opened)"
            before_uninstall = file_hashes(data)
            uninstall(program)
            assert not (program / "Studium.exe").exists() and not registered_install()
            assert not start_menu.exists() and not desktop.exists()
            assert file_hashes(data) == before_uninstall
            assert database_facts(data / "studium.sqlite") == before_facts
            assert not (program / "studium.sqlite").exists()
            install(upgrade, program, root)
            check_installed_payload(program, upgrade)
            assert file_hashes(data) == before_uninstall
            launch(program / "Studium.exe", profile, root)
            assert database_facts(data / "studium.sqlite") == before_facts
            assert file_hashes(data / "files") == managed_before
            assert (data / "preferences.json").read_bytes() == prefs_before
            assert file_hashes(data) == before_uninstall
            uninstall(program)
            assert not registered_install() and not start_menu.exists() and not desktop.exists()
            assert file_hashes(data) == before_uninstall
            print(
                json.dumps(
                    {
                        "native_windows": True,
                        "synthetic_only": True,
                        "fresh_launch_alembic": "PASS",
                        "installed_help": "PASS",
                        "installed_payload_manifest_and_no_extra_files": "PASS",
                        "two_launches_facts_files_preferences": "PASS",
                        "upgrade_data_preservation": "PASS"
                        if args.upgrade_installer
                        else "NOT RUN (same version repair tested)",
                        "uninstall_data_preservation": "PASS",
                        "repair_deleted_and_corrupted_owned_library": "PASS",
                        "running_application_refused_before_changes": "PASS",
                        "downgrade_refused_before_changes": "PASS"
                        if args.upgrade_installer
                        else "NOT RUN (no older installer)",
                        "exe_setup_registration_versions": "PASS",
                        "start_menu_optional_desktop_and_removal": "PASS",
                        "uninstall_reinstall_reopens_synthetic_data": "PASS",
                        "compatible_version_recovery": backup_result,
                        "manual_pdf_backup_restore": "PENDING: docs/windows-installer-smoke-tests.md",
                    }
                )
            )
        finally:
            # Only the uninstaller for this test's explicit program directory is eligible.
            uninstaller = program / "unins000.exe"
            if uninstaller.is_file() and registered_install():
                uninstall(program)
            if original_local is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = original_local


if __name__ == "__main__":
    main()
