"""Centralized Windows application data paths and small local preferences."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from studium.application.services import ApplicationError
from studium.domain.value_objects import EntityId


def data_directory(override: Path | None = None) -> Path:
    if override is not None:
        target = override.expanduser().resolve()
    else:
        local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        target = (local / "Studium").expanduser().resolve()
    ensure_outside_repository(target)
    return target


def ensure_outside_repository(target: Path) -> None:
    """Check lexical and resolved paths, including worktrees and linked directories."""
    target = target.absolute()
    checked = set()
    for ancestor in (target, *target.parents):
        resolved = ancestor.resolve()
        for parent in (ancestor, resolved, *resolved.parents):
            if parent in checked:
                continue
            checked.add(parent)
            if (parent / ".git").exists():
                raise ApplicationError("unsafe_data_directory")


@dataclass(frozen=True)
class AppPaths:
    """One runtime root; relative FileAsset keys remain backwards compatible."""

    root: Path

    def __post_init__(self):
        root = self.root.expanduser().resolve()
        ensure_outside_repository(root)
        object.__setattr__(self, "root", root)

    @classmethod
    def resolve(cls, override: Path | None = None) -> "AppPaths":
        return cls(data_directory(override))

    @property
    def database_path(self) -> Path:
        return self.root / "studium.sqlite"

    @property
    def preferences_path(self) -> Path:
        return self.root / "preferences.json"

    @property
    def files_dir(self) -> Path:
        return self.root / "files"

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def temp_dir(self) -> Path:
        return self.root / "temp"


class JsonPreferences:
    def table_widths(self, key):
        tables = self._read().get("table_widths", {})
        values = tables.get(key, []) if isinstance(tables, dict) else []
        return (
            tuple(values)
            if isinstance(values, list) and all(type(v) is int and 60 <= v <= 2000 for v in values)
            else ()
        )

    def save_table_widths(self, key, widths):
        tables = self._read().get("table_widths", {})
        tables = tables if isinstance(tables, dict) else {}
        tables[key] = [v for v in widths if type(v) is int and 60 <= v <= 2000]
        self._save(table_widths=tables)

    def __init__(self, path: Path):
        self.path = path

    def active_term(self) -> EntityId | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8")).get("active_term_id")
            return EntityId(value) if value else None
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def select_term(self, id: EntityId) -> None:
        self._save(active_term_id=id.value)

    def _read(self):
        try:
            values = json.loads(self.path.read_text(encoding="utf8"))
            return values if isinstance(values, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, **changes):
        temporary = self.path.with_suffix(".tmp")
        try:
            values = self._read()
            values.update(changes)
            temporary.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            raise ApplicationError("preferences_unavailable") from None

    def theme(self):
        return "dark" if self._read().get("theme") == "dark" else "light"

    def select_theme(self, theme):
        if theme not in {"light", "dark"}:
            raise ValueError("Unknown theme")
        self._save(theme=theme)

    def recent_offering(self):
        value = self._read().get("recent_offering_id")
        try:
            return EntityId(value) if value else None
        except (ValueError, TypeError):
            return None

    def select_offering(self, id):
        recent = self._read().get("recent_offering_ids", [])
        recent = recent if isinstance(recent, list) else []
        self._save(
            recent_offering_id=id.value,
            recent_offering_ids=[id.value, *[v for v in recent if v != id.value]][:5],
        )

    def recent_offerings(self):
        values = self._read().get("recent_offering_ids", [])
        result = []
        for value in values if isinstance(values, list) else []:
            try:
                result.append(EntityId(value))
            except (ValueError, TypeError):
                continue
        return tuple(result)

    def sidebar_state(self):
        values = self._read().get("sidebar_expanded", [])
        return (
            tuple(i for i in values if type(i) is int and i in (1, 2, 3))
            if isinstance(values, list)
            else ()
        )

    def save_sidebar_state(self, state):
        self._save(sidebar_expanded=[i for i in state if i in (1, 2, 3)])

    def recent_courses(self):
        values = self._read().get("recent_course_ids", [])
        result = []
        for value in values if isinstance(values, list) else []:
            try:
                result.append(EntityId(value))
            except (ValueError, TypeError):
                continue
        return tuple(result)

    def select_course(self, id):
        self._save(
            recent_course_ids=[id.value, *[v.value for v in self.recent_courses() if v != id]][:4]
        )
