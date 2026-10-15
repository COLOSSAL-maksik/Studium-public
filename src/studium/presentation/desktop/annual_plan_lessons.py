"""Minimum linked lesson planning, leaving factual lesson entry in its existing window."""

import json

from PySide6.QtWidgets import QVBoxLayout, QWidget

from studium.domain import annual_program as a
from studium.presentation.desktop.annual_forms import RowForm
from studium.presentation.desktop.annual_program import fill, readonly_table
from studium.presentation.desktop.components import hint, run_action, toolbar


class AnnualPlanLessons(QWidget):
    def __init__(self, service, context, parent=None):
        super().__init__(parent)
        self.service, self.context = service, context
        layout = QVBoxLayout(self)
        hint(layout, "Занятия: исходное содержание / текущее планирование / фактическое проведение")
        self.view = readonly_table(
            ["Вид", "Занятие", "Исходная неделя", "Текущая неделя", "Темы по плану", "Фактически"]
        )
        layout.addWidget(self.view)
        toolbar(
            layout,
            [
                ("Изменить планирование", lambda: run_action(self, self.edit)),
                ("Связать проведённое занятие", lambda: run_action(self, self.bind)),
            ],
        )
        self.rows = ()

    def refresh(self):
        context = self.context()
        self.rows = self.service.planned_program_lessons(context.offering.id) if context else ()
        topics = (
            {str(t.id): t.title for t in self.service.list_course_topics(context.course.id)}
            if context
            else {}
        )
        values = []
        for row in self.rows:
            before, current = json.loads(row.baseline_json), json.loads(row.current_json)
            actual, passed = self.service.actual_program_lesson_content(row)
            values.append(
                (
                    a.LESSON_KINDS[before["kind"]],
                    before["title"],
                    before.get("week"),
                    current.get("week"),
                    ", ".join(topics.get(id, "Тема недоступна") for id in current["topic_ids"]),
                    str(actual.lesson_date) + " · " + ", ".join(t.title for t in passed)
                    if actual
                    else "Не проведено",
                )
            )
        fill(self.view, values)

    def edit(self):
        index = self.view.currentRow()
        if index < 0:
            return
        original = self.rows[index]
        current = json.loads(original.current_json)
        form = RowForm(
            "Текущее планирование занятия", current, lambda value: self.save(original, value), self
        )
        form.integer("week", "Неделя рабочего плана", optional=True)
        form.topics(self.service, self.context().course.id)
        form.text("reason", "Причина изменения")
        form.exec()

    def save(self, original, value):
        self.service.update_program_plan_lesson(
            original, week=value["week"], topic_ids=value["topic_ids"], reason=value["reason"]
        )
        self.parentWidget().refresh()

    def bind(self):
        index = self.view.currentRow()
        if index < 0:
            return
        original = self.rows[index]
        form = RowForm(
            "Связать существующее проведённое занятие",
            {},
            lambda value: self.bind_value(original, value),
            self,
        )
        form.choice(
            "lesson_id",
            "Проведённое занятие",
            [
                (v.id, str(v.lesson_date) + " · " + v.title)
                for v in self.service.actual_program_lesson_choices(self.context().offering.id)
            ],
        )
        form.exec()

    def bind_value(self, original, value):
        self.service.bind_actual_program_lesson(original, value["lesson_id"])
        self.parentWidget().refresh()
