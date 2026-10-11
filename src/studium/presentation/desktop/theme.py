"""Linear Academic: explicit light/dark surfaces and native Qt interaction states."""

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QFont, QPalette, QPolygonF
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle, QStyleFactory

from studium.presentation.desktop import style_resources as style_resources
from studium.presentation.desktop.design import RADII, SPACES, TYPE, colors

MARGIN = SPACES["l"]
SPACING = SPACES["m"]
ROW_HEIGHT = 34


class AcademicStyle(QProxyStyle):
    """Keep native indicators readable, including the calendar navigation arrows."""

    def drawPrimitive(self, element, option, painter, widget=None):
        rotations = {
            QStyle.PrimitiveElement.PE_IndicatorArrowDown: 0,
            QStyle.PrimitiveElement.PE_IndicatorSpinDown: 0,
            QStyle.PrimitiveElement.PE_IndicatorSpinUp: 180,
            QStyle.PrimitiveElement.PE_IndicatorArrowUp: 180,
            QStyle.PrimitiveElement.PE_IndicatorArrowLeft: 90,
            QStyle.PrimitiveElement.PE_IndicatorArrowRight: -90,
        }
        if element not in rotations:
            return super().drawPrimitive(element, option, painter, widget)
        painter.save()
        painter.translate(option.rect.center())
        painter.rotate(rotations[element])
        painter.setPen(option.palette.buttonText().color())
        painter.setBrush(option.palette.buttonText())
        painter.drawPolygon(QPolygonF([QPointF(-4, -2), QPointF(4, -2), QPointF(0, 3)]))
        painter.restore()


