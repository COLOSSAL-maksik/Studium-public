"""Small file sections in existing history/student dialogs, without ORM access."""

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from studium.application.errors import ApplicationError
from studium.application.file_ports import FileIntegrity
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import (
    confirm,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.messages import FILE_LABELS, TEXT
from studium.presentation.desktop.models import TableModel, display_time
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.theme import resize_to_screen
from studium.presentation.desktop.widgets import search_shortcut
from studium.presentation.desktop.workflow_widgets import FileDropZone


class FilePreviewDialog(QDialog):
    def __init__(self, service, entry, parent=None, *, asynchronous=False, compact=False):
        super().__init__(parent)
        self.service, self.entry = service, entry
        self.compact = compact
        self.preview_closed = False
        self.setWindowTitle(TEXT["file_preview"])
        resize_to_screen(self, 920, 720)
        layout = QVBoxLayout(self)
        if compact:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)
        if hasattr(entry, "material"):
            context_text = entry.material.title
        elif hasattr(entry, "message"):
            context_text = f"{entry.student.full_name}\n{entry.case.title or TEXT['questions']}\n{TEXT['message']} · {display_time(entry.message.sent_at)}"
        else:
            context_text = f"{entry.student.full_name}\n{entry.assessment.title}\n{TEXT['file_attempt']} {entry.attempt.attempt_no} · {display_time(entry.attempt.occurred_at)}"
        self.context = hint(layout, context_text)
        self.context.setTextFormat(Qt.TextFormat.PlainText)
        self.metadata = hint(
            layout,
            f"{entry.asset.original_filename}\n{entry.asset.mime_type} · {entry.asset.size_bytes:,} {TEXT['file_bytes']} · {FILE_LABELS[entry.integrity]}\nSHA-256: {entry.asset.sha256}",
        )
        self.metadata.setTextFormat(Qt.TextFormat.PlainText)
        toolbar(
            layout,
            [
                (
                    TEXT["open"],
                    lambda: run_action(self, lambda: service.open_file_asset(entry.asset.id)),
                )
            ],
        )
        self.image = None
        if entry.integrity != FileIntegrity.AVAILABLE:
            hint(layout, TEXT["file_" + entry.integrity.value + "_hint"])
        elif entry.asset.mime_type.startswith("image/"):
            self.image = QLabel()
            self.image.setAccessibleName("Изображение условия")
            self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_pixmap = QPixmap()
            self.fit = QCheckBox(TEXT["file_fit"])
            self.fit.setChecked(True)
            self.fit.toggled.connect(self.scale_image)
            layout.addWidget(self.fit)
            self.fit.setVisible(not compact)
            self.scroll = QScrollArea()
            self.scroll.setWidget(self.image)
            self.scroll.setWidgetResizable(True)
            layout.addWidget(self.scroll, 1)
            if asynchronous:
                self.image.setText(TEXT["files_loading"])
                BackgroundCall(
                    self,
                    lambda: service.image_preview(entry.asset.id),
                    self.load_image,
                    self.preview_error,
                )
            else:
                self.load_image(service.image_preview(entry.asset.id))
        elif entry.asset.mime_type == "application/pdf":
            if asynchronous:
                self.loading = hint(layout, TEXT["files_loading"])
                BackgroundCall(
                    self,
                    lambda: service.accessible_file_path(entry.asset.id),
                    lambda path: self.load_pdf(layout, path),
                    self.preview_error,
                )
            else:
                self._pdf(layout)
        else:
            hint(layout, TEXT["file_metadata_only"])
        if self.image is None and not hasattr(self, "pdf_view"):
            layout.addStretch()

    def scale_image(self):
        if self.preview_pixmap.isNull():
            return
        if self.fit.isChecked():
            self.image.setMinimumSize(1, 1)
            pixmap = self.preview_pixmap.scaled(
                self.scroll.viewport().size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pixmap = self.preview_pixmap
            self.image.setMinimumSize(pixmap.size())
        self.image.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "image", None) is not None:
            self.scale_image()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "image", None) is not None:
            self.scale_image()

    def load_image(self, path):
        if self.preview_closed:
            return
        self.preview_pixmap = QPixmap(str(path))
        self.scale_image()

    def preview_error(self, error):
        if self.preview_closed:
            return
        from studium.presentation.desktop.messages import error_message

        label = self.image if self.image is not None else self.loading
        label.setText(error_message(error))

    def load_pdf(self, layout, path):
        if self.preview_closed:
            return
        if hasattr(self, "loading"):
            self.loading.hide()
        run_action(self, lambda: self._pdf(layout, path))

    def _pdf(self, layout, path=None):
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView
        except ImportError:
            hint(layout, TEXT["file_pdf_external"])
            return
        self.pdf_document = QPdfDocument(self)
        path = path or self.service.accessible_file_path(self.entry.asset.id)
        if self.pdf_document.load(str(path)) != QPdfDocument.Error.None_:
            raise ApplicationError("file_preview_invalid")
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_document)
        self.pdf_view.setPageMode(
            QPdfView.PageMode.SinglePage if self.compact else QPdfView.PageMode.MultiPage
        )
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addWidget(self.pdf_view, 1)

    def on_navigation_leave(self):
        self.preview_closed = True
        if hasattr(self, "pdf_document"):
            self.pdf_view.setDocument(None)
            self.pdf_document.close()

    def done(self, result):
        self.on_navigation_leave()
        super().done(result)


