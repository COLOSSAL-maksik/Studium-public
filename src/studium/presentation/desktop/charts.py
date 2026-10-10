"""Qt-native views of the same factual application DTOs, including missing data."""

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QStackedBarSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QTabWidget, QVBoxLayout, QWidget

from studium.presentation.desktop.chart_style import style_chart
from studium.presentation.desktop.components import hint


class AnalyticsCharts(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        hint(
            layout,
            "Графики по записанным фактам. Числа и «Нет данных» доступны на вкладке показателей.",
        )
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.charts = []
        for title in ("Работы и сроки", "Сдачи по неделям", "Посещаемость"):
            chart = QChart()
            chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
            view = QChartView(chart)
            view.setRenderHint(QPainter.RenderHint.Antialiasing)
            view.setMinimumHeight(240)
            self.tabs.addTab(view, title)
            self.charts.append(chart)
        self.notice = hint(layout, "")

    @staticmethod
    def reset(chart, title):
        chart.setTheme(
            QChart.ChartTheme.ChartThemeDark
            if QApplication.instance().property("studiumTheme") == "dark"
            else QChart.ChartTheme.ChartThemeLight
        )
        chart.removeAllSeries()
        for axis in chart.axes():
            chart.removeAxis(axis)
            axis.deleteLater()
        chart.setTitle(title)

    @staticmethod
    def bars(chart, labels, sets, *, stacked=False):
        series = QStackedBarSeries() if stacked else QBarSeries()
        for title, values in sets:
            values_set = QBarSet(title)
            values_set.append([float(value) for value in values])
            series.append(values_set)
        chart.addSeries(series)
        axis = QBarCategoryAxis()
        axis.append(labels)
        chart.addAxis(axis, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis)
        maximum = max(
            (
                sum(values[i] for _, values in sets)
                if stacked
                else max(values[i] for _, values in sets)
                for i in range(len(labels))
            ),
            default=0,
        )
        y = QValueAxis()
        y.setRange(0, max(1, maximum))
        y.setLabelFormat("%.0f")
        chart.addAxis(y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(y)

    def update_data(self, summary, workflow):
        self.summary, self.workflow = summary, workflow
        progress, weeks, attendance = self.charts
        self.reset(progress, "Работы и первая сдача — текущий срез")
        completed = summary.assessments_completed
        started = summary.assessments_started
        self.bars(
            progress,
            ["Начато", "Выполнено", "Вовремя", "Поздно", "Не сдано в срок"],
            [
                (
                    "Количество",
                    [
                        started,
                        completed,
                        summary.on_time_count,
                        summary.late_count,
                        summary.overdue_count,
                    ],
                )
            ],
        )
        self.reset(weeks, "Учебные недели: предъявления и попытки")
        for title, field in [
            ("Первые сдачи", "first_submissions"),
            ("Все попытки", "attempts"),
            ("Зачтённые попытки", "accepted_attempts"),
            ("Работ со сроком на неделе", "planned_due"),
        ]:
            series = QLineSeries()
            series.setName(title)
            for point in workflow.weeks:
                series.append(point.week, getattr(point, field))
            weeks.addSeries(series)
        weeks.createDefaultAxes()
        for axis in weeks.axes(Qt.Orientation.Horizontal):
            axis.setRange(1, max(2, len(workflow.weeks)))
            axis.setLabelFormat("%.0f")
            axis.setTitleText("Учебная неделя")
        for axis in weeks.axes(Qt.Orientation.Vertical):
            axis.setRange(
                0,
                max(
                    1,
                    max(
                        (
                            max(p.attempts, p.first_submissions, p.accepted_attempts, p.planned_due)
                            for p in workflow.weeks
                        ),
                        default=0,
                    ),
                ),
            )
            axis.setLabelFormat("%.0f")
        self.reset(attendance, "Посещаемость: известные отметки")
        self.bars(
            attendance,
            ["Семинары", "Лекции"],
            [
                (title, [getattr(workflow.seminars, field), getattr(workflow.lectures, field)])
                for title, field in [
                    ("Присутствовал", "present"),
                    ("Опоздал", "late"),
                    ("Отсутствовал", "absent"),
                    ("Уважительная причина", "excused"),
                    ("Неизвестно", "unknown"),
                    ("Не отмечено", "unmarked"),
                ]
            ],
            stacked=True,
        )

        def rate(value):
            return "Нет данных" if value is None else f"{value:.0%}"

        self.notice.setText(
            f"Семинары: {rate(workflow.seminars.attendance_rate)} · Лекции: {rate(workflow.lectures.attendance_rate)}\n"
            + (
                "Нет записанных попыток"
                if summary.attempts_total == 0
                else "Количество попыток не означает количество выполненных работ"
            )
        )
        self.refresh_visual_theme()

    def refresh_visual_theme(self):
        for chart in self.charts:
            style_chart(chart)
