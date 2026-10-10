"""Recovery paths never traverse links or publish into Git/active managed storage."""

import os
import stat
from pathlib import Path

from studium.application.errors import ApplicationError
from studium.infrastructure.user_data import data_directory, ensure_outside_repository


def unlinked_path(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise ApplicationError("backup_unsafe_path")
    return path


def external_path(path: Path, active_root: Path) -> Path:
    path = unlinked_path(path)
    ensure_outside_repository(path)
    for root in (active_root, data_directory()):
        if path.is_relative_to(root) or root.is_relative_to(path):
            raise ApplicationError("backup_unsafe_path")
    return path


def file_identity(path: Path) -> tuple | None:
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise ApplicationError("backup_unsafe_path")
    return path_identity(info)


def identity(info: os.stat_result) -> tuple:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def path_identity(info: os.stat_result) -> tuple:
    """Compare path/handle metadata using timestamps with the same meaning.

    Windows CPython stat reports creation in st_ctime_ns, whereas fstat reports
    metadata change. Both expose creation as st_birthtime_ns. Keep raw identity
    for handle-to-handle checks so metadata changes during IO are still rejected.
    """
    return (*identity(info)[:4], getattr(info, "st_birthtime_ns", info.st_ctime_ns))


def empty_destination(path: Path, active_root: Path) -> Path:
    path = external_path(path, active_root)
    if not path.parent.is_dir():
        raise ApplicationError("backup_destination_parent")
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ApplicationError("backup_destination_not_empty")
    return path
