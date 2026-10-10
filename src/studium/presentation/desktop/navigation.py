"""One MainWindow navigation history; retained pages preserve selection and tabs."""

from dataclasses import dataclass

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QStyle,
    QStyleOption,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from studium.presentation.desktop.icons import icon


@dataclass
class Route:
    page: QWidget
    title: str
    refresh: object = None
    leave: object = None
    transient: bool = False
    state: object = None


class NavigationStack(QWidget):
    changed = Signal()

    def __init__(self, pages, parent=None):
        super().__init__(parent)
        self.pages, self.routes = pages, []
        self.shortcut = QShortcut(QKeySequence("Alt+Left"), parent)
        self.shortcut.activated.connect(self.back)

    def root(self, page, title):
        for route in reversed(self.routes):
            if route.leave:
                route.leave()
            if route.transient:
                cleanup = getattr(route.page, "on_navigation_leave", None)
                if cleanup:
                    cleanup()
                self.pages.removeWidget(route.page)
                route.page.deleteLater()
        self.routes = [Route(page, title)]
        self.pages.setCurrentWidget(page)
        self.changed.emit()

    def push(self, page, title, *, refresh=None, leave=None, transient=True):
        if self.routes and self.routes[-1].page is not page:
            current = self.routes[-1]
            capture = getattr(current.page, "navigation_state", None)
            if capture:
                current.state = capture()
        if self.pages.indexOf(page) < 0:
            page.setParent(self.pages, Qt.WindowType.Widget)
            page.setMinimumSize(0, 0)
            self.pages.addWidget(page)
        self.routes.append(Route(page, title, refresh, leave, transient))
        self.pages.setCurrentWidget(page)
        page.show()
        self.changed.emit()

    def back(self):
        if len(self.routes) < 2:
            return
        route = self.routes.pop()
        cleanup = getattr(route.page, "on_navigation_leave", None)
        if cleanup:
            cleanup()
        if route.leave:
            route.leave()
        if route.transient:
            self.pages.removeWidget(route.page)
            route.page.deleteLater()
        previous = self.routes[-1]
        self.pages.setCurrentWidget(previous.page)
        restore = getattr(previous.page, "restore_navigation_state", None)
        if restore and previous.state is not None:
            restore(previous.state)
        if previous.refresh:
            previous.refresh()
        self.changed.emit()


def main_window(widget):
    while widget is not None:
        if hasattr(widget, "router"):
            return widget
        widget = widget.parentWidget()
    return None


def present_detail(dialog, parent, *, refresh=None, title=None):
    window = main_window(parent)
    if window is None:
        result = dialog.exec()
        if refresh:
            refresh()
        return result
    if window.router.routes and refresh:
        window.router.routes[-1].refresh = refresh
    window.router.push(dialog, title or dialog.windowTitle())
    dialog.finished.connect(
        lambda _: (
            window.router.back()
            if window.router.routes and window.router.routes[-1].page is dialog
            else None
        )
    )
    return QDialog.DialogCode.Rejected


class Sidebar(QTreeWidget):
    """Expandable contextual group links with a small primary navigation."""

    currentRowChanged = Signal(int)
    groupSelected = Signal(object)
    courseSelected = Signal(object)
    librarySelected = Signal(str)
    expansionChanged = Signal()

    def drawBranches(self, painter, rect, index):
        if not self.selectionModel().isSelected(index):
            return super().drawBranches(painter, rect, index)
        from studium.presentation.desktop.design import colors

        painter.fillRect(
            rect, QColor(colors(QApplication.instance().property("studiumTheme")).navigation)
        )
        if self.model().rowCount(index):
            option = QStyleOption()
            option.initFrom(self)
            option.rect = QRect(
                rect.right() - self.indentation() + 1,
                rect.y() + (rect.height() - 16) // 2,
                self.indentation(),
                16,
            )
            option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Children
            if self.isExpanded(index):
                option.state |= QStyle.StateFlag.State_Open
            self.style().drawPrimitive(
                QStyle.PrimitiveElement.PE_IndicatorBranch, option, painter, self
            )

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setObjectName("navigation")
        self.setMinimumWidth(0)
        self.setIconSize(QSize(18, 18))
        self.setRootIsDecorated(True)
        self.setIndentation(14)
        for title, symbol in (
            ("Главная", "home"),
            ("Работа", "work"),
            ("Дисциплины", "course"),
            ("Библиотека", "library"),
            ("Отчёты", "file"),
        ):
            item = QTreeWidgetItem(self, [title])
            item.setIcon(0, icon(symbol))
        self.currentItemChanged.connect(self.selected)
        self.itemExpanded.connect(lambda _: self.expansionChanged.emit())
        self.itemCollapsed.connect(lambda _: self.expansionChanged.emit())
        from studium.presentation.desktop.library import LIBRARY_LABELS

        for kind, title in LIBRARY_LABELS.items():
            child = QTreeWidgetItem(self.topLevelItem(3), [title])
            child.setData(0, Qt.ItemDataRole.UserRole, ("library", kind))

    def count(self):
        return self.topLevelItemCount()

    def setCurrentRow(self, row):
        item = self.topLevelItem(row) if row >= 0 else None
        if item is not None and item is self.currentItem():
            self.selected(item, None)
        else:
            self.setCurrentItem(item)

    def selected(self, item, _previous):
        if item is None:
            return
        if item.parent() is not None:
            kind, value = item.data(0, Qt.ItemDataRole.UserRole)
            if kind == "group":
                self.groupSelected.emit(value)
            elif kind == "course":
                self.courseSelected.emit(value)
            elif kind == "library":
                self.librarySelected.emit(value)
            else:
                self.currentRowChanged.emit(value)
        else:
            self.currentRowChanged.emit(self.indexOfTopLevelItem(item))

    def set_groups(self, contexts):
        self.blockSignals(True)
        group_root = self.topLevelItem(1)
        expanded = group_root.isExpanded()
        group_root.takeChildren()
        seen = set()
        for context in contexts:
            if context.group.id in seen:
                continue
            seen.add(context.group.id)
            child = QTreeWidgetItem(group_root, [context.group.number])
            child.setToolTip(0, context.course.name)
            child.setData(0, Qt.ItemDataRole.UserRole, ("group", context))
            if len(seen) == 4:
                break
        child = QTreeWidgetItem(group_root, ["Все группы"])
        child.setData(0, Qt.ItemDataRole.UserRole, ("root", 1))
        group_root.setExpanded(expanded)
        self.blockSignals(False)

    def set_courses(self, courses):
        self.blockSignals(True)
        root = self.topLevelItem(2)
        root.takeChildren()
        for course in courses[:4]:
            child = QTreeWidgetItem(root, [course.name])
            child.setData(0, Qt.ItemDataRole.UserRole, ("course", course))
        child = QTreeWidgetItem(root, ["Все дисциплины"])
        child.setData(0, Qt.ItemDataRole.UserRole, ("root", 2))
        self.blockSignals(False)

    def expansion_state(self):
        return [i for i in (1, 2, 3) if self.topLevelItem(i).isExpanded()]

    def restore_expansion(self, state):
        self.blockSignals(True)
        for i in (1, 2, 3):
            self.topLevelItem(i).setExpanded(i in state)
        self.blockSignals(False)
