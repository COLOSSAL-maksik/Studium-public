"""Small reusable compositions over standard, keyboard-accessible Qt widgets."""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from studium.presentation.desktop.icons import icon
from studium.presentation.desktop.theme import theme_color


def text_label(text, role="hint", parent=None):
    label = QLabel(text, parent)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setProperty("role", role)
    label.setWordWrap(True)
    return label


class HomeTile(QPushButton):
    def __init__(self, title, description, symbol, parent=None):
        super().__init__(parent)
        self.setAccessibleName(title)
        self.setProperty("role", "homeTile")
        self.setMinimumHeight(196)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        self.symbol = QLabel()
        self.symbol.setFixedSize(48, 48)
        self.symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.symbol.setProperty("role", "tileIcon")
        self.symbol.setProperty("tone", symbol)
        self.symbol_name = symbol
        layout.addWidget(self.symbol)
        layout.addSpacing(8)
        layout.addWidget(text_label(title, "subheading"))
        layout.addWidget(text_label(description))
        layout.addStretch()
        self.detail = text_label("", "caption")
        layout.addWidget(self.detail)
        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.refresh_visual_theme()

    def refresh_visual_theme(self):
        tint = {
            "work": theme_color("#7061c9", "#b7aafa"),
            "course": theme_color("#246ed1", "#9dc7fb"),
            "library": theme_color("#268c7b", "#87d3bf"),
        }[self.symbol_name]
        self.symbol.setPixmap(icon(self.symbol_name, tint.name()).pixmap(QSize(28, 28)))


class RecentGroupDelegate(QStyledItemDelegate):
    """Render the existing Home table as a compact two-line list."""

    def paint(self, painter, option, index):
        context = index.model().rows[index.row()]
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, option.palette.alternateBase())
        left = option.rect.left() + 10
        top = option.rect.top()
        painter.drawPixmap(left, top + 17, icon("work").pixmap(18, 18))
        rect = QRect(left + 30, top + 8, option.rect.width() - 46, 24)
        painter.setPen(option.palette.text().color())
        font = option.font
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignLeft, context.group.number)
        font.setBold(False)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(option.palette.placeholderText().color())
        text = painter.fontMetrics().elidedText(
            context.course.name, Qt.TextElideMode.ElideRight, rect.width()
        )
        painter.drawText(rect.translated(0, 23), Qt.AlignmentFlag.AlignLeft, text)
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(option.palette.link().color())
            painter.drawRoundedRect(option.rect.adjusted(1, 1, -2, -2), 6, 6)
        painter.restore()

    @staticmethod
    def configure(view):
        view.setObjectName("recentGroups")
        view.setItemDelegate(RecentGroupDelegate(view))
        view.setColumnHidden(1, True)
        view.setColumnHidden(2, True)
        view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        view.verticalHeader().setDefaultSectionSize(60)
        view.setAlternatingRowColors(False)


class EmptyState(QFrame):
    def __init__(self, title, description, action=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(text_label(title, "subheading"))
        layout.addWidget(text_label(description))
        if action:
            button = QPushButton(action[0])
            button.setProperty("primary", True)
            button.clicked.connect(action[1])
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)


class Disclosure(QWidget):
    def __init__(self, title, content, *, expanded=False, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setProperty("role", "quiet")
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.content = content
        layout.addWidget(self.toggle)
        layout.addWidget(content)
        self.toggle.toggled.connect(self.set_expanded)
        self.set_expanded(expanded)

    def set_expanded(self, shown):
        self.content.setVisible(shown)
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if shown else Qt.ArrowType.RightArrow)


def action_card(title, description, callback):
    card = QFrame()
    card.setProperty("role", "surface")
    row = QHBoxLayout(card)
    row.setContentsMargins(20, 16, 20, 16)
    copy = QVBoxLayout()
    copy.addWidget(text_label(title, "subheading"))
    copy.addWidget(text_label(description))
    row.addLayout(copy, 1)
    button = QPushButton()
    button.setIcon(icon("next"))
    button.setToolTip("Открыть · " + title)
    button.setAccessibleName("Открыть · " + title)
    button.setProperty("role", "quiet")
    button.clicked.connect(callback)
    row.addWidget(button)
    return card


def advanced_rows(form, fields, title="Дополнительно"):
    """Move existing controls without changing values, validators or save contracts."""
    content = QWidget()
    advanced = QFormLayout(content)
    advanced.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    advanced.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    for field in fields:
        if field is not None and form.indexOf(field) >= 0:
            row = form.takeRow(field)
            advanced.addRow(row.labelItem.widget(), row.fieldItem.widget())
    return Disclosure(title, content)


class ModuleTimeline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = QVBoxLayout(self)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(10)

    def set_modules(self, modules, open_module):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index, module in enumerate(modules):
            content = QWidget()
            content.setProperty("role", "moduleRow")
            row = QHBoxLayout(content)
            row.setContentsMargins(18, 14, 14, 14)
            weeks = text_label(f"{module.start_week}–{module.end_week}\nнедели", "caption")
            weeks.setFixedWidth(64)
            row.addWidget(weeks)
            title = text_label(module.title, "moduleTitle")
            row.addWidget(title, 1)
            button = QPushButton("Открыть")
            button.setProperty("role", "quiet")
            button.clicked.connect(lambda _=False, index=index: open_module(index))
            row.addWidget(button)
            self.rows.addWidget(content)


class TagList(QWidget):
    """A wrapping selection summary; remove uses the original picker state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(6)

    def set_values(self, values, remove=None):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not values:
            self.grid.addWidget(text_label("Пока не добавлены", "caption"), 0, 0)
        for i, (key, title) in enumerate(values):
            if remove:
                label = QPushButton(title + "  ×")
                label.setAccessibleName("Удалить связь · " + title)
                label.setToolTip(title + " · удалить связь")
                label.clicked.connect(lambda _=False, key=key: remove(key))
            else:
                label = text_label(title, "tag")
                label.setMaximumWidth(450)
            self.grid.addWidget(label, i // 3, i % 3, Qt.AlignmentFlag.AlignLeft)