def theme_stylesheet(theme):
    c = colors(theme)
    return f"""
QWidget {{ color: {c.text}; font-family: "Segoe UI"; font-size: {TYPE["body"]}px; }}
QMainWindow, QDialog {{ background: {c.background}; }}
QWidget#sidebar {{ background: {c.navigation}; border-right: 1px solid {c.border}; }}
QLabel[role="brand"] {{ font-size: 22px; font-weight: 600; padding: 0 8px; }}
QLabel[role="heading"] {{ font-size: {TYPE["page"]}px; font-weight: 600; }}
QLabel[role="subheading"] {{ font-size: {TYPE["section"]}px; font-weight: 600; }}
QLabel[role="moduleTitle"] {{ font-size: 14px; font-weight: 600; }}
QLabel[role="metric"] {{ font-size: 28px; font-weight: 600; }}
QLabel[role="hint"], QLabel[role="status"] {{ color: {c.muted}; }}
QLabel[role="caption"], QLabel#breadcrumb {{ color: {c.muted}; font-size: {TYPE["caption"]}px; }}
QLabel[role="error"] {{ color: {c.error}; }}
QLabel[role="success"] {{ color: {c.success}; }}
QLabel[role="warning"] {{ color: {c.warning}; }}
QLabel[role="notice"] {{ background: {c.secondary}; color: {c.warning}; padding: 10px; border-radius: 5px; }}
QFrame[role="surface"], QWidget[role="surface"] {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: {RADII["surface"]}px; }}
QWidget[role="moduleRow"] {{ background: {c.surface}; border: 1px solid {c.border}; border-left: 3px solid {c.success}; border-radius: 8px; }}
QLabel[role="tileIcon"] {{ background: {c.selected}; border-radius: 10px; }}
QLabel[role="tileIcon"][tone="work"] {{ background: {"#eeeaff" if theme == "light" else "#3a3655"}; }}
QLabel[role="tileIcon"][tone="library"] {{ background: {"#e1f5f0" if theme == "light" else "#254841"}; }}
QLabel[role="tag"] {{ background: {c.selected}; color: {c.information}; border-radius: 4px; padding: 5px 8px; }}
QPushButton, QToolButton {{ min-height: 28px; padding: 3px 12px; background: {c.surface};
    border: 1px solid {c.border}; border-radius: {RADII["control"]}px; }}
QPushButton:hover, QToolButton:hover {{ background: {c.hover}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {c.selected}; }}
QPushButton:focus, QToolButton:focus {{ border-color: {c.accent}; }}
QPushButton:default, QPushButton[primary="true"] {{ background: {c.accent}; color: {c.on_accent}; border-color: {c.accent}; }}
QPushButton:default:hover, QPushButton[primary="true"]:hover {{ background: {c.accent_hover}; }}
QPushButton:default:focus, QPushButton[primary="true"]:focus {{ border: 2px solid {c.text}; padding: 2px 11px; }}
QPushButton:disabled, QToolButton:disabled {{ color: {c.disabled}; background: {c.secondary}; border-color: {c.border}; }}
QPushButton[role="quiet"], QToolButton[role="quiet"] {{ background: transparent; border-color: transparent; text-align: left; }}
QPushButton[role="quiet"]:hover, QToolButton[role="quiet"]:hover {{ background: {c.hover}; }}
QPushButton[role="quiet"]:focus, QToolButton[role="quiet"]:focus {{ border-color: {c.accent}; }}
QPushButton[role="quiet"]:checked {{ background: {c.selected}; }}
QPushButton[role="homeTile"] {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: {RADII["surface"]}px; text-align: left; padding: 0; min-height: 196px; }}
QPushButton[role="homeTile"]:hover {{ background: {c.secondary}; border-color: {c.accent}; }}
QPushButton[role="homeTile"]:focus {{ border: 2px solid {c.accent}; }}
QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {{ min-height: 28px;
    padding: 3px 8px; background: {c.surface}; border: 1px solid {c.border}; border-radius: {RADII["control"]}px; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {c.accent}; }}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QDateTimeEdit:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {c.secondary}; color: {c.disabled}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ width: 24px; border: 0; border-top-right-radius: 6px; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ width: 24px; border: 0; border-bottom-right-radius: 6px; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url(:/studium-style/up-{"dark" if theme == "dark" else "light"}.svg); width: 10px; height: 7px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url(:/studium-style/down-{"dark" if theme == "dark" else "light"}.svg); width: 10px; height: 7px; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{ background: {c.hover}; }}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed, QDoubleSpinBox::up-button:pressed, QDoubleSpinBox::down-button:pressed {{ background: {c.selected}; }}
QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {{ border: 0; width: 24px; }}
QComboBox QAbstractItemView {{ background: {c.elevated}; color: {c.text};
    alternate-background-color: {c.elevated}; selection-background-color: {c.selected};
    selection-color: {c.text}; border: 1px solid {c.border}; outline: 0; padding: 4px; }}
QComboBox QAbstractItemView::item {{ min-height: 30px; padding: 2px 6px; background: {c.elevated}; }}
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {{ background: {c.selected}; color: {c.text}; }}
QComboBox QAbstractItemView::item:disabled {{ color: {c.disabled}; }}
QPlainTextEdit, QTextEdit {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: {RADII["control"]}px; padding: 8px; }}
QPlainTextEdit[readOnly="true"] {{ background: {c.secondary}; }}
QTableView, QTreeWidget, QListWidget {{ background: {c.surface}; alternate-background-color: {c.secondary};
    border: 1px solid {c.border}; border-radius: {RADII["control"]}px; selection-background-color: {c.selected}; selection-color: {c.text}; gridline-color: {c.border}; }}
QTableView#recentGroups {{ border: 0; background: transparent; }}
QTableView::item {{ padding: 3px 6px; border-bottom: 1px solid {c.secondary}; }}
QTableView::item:hover {{ background: {c.hover}; }}
QTableView::item:selected {{ background: {c.selected}; color: {c.text}; }}
QTableView::item:focus {{ border: 1px solid {c.accent}; }}
QHeaderView::section {{ background: {c.secondary}; color: {c.muted}; padding: 7px 8px;
    border: 0; border-bottom: 1px solid {c.border}; font-size: {TYPE["table"]}px; }}
QTabWidget::pane {{ background: transparent; border: 0; border-top: 1px solid {c.border}; }}
QTabBar::tab {{ background: transparent; color: {c.muted}; padding: 10px 12px; border: 0; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {c.accent}; background: {c.selected}; border-bottom-color: {c.accent}; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:hover {{ background: {c.hover}; }}
QTabBar::tab:focus {{ background: {c.selected}; }}
QTabBar::tab:disabled {{ color: {c.disabled}; }}
QTreeWidget#navigation {{ background: transparent; border: 0; outline: 0; show-decoration-selected: 0; }}
QTreeWidget#navigation::item {{ height: 34px; padding: 3px 10px; margin: 3px 0; border-radius: 8px; }}
QTreeWidget#navigation::item:hover {{ background: {c.hover}; }}
QTreeWidget#navigation::item:selected {{ background: {c.selected}; color: {c.accent}; }}
QTreeWidget#navigation::branch {{ background: transparent; border: 0; }}
QTreeWidget#navigation::branch:hover, QTreeWidget#navigation::branch:selected {{ background: transparent; }}
QTableView#journalNames {{ border: 0; border-radius: 0; border-right: 1px solid {c.border}; }}
QPushButton[role="resumeGroup"] {{ text-align: left; background: {c.surface}; border: 1px solid {c.border}; min-height: 88px; padding: 0; }}
QPushButton[role="resumeGroup"]:hover {{ background: {c.hover}; border-color: {c.accent}; }}
QGroupBox {{ border: 0; border-top: 1px solid {c.border}; margin-top: 18px; padding-top: 18px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 0; padding: 0 8px 0 0; font-weight: 600; }}
QCheckBox, QRadioButton {{ spacing: 8px; padding: 4px 0; }}
QCheckBox:focus, QRadioButton:focus {{ color: {c.accent}; }}
QMenu {{ background: {c.elevated}; border: 1px solid {c.border}; padding: 5px; }}
QMenu::item {{ padding: 8px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: {c.selected}; }}
QMenu::item:disabled {{ color: {c.disabled}; }}
QMenu::separator {{ height: 1px; background: {c.border}; margin: 4px 8px; }}
QToolTip {{ background: {c.elevated}; color: {c.text}; border: 1px solid {c.border}; padding: 8px; }}
QScrollArea {{ border: 0; background: transparent; }}
QScrollBar:vertical {{ width: 11px; background: {c.secondary}; margin: 0; }}
QScrollBar:horizontal {{ height: 11px; background: {c.secondary}; margin: 0; }}
QScrollBar::handle {{ background: {c.border}; border-radius: 4px; min-height: 28px; min-width: 28px; margin: 2px; }}
QScrollBar::handle:hover {{ background: {c.muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QCalendarWidget QWidget {{ background: {c.elevated}; color: {c.text}; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {c.secondary}; padding: 4px; }}
QCalendarWidget QToolButton {{ border: 0; background: transparent; min-height: 28px; padding: 5px 8px; }}
QCalendarWidget QToolButton:hover {{ background: {c.hover}; }}
QCalendarWidget QToolButton:focus {{ border: 1px solid {c.accent}; }}
QCalendarWidget QSpinBox {{ background: {c.surface}; min-height: 28px; }}
QCalendarWidget QAbstractItemView {{ background: {c.elevated}; border: 0; outline: 0; selection-background-color: {c.accent}; selection-color: {c.on_accent}; }}
QCalendarWidget QAbstractItemView:focus {{ border: 1px solid {c.accent}; }}
QFrame#fileDropZone {{ background: {c.secondary}; border: 1px dashed {c.border}; border-radius: 5px; }}
QFrame#fileDropZone[dragActive="true"] {{ background: {c.selected}; border: 2px solid {c.accent}; }}
"""


