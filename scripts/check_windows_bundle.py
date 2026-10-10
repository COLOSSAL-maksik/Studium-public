"""Fail closed before packaging a Windows onedir; never read the user's data root."""

import argparse
import ast
import hashlib
import importlib.metadata
import json
import re
import shutil
import stat
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
RESOURCE_ROOTS = (
    "studium/infrastructure/database/migrations",
    "studium/presentation/desktop/help_articles",
)
RESOURCE_SUFFIXES = {
    RESOURCE_ROOTS[0]: {".py", ".sql", ".mako"},
    RESOURCE_ROOTS[1]: {".md", ".json"},
}
PRIVATE_PARTS = {
    "files",
    "fileasset",
    "attachments",
    "backups",
    "exports",
    "logs",
    "cache",
    "temp",
    "tmp",
    "data",
    "runtime",
    "storage",
    "local-data",
    "user-data",
    ".git",
    ".venv",
    ".imports",
    "secrets",
    ".secrets",
}
PRIVATE_NAME = re.compile(
    r"(?:\.env(?:\..*)?|preferences\.json|settings\..*|config\.local\..*|"
    r"credentials.*|service-account.*|.*\.(?:db|sqlite|sqlite3|sqlitedb)(?:-.*)?|"
    r".*\.(?:log|bak|dump|pem|key|p12|pfx|dmp|mdmp|local|tmp|temp))$",
    re.I,
)
RECEIPT_NAME = "studium-payload.txt"
RECEIPT_HEADER = "STUDIUM-PAYLOAD-1"
WINDOWS_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", re.I)


class BundleAuditError(ValueError):
    """A fixed diagnostic message that never contains input paths or contents."""


def application_version(project: Path = PROJECT) -> str:
    version = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf8"))["project"][
        "version"
    ]
    values = ast.parse((project / "src/studium/__init__.py").read_text(encoding="utf8"))
    declared = [
        ast.literal_eval(node.value)
        for node in values.body
        if isinstance(node, ast.Assign)
        and any(isinstance(name, ast.Name) and name.id == "__version__" for name in node.targets)
    ]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or declared != [version]:
        raise BundleAuditError("Application versions must match and use major.minor.patch")
    if any(int(part) > 65535 for part in version.split(".")):
        raise BundleAuditError("Version does not fit Windows version resources")
    return version


def source_resources(project: Path) -> dict[str, Path]:
    return {
        f"_internal/{root}/{path.relative_to(project / 'src' / root).as_posix()}": path
        for root in RESOURCE_ROOTS
        for path in (project / "src" / root).rglob("*")
        if path.is_file()
        and path.suffix in RESOURCE_SUFFIXES[root]
        and "__pycache__" not in path.parts
    }


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dependency_resources(project: Path) -> dict[str, Path]:
    # The pinned PyInstaller setuptools hook collects this one vendor text resource.
    # Never accept arbitrary TXT files, or entire package data directories.
    lock = project / "requirements-build.lock"
    if not lock.is_file():
        return {}
    pinned = re.findall(r"^setuptools==([0-9.]+)$", lock.read_text(encoding="utf8"), re.M)
    distribution = importlib.metadata.distribution("setuptools")
    if pinned != [distribution.version]:
        raise BundleAuditError("Build dependency resource version differs from its lock")
    relative = "setuptools/_vendor/jaraco/text/Lorem ipsum.txt"
    source = Path(distribution.locate_file(relative))
    if not source.is_file() or source.is_symlink() or source.is_junction():
        raise BundleAuditError("Pinned dependency resource is unavailable")
    approved = {f"_internal/{relative}": source}
    # PyInstaller detects MarkupSafe's metadata lookup from Mako. Only the fixed
    # wheel metadata set is needed; never approve an arbitrary dist-info tree.
    runtime_lock = project / "requirements-dev.lock"
    pinned_markup = re.findall(
        r"^markupsafe==([0-9.]+)$", runtime_lock.read_text(encoding="utf8"), re.M | re.I
    )
    markup = importlib.metadata.distribution("markupsafe")
    if pinned_markup != [markup.version]:
        raise BundleAuditError("Runtime dependency metadata version differs from its lock")
    for name in (
        "INSTALLER",
        "METADATA",
        "RECORD",
        "REQUESTED",
        "WHEEL",
        "top_level.txt",
        "licenses/LICENSE.txt",
    ):
        relative = f"markupsafe-{markup.version}.dist-info/{name}"
        source = Path(markup.locate_file(relative))
        if not source.is_file() or source.is_symlink() or source.is_junction():
            raise BundleAuditError("Pinned runtime dependency metadata is unavailable")
        approved[f"_internal/{relative}"] = source
    return approved


