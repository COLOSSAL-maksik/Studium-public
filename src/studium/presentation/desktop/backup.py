"""Settings recovery controls; all IO runs in workers with private SQLite connections."""

import time
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from studium.application.backup import BackupControl
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import hint
from studium.presentation.desktop.messages import error_message

PRIVACY = (
    "ZIP содержит конфиденциальные учебные данные и вложения. Архив не зашифрован. "
    "Храните его в безопасном месте и передавайте только доверенным людям."
)
RESTORE_WARNING = (
    "Восстановление создаст отдельное хранилище в выбранном пустом каталоге. "
    "Текущая база останется активной. Автоматическое переключение не выполняется."
)
PHASES = {
    "snapshot": "Снимок SQLite",
    "database_check": "Проверка SQLite и связей",
    "files": "Проверка управляемых файлов",
    "verify": "Проверка и чтение архива",
    "archive_check": "Контроль целостности архива",
    "publish": "Завершение операции",
}


def size_text(size):
    return f"{size:,} байт".replace(",", " ")


def preview_text(preview):
    return (
        f"Создана (UTC): {preview.created_utc}\n"
        f"Studium: {preview.app_version}\nСхема: {preview.schema_revision}\n"
        f"Управляемых файлов: {preview.file_count}\n"
        f"Снимок БД: {size_text(preview.database_size)}\n"
        f"Общий размер данных: {size_text(preview.total_size)}\n"
        "Проверка: ZIP, SHA-256, SQLite, связи и структура файлов — успешно."
    )


def wrap(label):
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


class _Progress(QObject):
    changed = Signal(str, int, int)


class RestorePreviewDialog(QDialog):
    def __init__(self, panel, archive):
        super().__init__(panel)
        self.panel, self.archive, self.preview = panel, archive, None
        self.setWindowTitle("Просмотр резервной копии")
        self.resize(560, 430)
        layout = QVBoxLayout(self)
        self.summary = wrap(hint(layout, "Проверка архива…"))
        wrap(hint(layout, PRIVACY))
        wrap(hint(layout, RESTORE_WARNING))
        self.restore_button = QPushButton("Выбрать пустой каталог и восстановить…")
        self.restore_button.setEnabled(False)
        self.restore_button.clicked.connect(self.select_destination)
        layout.addWidget(self.restore_button)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.reject)
        layout.addWidget(close)
        self.rejected.connect(panel.cancel_active)

    def verified(self, preview):
        self.preview = preview
        self.summary.setText(preview_text(preview))
        self.restore_button.setEnabled(True)

    def failed(self, error):
        self.summary.setText("Восстановление недоступно. " + error_message(error))
        self.restore_button.setEnabled(False)

    def select_destination(self):
        selected = QFileDialog.getExistingDirectory(
            self, "Выберите отдельный пустой каталог данных"
        )
        if not selected:
            return
        self.accept()
        self.panel.restore_to(self.archive, Path(selected), self.preview)


class BackupPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window, self.control, self.call, self.preview_dialog = window, None, None, None
        self.progress_signal = _Progress(self)
        self.progress_signal.changed.connect(
            self.update_progress, Qt.ConnectionType.QueuedConnection
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint(layout, "Резервная копия и восстановление").setProperty("role", "heading")
        wrap(hint(layout, PRIVACY))
        self.create_button = QPushButton("Создать резервную копию…")
        self.verify_button = QPushButton("Проверить резервную копию…")
        self.restore_button = QPushButton("Восстановить в отдельный каталог…")
        self.health_button = QPushButton("Проверить состояние хранилища")
        for button in self.actions:
            layout.addWidget(button)
        self.create_button.clicked.connect(self.create)
        self.verify_button.clicked.connect(self.verify)
        self.restore_button.clicked.connect(self.restore_preview)
        self.health_button.clicked.connect(self.diagnose)
        self.health = wrap(hint(layout, "Состояние хранилища ещё не проверено."))
        self.result = wrap(hint(layout, "Выберите действие. Архив проверяется до восстановления."))
        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setAccessibleName("Прогресс резервного копирования и восстановления")
        self.cancel_button = QPushButton("Отменить операцию")
        self.cancel_button.clicked.connect(self.cancel_active)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.cancel_button)
        layout.addLayout(progress_row)
        self.progress.hide()
        self.cancel_button.hide()

    @property
    def actions(self):
        return (self.create_button, self.verify_button, self.restore_button, self.health_button)

    @property
    def service(self):
        return self.window.service.backups

    def start(self, action, success, failure=None):
        if self.control is not None:
            return
        last = [0.0, None]

        def progress(phase, completed, total):
            now = time.monotonic()
            if now - last[0] >= 0.08 or phase != last[1]:
                # Qt signals are the only Qt interaction in the worker.
                self.progress_signal.changed.emit(
                    phase, int(1000 * completed / total) if total else 0, int(bool(total))
                )
                last[:] = now, phase

        control = BackupControl(progress)
        self.control = control
        for button in self.actions:
            button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self.result.setText("Операция выполняется…")

        def finished(result):
            self.idle()
            success(result)

        def failed(error):
            self.idle()
            self.result.setText(error_message(error))
            if failure:
                failure(error)

        self.call = BackgroundCall(self, lambda: action(control), finished, failed)

    def idle(self):
        self.control, self.call = None, None
        for button in self.actions:
            button.setEnabled(True)
        self.progress.hide()
        self.cancel_button.hide()

    @Slot(str, int, int)
    def update_progress(self, phase, completed, has_total):
        if self.control is None:
            return
        self.result.setText(PHASES.get(phase, "Операция выполняется…"))
        self.progress.setRange(0, 1000 if has_total else 0)
        self.progress.setValue(completed)

    def cancel_active(self):
        if self.control is not None:
            self.control.cancel()
            self.cancel_button.setEnabled(False)
            self.result.setText("Отмена и удаление временных файлов…")

    def create(self):
        selected, _ = QFileDialog.getSaveFileName(
            self, "Создать резервную копию", "studium-backup.zip", "ZIP (*.zip)"
        )
        if not selected:
            return
        destination = Path(selected)
        service = self.service
        self.start(
            lambda control: service.create(destination, control),
            lambda preview: self.result.setText(
                "Резервная копия создана и проверена.\n" + preview_text(preview)
            ),
        )

    def select_archive(self):
        selected, _ = QFileDialog.getOpenFileName(
            self, "Выберите резервную копию Studium", "", "ZIP (*.zip)"
        )
        return Path(selected) if selected else None

    def verify(self):
        archive = self.select_archive()
        if archive is None:
            return
        service = self.service
        self.start(
            lambda control: service.verify(archive, control),
            lambda preview: self.result.setText(preview_text(preview)),
        )

    def restore_preview(self):
        archive = self.select_archive()
        if archive is None:
            return
        if self.preview_dialog is not None:
            self.preview_dialog.deleteLater()
        dialog = RestorePreviewDialog(self, archive)
        self.preview_dialog = dialog
        dialog.open()
        service = self.service

        def verified(preview):
            self.result.setText(preview_text(preview))
            dialog.verified(preview)

        self.start(lambda control: service.verify(archive, control), verified, dialog.failed)

    def restore_to(self, archive, destination, preview):
        service = self.service
        self.start(
            lambda control: service.restore(archive, destination, preview, control),
            lambda root: self.result.setText(
                f"Данные восстановлены в отдельный каталог:\n{root}\n" + RESTORE_WARNING
            ),
        )

    def diagnose(self):
        if self.control is not None:
            return
        service = self.service

        def show(health):
            status = (
                "В порядке"
                if health.database_ok and not (health.missing_files or health.damaged_files)
                else "Требует внимания"
            )
            self.health.setText(
                f"Каталог данных: {health.data_root}\nСхема: {health.schema_revision}\n"
                f"Размер БД: {size_text(health.database_size)}\n"
                f"Управляемые файлы: {health.file_count}, {size_text(health.file_size)}\n"
                f"Целостность: {status}; отсутствуют: {health.missing_files}, повреждены: {health.damaged_files}\n"
                f"Свободное место: {size_text(health.free_bytes) if health.free_bytes is not None else 'Не определяется'}"
            )
            self.result.setText("Диагностика завершена. Пользовательские записи не изменены.")

        self.start(service.diagnose, show)
