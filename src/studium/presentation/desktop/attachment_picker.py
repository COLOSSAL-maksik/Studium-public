"""Staged, reusable file selection: bounded passive previews and zero persistence."""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QImageReader, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import hint, run_action, toolbar

PASSIVE = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
PREVIEW_LIMIT = 64 * 1024 * 1024


def passive_thumbnail(path, maximum=180):
    """Worker returns QImage only; DOC/macros are never opened by this component."""
    path = Path(path)
    if (
        path.is_symlink()
        or path.is_junction()
        or not path.is_file()
        or path.stat().st_size > PREVIEW_LIMIT
    ):
        return QImage()
    if path.suffix.lower() == ".pdf":
        document = QPdfDocument()
        if (
            document.load(str(path)) != QPdfDocument.Error.None_
            or not 1 <= document.pageCount() <= 10000
        ):
            return QImage()
        image = document.render(0, QSize(maximum, maximum))
        document.close()
        return image
    if path.suffix.lower() not in PASSIVE:
        return QImage()
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if not size.isValid() or size.width() * size.height() > 40_000_000:
        return QImage()
    reader.setScaledSize(size.scaled(maximum, maximum, Qt.AspectRatioMode.KeepAspectRatio))
    return reader.read()


class FileList(QListWidget):
    dropped = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(100, 76))
        self.setWordWrap(True)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if (
            self.isEnabled()
            and urls
            and all(url.isLocalFile() and Path(url.toLocalFile()).is_file() for url in urls)
        ):
            self.setProperty("dragActive", True)
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if not self.isEnabled():
            event.ignore()
            return
        self.dropped.emit(
            tuple(Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile())
        )
        event.acceptProposedAction()


class StagedAttachmentPicker(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint(
            layout,
            "Вложения: выберите или перетащите файлы. До сохранения они остаются только в этом списке.",
        )
        self.list = FileList(self)
        self.list.setMinimumHeight(100)
        layout.addWidget(self.list, 1)
        toolbar(
            layout,
            [("+ Файлы", self.choose), ("Предпросмотр", self.preview), ("Убрать", self.remove)],
        )
        self.list.dropped.connect(lambda paths: run_action(self, lambda: self.add_paths(paths)))
        self.list.itemDoubleClicked.connect(lambda _: self.preview())
        self.list.itemClicked.connect(
            lambda item: (
                self.preview()
                if item.data(Qt.ItemDataRole.UserRole).suffix.lower() in PASSIVE
                else None
            )
        )
        self._generation = 0

    @property
    def paths(self):
        return tuple(
            self.list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.list.count())
        )

    def choose(self):
        values, _ = QFileDialog.getOpenFileNames(
            self,
            "Вложения",
            "",
            "Документы и изображения (*.doc *.docx *.pdf *.jpg *.jpeg *.png *.webp);;Все файлы (*)",
        )
        run_action(self, lambda: self.add_paths(values))

    def add_paths(self, values):
        existing = set(self.paths)
        for value in values:
            path = Path(value).absolute()
            if path in existing:
                continue
            if path.is_symlink() or path.is_junction() or not path.is_file():
                raise ValueError("Выберите обычный локальный файл")
            item = QListWidgetItem(
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),
                f"{path.name}\n{path.stat().st_size:,} байт",
            )
            item.setToolTip(str(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.list.addItem(item)
            existing.add(path)
            generation = self._generation

            def loaded(image, path=path, item=item, generation=generation):
                if generation == self._generation and path in self.paths and not image.isNull():
                    item.setIcon(QIcon(QPixmap.fromImage(image)))

            BackgroundCall(self, lambda path=path: passive_thumbnail(path), loaded, lambda _: None)
        self.changed.emit()

    def remove(self):
        self._generation += 1
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self.changed.emit()

    def clear(self):
        self._generation += 1
        self.list.clear()
        self.changed.emit()

    def preview(self):
        item = self.list.currentItem()
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)

        def show(image):
            if path not in self.paths or not path.is_file():
                return
            dialog = QDialog(self)
            dialog.setWindowTitle(path.name)
            dialog.resize(650, 520)
            layout = QVBoxLayout(dialog)
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if image.isNull():
                label.setText(
                    "Для этого формата доступна информация о файле.\nDOC/DOCX и активное содержимое не запускаются."
                )
            else:
                label.setPixmap(QPixmap.fromImage(image))
            layout.addWidget(label, 1)
            hint(layout, f"{path.name} · {path.stat().st_size:,} байт")
            close = QPushButton("Закрыть")
            close.clicked.connect(dialog.accept)
            layout.addWidget(close)
            dialog.exec()

        BackgroundCall(self, lambda: passive_thumbnail(path, 550), show, lambda _: None)
