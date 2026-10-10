"""Shared week selection, direct calendar selection and Explorer file drops."""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout

from studium.domain.value_objects import AcademicWeekNumber
from studium.presentation.desktop.calendar import StudyCalendar


def data_index(field, value):
    """Qt's QVariant comparison cannot compare our Python UUID value objects."""
    return next((i for i in range(field.count()) if field.itemData(i) == value), -1)


def week_label(week):
    if week is None:
        return "Не задана"
    return f"{week.value} неделя — {'числитель' if week.numerator else 'знаменатель'}"


class WeekSelector(QComboBox):
    def __init__(self, value=None, *, weeks=17):
        super().__init__()
        self.addItem("Не задана", None)
        for number in range(1, weeks + 1):
            week = AcademicWeekNumber(number)
            self.addItem(week_label(week), week)
        self.setCurrentIndex(value.value if value and value.value <= weeks else 0)


def direct_calendar(field):
    field.setCalendarPopup(True)
    if not isinstance(field.calendarWidget(), StudyCalendar):
        field.setCalendarWidget(StudyCalendar(field))
    calendar = field.calendarWidget()
    calendar.setGridVisible(False)
    calendar.clicked.connect(field.setDate)
    calendar.activated.connect(field.setDate)
    return field


class FileDropZone(QFrame):
    pathsDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fileDropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(136)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("Перетащите файлы сюда")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.picker = QPushButton("Выбрать файлы…")
        self.picker.clicked.connect(self.pick)
        layout.addWidget(self.picker)

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.pick()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.EnabledChange:
            self.highlight(False)
        super().changeEvent(event)

    def pick(self):
        if not self.isEnabled():
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Добавить файлы")
        if paths:
            self.pathsDropped.emit(paths)

    def paths(self, event):
        urls = event.mimeData().urls()
        if (
            not self.isEnabled()
            or not urls
            or not all(url.isLocalFile() and Path(url.toLocalFile()).is_file() for url in urls)
        ):
            return []
        return [url.toLocalFile() for url in urls]

    def highlight(self, enabled):
        self.setProperty("dragActive", enabled)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if self.paths(event):
            self.highlight(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.highlight(False)
        event.accept()

    def dropEvent(self, event):
        self.highlight(False)
        paths = self.paths(event)
        if paths:
            self.pathsDropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
