"""Equal-angle student sectors: radius is factual completion, never ranking."""

import math

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from studium.presentation.desktop.chart_style import chart_colors, style_chart
from studium.presentation.desktop.components import hint, table, toolbar
from studium.presentation.desktop.models import TableModel


class RadialProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.setMinimumSize(280, 240)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = chart_colors()
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width() * 0.36, max(1, self.height() - 70) * 0.42)
        painter.setPen(QPen(self.palette().mid().color(), 1))
        for rate in (0.25, 0.5, 0.75, 1):
            painter.drawEllipse(center, radius * rate, radius * rate)
        sectors = self.data.students if self.data else ()
        if not sectors:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет студентов")
            return
        angle = 360 / len(sectors)
        for i, sector in enumerate(sectors):
            start = 90 - i * angle
            value = sector.progress or 0
            extent = radius * value
            path = QPainterPath(center)
            path.arcTo(
                QRectF(center.x() - extent, center.y() - extent, extent * 2, extent * 2),
                start,
                -angle,
            )
            path.closeSubpath()
            fill = QColor(c.accent)
            fill.setAlpha(175 if i % 2 else 215)
            painter.fillPath(path, fill)
            painter.setPen(QPen(QColor(c.surface), 1))
            painter.drawPath(path)
            radians = math.radians(start - angle / 2)
            point = QPointF(
                center.x() + (radius + 20) * math.cos(radians),
                center.y() - (radius + 20) * math.sin(radians),
            )
            painter.setPen(self.palette().text().color())
            painter.drawText(
                QRectF(point.x() - 22, point.y() - 12, 44, 24),
                Qt.AlignmentFlag.AlignCenter,
                str(i + 1),
            )
        painter.setPen(self.palette().text().color())
        grid = QColor(c.border)
        grid.setAlpha(160)
        painter.setPen(QPen(grid, 0.8))
        for rate in (0.25, 0.5, 0.75, 1):
            painter.drawEllipse(center, radius * rate, radius * rate)
        painter.setPen(QColor(c.muted))
        painter.drawText(8, 18, "Радиус: доля зачтённых работ · 0–100%")

    def mouseMoveEvent(self, event):
        sectors = self.data.students if self.data else ()
        if sectors:
            point = event.position()
            angle = (
                math.degrees(
                    math.atan2(point.x() - self.width() / 2, self.height() / 2 - point.y())
                )
                + 360
            ) % 360
            sector = sectors[min(len(sectors) - 1, int(angle / (360 / len(sectors))))]
            rate = "Нет назначенных работ" if sector.progress is None else f"{sector.progress:.0%}"
            self.setToolTip(f"{sector.label}\nЗачтено: {sector.completed}/{sector.total} · {rate}")


class ProgressCharts(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.mode = QComboBox()
        self.mode.addItems(["Радиальный прогресс группы", "Прогресс по учебным неделям"])
        layout.addWidget(self.mode)
        self.notice = hint(layout, "")
        self.stack = QStackedWidget()
        self.radial = RadialProgress()
        self.chart = QChart()
        self.line = QChartView(self.chart)
        self.line.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.stack.addWidget(self.radial)
        self.stack.addWidget(self.line)
        self.mode.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.table_model = TableModel(
            [
                ("Студент", lambda r: r.label),
                ("Зачтено", lambda r: r.completed),
                ("Выдано", lambda r: r.total),
                ("Доля", lambda r: f"{r.progress:.0%}" if r.progress is not None else "Нет данных"),
            ]
        )
        self.table_view = table(self.table_model)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.stack)
        self.splitter.addWidget(self.table_view)
        self.splitter.setSizes([300, 180])
        self.splitter.splitterMoved.connect(lambda *_: self.persist())
        layout.addWidget(self.splitter, 1)
        toolbar(layout, [("Развернуть таблицу", self.expand_table)])
        self.restored_key = None

    def preference_context(self):
        owner = self.parentWidget()
        while owner and not hasattr(owner, "service_provider"):
            owner = owner.parentWidget()
        if owner and owner.context_provider():
            return owner.service_provider(), "analytics:" + str(
                owner.context_provider().offering.id
            )
        return None, None

    def persist(self):
        service, key = self.preference_context()
        if service:
            service.save_splitter_sizes(key, self.splitter.sizes())

    def expand_table(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Прогресс · таблица")
        dialog.resize(900, 620)
        layout = QVBoxLayout(dialog)
        layout.addWidget(table(self.table_model))
        dialog.exec()

    def update_data(self, data):
        self.data = data
        self.table_model.replace_rows(data.students)
        service, key = self.preference_context()
        if service and self.restored_key != key:
            sizes = service.splitter_sizes(key)
            if len(sizes) == 2:
                self.splitter.blockSignals(True)
                self.splitter.setSizes(list(sizes))
                self.splitter.blockSignals(False)
            self.restored_key = key
        self.radial.data = data
        self.radial.update()
        self.notice.setText(
            data.metric
            + ". Будущие недели пусты. Номера секторов следуют списку ФИО; подсказка показывает студента."
        )
        self.chart.setTheme(
            QChart.ChartTheme.ChartThemeDark
            if QApplication.instance().property("studiumTheme") == "dark"
            else QChart.ChartTheme.ChartThemeLight
        )
        self.chart.removeAllSeries()
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)
            axis.deleteLater()
        series = QLineSeries()
        series.setName("Средняя доля зачтённых работ")
        for point in data.weeks:
            if point.progress is not None:
                series.append(point.week, point.progress * 100)
        self.chart.addSeries(series)
        x, y = QValueAxis(), QValueAxis()
        x.setRange(1, max(2, len(data.weeks)))
        x.setLabelFormat("%.0f")
        x.setTitleText("Учебная неделя")
        y.setRange(0, 100)
        y.setTitleText("Зачтено, %")
        self.chart.addAxis(x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(x)
        series.attachAxis(y)
        self.refresh_visual_theme()

    def refresh_visual_theme(self):
        style_chart(self.chart)
        self.radial.update()
