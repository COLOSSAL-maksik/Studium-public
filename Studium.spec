# Windows onedir distribution. Launch Studium/Studium.exe; keep _internal alongside it.
from pathlib import Path
from importlib.util import find_spec
from tempfile import mkdtemp
import os
import shutil
import sys
import tomllib

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

root = Path(SPECPATH)
app_version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
version_tuple = tuple(int(part) for part in app_version.split(".")) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple, OS=0x40004, fileType=1),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "COLOSSAL-maksik"),
            StringStruct("FileDescription", "Studium"),
            StringStruct("FileVersion", app_version),
            StringStruct("InternalName", "Studium"),
            StringStruct("OriginalFilename", "Studium.exe"),
            StringStruct("ProductName", "Studium"),
            StringStruct("ProductVersion", app_version),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)
# Resolve native dependencies from this production Python/Qt and Windows only.
# An editor/tool PATH can contain another ICU DLL with incompatible exports.
windows_root = Path(os.environ["WINDIR"])
os.environ["PATH"] = os.pathsep.join(str(path) for path in (
    Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
    Path(find_spec("PySide6").origin).parent,
    Path(find_spec("shiboken6").origin).parent,
    windows_root / "System32", windows_root,
))
# SQLAlchemy 2.1 ships equivalent Python implementations alongside its optional
# Cython binaries. The frozen Cython processor blocks during import on this host;
# use the unmodified, pinned Python implementation in the portable distribution.
packaging_root = root / "build" / "packaging"
packaging_root.mkdir(parents=True, exist_ok=True)
sqlalchemy_stage = Path(mkdtemp(prefix="sqlalchemy-pure-", dir=packaging_root))
sqlalchemy_source = Path(find_spec("sqlalchemy").origin).parent
shutil.copytree(
    sqlalchemy_source, sqlalchemy_stage / "sqlalchemy",
    ignore=shutil.ignore_patterns("*.pyd", "*.pyc", "__pycache__"),
)
migrations = collect_data_files(
    "studium.infrastructure.database.migrations", include_py_files=True,
    includes=["**/*.py", "**/*.sql", "script.py.mako"],
)
a = Analysis(
    [str(root / "scripts" / "windows_entry.py")],
    pathex=[str(sqlalchemy_stage), str(root / "src")],
    binaries=[],
    datas=migrations + collect_data_files("studium.presentation.desktop.help_articles"),
    hiddenimports=["sqlalchemy.dialects.sqlite", "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtCharts", "studium.presentation.desktop.help_articles"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
    optimize=0,
)
assert not any(name.replace("\\", "/").startswith("sqlalchemy/") for name, _, _ in a.binaries)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Studium", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=True,
    version=version_info,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Studium")
