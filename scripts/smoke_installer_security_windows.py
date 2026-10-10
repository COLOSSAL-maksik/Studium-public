"""Native Inno guard/upgrade regressions in a disposable account; only synthetic bytes.

The fixture shares the shipping InstallSafety.iss, uses a distinct AppId and an
embedded temporary data root. It never reads the real Known Folder data root.
This is installer security regression evidence, not application release acceptance.
"""

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from check_windows_bundle import RECEIPT_NAME, RESOURCE_ROOTS, stage_bundle
from smoke_installer_windows import registered_install, uninstall

PROJECT = Path(__file__).resolve().parents[1]
FIXTURE_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    r"\{F6C8A96D-0143-4591-9451-95B516F1446B}_is1"
)


def registry_snapshot():
    import winreg

    result = {}
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, FIXTURE_KEY, 0, winreg.KEY_READ | view
            ) as key:
                values, index = [], 0
                while True:
                    try:
                        values.append(winreg.EnumValue(key, index))
                        index += 1
                    except OSError as error:
                        if error.winerror != 259:
                            raise
                        break
                result[view] = sorted(values)
        except FileNotFoundError:
            pass
    return result


def set_fixture_receipt_digest(receipt):
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        FIXTURE_KEY,
        0,
        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
    ) as key:
        winreg.SetValueEx(
            key,
            "StudiumPayloadSHA256",
            0,
            winreg.REG_SZ,
            hashlib.sha256(receipt.read_bytes()).hexdigest(),
        )


def tree_snapshot(root):
    """Record owned synthetic paths without traversing a single reparse point."""
    result = {}

    def visit(directory):
        for entry in directory.iterdir():
            relative = entry.relative_to(root).as_posix()
            attributes = entry.lstat()
            if getattr(attributes, "st_file_attributes", 0) & 0x400 or entry.is_symlink():
                result[relative] = ("reparse", os.readlink(entry))
            elif entry.is_dir():
                result[relative] = ("directory",)
                visit(entry)
            else:
                result[relative] = ("file", hashlib.sha256(entry.read_bytes()).hexdigest())

    visit(root)
    return result


def run_setup(installer, program, log):
    result = subprocess.run(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/SP-",
            f"/DIR={program}",
            f"/LOG={log}",
        ],
        timeout=90,
        check=False,
    ).returncode
    if result and log.exists():
        raw = log.read_bytes()
        text = raw.decode(
            "utf16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig",
            errors="replace",
        )
        for line in text.splitlines():
            if "STUDIUM_GUARD_" in line:
                print(line[line.index("STUDIUM_GUARD_") :], flush=True)
    return result


def assert_refused(installer, program, locations, log):
    files_before, registry_before = tree_snapshot(locations), registry_snapshot()
    # Inno exit 7 specifically identifies PrepareToInstall refusal (before PerformInstall).
    assert run_setup(installer, program, log) == 7, "Expected pre-install safety refusal"
    assert tree_snapshot(locations) == files_before, "Refusal changed synthetic files/directories"
    assert registry_snapshot() == registry_before, "Refusal changed installation registration"