def validate_relative_path(relative: str) -> None:
    parts = PurePosixPath(relative).parts
    if (
        not parts
        or PurePosixPath(relative).is_absolute()
        or any(
            not re.fullmatch(r"[A-Za-z0-9_.+ -]+", part)
            or part in {".", ".."}
            or part.endswith((".", " "))
            or WINDOWS_DEVICE.fullmatch(part)
            for part in parts
        )
    ):
        raise BundleAuditError("Unexpected payload path syntax")


def validate_bundle(bundle: Path, project: Path = PROJECT) -> list[dict]:
    # Check lexical ancestors before resolve, so junctions/symlinks cannot hide a data root.
    bundle = bundle.absolute()
    if any(p.is_symlink() or p.is_junction() for p in (bundle, *bundle.parents)):
        raise BundleAuditError("Linked bundle roots are forbidden")
    if not bundle.is_dir() or not (bundle / "Studium.exe").is_file():
        raise BundleAuditError(
            "Build the Windows PyInstaller onedir first (Studium.exe is missing)"
        )
    resources = source_resources(project)
    approved_resources = resources | dependency_resources(project)
    entries, names = [], set()
    for path in sorted(bundle.rglob("*")):
        relative = path.relative_to(bundle).as_posix()
        parts = PurePosixPath(relative).parts
        if (
            path.is_symlink()
            or path.is_junction()
            or not (stat.S_ISREG(path.lstat().st_mode) or path.is_dir())
        ):
            raise BundleAuditError("Linked or special payload entries are forbidden")
        if any(part.lower() in PRIVATE_PARTS for part in parts) or (
            relative != f"_internal/{RESOURCE_ROOTS[1]}/settings.md"
            and PRIVATE_NAME.fullmatch(parts[-1])
        ):
            raise BundleAuditError(
                "Private/runtime payload entry detected; rebuild from a clean checkout"
            )
        validate_relative_path(relative)
        if path.is_dir():
            continue
        if relative.lower() in names:
            raise BundleAuditError("Duplicate case-insensitive payload path")
        names.add(relative.lower())
        if relative in approved_resources:
            if digest(path) != digest(approved_resources[relative]):
                raise BundleAuditError(
                    "Packaged migration/help/vendor resource differs from source; rebuild"
                )
        elif relative == "_internal/base_library.zip":
            with zipfile.ZipFile(path) as archive:
                for entry in archive.infolist():
                    archive_path = PurePosixPath(entry.filename)
                    if (
                        archive_path.is_absolute()
                        or ".." in archive_path.parts
                        or "\\" in entry.filename
                        or archive_path.suffix != ".pyc"
                        or entry.is_dir()
                    ):
                        raise BundleAuditError(
                            "Unexpected entry in Python standard library archive"
                        )
                if archive.testzip() is not None:
                    raise BundleAuditError("Damaged Python standard library archive")
        elif relative == "Studium.exe" or (
            parts[0] == "_internal" and path.suffix.lower() in {".dll", ".pyd"}
        ):
            with path.open("rb") as stream:
                if stream.read(2) != b"MZ":
                    raise BundleAuditError("Expected a Windows executable/library")
        elif relative.startswith("_internal/PySide6/translations/") and path.suffix == ".qm":
            with path.open("rb") as stream:
                if stream.read(16) != bytes.fromhex("3cb86418caef9c95cd211cbf60a1bddd"):
                    raise BundleAuditError("Invalid Qt translation resource")
        else:
            # Documents, images, arbitrary JSON, ZIPs, or extra checkout material are never inputs.
            raise BundleAuditError(
                "Unapproved payload resource; review build inputs before packaging"
            )
        entries.append({"path": relative, "size": path.stat().st_size, "sha256": digest(path)})
    required = {
        "Studium.exe",
        "_internal/base_library.zip",
        "_internal/PySide6/Qt6Core.dll",
        "_internal/PySide6/Qt6Gui.dll",
        "_internal/PySide6/Qt6Widgets.dll",
        "_internal/PySide6/Qt6Pdf.dll",
        "_internal/PySide6/Qt6PdfWidgets.dll",
        "_internal/PySide6/Qt6Charts.dll",
        "_internal/PySide6/plugins/platforms/qwindows.dll",
        *resources,
    }
    if not {p.lower() for p in required}.issubset(names):
        raise BundleAuditError("Incomplete Qt, Alembic or Help Center resources")
    return entries


