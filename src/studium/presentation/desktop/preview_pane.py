"""Reusable on-demand image/PDF pane using the existing bounded preview pipeline."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget

from studium.presentation.desktop.components import hint, run_action
from studium.presentation.desktop.files import FilePreviewDialog


class FilePreviewPane(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service, self.entries, self.preview = service, (), None
        self.setMinimumWidth(220)
        self.layout = QVBoxLayout(self)
        hint(self.layout, "Предпросмотр условия").setProperty("role", "subheading")
        self.selector = QComboBox()
        self.layout.addWidget(self.selector)
        self.placeholder = hint(self.layout, "Выберите задачу для просмотра условия.")
        self.selector.currentIndexChanged.connect(lambda _: run_action(self, self.show_file))

    def set_entries(self, entries, *, placeholder="Нет файлов для предпросмотра."):
        self.clear_preview()
        self.entries = tuple(entries)
        self.selector.blockSignals(True)
        self.selector.clear()
        for entry in self.entries:
            self.selector.addItem(entry.asset.original_filename)
        self.selector.blockSignals(False)
        self.selector.setVisible(len(self.entries) > 1)
        self.placeholder.setText(placeholder)
        self.placeholder.setVisible(not self.entries)
        self.show_file()

    def clear_preview(self):
        if self.preview is not None:
            self.preview.on_navigation_leave()
            self.layout.removeWidget(self.preview)
            self.preview.hide()
            self.preview.deleteLater()
            self.preview = None

    def show_file(self):
        self.clear_preview()
        index = self.selector.currentIndex()
        if not 0 <= index < len(self.entries):
            return
        self.preview = FilePreviewDialog(
            self.service, self.entries[index], self, asynchronous=True, compact=True
        )
        self.preview.setParent(self, Qt.WindowType.Widget)
        self.preview.setMinimumSize(0, 0)
        self.preview.context.hide()
        self.preview.metadata.hide()
        self.layout.addWidget(self.preview, 1)
        self.preview.show()

    def on_navigation_leave(self):
        self.clear_preview()
