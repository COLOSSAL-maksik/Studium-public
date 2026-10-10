"""Consistent chart surfaces, axes and restricted factual series colors."""

from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QApplication

from studium.presentation.desktop.design import colors


def chart_colors():
    return colors(QApplication.instance().property("studiumTheme"))


def style_chart(chart):
    c = chart_colors()
    chart.setBackgroundBrush(QColor(c.surface))
    chart.setBackgroundRoundness(0)
    chart.setTitleBrush(QColor(c.text))
    chart.legend().setLabelColor(QColor(c.muted))
    shades = (c.accent, c.success, c.warning, c.error, c.muted, c.border)
    for i, series in enumerate(chart.series()):
        if hasattr(series, "barSets"):
            for j, bar in enumerate(series.barSets()):
                bar.setColor(QColor(shades[j % len(shades)]))
                bar.setBorderColor(QColor(shades[j % len(shades)]))
        else:
            series.setPen(QPen(QColor(shades[i % len(shades)]), 2.5))
    for axis in chart.axes():
        axis.setLabelsColor(QColor(c.muted))
        axis.setTitleBrush(QColor(c.muted))
        axis.setLinePen(QPen(QColor(c.border)))
        axis.setGridLinePen(QPen(QColor(c.border), 0.7))
        axis.setMinorGridLineVisible(False)