def stage_bundle(bundle: Path, stage: Path, project: Path = PROJECT) -> None:
    before = validate_bundle(bundle, project)
    # The caller owns a new unique build directory; never merge into an existing tree.
    payload = stage / "payload"
    shutil.copytree(bundle, payload, symlinks=True)
    if validate_bundle(payload, project) != before:
        raise BundleAuditError("Bundle changed while creating its packaging snapshot")
    receipt = stage / RECEIPT_NAME
    receipt.write_text(
        RECEIPT_HEADER
        + "\n"
        + "".join(
            entry["sha256"] + " " + entry["path"].replace("/", "\\") + "\n" for entry in before
        ),
        encoding="ascii",
    )
    lines = [f'#define PayloadReceiptSHA256 "{digest(receipt)}"']
    for entry in before:
        relative = PurePosixPath(entry["path"])
        target = (
            "{app}"
            if relative.parent == PurePosixPath(".")
            else "{app}\\" + str(relative.parent).replace("/", "\\")
        )
        source = str(payload / entry["path"])
        if any(char in source for char in '"\r\n{}'):
            raise BundleAuditError("Unsupported staging path syntax")
        windows_path = str(relative).replace("/", "\\")
        lines.append(
            f'Source: "{source}"; DestDir: "{target}"; Flags: ignoreversion; '
            f"BeforeInstall: CheckDestination('{windows_path}')"
        )
    lines.append(
        f'Source: "{receipt}"; DestDir: "{{app}}"; Flags: ignoreversion; '
        f"BeforeInstall: CheckDestination('{RECEIPT_NAME}')"
    )
    lines.extend(["[Code]", "procedure LoadNewPayload(Files: TStringList);", "begin"])
    for entry in before:
        owned = entry["sha256"] + " " + entry["path"].replace("/", "\\")
        lines.append(f"  Files.Add('{owned}');")
    lines.append("end;")
    (stage / "payload.iss").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    (stage / "payload-manifest.json").write_text(
        json.dumps({"version": application_version(project), "files": before}, indent=2) + "\n",
        encoding="utf8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=PROJECT / "dist/Studium")
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    try:
        if args.version:
            print(application_version())
        elif args.stage:
            stage_bundle(args.bundle, args.stage)
            print("Audited packaging snapshot ready")
        else:
            print(f"Windows payload audit PASS: {len(validate_bundle(args.bundle))} files")
    except BundleAuditError as error:
        parser.exit(1, f"Windows payload audit FAILED: {error}.\n")
    except (OSError, ValueError, zipfile.BadZipFile):
        # File names and underlying exceptions might expose confidential source paths.
        parser.exit(
            1, "Windows payload audit FAILED: missing, private, changed or unapproved inputs.\n"
        )


if __name__ == "__main__":
    main()
