"""Build and exercise two genuine packaged app versions; disposable Windows only.

The newer app changes version only in an isolated archive of tracked source.
Synthetic, unused DLL fixtures add/change/remove payload entries. No binary is
published and repository application/dependency versions are never edited.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from check_windows_bundle import RESOURCE_ROOTS, application_version, stage_bundle, validate_bundle
from smoke_installer_windows import product_version, registered_install

PROJECT = Path(__file__).resolve().parents[1]


def next_version(version):
    major, minor, patch = map(int, version.split("."))
    if patch >= 65535:
        raise ValueError("Synthetic test requires a patch component below 65535")
    return f"{major}.{minor}.{patch + 1}"


def compile_installer(compiler, bundle, source, work):
    version = application_version(source)
    assert product_version(bundle / "Studium.exe") == version
    stage = work / "stage"
    stage_bundle(bundle, stage, source)
    output = work / "compiled"
    subprocess.run(
        [
            str(compiler),
            f"/DAppVersion={version}",
            f"/DPayloadInclude={stage / 'payload.iss'}",
            f"/O{output}",
            str(PROJECT / "installer/Studium.iss"),
        ],
        check=True,
        timeout=240,
    )
    installer = output / f"Studium-Setup-{version}.exe"
    assert product_version(installer) == version
    shutil.copyfile(stage / "payload-manifest.json", installer.with_suffix(".payload.json"))
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    installer.with_suffix(".exe.sha256").write_text(
        f"{digest}  {installer.name}\n", encoding="ascii"
    )
    return installer, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disposable-account", action="store_true")
    parser.add_argument("--inno-setup-compiler", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32" or not args.disposable_account:
        parser.error("Requires native Windows and an explicitly disposable account")
    if registered_install():
        parser.error("Existing Studium registration; nothing was changed")
    compiler = args.inno_setup_compiler or shutil.which("ISCC.exe")
    if not compiler:
        compiler = Path(os.environ["ProgramFiles(x86)"]) / "Inno Setup 6/ISCC.exe"
    if not Path(compiler).is_file():
        parser.error("Install Inno Setup or supply --inno-setup-compiler")
    from studium.infrastructure.user_data import ensure_outside_repository

    base_bundle = PROJECT / "dist/Studium"
    before = validate_bundle(base_bundle)
    version = application_version()
    assert product_version(base_bundle / "Studium.exe") == version
    newer = next_version(version)
    with TemporaryDirectory(prefix="studium-two-version-synthetic-") as temporary:
        root = Path(temporary).resolve()
        ensure_outside_repository(root)
        archive = root / "tracked-source.tar"
        subprocess.run(
            ["git", "archive", "--format=tar", f"--output={archive}", "HEAD"],
            cwd=PROJECT,
            check=True,
            timeout=60,
        )
        old_source, new_source = root / "old-source", root / "new-source"
        for source in (old_source, new_source):
            source.mkdir()
            with tarfile.open(archive) as tracked:
                tracked.extractall(source, filter="data")
            assert application_version(source) == version
        for relative, old_text, new_text in (
            ("pyproject.toml", f'version = "{version}"', f'version = "{newer}"'),
            ("src/studium/__init__.py", f'__version__ = "{version}"', f'__version__ = "{newer}"'),
        ):
            path = new_source / relative
            text = path.read_text(encoding="utf8")
            assert text.count(old_text) == 1
            path.write_text(text.replace(old_text, new_text), encoding="utf8")
        assert application_version(new_source) == newer
        old_bundle = root / "old-bundle"
        shutil.copytree(base_bundle, old_bundle)
        assert validate_bundle(old_bundle, old_source) == before
        retired = "_internal/studium-installer-retired.dll"
        changed = "_internal/studium-installer-changed.dll"
        added = "_internal/studium-installer-added.dll"
        (old_bundle / retired).write_bytes(b"MZ Synthetic retired plugin fixture")
        (old_bundle / changed).write_bytes(b"MZ Synthetic old plugin fixture")
        help_relative = Path(RESOURCE_ROOTS[1]) / "installer-synthetic-retired.md"
        help_source = old_source / "src" / help_relative
        help_source.write_bytes(b"# Synthetic retired installer fixture\n")
        shutil.copyfile(help_source, old_bundle / "_internal" / help_relative)

        environment = dict(os.environ, PYTHONPATH=str(new_source / "src"))
        environment.pop("PYTHONHOME", None)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--clean",
                "--noconfirm",
                "--distpath",
                str(root / "new-dist"),
                "--workpath",
                str(root / "new-build"),
                str(new_source / "Studium.spec"),
            ],
            cwd=new_source,
            env=environment,
            check=True,
            timeout=900,
        )
        new_bundle = root / "new-dist/Studium"
        (new_bundle / changed).write_bytes(b"MZ Synthetic changed plugin fixture")
        (new_bundle / added).write_bytes(b"MZ Synthetic added plugin fixture")
        old, old_hash = compile_installer(compiler, old_bundle, old_source, root / "old-setup")
        new, new_hash = compile_installer(compiler, new_bundle, new_source, root / "new-setup")
        assert old_hash != new_hash
        old_files = json.loads(old.with_suffix(".payload.json").read_text())["files"]
        new_files = json.loads(new.with_suffix(".payload.json").read_text())["files"]
        old_entries = {entry["path"]: entry["sha256"] for entry in old_files}
        new_entries = {entry["path"]: entry["sha256"] for entry in new_files}
        assert retired in old_entries and retired not in new_entries
        assert added in new_entries and added not in old_entries
        assert old_entries[changed] != new_entries[changed]
        assert old_entries["Studium.exe"] != new_entries["Studium.exe"]
        subprocess.run(
            [
                sys.executable,
                str(PROJECT / "scripts/smoke_installer_windows.py"),
                "--installer",
                str(old),
                "--upgrade-installer",
                str(new),
                "--disposable-account",
            ],
            check=True,
            timeout=900,
        )
        print(
            json.dumps(
                {
                    "genuine_two_version_packaged_lifecycle": "PASS",
                    "versions": [version, newer],
                    "installer_sha256": [old_hash, new_hash],
                    "added_changed_removed_payload": "PASS",
                    "non_admin_interactive_acceptance": "NOT RUN (CI account is not a client VM)",
                    "release_distribution": "NOT RUN (synthetic versions; binaries deleted)",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