class FilesWidget(QWidget):
    def __init__(
        self,
        service,
        *,
        student_id=None,
        editable=True,
        lazy=False,
        asynchronous=False,
        compact=False,
        parent=None,
    ):
        super().__init__(parent)
        self.service, self.student_id = service, student_id
        self.asynchronous, self.generation = asynchronous, 0
        self.attempt_id = None
        self.editable = editable and student_id is None
        self.setAcceptDrops(self.editable)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heading = hint(layout, TEXT["files"])
        self.drop_zone = FileDropZone(self)
        self.drop_zone.pathsDropped.connect(self.import_paths)
        self.drop_zone.setVisible(self.editable)
        self.drop_zone.setEnabled(False)
        layout.addWidget(self.drop_zone)
        self.model = TableModel(
            [
                (TEXT["occurred_at"], lambda e: display_time(e.attempt.occurred_at)),
                (TEXT["assessment_title"], lambda e: e.assessment.title),
                (TEXT["file_attempt"], lambda e: e.attempt.attempt_no),
                (TEXT["file_name"], lambda e: e.asset.original_filename),
                (TEXT["type"], lambda e: e.asset.mime_type),
                (TEXT["status"], lambda e: FILE_LABELS[e.integrity]),
            ]
        )
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search = QLineEdit()
        self.search.setPlaceholderText(TEXT["file_search"])
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.search.setVisible(not compact)
        layout.addWidget(self.search)
        search_shortcut(self, self.search)
        self.view = table(self.proxy, stretch=False)
        for i, width in enumerate((140, 135, 65, 220, 140, 150)):
            self.view.setColumnWidth(i, width)
        if student_id is None:
            for column in (0, 1, 2):
                self.view.hideColumn(column)
        self.view.setMinimumHeight(60 if compact else 115)
        layout.addWidget(self.view, 1)
        actions = []
        if student_id is None and self.editable:
            actions.append((TEXT["file_add"], lambda: run_action(self, self.pick_files)))
        actions += [
            (TEXT["open"], lambda: run_action(self, self.open_selected)),
            (TEXT["file_view"], lambda: run_action(self, self.preview_selected)),
        ]
        if student_id is None and self.editable:
            actions.append((TEXT["file_detach"], lambda: run_action(self, self.detach_selected)))
        actions.append((TEXT["file_refresh"], lambda: run_action(self, self.refresh)))
        row = toolbar(layout, actions)
        self.add_button = row.itemAt(0).widget() if self.editable else None
        self.detach_button = row.itemAt(3).widget() if self.editable else None
        self.empty = hint(layout, TEXT["student_file_empty"] if student_id else TEXT["file_empty"])
        self.thumbnail = QLabel()
        self.thumbnail.setMaximumHeight(110)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.thumbnail.setVisible(not compact)
        layout.addWidget(self.thumbnail)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.preview_selected))
        self.view.selectionModel().currentChanged.connect(
            lambda *_: run_action(self, self.show_thumbnail)
        )
        if not lazy:
            self.refresh()

    def set_attempt(self, attempt):
        self.attempt_id = attempt.id if attempt else None
        self.drop_zone.setEnabled(self.editable and self.attempt_id is not None)
        self.heading.setText(
            TEXT["files"] + (f" · {TEXT['file_attempt']} {attempt.attempt_no}" if attempt else "")
        )
        self.refresh()

    def refresh(self):
        self.generation += 1
        generation = self.generation
        student_id, attempt_id = self.student_id, self.attempt_id
        if self.asynchronous:
            self.model.replace_rows([])
            self.empty.setText(TEXT["files_loading"])
            self.empty.show()
            BackgroundCall(
                self,
                lambda: self.query_files(student_id, attempt_id),
                lambda rows: self.apply_files(rows) if generation == self.generation else None,
                lambda error: self.file_error(error) if generation == self.generation else None,
            )
        else:
            self.apply_files(self.query_files(student_id, attempt_id))

    def query_files(self, student_id, attempt_id):
        if student_id is not None:
            return self.service.list_student_files(student_id)
        elif attempt_id is not None:
            return self.service.list_attempt_attachments(attempt_id)
        return []

    def file_error(self, error):
        from studium.presentation.desktop.messages import error_message

        self.empty.setText(error_message(error))

    def apply_files(self, rows):
        self.model.replace_rows(rows)
        self.empty.setText(
            TEXT["student_file_empty"]
            if self.student_id
            else TEXT["file_empty"]
            if self.editable
            else "У этой попытки нет файлов."
        )
        self.empty.setVisible(not rows)
        self.thumbnail.clear()
        if self.add_button:
            self.add_button.setEnabled(self.editable and self.attempt_id is not None)
            self.detach_button.setEnabled(self.editable and self.attempt_id is not None)

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, TEXT["file_add"], "", TEXT["file_picker_filter"]
        )
        self.import_paths(paths)

    def import_paths(self, paths):
        if not self.editable or self.attempt_id is None:
            raise ApplicationError("file_attempt_required")
        if self.asynchronous and paths:
            attempt_id = self.attempt_id
            self.drop_zone.setEnabled(False)
            self.empty.setText("Импорт файлов…")
            self.empty.show()

            def batch():
                for path in paths:
                    self.service.import_file_for_attempt(attempt_id, path)

            def completed(_):
                self.drop_zone.setEnabled(self.editable and self.attempt_id is not None)
                self.refresh()

            def failed(error):
                self.drop_zone.setEnabled(self.editable and self.attempt_id is not None)
                self.refresh()
                self.file_error(error)
                self.empty.show()

            BackgroundCall(self, batch, completed, failed)
            return
        for path in paths:
            run_action(
                self, lambda path=path: self.service.import_file_for_attempt(self.attempt_id, path)
            )
        self.refresh()

    def open_selected(self):
        entry = selected(self.view)
        if entry:
            self.service.open_file_asset(entry.asset.id)

    def preview_selected(self):
        entry = selected(self.view)
        if entry:
            present_detail(
                FilePreviewDialog(self.service, entry, self, asynchronous=self.asynchronous),
                self,
                title=entry.asset.original_filename,
            )

    def show_thumbnail(self):
        self.thumbnail.clear()
        index = self.view.currentIndex()
        entry = self.proxy.data(index, Qt.ItemDataRole.UserRole) if index.isValid() else None
        if (
            entry
            and entry.integrity == FileIntegrity.AVAILABLE
            and entry.asset.mime_type.startswith("image/")
        ):
            if self.asynchronous:
                generation = self.generation
                BackgroundCall(
                    self,
                    lambda: self.service.get_thumbnail(entry.asset.id),
                    lambda path: self.apply_thumbnail(path, entry, generation),
                    lambda error: self.thumbnail_error(error, entry, generation),
                )
            else:
                self.apply_thumbnail(
                    self.service.get_thumbnail(entry.asset.id), entry, self.generation
                )

    def apply_thumbnail(self, path, entry, generation):
        index = self.view.currentIndex()
        current = self.proxy.data(index, Qt.ItemDataRole.UserRole) if index.isValid() else None
        if generation == self.generation and current == entry:
            self.thumbnail.setPixmap(
                QPixmap(str(path)).scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
            )

    def thumbnail_error(self, error, entry, generation):
        index = self.view.currentIndex()
        current = self.proxy.data(index, Qt.ItemDataRole.UserRole) if index.isValid() else None
        if generation == self.generation and current == entry:
            self.file_error(error)

    def detach_selected(self):
        if not self.editable:
            return
        entry = selected(self.view)
        if entry and confirm(self, TEXT["file_detach_confirm"], action_label=TEXT["file_detach"]):
            self.service.detach_attachment(
                entry.attachment.id, expected_revision=entry.attachment.revision
            )
            self.refresh()

    def dragEnterEvent(self, event):
        if (
            self.editable
            and self.attempt_id is not None
            and event.mimeData().hasUrls()
            and all(url.isLocalFile() for url in event.mimeData().urls())
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if (
            self.editable
            and self.attempt_id is not None
            and event.mimeData().hasUrls()
            and all(url.isLocalFile() for url in event.mimeData().urls())
        ):
            run_action(
                self,
                lambda: self.import_paths([url.toLocalFile() for url in event.mimeData().urls()]),
            )
            event.acceptProposedAction()
        else:
            event.ignore()
