import os
import stat
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QDropEvent, QImage, QPainter, QPdfWriter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from studium.application.errors import ApplicationError
from studium.domain.enums import AttemptResult
from studium.domain.value_objects import UtcInstant
from studium.presentation.desktop.components import run_action
from studium.presentation.desktop.dialogs import HistoryDialog, StudentDetailsDialog
from studium.presentation.desktop.files import FilePreviewDialog
from studium.presentation.desktop.messages import FILE_LABELS
from tests.integration.test_desktop import desktop as desktop
from tests.integration.test_desktop import qt_app as qt_app


@pytest.fixture(autouse=True)
def fail_unexpected_messages(monkeypatch):
    def fail(*_):
        pytest.fail("Unexpected modal message")

    monkeypatch.setattr(QMessageBox, "warning", fail)
    monkeypatch.setattr(QMessageBox, "information", fail)


def image_source(path, format="JPEG"):
    image = QImage(800, 600, QImage.Format.Format_RGB32)
    image.fill(QColor("#e5edf5"))
    assert image.save(str(path), format)
    return path


def target(desktop):
    _, runtime, _, offering, student, assessment = desktop
    service = runtime.service
    work = service.get_or_create_work(student.id, assessment.id)
    attempt = service.add_attempt(work.id, UtcInstant.now(), AttemptResult.PRESENTED)
    return service, work, attempt, student, offering


@pytest.mark.parametrize("extension,format", [("jpg", "JPEG"), ("png", "PNG"), ("webp", "WEBP")])
def test_image_import_preview_thumbnail_delete_and_regenerate(desktop, tmp_path, extension, format):
    service, _, attempt, *_ = target(desktop)
    source = image_source(tmp_path / ("synthetic." + extension), format)
    link = service.import_file_for_attempt(attempt.id, source)
    asset = service.get_file_asset(link.file_asset_id)
    cached = service.get_thumbnail(asset.id)
    assert cached.is_relative_to(tmp_path / "cache/thumbnails")
    assert max(QImage(str(cached)).width(), QImage(str(cached)).height()) == 240
    modified = cached.stat().st_mtime_ns
    assert service.get_thumbnail(asset.id) == cached and cached.stat().st_mtime_ns == modified
    cached.unlink()
    assert service.get_thumbnail(asset.id).exists()
    cached.write_bytes(b"Invalid thumbnail cache")
    assert not QImage(str(service.get_thumbnail(asset.id))).isNull()
    entry = service.list_attempt_attachments(attempt.id)[0]
    preview = FilePreviewDialog(service, entry)
    assert not preview.image.pixmap().isNull()
    assert student_context(entry) in preview.context.text()
    assert service.get_file_asset(asset.id) == asset
    preview.close()


def student_context(entry):
    return entry.student.full_name


def test_cached_thumbnail_cannot_hide_missing_original(desktop, tmp_path):
    service, _, attempt, *_ = target(desktop)
    link = service.import_file_for_attempt(attempt.id, image_source(tmp_path / "synthetic.jpg"))
    cache = service.get_thumbnail(link.file_asset_id)
    path = service.accessible_file_path(link.file_asset_id)
    path.chmod(stat.S_IREAD | stat.S_IWRITE)
    path.unlink()
    with pytest.raises(ApplicationError, match="file_missing"):
        service.get_thumbnail(link.file_asset_id)
    assert cache.exists()


def test_attempt_picker_multi_import_and_separate_attempt_lists(desktop, tmp_path, monkeypatch):
    service, work, attempt, *_ = target(desktop)
    paths = [image_source(tmp_path / "page1.jpg"), image_source(tmp_path / "page2.png", "PNG")]
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *_: ([str(p) for p in paths], ""))
    dialog = HistoryDialog(service, work.id)
    dialog.files.pick_files()
    assert dialog.files.model.rowCount() == 2
    dialog.files.view.selectRow(0)
    assert not dialog.files.thumbnail.pixmap().isNull()
    service.add_attempt(work.id, UtcInstant.now(), AttemptResult.ACCEPTED)
    dialog.refresh()
    dialog.view.selectRow(1)
    assert dialog.files.model.rowCount() == 0
    dialog.view.selectRow(0)
    assert dialog.files.model.rowCount() == 2 and dialog.files.attempt_id == attempt.id
    dialog.close()


