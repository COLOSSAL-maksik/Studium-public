"""Modular offline help. Each article is an individually packaged Markdown resource."""

import json
from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

PACKAGE = "studium.presentation.desktop.help_articles"


def help_index():
    return json.loads(files(PACKAGE).joinpath("index.json").read_text(encoding="utf-8"))


def help_article(article_id):
    article = next((a for a in help_index() if a["id"] == article_id), None)
    if article is None:
        return (
            "# Статья не найдена\n\nВыберите раздел слева или найдите нужное действие через поиск."
        )
    try:
        return files(PACKAGE).joinpath(article["file"]).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return "# Статья временно недоступна\n\nВыберите другой раздел слева."


class HelpCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск в справке: периоды, файлы, попытки…")
        self.search.setAccessibleName("Поиск в справке")
        layout.addWidget(self.search)
        row = QHBoxLayout()
        self.navigation = QListWidget()
        self.navigation.setMinimumWidth(210)
        self.navigation.setMaximumWidth(320)
        row.addWidget(self.navigation)
        self.content = QTextBrowser()
        self.content.setAccessibleName("Статья справки")
        self.content.setOpenExternalLinks(False)
        self.content.anchorClicked.connect(
            lambda url: self.open_article(url.path()) if url.scheme() == "help" else None
        )
        row.addWidget(self.content, 1)
        layout.addLayout(row)
        self.articles = help_index()
        self.search.textChanged.connect(self.filter)
        self.navigation.currentItemChanged.connect(
            lambda item, _: self.open_article(item.data(Qt.ItemDataRole.UserRole)) if item else None
        )
        self.filter("")

    def filter(self, query):
        self.navigation.blockSignals(True)
        self.navigation.clear()
        for article in self.articles:
            if (
                query.casefold()
                in (
                    article["title"] + " " + article["section"] + " " + help_article(article["id"])
                ).casefold()
            ):
                item = QListWidgetItem(article["section"] + " · " + article["title"])
                item.setData(Qt.ItemDataRole.UserRole, article["id"])
                self.navigation.addItem(item)
        self.navigation.blockSignals(False)
        if self.navigation.count():
            self.navigation.setCurrentRow(0)
        else:
            self.content.setMarkdown(
                "# Ничего не найдено\n\nПопробуйте другое слово или очистите поиск."
            )

    def open_article(self, article_id):
        self.current_article_id = article_id
        self.content.setMarkdown(help_article(article_id))


def open_help(owner, article_id):
    from studium.presentation.desktop.navigation import main_window

    window = main_window(owner)
    if window:
        window.open_help(article_id)