def apply_theme(theme="light"):
    app = QApplication.instance()
    if not app or app.property("studiumTheme") == theme:
        return
    c = colors(theme)
    app.setStyle(AcademicStyle(QStyleFactory.create("Fusion")))
    app.setFont(QFont("Segoe UI", 10))
    palette = QPalette()
    mapping = {
        QPalette.ColorRole.Window: c.background,
        QPalette.ColorRole.WindowText: c.text,
        QPalette.ColorRole.Base: c.surface,
        QPalette.ColorRole.AlternateBase: c.secondary,
        QPalette.ColorRole.Text: c.text,
        QPalette.ColorRole.PlaceholderText: c.muted,
        QPalette.ColorRole.Button: c.secondary,
        QPalette.ColorRole.ButtonText: c.text,
        QPalette.ColorRole.Mid: c.border,
        QPalette.ColorRole.Light: c.surface,
        QPalette.ColorRole.Dark: c.border,
        QPalette.ColorRole.Highlight: c.selected,
        QPalette.ColorRole.HighlightedText: c.text,
        QPalette.ColorRole.ToolTipBase: c.elevated,
        QPalette.ColorRole.ToolTipText: c.text,
        QPalette.ColorRole.Link: c.accent,
    }
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        for role, color in mapping.items():
            if group == QPalette.ColorGroup.Disabled and role in (
                QPalette.ColorRole.Text,
                QPalette.ColorRole.WindowText,
                QPalette.ColorRole.ButtonText,
            ):
                color = c.disabled
            palette.setColor(group, role, QColor(color))
    app.setProperty("studiumTheme", theme)
    app.setPalette(palette)
    app.setStyleSheet(theme_stylesheet(theme))
    # Icons and charts are palette-aware; refresh retained pages when theme changes.
    for widget in app.allWidgets():
        refresh = getattr(widget, "refresh_visual_theme", None)
        if refresh:
            refresh()
        widget.update()


def theme_color(light, dark):
    app = QApplication.instance()
    return QColor(dark if app and app.property("studiumTheme") == "dark" else light)


def resize_to_screen(window, width, height):
    """Keep native windows inside the Windows work area, in logical pixels."""
    app = QApplication.instance()
    if app and app.platformName() == "windows" and app.primaryScreen():
        available = app.primaryScreen().availableGeometry()
        width = min(width, int(available.width() * 0.94))
        height = min(height, int(available.height() * 0.9))
    window.resize(width, height)
