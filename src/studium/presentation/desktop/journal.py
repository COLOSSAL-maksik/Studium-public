"""Dense journal model with module/category headers and the existing frozen view."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QHeaderView

from studium.presentation.desktop.design import ATTENDANCE_NAMES, attendance_color, colors


class JournalModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.snapshot = self.matrix = None

    def replace_matrix(self, snapshot):
        self.beginResetModel()
        self.snapshot = snapshot
        self.matrix = snapshot.matrix if snapshot else None
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.matrix.roster) if self.matrix and not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.snapshot.columns) + 1 if self.snapshot and not parent.isValid() else 0

    def column(self, index):
        return self.snapshot.columns[index - 1] if self.snapshot and index > 0 else None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.ToolTipRole,
        ):
            column = self.column(section)
            return (
                (
                    (column.full_title or column.title)
                    if role == Qt.ItemDataRole.ToolTipRole
                    else column.title
                )
                if column
                else "ФИО"
            )

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not self.matrix:
            return None
        entry = self.matrix.roster[index.row()]
        if index.column() == 0:
            return (
                entry.student.full_name
                if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole)
                else None
            )
        column = self.column(index.column())
        if role == Qt.ItemDataRole.BackgroundRole and column.kind == "attendance":
            value = self.snapshot.values.get((entry.student.id, index.column()), "—")
            fill = QColor(attendance_color(value, QApplication.instance().property("studiumTheme")))
            fill.setAlpha(28 if value != "—" else 0)
            return fill
        if role == Qt.ItemDataRole.ForegroundRole:
            value = self.snapshot.values.get((entry.student.id, index.column()), "—")
            theme = QApplication.instance().property("studiumTheme")
            if column.kind == "attendance":
                return QColor(attendance_color(value, theme))
            c = colors(theme)
            return QColor(
                c.success
                if value.startswith("✓") or value == "•"
                else c.warning
                if value.startswith("⚠") or value == "◷"
                else c.muted
                if value == "—"
                else c.text
            )
        if role == Qt.ItemDataRole.UserRole:
            return (
                self.matrix.cells[entry.student.id, column.assessment.id]
                if column.assessment
                else None
            )
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.DisplayRole:
            return self.snapshot.values.get((entry.student.id, index.column()), "—")
        if role == Qt.ItemDataRole.ToolTipRole:
            if column.kind == "attendance":
                value = self.snapshot.values.get((entry.student.id, index.column()), "—")
                return (
                    entry.student.full_name
                    + "\n"
                    + ATTENDANCE_NAMES.get(value, value)
                    + "\n"
                    + self.snapshot.tooltips.get((entry.student.id, index.column()), "")
                )
            return (
                entry.student.full_name
                + "\n"
                + self.snapshot.tooltips.get((entry.student.id, index.column()), "")
            )


class GroupedJournalHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMinimumHeight(70)
        self.setFixedHeight(70)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def paintSection(self, painter, rect, index):
        painter.save()
        painter.fillRect(rect, self.palette().alternateBase())
        painter.setPen(self.palette().mid().color())
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.setPen(self.palette().text().color())
        painter.drawText(
            rect.adjusted(3, 48, -3, 0),
            Qt.AlignmentFlag.AlignCenter,
            painter.fontMetrics().elidedText(
                self.model().headerData(index, Qt.Orientation.Horizontal) or "",
                Qt.TextElideMode.ElideRight,
                max(1, rect.width() - 6),
            ),
        )
        painter.restore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not getattr(self.model(), "snapshot", None):
            return
        painter = QPainter(self.viewport())
        visible = [i for i in range(1, self.count()) if not self.isSectionHidden(i)]
        for top in (True, False):
            groups = []
            for index in visible:
                column = self.model().column(index)
                key = column.module_title if top else (column.module_title, column.week)
                if groups and groups[-1][0] == key:
                    groups[-1][2] = index
                else:
                    groups.append([key, index, index])
            for key, first, last in groups:
                x = self.sectionViewportPosition(first)
                end = self.sectionViewportPosition(last) + self.sectionSize(last)
                rect = QRect(x, 0 if top else 24, end - x, 24)
                painter.fillRect(
                    rect, self.palette().alternateBase() if top else self.palette().base()
                )
                painter.setPen(self.palette().mid().color())
                painter.drawLine(rect.bottomLeft(), rect.bottomRight())
                painter.drawLine(rect.topRight(), rect.bottomRight())
                font = painter.font()
                font.setBold(top)
                painter.setFont(font)
                painter.setPen(self.palette().text().color())
                text = (
                    key if top else ("Неделя " + str(key[1]) if key[1] is not None else "Без срока")
                )
                if top:
                    missing = [
                        kind for title, kind in self.model().snapshot.empty_sections if title == key
                    ]
                    text += "".join(
                        " · " + {"homework": "ДЗ —", "control": "РК —"}[kind] for kind in missing
                    )
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
