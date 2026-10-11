"""A palette-aware calendar retaining Qt's month/year and keyboard controls."""

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QColor, QPen, QTextCharFormat
from PySide6.QtWidgets import QApplication, QCalendarWidget, QToolButton

from studium.presentation.desktop.design import colors
from studium.presentation.desktop.icons import icon


class StudyCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGridVisible(False)
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.setMinimumSize(320, 260)
        self.refresh_visual_theme()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.fit_popup)

    def fit_popup(self):
        popup = self.window()
        if popup is self or not popup.windowFlags() & Qt.WindowType.Popup:
            return
        screen = popup.screen() or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        rect = popup.frameGeometry()
        if rect.width() > bounds.width() or rect.height() > bounds.height():
            popup.resize(min(rect.width(), bounds.width()), min(rect.height(), bounds.height()))
            rect = popup.frameGeometry()
        popup.move(
            max(bounds.left(), min(rect.left(), bounds.right() - rect.width() + 1)),
            max(bounds.top(), min(rect.top(), bounds.bottom() - rect.height() + 1)),
        )

    def refresh_visual_theme(self):
        c = colors(QApplication.instance().property("studiumTheme"))
        for object_name, icon_name in (
            ("qt_calendar_prevmonth", "previous"),
            ("qt_calendar_nextmonth", "next"),
        ):
            button = self.findChild(QToolButton, object_name)
            if button:
                button.setIcon(icon(icon_name))
        header = QTextCharFormat()
        header.setForeground(QColor(c.muted))
        header.setBackground(QColor(c.secondary))
        self.setHeaderTextFormat(header)
        weekend = QTextCharFormat()
        weekend.setForeground(QColor(c.muted))
        for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            self.setWeekdayTextFormat(day, weekend)
        self.updateCells()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if date == QDate.currentDate():
            painter.save()
            c = colors(QApplication.instance().property("studiumTheme"))
            painter.setPen(QPen(QColor(c.accent), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
            painter.restore()
