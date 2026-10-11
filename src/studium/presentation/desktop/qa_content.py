"""Exact topic selections and teacher-only structured answer snapshots."""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QInputDialog,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from studium.domain.qa import validate_answers
from studium.presentation.desktop.components import hint, run_action, toolbar


class TopicTreePicker(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.nodes = {}
        self.setMinimumHeight(140)

    def fill_topics(self, values, selected_ids=()):
        self.clear()
        self.nodes = {}
        selected = {str(id) for id in selected_ids}
        for topic in values:
            item = QTreeWidgetItem([topic.title + (" (в архиве)" if topic.deleted_at else "")])
            item.setData(0, Qt.ItemDataRole.UserRole, topic.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Checkboxes never propagate to parents or children.
            item.setCheckState(
                0, Qt.CheckState.Checked if str(topic.id) in selected else Qt.CheckState.Unchecked
            )
            self.nodes[topic.id] = item
        for topic in values:
            parent = self.nodes.get(topic.parent_topic_id)
            if parent:
                parent.addChild(self.nodes[topic.id])
            else:
                self.addTopLevelItem(self.nodes[topic.id])
        self.expandAll()

    def ids(self):
        return tuple(
            id for id, item in self.nodes.items() if item.checkState(0) == Qt.CheckState.Checked
        )

    def search(self, text):
        text = text.casefold().strip()
        shown = set()
        for item in self.nodes.values():
            if text in item.text(0).casefold():
                current = item
                while current:
                    shown.add(id(current))
                    current = current.parent()
        for item in self.nodes.values():
            item.setHidden(id(item) not in shown)
        if text:
            self.expandAll()


class StructuredAnswers(QWidget):
    COLUMNS = ("Название", "Обозначение", "Тип", "Значение", "Единицы", "Формула", "Комментарий")

    def __init__(self, service, details_json="{}", parent=None):
        super().__init__(parent)
        self.service = service
        self.source = json.loads(details_json)
        layout = QVBoxLayout(self)
        hint(
            layout,
            "Ответы преподавателя. Формулы и комментарии сохраняются как текст; единицы необязательны.",
        )
        self.templates = QComboBox()
        layout.addWidget(self.templates)
        toolbar(
            layout,
            [
                ("+ Ответ", lambda: self.add()),
                ("Убрать ответ", self.remove),
                ("Скопировать шаблон", lambda: run_action(self, self.use_template)),
                ("Сохранить как шаблон", lambda: run_action(self, self.save_template)),
                (
                    "Обновить шаблон",
                    lambda: run_action(self, lambda: self.save_template(update=True)),
                ),
            ],
        )
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.refresh_templates()
        for answer in self.source.get("structured_answers", []):
            self.add(answer)

    def refresh_templates(self):
        self.templates.clear()
        self.templates.addItem("Шаблон (по желанию)", None)
        for value in self.service.answer_templates():
            self.templates.addItem(value.title, value)

    def add(self, answer=None):
        answer = answer or {}
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, key in enumerate(
            ("name", "symbol", "kind", "value", "units", "formula", "comment")
        ):
            if key == "kind":
                field = QComboBox()
                field.addItem("Число", "numeric")
                field.addItem("Символическое", "symbolic")
                field.setCurrentIndex(max(0, field.findData(answer.get(key))))
                self.table.setCellWidget(row, column, field)
            else:
                self.table.setItem(row, column, QTableWidgetItem(str(answer.get(key, ""))))

    def remove(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def answers(self):
        values = []
        for row in range(self.table.rowCount()):
            value = {
                key: self.table.cellWidget(row, col).currentData()
                if key == "kind"
                else self.table.item(row, col).text().strip()
                for col, key in enumerate(
                    ("name", "symbol", "kind", "value", "units", "formula", "comment")
                )
            }
            values.append(value)
        validate_answers(values)
        return values

    def document(self):
        return json.dumps(self.source | {"structured_answers": self.answers()}, ensure_ascii=False)

    def use_template(self):
        template = self.templates.currentData()
        if template is None:
            return
        values = json.loads(template.schema_json)
        self.table.setRowCount(0)
        for answer in values:
            self.add(answer)
        self.source["answer_template_snapshot"] = {
            "id": str(template.id),
            "revision": template.revision,
            "title": template.title,
            "schema": values,
        }

    def save_template(self, update=False):
        values = self.answers()
        selected = self.templates.currentData()
        if update and selected is None:
            raise ValueError("Выберите шаблон")
        title, accepted = QInputDialog.getText(
            self, "Шаблон ответов", "Название", text=selected.title if selected else ""
        )
        if not accepted:
            return
        if update:
            self.service.update_answer_template(selected, title, values)
        else:
            self.service.create_answer_template(title, values)
        self.refresh_templates()
