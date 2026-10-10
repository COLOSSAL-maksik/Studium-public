from pathlib import Path

import pytest

from studium.application.services import ApplicationError
from studium.domain.value_objects import EntityId
from studium.infrastructure.user_data import JsonPreferences, data_directory


def test_standard_windows_location_is_outside_repository(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert data_directory() == tmp_path / "Studium"
    assert data_directory(tmp_path / "dev") == tmp_path / "dev"


def test_misconfigured_location_cannot_create_user_db_in_git(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    with pytest.raises(ApplicationError, match="unsafe_data_directory"):
        data_directory()


def test_corrupt_preferences_fall_back_and_selection_is_persisted(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text("broken", encoding="utf-8")
    prefs = JsonPreferences(path)
    assert prefs.active_term() is None
    id = EntityId.generate()
    prefs.select_term(id)
    assert JsonPreferences(path).active_term() == id
    assert not Path(path.with_suffix(".tmp")).exists()
