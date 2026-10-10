"""Helpers assembling standard Qt widgets; no custom widget framework."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from studium.presentation.desktop.messages import TEXT, error_message
from studium.presentation.desktop.theme import ROW_HEIGHT, SPACING
from studium.presentation.desktop.widgets import DataTable

logger = logging.getLogger(__name__)


def run_action(parent, action):
    try:
        return action()
    except Exception as error:
        logger.error("Desktop operation failed (%s)", type(error).__name__)
        QMessageBox.warning(parent, TEXT["error_title"], error_message(error))
        return None


def confirm(parent, text, *, action_label=None):
    box = QMessageBox(QMessageBox.Icon.Question, TEXT["confirm_title"], text, parent=parent)
    yes = box.addButton(action_label or TEXT["hide"], QMessageBox.ButtonRole.AcceptRole)
    box.addButton(TEXT["cancel"], QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(box.buttons()[-1])
    box.exec()
    return box.clickedButton() == yes


def confirm_delete(parent, service, kind, original, *, name=None):
    name = name or next(
        (
            getattr(original, key)
            for key in ("title", "name", "number", "full_name")
            if hasattr(original, key)
        ),
        "запись",
    )
    impact = service.deletion_impact(kind, original)
    text = f"Удалить «{name}» из активной работы?\n\nИстория и прикреплённые файлы сохранятся."
    if kind in {"course", "group", "term"}:
        text += f"\nУчебные контексты ({impact.contexts}) останутся в архиве."
        text += "\nМатериалы Библиотеки и рабочие программы не будут удалены."
    if impact.library_materials:
        text += f"\nМатериалы ({impact.library_materials}) сохранят связь с удалённой дисциплиной с пометкой."
    if impact.dependents:
        text += f"\nГруппы ({impact.dependents}) сохранят прежний учебный план и историю."
    return confirm(parent, text, action_label="Удалить")


def panel():
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 12, 0, 12)
    layout.setSpacing(SPACING)
    return widget, layout


def toolbar(layout, items):
    row = QGridLayout() if len(items) > 4 else QHBoxLayout()
    for index, (label, callback) in enumerate(items):
        button = QPushButton(label)
        button.clicked.connect(callback)
        if isinstance(row, QGridLayout):
            row.addWidget(button, index // 3, index % 3)
        else:
            row.addWidget(button)
    if isinstance(row, QHBoxLayout):
        row.addStretch()
    layout.addLayout(row)
    return row


def hint(layout, text):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setProperty("role", "hint")
    if "✓" in text or "⚠" in text:
        label.setProperty("role", "status")
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(label)
    return label


def table(model, *, stretch=True, view=None):
    view = view or DataTable()
    view.setModel(model)
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    view.setAlternatingRowColors(True)
    view.setShowGrid(False)
    view.setMouseTracking(True)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.verticalHeader().hide()
    view.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
    view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    view.horizontalHeader().setStretchLastSection(stretch)
    view.horizontalHeader().setMinimumSectionSize(60)
    view.horizontalHeader().setDefaultSectionSize(180)
    view.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideRight)
    view.horizontalHeader().setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    view.enable_width_preferences()
    view.setWordWrap(False)
    return view


def selected(view):
    index = view.currentIndex()
    if index.isValid():
        return view.model().data(index, Qt.ItemDataRole.UserRole)
    QMessageBox.information(view, TEXT["app"], TEXT["choose_row"])
    return None