def test_student_files_tab_aggregates_and_filters_all_works(desktop, tmp_path):
    service, _, attempt, student, offering = target(desktop)
    path = tmp_path / "synthetic.txt"
    path.write_text("Synthetic only", encoding="utf-8")
    service.import_file_for_attempt(attempt.id, path)
    context = service.list_offerings()[0]
    entry = service.list_students_for_offering(offering.id)[0]
    dialog = StudentDetailsDialog(service, context, entry)
    dialog.tabs.setCurrentWidget(dialog.files)
    for _ in range(100):
        if dialog.files.model.rowCount() == 1:
            break
        QTest.qWait(20)
    assert dialog.tabs.tabText(3) == "Файлы" and dialog.files.model.rowCount() == 1
    row = dialog.files.model.rows[0]
    assert row.student.id == student.id and row.attempt.attempt_no == 1
    assert not hasattr(row.asset, "_sa_instance_state")
    dialog.files.search.setText("not found")
    assert dialog.files.proxy.rowCount() == 0
    dialog.files.search.setText("synthetic")
    assert dialog.files.proxy.rowCount() == 1
    dialog.close()


def test_missing_preview_shows_context_and_metadata(desktop, tmp_path):
    service, _, attempt, *_ = target(desktop)
    link = service.import_file_for_attempt(attempt.id, image_source(tmp_path / "synthetic.jpg"))
    path = service.accessible_file_path(link.file_asset_id)
    path.chmod(stat.S_IREAD | stat.S_IWRITE)
    path.unlink()
    entry = service.list_attempt_attachments(attempt.id)[0]
    preview = FilePreviewDialog(service, entry)
    assert FILE_LABELS[entry.integrity] in preview.metadata.text()
    assert entry.assessment.title in preview.context.text()
    assert "Попытка 1" in preview.context.text()
    assert preview.image is None
    preview.close()


def test_pdf_builtin_preview_and_unknown_metadata(desktop, tmp_path):
    service, _, attempt, *_ = target(desktop)
    path = tmp_path / "synthetic.pdf"
    writer = QPdfWriter(str(path))
    painter = QPainter(writer)
    painter.drawText(200, 300, "Synthetic PDF")
    painter.end()
    del painter, writer
    link = service.import_file_for_attempt(attempt.id, path)
    preview = FilePreviewDialog(service, service.list_attempt_attachments(attempt.id)[0])
    assert preview.pdf_document.pageCount() == 1
    preview.reject()
    binary = tmp_path / "synthetic.bin"
    binary.write_bytes(b"Ordinary synthetic bytes")
    other = service.import_file_for_attempt(attempt.id, binary)
    entry = next(
        e for e in service.list_attempt_attachments(attempt.id) if e.asset.id == other.file_asset_id
    )
    preview = FilePreviewDialog(service, entry)
    assert preview.image is None and "synthetic.bin" in preview.metadata.text()
    assert link.file_asset_id != other.file_asset_id
    preview.close()


def test_drag_drop_local_files_only(desktop, tmp_path):
    service, work, _, *_ = target(desktop)
    dialog = HistoryDialog(service, work.id)
    source = image_source(tmp_path / "dropped.jpg")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    dialog.files.dropEvent(event)
    assert event.isAccepted() and dialog.files.model.rowCount() == 1
    mime.setUrls([QUrl("https://example.invalid/file")])
    event = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    dialog.files.dropEvent(event)
    assert not event.isAccepted()
    dialog.close()


def test_open_adapter_uses_encoded_local_url(desktop, tmp_path, monkeypatch):
    service, _, attempt, *_ = target(desktop)
    source = tmp_path / "synthetic space & quote.txt"
    source.write_text("Synthetic", encoding="utf-8")
    link = service.import_file_for_attempt(attempt.id, source)
    seen = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: seen.append(url) or True)
    service.open_file_asset(link.file_asset_id)
    assert len(seen) == 1 and seen[0].isLocalFile()
    assert Path(seen[0].toLocalFile()) == service.accessible_file_path(link.file_asset_id)
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda _: False)
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[-1]))
    assert run_action(None, lambda: service.open_file_asset(link.file_asset_id)) is None
    assert "Windows" in messages[0]


def test_invalid_image_error_is_friendly_and_does_not_crash(desktop, tmp_path, monkeypatch):
    service, _, attempt, *_ = target(desktop)
    source = tmp_path / "broken.jpg"
    source.write_bytes(b"Not a valid image")
    link = service.import_file_for_attempt(attempt.id, source)
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[-1]))
    assert run_action(None, lambda: service.get_thumbnail(link.file_asset_id)) is None
    assert messages and "формат" in messages[0]