def synthetic_bundle(root, version, retired):
    source, bundle = root / "source", root / "onedir"
    (source / "src/studium").mkdir(parents=True)
    (source / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n', encoding="utf8")
    (source / "src/studium/__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf8")
    resources = [(RESOURCE_ROOTS[0], "versions/synthetic.py"), (RESOURCE_ROOTS[1], "index.json")]
    if retired:
        resources.append((RESOURCE_ROOTS[1], "retired.md"))
    for resource, name in resources:
        original = source / "src" / resource / name
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_bytes(b"Synthetic fixture; never application data\n")
        target = bundle / "_internal" / resource / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    names = [
        "Studium.exe",
        "_internal/PySide6/Qt6Core.dll",
        "_internal/PySide6/Qt6Gui.dll",
        "_internal/PySide6/Qt6Widgets.dll",
        "_internal/PySide6/Qt6Pdf.dll",
        "_internal/PySide6/Qt6PdfWidgets.dll",
        "_internal/PySide6/Qt6Charts.dll",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
    ]
    if retired:
        names.append("_internal/retired/retired.dll")
    else:
        names.append("_internal/added/added.dll")
    for name in names:
        target = bundle / name
        target.parent.mkdir(parents=True, exist_ok=True)
        # Not runnable. Tests execute the real Inno installer, never this placeholder.
        target.write_bytes(b"MZ Synthetic placeholder " + version.encode("ascii"))
    with zipfile.ZipFile(bundle / "_internal/base_library.zip", "w") as archive:
        archive.writestr("synthetic.pyc", b"Synthetic placeholder")
    return source, bundle


def compile_fixture(root, compiler, data, version, retired):
    source, bundle = synthetic_bundle(root, version, retired)
    stage = root / "stage"
    stage_bundle(bundle, stage, source)
    subprocess.run(
        [
            str(compiler),
            f"/DAppVersion={version}",
            f"/DPayloadInclude={stage / 'payload.iss'}",
            f"/DSyntheticTestRoot={data}",
            f"/O{root / 'compiled'}",
            str(PROJECT / "installer/tests/Synthetic.iss"),
        ],
        check=True,
        timeout=120,
    )
    return root / "compiled" / f"Studium-Synthetic-Setup-{version}.exe", stage


def short_path(path):
    function = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    function.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    function.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    count = function(str(path), buffer, len(buffer))
    if not count or count >= len(buffer):
        return None
    return Path(buffer.value) if buffer.value.casefold() != str(path).casefold() else None


def make_link(link, target, kind):
    if kind == "symlink":
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
            return True
        except OSError as error:
            if error.winerror in (5, 50, 1314):
                return False
            raise
    command = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        check=False,
    )
    return command.returncode == 0 and link.is_junction()


