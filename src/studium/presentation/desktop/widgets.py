"""Table keyboard support and the Qt shared-model frozen-column pattern."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
)


def search_shortcut(owner, field):
    shortcut = QShortcut(QKeySequence.StandardKey.Find, owner)
    shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    shortcut.activated.connect(lambda: (field.setFocus(), field.selectAll()))
    return shortcut


class DataTable(QTableView):
    def enable_width_preferences(self):
        self._widths_restored = False
        self.horizontalHeader().sectionResized.connect(self.save_widths)

    def width_preferences(self):
        from studium.presentation.desktop.navigation import main_window

        window = main_window(self)
        if window and window.service:
            key = "|".join(
                str(self.model().headerData(i, Qt.Orientation.Horizontal) or "")
                for i in range(self.model().columnCount())
            )
            return window.service, key
        return None, None

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_widths_restored") and not self._widths_restored:
            service, key = self.width_preferences()
            if service:
                widths = service.table_widths(key)
                for i, width in enumerate(widths[: self.model().columnCount()]):
                    self.setColumnWidth(i, width)
                self._widths_restored = True

    def save_widths(self, *_):
        if getattr(self, "_widths_restored", False):
            service, key = self.width_preferences()
            if service:
                service.save_table_widths(
                    key, [self.columnWidth(i) or 180 for i in range(self.model().columnCount())]
                )

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        self.setProperty("hoverRow", index.row() if index.isValid() else -1)
        self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hoverRow", -1)
        self.viewport().update()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.currentIndex().isValid():
            (self.activated if self.objectName() == "recentGroups" else self.doubleClicked).emit(
                self.currentIndex()
            )
            event.accept()
        else:
            super().keyPressEvent(event)


class JournalTable(DataTable):
    """Two views of one model/selection; no duplicated data or business logic.

    Adapted from Qt's Frozen Column Example. The overlay only shows names.
    """

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.frozen = DataTable(self)
        self.frozen.setFrameShape(QFrame.Shape.NoFrame)
        self.frozen.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.frozen.verticalHeader().hide()
        self.frozen.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.frozen.horizontalHeader().sectionResized.connect(
            lambda column, _old, width: self.setColumnWidth(0, width) if column == 0 else None
        )
        self.frozen.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.frozen.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.frozen.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.frozen.setAlternatingRowColors(True)
        self.frozen.setShowGrid(False)
        self.frozen.setMouseTracking(True)
        self.setObjectName("journal")
        self.frozen.setObjectName("journalNames")
        self.setItemDelegate(JournalRowDelegate(self))
        self.frozen.setItemDelegate(JournalRowDelegate(self.frozen))
        self.setModel(model)
        self.frozen.setModel(model)
        self.frozen.setSelectionModel(self.selectionModel())
        self.selectionModel().currentChanged.connect(lambda *_: self.frozen.viewport().update())
        self.frozen.doubleClicked.connect(self.doubleClicked.emit)
        self.frozen.clicked.connect(self.clicked.emit)
        self.verticalScrollBar().valueChanged.connect(self.frozen.verticalScrollBar().setValue)
        self.frozen.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self.horizontalHeader().sectionResized.connect(self._column_resized)
        self.verticalHeader().sectionResized.connect(
            lambda row, _old, height: self.frozen.setRowHeight(row, height)
        )
        model.modelReset.connect(self.sync_frozen)
        self.viewport().stackUnder(self.frozen)
        self.sync_frozen()

    def setHorizontalHeader(self, header):
        super().setHorizontalHeader(header)
        header.sectionResized.connect(self._column_resized)
        header.geometriesChanged.connect(self.sync_frozen)

    def sync_frozen(self):
        for column in range(1, self.model().columnCount()):
            self.frozen.setColumnHidden(column, True)
        self.frozen.setColumnWidth(0, self.columnWidth(0))
        self.frozen.verticalHeader().setDefaultSectionSize(
            self.verticalHeader().defaultSectionSize()
        )
        self.frozen.horizontalHeader().setFixedHeight(self.horizontalHeader().height())
        for row in range(self.model().rowCount()):
            self.frozen.setRowHeight(row, self.rowHeight(row))
        self.frozen.setVisible(self.model().columnCount() > 0)
        self._position_frozen()
        # A replacement grouped header is created later than the overlay.
        # Keep both its name header and rows above that sibling widget.
        self.frozen.raise_()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.currentIndex().isValid():
            self.activated.emit(self.currentIndex())
            event.accept()
        else:
            super().keyPressEvent(event)

    def _column_resized(self, column, _old, width):
        if column == 0:
            self.frozen.setColumnWidth(0, width)
            self._position_frozen()

    def _position_frozen(self):
        self.frozen.setGeometry(
            self.viewport().x(),
            self.horizontalHeader().y(),
            self.columnWidth(0),
            self.viewport().geometry().bottom() - self.horizontalHeader().y() + 1,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sync_frozen()

    def scrollTo(self, index, hint=QAbstractItemView.ScrollHint.EnsureVisible):
        if index.column() > 0:
            super().scrollTo(index, hint)
            left = self.visualRect(index).left()
            if left < self.columnWidth(0):
                bar = self.horizontalScrollBar()
                bar.setValue(bar.value() - self.columnWidth(0) + left)


class JournalRowDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        view = self.parent()
        styled = QStyleOptionViewItem(option)
        if view.objectName() == "journalNames" and view.currentIndex().row() == index.row():
            styled.state |= QStyle.StateFlag.State_Selected
        elif (
            view.property("hoverRow") == index.row()
            and not styled.state & QStyle.StateFlag.State_Selected
        ):
            styled.backgroundBrush = QBrush(view.palette().alternateBase())
        super().paint(painter, styled, index)
