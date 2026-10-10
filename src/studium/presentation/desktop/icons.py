"""Original line icons painted by Qt: no fonts, bitmap assets or dependencies."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication


class LineIcon(QIconEngine):
    def __init__(self, name, tint=None):
        super().__init__()
        self.name = name
        self.tint = tint

    def clone(self):
        return LineIcon(self.name, self.tint)

    def pixmap(self, size, mode, state):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, pixmap.rect(), mode, state)
        painter.end()
        return pixmap

    def paint(self, painter, rect, mode, state):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / 24, rect.height() / 24)
        palette = QApplication.palette()
        color = palette.text().color() if mode != QIcon.Mode.Disabled else palette.mid().color()
        if self.tint and mode != QIcon.Mode.Disabled:
            color = QColor(self.tint)
        painter.setPen(
            QPen(
                color,
                1.6,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)

        def line(x1, y1, x2, y2):
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        if self.name == "home":
            line(3, 11, 12, 3)
            line(12, 3, 21, 11)
            painter.drawRect(QRectF(6, 10, 12, 11))
            painter.drawRect(QRectF(10, 15, 4, 6))
        elif self.name == "work":
            painter.drawRoundedRect(QRectF(3, 6, 18, 15), 2, 2)
            line(7, 3, 7, 8)
            line(17, 3, 17, 8)
            line(3, 11, 21, 11)
            line(7, 15, 10, 15)
            line(14, 15, 17, 15)
        elif self.name == "course":
            painter.drawPolygon(
                QPolygonF([QPointF(2, 9), QPointF(12, 4), QPointF(22, 9), QPointF(12, 14)])
            )
            line(6, 11, 6, 17)
            line(6, 17, 12, 20)
            line(12, 20, 18, 17)
            line(18, 17, 18, 11)
            line(22, 9, 22, 17)
        elif self.name == "library":
            painter.drawRoundedRect(QRectF(4, 3, 16, 18), 2, 2)
            line(8, 3, 8, 21)
            line(11, 8, 17, 8)
            line(11, 12, 17, 12)
            if self.name == "library":
                line(11, 16, 17, 16)
        elif self.name == "settings":
            for y, x in ((6, 8), (12, 16), (18, 10)):
                line(3, y, x - 2, y)
                line(x + 2, y, 21, y)
                painter.drawEllipse(QRectF(x - 2, y - 2, 4, 4))
        elif self.name == "back":
            line(19, 12, 5, 12)
            line(5, 12, 11, 6)
            line(5, 12, 11, 18)
        elif self.name == "previous":
            line(15, 6, 9, 12)
            line(9, 12, 15, 18)
        elif self.name == "next":
            line(9, 6, 15, 12)
            line(15, 12, 9, 18)
        elif self.name == "file":
            painter.drawRoundedRect(QRectF(5, 3, 14, 18), 1, 1)
            line(9, 9, 15, 9)
            line(9, 13, 15, 13)
            line(9, 17, 13, 17)
        else:
            line(5, 12, 19, 12)
            line(12, 5, 12, 19)
        painter.restore()


def icon(name, tint=None):
    return QIcon(LineIcon(name, tint))