def check_payload(program, stage, unknown):
    manifest = json.loads((stage / "payload-manifest.json").read_text(encoding="utf8"))
    expected = {entry["path"] for entry in manifest["files"]}
    for entry in manifest["files"]:
        target = program / entry["path"]
        assert target.stat().st_size == entry["size"]
        assert hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]
    actual = {name for name, value in tree_snapshot(program).items() if value[0] == "file"}
    assert actual - expected == {RECEIPT_NAME, "unins000.exe", "unins000.dat", *unknown}
    assert (program / RECEIPT_NAME).read_bytes() == (stage / RECEIPT_NAME).read_bytes()
    registration = registry_snapshot()
    assert registration, "Missing fixture registration"
    for values in registration.values():
        by_name = {name: value for name, value, _kind in values}
        assert by_name["DisplayVersion"] == manifest["version"]
        assert (
            by_name["StudiumPayloadSHA256"]
            == hashlib.sha256((program / RECEIPT_NAME).read_bytes()).hexdigest()
        ), "Ownership digest missing or stale after install/upgrade/repair"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inno-setup-compiler", type=Path)
    parser.add_argument("--disposable-account", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32" or not args.disposable_account:
        parser.error("Requires native Windows and an explicitly disposable account")
    if registered_install() or registry_snapshot():
        parser.error("Existing application/test registration; nothing was changed")
    compiler = args.inno_setup_compiler or shutil.which("ISCC.exe")
    if not compiler:
        compiler = Path(os.environ["ProgramFiles(x86)"]) / "Inno Setup 6/ISCC.exe"
    if not Path(compiler).is_file():
        parser.error("Install Inno Setup or supply --inno-setup-compiler")
    from studium.infrastructure.user_data import ensure_outside_repository

    results = {}
    with TemporaryDirectory(prefix="studium-security-synthetic-") as temporary:
        root = Path(temporary).resolve()
        ensure_outside_repository(root)
        if any(character in str(root) for character in "'\"\r\n%{}"):
            parser.error("Unsupported synthetic fixture path")
        locations, logs = root / "locations", root / "setup-logs"
        data = locations / "Private Synthetic Profile/Studium"
        data.mkdir(parents=True)
        logs.mkdir()
        with closing(sqlite3.connect(data / "studium.sqlite")) as connection:
            connection.execute("CREATE TABLE synthetic (value TEXT)")
            connection.execute("INSERT INTO synthetic VALUES ('Synthetic row')")
            connection.commit()
        (data / "files").mkdir()
        (data / "files/attachment.txt").write_bytes(b"Synthetic attachment")
        (data / "preferences.json").write_bytes(b'{"synthetic": true}')
        (locations / "sentinel.txt").write_bytes(b"Synthetic ancestor sentinel")
        old, old_stage = compile_fixture(root / "old", compiler, data, "1.9.0", True)
        new, new_stage = compile_fixture(root / "new", compiler, data, "1.10.0", False)
        program = locations / "Отдельная Программа/Missing Parent/Studium"
        try:
            for name, target in {
                "data-root": data,
                "data-ancestor": data.parent,
                "data-descendant-missing": data / "missing/child",
            }.items():
                assert_refused(old, target, locations, logs / f"{name}.log")
                results[name] = "PASS (exit 7; files/data/registration unchanged)"
            alias = short_path(data)
            if alias:
                assert_refused(old, alias, locations, logs / "8dot3.log")
                assert_refused(old, alias / "absent/child", locations, logs / "8dot3-missing.log")
                results["8dot3-alias"] = "PASS (existing and missing destination)"
            else:
                results["8dot3-alias"] = "NOT RUN (volume supplied no alternative short path)"

            moved_data = data.with_name("Synthetic saved data")
            data.rename(moved_data)
            try:
                assert_refused(old, Path(str(data) + "."), locations, logs / "missing-data-dot.log")
                results["missing-data-root-trailing-dot-alias"] = "PASS"
            finally:
                moved_data.rename(data)

            for kind in ("junction", "symlink"):
                link = locations / f"{kind}-alias"
                if make_link(link, data.parent, kind):
                    try:
                        assert_refused(
                            old, link / "Studium", locations, logs / f"{kind}-ancestor.log"
                        )
                        assert_refused(old, link, locations, logs / f"{kind}-target.log")
                        results[f"{kind}-target-and-ancestor"] = "PASS"
                    finally:
                        link.unlink() if kind == "symlink" else link.rmdir()
                else:
                    results[f"{kind}-target-and-ancestor"] = "NOT RUN (link creation unavailable)"
            # Missing, separate destination: real native install, with unrelated sentinel preserved.
            program.parents[1].mkdir()
            outside_sentinel = program.parents[1] / "keep-outside-program.txt"
            outside_sentinel.write_bytes(b"Synthetic separate ancestor sentinel")
            data_before = tree_snapshot(data)
            assert not program.exists()
            assert run_setup(old, program, logs / "fresh.log") == 0
            check_payload(program, old_stage, set())
            assert tree_snapshot(data) == data_before
            results["separate-directory-fresh-install"] = "PASS"
            # Exercise links after ownership is established: a fresh directory with
            # _internal would already fail the unrelated/pre-inventory guard.
            for kind in ("junction", "symlink"):
                for name, relative in {
                    "payload-directory": "_internal/PySide6/plugins",
                    "obsolete-directory": "_internal/retired",
                }.items():
                    link = program / relative
                    saved = locations / f"saved-{kind}-{name}"
                    link.rename(saved)
                    # If redirected deletion followed the link, it would delete
                    # this byte-identical synthetic data file.
                    protected = data / "retired.dll"
                    protected.write_bytes(
                        (program / "_internal/retired/retired.dll").read_bytes()
                        if name == "payload-directory"
                        else (saved / "retired.dll").read_bytes()
                    )
                    created = False
                    try:
                        created = make_link(link, data, kind)
                        if created:
                            assert_refused(new, program, locations, logs / f"{kind}-{name}.log")
                            results[f"{kind}-{name}"] = (
                                "PASS (owned upgrade refused; files/data/registration unchanged)"
                            )
                        else:
                            results[f"{kind}-{name}"] = "NOT RUN (link creation unavailable)"
                    finally:
                        if created:
                            link.unlink() if kind == "symlink" else link.rmdir()
                        saved.rename(link)
                        protected.unlink()
                    assert tree_snapshot(data) == data_before
            sentinel = program / "keep-me.txt"
            sentinel.write_bytes(b"Synthetic unrelated file; installer does not own it")
            sentinel_before = sentinel.read_bytes()
            nested_sentinel = program / "_internal/retired/keep-me.txt"
            nested_sentinel.write_bytes(b"Synthetic unrelated file inside a retired directory")
            unknown = {"keep-me.txt", "_internal/retired/keep-me.txt"}
            nested_before = nested_sentinel.read_bytes()

            # An altered previous receipt must not permit deletion, copy or registry updates.
            receipt = program / RECEIPT_NAME
            receipt_before = receipt.read_bytes()
            receipt.unlink()
            assert_refused(new, program, locations, logs / "missing-receipt.log")
            receipt.write_bytes(receipt_before)
            results["missing-ownership-receipt"] = "PASS"
            receipt.write_bytes((new_stage / RECEIPT_NAME).read_bytes())
            assert_refused(new, program, locations, logs / "substituted-receipt.log")
            receipt.write_bytes(receipt_before)
            results["substituted-ownership-receipt"] = "PASS"
            receipt.write_bytes(receipt_before + b"Synthetic tampering\n")
            assert_refused(new, program, locations, logs / "receipt-tampering.log")
            receipt.write_bytes(receipt_before)
            results["changed-ownership-receipt"] = "PASS"
            # Deliberately update only the fixture marker to exercise path validation
            # after the digest check. No production registry values are ever written.
            entry = receipt_before.decode("ascii").splitlines()[1]
            invalid_paths = [
                r"..\outside.dll",
                r"C:\outside.dll",
                r"_internal\..\outside.dll",
                r"unowned.dll",
                r"_internal\library.dll.",
                r"_internal\CON.dll",
            ]
            try:
                for index, invalid in enumerate(invalid_paths):
                    receipt.write_text(
                        "STUDIUM-PAYLOAD-1\n" + entry[:65] + invalid + "\n", encoding="ascii"
                    )
                    set_fixture_receipt_digest(receipt)
                    assert_refused(new, program, locations, logs / f"invalid-receipt-{index}.log")
                receipt.write_text(
                    "STUDIUM-PAYLOAD-1\n" + entry + "\n" + entry + "\n", encoding="ascii"
                )
                set_fixture_receipt_digest(receipt)
                assert_refused(new, program, locations, logs / "duplicate-receipt.log")
                results["invalid-paths-and-duplicate-ownership-entry"] = "PASS"
            finally:
                receipt.write_bytes(receipt_before)
                set_fixture_receipt_digest(receipt)
            retired = program / "_internal/retired/retired.dll"
            retired_before = retired.read_bytes()
            retired.write_bytes(b"MZ modified synthetic owned DLL")
            assert_refused(new, program, locations, logs / "changed-old-file.log")
            retired.write_bytes(retired_before)
            results["changed-owned-file"] = "PASS"

            assert run_setup(new, program, logs / "upgrade.log") == 0
            check_payload(program, new_stage, unknown)
            assert not retired.exists()
            assert not (program / "_internal" / RESOURCE_ROOTS[1] / "retired.md").exists()
            assert tree_snapshot(data) == data_before
            assert sentinel.read_bytes() == sentinel_before
            assert nested_sentinel.read_bytes() == nested_before
            results["fixture-1.9.0-to-1.10.0-upgrade"] = (
                "PASS (obsolete DLL/help removed; unknown file/data preserved)"
            )
            assert_refused(old, program, locations, logs / "numeric-downgrade.log")
            results["numeric-downgrade-refused-before-changes"] = "PASS"
            repair_target = program / "_internal/PySide6/Qt6Core.dll"
            for fault in ("deleted", "corrupted"):
                if fault == "deleted":
                    repair_target.unlink()
                else:
                    repair_target.write_bytes(b"Synthetic corruption of an owned current file")
                assert run_setup(new, program, logs / f"repair-{fault}.log") == 0
                check_payload(program, new_stage, unknown)
                assert tree_snapshot(data) == data_before
                results[f"repair-{fault}-owned-file"] = "PASS"
            assert run_setup(new, program, logs / "repair.log") == 0
            check_payload(program, new_stage, unknown)
            results["same-version-repair"] = "PASS"
            uninstall(program)
            assert not registry_snapshot()
            assert tree_snapshot(data) == data_before
            assert sentinel.read_bytes() == sentinel_before
            assert nested_sentinel.read_bytes() == nested_before
            assert not (program / RECEIPT_NAME).exists()
            assert not (program / "Studium.exe").exists()
            results["uninstall-preserves-data-and-unknown-file"] = "PASS"
        finally:
            # Cleanup only the fixture's own registration, never an existing application.
            if registry_snapshot() and (program / "unins000.exe").exists():
                uninstall(program)
        print(
            json.dumps(
                {
                    "native_security_regressions": results,
                    "real_application_newer_release_acceptance": "NOT RUN (synthetic fixture versions)",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
