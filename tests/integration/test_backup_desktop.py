"""Synthetic Qt recovery workflows, cancellation, worker affinity and compact themes."""

import time
from pathlib import Path
from threading import Event, get_ident

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QScrollArea

from studium.application.errors import ApplicationError
from studium.composition import create_runtime
from studium.presentation.desktop.backup import BackupPanel
from studium.presentation.desktop.messages import APPLICATION_ERRORS
from studium.presentation.desktop.theme import apply_theme
from tests.integration.test_backup_recovery import tree_bytes
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app
from tests.integration.test_reporting import database_facts


def idle(panel):
    deadline = time.monotonic() + 15
    while panel.control is not None and time.monotonic() < deadline:
        QTest.qWait(10)
        time.sleep(0.002)
    assert panel.control is None, "Synthetic recovery worker did not finish"
    QApplication.processEvents()


def open_panel(window):
    window.show_settings()
    return window.backup_panel


@pytest.fixture
def worker_failures(monkeypatch):
    """Expose stable failure metadata without printing exception payloads or paths."""
    failures = []
    start = BackupPanel.start

    def observed_start(panel, action, success, failure=None):
        def observed_failure(error):
            key = str(error) if isinstance(error, ApplicationError) else None
            failures.append(
                {
                    "exception_type": type(error).__name__,
                    "application_code": key if key in APPLICATION_ERRORS else "redacted",
                    "ui_message": panel.result.text(),
                }
            )
            if failure:
                failure(error)

        return start(panel, action, success, observed_failure)

    monkeypatch.setattr(BackupPanel, "start", observed_start)
    return failures


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ApplicationError("backup_source_changed"), "backup_source_changed"),
        (ApplicationError("synthetic private payload"), "redacted"),
        (OSError("synthetic private payload"), "redacted"),
    ],
)
def test_worker_failure_diagnostics_are_safe(desktop, worker_failures, error, code):
    window, *_ = desktop
    panel = open_panel(window)

    def fail(_):
        raise error

    panel.start(fail, lambda _: pytest.fail("Unexpected success"))
    idle(panel)
    assert worker_failures == [
        {
            "exception_type": type(error).__name__,
            "application_code": code,
            "ui_message": panel.result.text(),
        }
    ]
    assert "synthetic private payload" not in str(worker_failures)


@pytest.mark.parametrize("action", ["create", "verify", "restore_preview"])
def test_file_dialog_cancellation_has_no_side_effects(desktop, monkeypatch, action):
    window, runtime, *_ = desktop
    panel = open_panel(window)
    root = Path(runtime.diagnostics.data_directory)
    before = tree_bytes(root), database_facts(runtime._engine)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: ("", ""))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: ("", ""))
    getattr(panel, action)()
    assert panel.control is None and panel.preview_dialog is None
    assert (tree_bytes(root), database_facts(runtime._engine)) == before


def test_ui_create_verify_preview_restore_and_runtime_open(
    desktop, monkeypatch, tmp_path_factory, worker_failures
):
    window, runtime, *_ = desktop
    panel = open_panel(window)
    external = tmp_path_factory.mktemp("synthetic-recovery")
    archive, destination = external / "synthetic.zip", external / "restored"
    destination.mkdir()
    before = database_facts(runtime._engine), tree_bytes(Path(runtime.diagnostics.data_directory))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(archive), ""))
    panel.create()
    assert not panel.create_button.isEnabled() and not panel.progress.isHidden()
    idle(panel)
    assert archive.exists(), worker_failures
    assert "создана и проверена" in panel.result.text()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(archive), ""))
    panel.verify()
    idle(panel)
    assert "успешно" in panel.result.text()
    panel.restore_preview()
    dialog = panel.preview_dialog
    assert not dialog.restore_button.isEnabled()
    idle(panel)
    assert dialog.restore_button.isEnabled()
    for label in (
        "Создана (UTC)",
        "Studium",
        "Схема",
        "Управляемых файлов",
        "Общий размер",
        "успешно",
    ):
        assert label in dialog.summary.text()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_: "")
    dialog.select_destination()
    assert panel.control is None and list(destination.iterdir()) == []
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_: str(destination))
    dialog.select_destination()
    idle(panel)
    assert "отдельный каталог" in panel.result.text()
    recovered = create_runtime(destination)
    try:
        assert database_facts(recovered._engine) == before[0]
    finally:
        recovered.close()
    assert (
        database_facts(runtime._engine),
        tree_bytes(Path(runtime.diagnostics.data_directory)),
    ) == before


