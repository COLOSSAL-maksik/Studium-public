"""A palette-aware calendar retaining Qt's month/year and keyboard controls."""

from PySide6.QtCore import QDate, Qt
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
