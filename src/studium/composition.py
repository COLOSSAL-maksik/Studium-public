"""Composition root: the only bridge between desktop and persistence adapters."""

import platform
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import qVersion
from sqlalchemy import text
from sqlalchemy.engine import Engine

from studium import __version__
from studium.application.backup import BackupService
from studium.application.services import StudiumService
from studium.application.view_models import Diagnostics
from studium.infrastructure.backup import LocalBackup
from studium.infrastructure.database.migrations import upgrade_database
from studium.infrastructure.database.session import create_database_engine, create_session_factory
from studium.infrastructure.database.unit_of_work import repository_set, transaction_factory
from studium.infrastructure.file_preview import QtFileOpener, QtThumbnailCache
from studium.infrastructure.file_storage import LocalFileStorage
from studium.infrastructure.program_exchange import LocalProgramExchange
from studium.infrastructure.user_data import AppPaths, JsonPreferences


@dataclass
class Runtime:
    service: StudiumService
    diagnostics: Diagnostics
    _engine: Engine

    def close(self):
        self._engine.dispose()


def create_runtime(override: Path | None = None) -> Runtime:
    paths = AppPaths.resolve(override)
    directory = paths.root
    directory.mkdir(parents=True, exist_ok=True)
    database_path = paths.database_path
    engine = create_database_engine(database_path)
    try:
        upgrade_database(engine)
        with engine.connect() as connection:
            schema = connection.scalar(text("SELECT version_num FROM alembic_version"))
        sessions = create_session_factory(engine)
        repositories = repository_set(sessions)
        storage = LocalFileStorage(paths.root)
        storage.recover_pending(
            lambda id: repositories.file_assets.find_by_id(id, include_deleted=True)
        )
        service = StudiumService(
            repositories,
            transaction_factory(sessions),
            JsonPreferences(paths.preferences_path),
            file_storage=storage,
            file_opener=QtFileOpener(),
            thumbnails=QtThumbnailCache(storage),
            backups=BackupService(LocalBackup(paths)),
            program_exchange=LocalProgramExchange(paths.root),
        )
        return Runtime(
            service,
            Diagnostics(
                str(database_path),
                str(directory),
                __version__,
                schema,
                platform.python_version(),
                qVersion(),
            ),
            engine,
        )
    except Exception:
        engine.dispose()
        raise