def test_invalid_archive_disables_restore_and_shows_error(desktop, monkeypatch, tmp_path_factory):
    window, *_ = desktop
    panel = open_panel(window)
    archive = tmp_path_factory.mktemp("synthetic-invalid") / "invalid.zip"
    archive.write_bytes(b"Synthetic truncated archive")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(archive), ""))
    panel.restore_preview()
    idle(panel)
    dialog = panel.preview_dialog
    assert not dialog.restore_button.isEnabled()
    assert "недоступно" in dialog.summary.text() and "повреждён" in panel.result.text()
    dialog.reject()


def test_unsafe_save_reports_error_without_writing(desktop, monkeypatch):
    window, runtime, *_ = desktop
    panel = open_panel(window)
    root = Path(runtime.diagnostics.data_directory)
    before = tree_bytes(root)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(root / "unsafe.zip"), ""))
    panel.create()
    idle(panel)
    assert "вне Git" in panel.result.text() and tree_bytes(root) == before


@pytest.mark.parametrize("close", [False, True])
@pytest.mark.windows
def test_long_operation_keeps_gui_responsive_and_cancels_safely(desktop, monkeypatch, close):
    window, runtime, *_ = desktop
    panel = open_panel(window)
    entered, release = Event(), Event()
    gui_thread = get_ident()
    worker_threads, callbacks = [], []

    def long_work(control):
        worker_threads.append(get_ident())
        entered.set()
        while not release.wait(0.01):
            control.report("files", 1, 10)
        control.check()
        return "Synthetic complete"

    panel.start(long_work, lambda _: callbacks.append(get_ident()))
    deadline = time.monotonic() + 5
    while not entered.is_set() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert entered.is_set() and worker_threads[0] != gui_thread
    window.theme_combo.setCurrentIndex(1)
    QTest.qWait(20)
    assert runtime.service.preferred_theme() == "dark"
    if close:
        window.close()
    else:
        panel.cancel_button.click()
    release.set()
    idle(panel)
    assert "отменена" in panel.result.text() and callbacks == []
    panel.start(lambda _: "Synthetic result", lambda _: callbacks.append(get_ident()))
    idle(panel)
    assert callbacks == [gui_thread]


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_settings_health_empty_state_long_strings_and_960_geometry(desktop, tmp_path, theme):
    window, runtime, *_ = desktop
    apply_theme(theme)
    window.resize(960, 620)
    window.show()
    panel = open_panel(window)
    assert "ещё не проверено" in panel.health.text()
    panel.diagnose()
    idle(panel)
    assert "Управляемые файлы: 0" in panel.health.text() and "В порядке" in panel.health.text()
    panel.health.setText(panel.health.text() + "\n" + "synthetic-long-path-" * 100)
    panel.result.setText("Синтетическая длинная строка ошибки " * 100)
    QApplication.processEvents()
    scroll = window.settings_page
    assert isinstance(scroll, QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert window.width() == 960 and window.height() == 620
    assert window.grab().save(str(tmp_path / f"synthetic-settings-{theme}.png"))
    window.open_help("settings")
    assert window.help_page.current_article_id == "settings"


def test_preview_close_cancels_inflight_check(desktop, monkeypatch, tmp_path_factory):
    window, runtime, *_ = desktop
    panel = open_panel(window)
    archive = tmp_path_factory.mktemp("synthetic-cancel") / "unused.zip"
    entered = Event()

    def verify(_, control):
        entered.set()
        while True:
            control.report("verify", 1, 10)
            time.sleep(0.01)

    monkeypatch.setattr(runtime.service.backups, "verify", verify)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(archive), ""))
    panel.restore_preview()
    deadline = time.monotonic() + 5
    while not entered.is_set() and time.monotonic() < deadline:
        QTest.qWait(10)
    panel.preview_dialog.reject()
    idle(panel)
    assert "отменена" in panel.result.text()
