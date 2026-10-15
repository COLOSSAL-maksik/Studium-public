"""Course-wide version editor and the independently saved group semester plan."""

import json
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.domain.enums import AssessmentType
from studium.domain.qa import score_text
from studium.domain.value_objects import UtcInstant
from studium.presentation.desktop.components import (
    confirm,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import FormDialog, date_value, instant_value
from studium.presentation.desktop.learning import CheckList
from studium.presentation.desktop.messages import ASSESSMENT_LABELS
from studium.presentation.desktop.models import TableModel, display_time
from studium.presentation.desktop.workflow_widgets import data_index


def spin(value, minimum=1, maximum=104):
    field = QSpinBox()
    field.setRange(minimum, maximum)
    field.setValue(value)
    return field


def choose(values, selected_value=None):
    field = QComboBox()
    for label, value in values:
        field.addItem(label, value)
        field.setItemData(field.count() - 1, label, Qt.ItemDataRole.ToolTipRole)
    index = data_index(field, selected_value)
    field.setCurrentIndex(max(0, index))
    return field


def history_text(snapshot_json):
    data = json.loads(snapshot_json)
    plan = data.get("plan", {})
    lines = [
        f"Начало учебных недель: {plan.get('first_week_start', '—')}",
        f"Учебных недель: {plan.get('weeks', '—')}",
        "",
        "Модули:",
    ]
    lines.extend(
        f"{m['title']}: недели {m['start_week']}–{m['end_week']}" for m in data.get("modules", [])
    )
    lines.extend(["", "Работы:"])
    lines.extend(
        f"{w['title']}: плановая выдача {w.get('issue_date') or '—'}; срок "
        + (
            str(w.get("due_date") or "—")
            if w.get("deadline_kind") != "EXACT_INCLUSIVE"
            else display_time(UtcInstant.from_epoch_microseconds(w["exact_due_at"]))
        )
        for w in data.get("works", [])
    )
    return "\n".join(lines)


class DirectionForm(FormDialog):
    def __init__(self, service, parent=None):
        super().__init__(
            "Направление подготовки", lambda values: service.create_direction(**values), parent
        )
        self.code = QLineEdit()
        self.name = QLineEdit()
        self.form.addRow("Код *", self.code)
        self.form.addRow("Название (необязательно)", self.name)

    def values(self):
        return {"code": self.code.text(), "name": self.name.text()}


class CourseVersionForm(FormDialog):
    def __init__(self, service, course, previous=None, parent=None):
        self.service, self.course, self.previous = service, course, previous
        super().__init__("Версия программы целого курса", self.save_version, parent)
        program = service.get_course_program(previous.course_program_id) if previous else None
        self.title = self.line("name", program.title if program else "", required=True)
        self.title.setReadOnly(previous is not None)
        self.label = QLineEdit()
        self.form.addRow("Обозначение версии", self.label)
        self.directions = CheckList()
        self.directions.setMinimumHeight(90)
        self.direction_ids = service.version_direction_ids(previous.id) if previous else ()
        self.refresh_directions()
        self.body_layout.addWidget(self.directions)
        toolbar(self.body_layout, [("+ Направление", self.add_direction)])
        hint(
            self.body_layout,
            "Назначенные версии сохраняются. Изменение создаёт следующую версию; группы выбирают её явно.",
        )
        self.tabs = QTabWidget()
        self.body_layout.addWidget(self.tabs, 1)
        self.modules = QTableWidget(0, 4)
        self.modules.setHorizontalHeaderLabels(["Модуль", "Семестр курса", "С недели", "По неделю"])
        self.tabs.addTab(self.modules, "Модули курса")
        self.works = QTableWidget(0, 2)
        self.works.setHorizontalHeaderLabels(["Работа из библиотеки", "Модуль курса"])
        self.tabs.addTab(self.works, "Содержание работ")
        self.module_keys = []
        data = json.loads(previous.content_json) if previous else {}
        self.source_data = data
        self.reference_lists = {}
        for field, label, values, legacy_name, target in (
            (
                "topic_ids",
                "Темы",
                service.list_course_topics(course.id),
                "program_topics",
                "topic_id",
            ),
            (
                "skill_ids",
                "Навыки",
                service.list_course_skills(course.id),
                "program_skills",
                "skill_id",
            ),
            (
                "seminar_material_ids",
                "Материалы",
                service.list_materials("seminars", course_id=course.id),
                "program_materials",
                "seminar_material_id",
            ),
            (
                "literature_item_ids",
                "Литература",
                service.list_materials("literature", course_id=course.id),
                "program_literature",
                "literature_item_id",
            ),
        ):
            selector = CheckList()
            selector.fill(
                [(str(value.id), value.title) for value in values],
                data.get(field, [row[target] for row in data.get(legacy_name, [])]),
            )
            self.reference_lists[field] = selector
            self.tabs.addTab(selector, label)
        for module in data.get("modules", []):
            self.add_module(module)
        for work in data.get("works", []):
            self.add_work(work)
        toolbar(
            self.body_layout,
            [
                ("+ Модуль", lambda: self.add_module()),
                ("+ Работа", lambda: self.add_work()),
                ("Убрать выбранное", self.remove_row),
            ],
        )
        self.modules.itemChanged.connect(lambda _: self.refresh_work_modules())
        self.resize(830, 650)

    def refresh_directions(self):
        self.directions.fill(
            [
                (d.id, d.code + (" — " + d.name if d.name else ""))
                for d in self.service.list_directions()
            ],
            self.direction_ids,
        )

    def add_direction(self):
        self.direction_ids = self.directions.selected_ids()
        if DirectionForm(self.service, self).exec():
            self.refresh_directions()

    def add_module(self, source=None):
        source = source or {}
        row = self.modules.rowCount()
        self.modules.insertRow(row)
        self.module_keys.append(source.get("key", source.get("id", str(uuid4()))))
        self.modules.setItem(row, 0, QTableWidgetItem(source.get("title", f"Модуль {row + 1}")))
        for column, value in enumerate(
            (
                source.get("course_semester") or 1,
                source.get("start_week", 1),
                source.get("end_week", 6),
            ),
            1,
        ):
            self.modules.setCellWidget(row, column, spin(value))
        self.refresh_work_modules()

    def refresh_work_modules(self):
        for row in range(self.works.rowCount()):
            field = self.works.cellWidget(row, 1)
            selected_value = field.currentData()
            field.blockSignals(True)
            field.clear()
            for index, key in enumerate(self.module_keys):
                item = self.modules.item(index, 0)
                if item:
                    field.addItem(item.text(), key)
            field.setCurrentIndex(max(0, data_index(field, selected_value)))
            field.blockSignals(False)

    def add_work(self, source=None):
        source = source or {}
        row = self.works.rowCount()
        self.works.insertRow(row)
        definitions = self.service.list_work_definitions(self.course.id)
        field = choose(
            [(f"{ASSESSMENT_LABELS[d.type]} · {d.title}", str(d.id)) for d in definitions],
            source.get("definition_id"),
        )
        self.works.setCellWidget(row, 0, field)
        self.works.setCellWidget(row, 1, QComboBox())
        self.refresh_work_modules()
        field = self.works.cellWidget(row, 1)
        field.setCurrentIndex(
            max(0, field.findData(source.get("module_key", source.get("module_id"))))
        )

    def remove_row(self):
        if self.tabs.currentIndex() > 1:
            return
        view = self.modules if self.tabs.currentIndex() == 0 else self.works
        row = view.currentRow()
        if row < 0:
            return
        if view is self.modules:
            key = self.module_keys[row]
            if any(
                self.works.cellWidget(i, 1).currentData() == key
                for i in range(self.works.rowCount())
            ):
                raise ValueError("Сначала уберите или переназначьте работы этого модуля")
            self.module_keys.pop(row)
        view.removeRow(row)
        self.refresh_work_modules()

    def values(self):
        modules = [
            {
                "key": self.module_keys[row],
                "title": self.modules.item(row, 0).text(),
                "course_semester": self.modules.cellWidget(row, 1).value(),
                "start_week": self.modules.cellWidget(row, 2).value(),
                "end_week": self.modules.cellWidget(row, 3).value(),
            }
            for row in range(self.modules.rowCount())
        ]
        by_key = {m["key"]: m for m in modules}
        works = []
        for row in range(self.works.rowCount()):
            definition, module = (
                self.works.cellWidget(row, 0).currentData(),
                self.works.cellWidget(row, 1).currentData(),
            )
            if definition is None or module not in by_key:
                raise ValueError("Выберите библиотечную работу и модуль")
            works.append(
                {
                    "definition_id": definition,
                    "module_key": module,
                    "course_semester": by_key[module]["course_semester"],
                }
            )
        return {
            "content": dict(self.source_data)
            | {"modules": modules, "works": works}
            | {
                field: list(selector.selected_ids())
                for field, selector in self.reference_lists.items()
            },
            "direction_ids": self.directions.selected_ids(),
            "label": self.label.text(),
        }

    def save_version(self, values):
        if self.previous:
            self.service.new_program_version(self.previous, **values)
        else:
            self.service.create_course_program(self.course.id, self.title.text(), **values)


class CourseProgramsWidget(QWidget):
    def __init__(self, window, course, parent=None):
        super().__init__(parent)
        self.window, self.course = window, course
        layout = QVBoxLayout(self)
        self.model = TableModel(
            [
                ("Учебная программа", lambda v: self.row_title(v)),
                (
                    "Состояние",
                    lambda v: (
                        "Черновик" if hasattr(v, "base_version_id") else f"Версия {v.version_no}"
                    ),
                ),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        toolbar(
            layout,
            [
                ("Создать учебную программу", lambda: run_action(self, self.create)),
                ("Открыть", lambda: run_action(self, self.next_version)),
                ("Импортировать", lambda: self.import_program()),
            ],
        )
        self.view.doubleClicked.connect(lambda _: run_action(self, self.next_version))
        self.empty = hint(
            layout, "Создайте годовую программу. Группы, студенты и календарь для этого не нужны."
        )
        self.refresh()

    def row_title(self, value):
        data = json.loads(value.content_json)
        passport = data.get("annual", {}).get("passport")
        return (
            passport["title"] + (" · " + passport["label"] if passport["label"] else "")
            if passport
            else self.names.get(value.id, "Прежняя программа")
        )

    def refresh(self):
        self.names = self.window.service.program_display_names(self.course.id)
        self.model.replace_rows(
            [
                *self.window.service.list_program_drafts(self.course.id),
                *self.window.service.program_versions(self.course.id),
            ]
        )
        self.empty.setVisible(not self.model.rows)

    def create(self):
        from studium.presentation.desktop.annual_program import ProgramEditor

        draft = self.window.service.create_program_draft(self.course.id)
        self.window.router.push(
            ProgramEditor(self.window, self.course, draft=draft), "Учебная программа"
        )

    def next_version(self):
        from studium.presentation.desktop.annual_program import ProgramEditor

        value = selected(self.view)
        if value:
            kwargs = {"draft": value} if hasattr(value, "base_version_id") else {"version": value}
            self.window.router.push(
                ProgramEditor(self.window, self.course, **kwargs), "Учебная программа"
            )

    def import_program(self):
        from studium.presentation.desktop.annual_program import import_program

        import_program(self.window, self.course)


class PlanSetupForm(FormDialog):
    def __init__(self, service, context, parent=None):
        super().__init__(
            "План семестра",
            lambda values: service.create_semester_plan(context.offering.id, **values),
            parent,
        )
        names = service.program_display_names(context.course.id)
        self.version = choose(
            [("Настроить без программы", None)]
            + [(names[v.id], v.id) for v in service.program_versions(context.course.id)]
        )
        self.ordinal = spin(1)
        self.first = self.day("starts_on", context.term.starts_on)
        self.weeks = spin(17)
        self.offset = spin(180, -840, 840)
        self.form.addRow("Версия содержания", self.version)
        self.form.addRow("Номер семестра в курсе (явное сопоставление)", self.ordinal)
        self.form.addRow("Учебных недель", self.weeks)
        self.form.addRow("UTC offset, минут (Москва +180)", self.offset)
        hint(
            self.body_layout,
            "Можно отменить и настроить позже. Само открытие формы ничего не создаёт.",
        )

    def values(self):
        return {
            "version_id": self.version.currentData(),
            "course_semester": self.ordinal.value() if self.version.currentData() else None,
            "first_week_start": date_value(self.first),
            "weeks": self.weeks.value(),
            "offset": self.offset.value(),
        }


class PlanContentForm(PlanSetupForm):
    def __init__(self, service, context, snapshot, parent=None):
        super().__init__(service, context, parent)
        self.service, self.context, self.snapshot = service, context, snapshot
        self.setWindowTitle("Переназначение содержания плана")
        for field in (self.first, self.weeks, self.offset):
            self.form.setRowVisible(field, False)
        self.mode = choose(
            [
                ("Сохранить все назначения и добавить содержание", "retain"),
                ("Заменить невыданные работы; выданные сохранить", "replace_unissued"),
            ]
        )
        self.form.addRow("Существующий план", self.mode)
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(180)
        self.body_layout.addWidget(self.preview_text)
        self.confirmed = QCheckBox(
            "Подтверждаю перечисленные изменения и сохранение прежних фактов"
        )
        self.confirmed.setEnabled(False)
        self.body_layout.addWidget(self.confirmed)
        self.preview = None
        self.save_button.setText("Показать последствия")
        self.version.currentIndexChanged.connect(self.clear_preview)
        self.ordinal.valueChanged.connect(self.clear_preview)
        self.mode.currentIndexChanged.connect(self.clear_preview)

    def clear_preview(self, *_):
        self.preview = None
        self.confirmed.setChecked(False)
        self.confirmed.setEnabled(False)
        self.preview_text.clear()
        self.save_button.setText("Показать последствия")

    def submit(self):
        from studium.presentation.desktop.components import error_message

        try:
            if self.preview is None:
                self.preview = self.service.preview_plan_content(
                    self.context.offering.id,
                    self.version.currentData(),
                    self.ordinal.value(),
                    expected_revision=self.snapshot.plan.revision,
                    mode=self.mode.currentData(),
                )
                p = self.preview
                lines = ["Сохранённые модули:"] + [
                    f"{m.title}: {m.start_week}–{m.end_week}" for m in p.retained_modules
                ]
                lines += ["Сохранённые работы:"] + [w.title for w in p.retained_works]
                lines += ["Архивируемые невыданные работы:"] + [w.title for w in p.retired_works]
                lines += ["Новые модули:"] + [
                    f"{m['title']}: {m['start_week']}–{m['end_week']}" for m in p.incoming_modules
                ]
                lines += [
                    f"Новых работ: {len(p.incoming_works)}",
                    f"Выдачи / попытки / сдачи / проверки / наборы обязательности: {' / '.join(map(str, p.facts))}",
                ]
                definition_names = {
                    d["id"]: d["title"]
                    for d in json.loads(
                        self.service.get_program_version(p.version_id).content_json
                    ).get("definitions", [])
                }
                lines += [
                    f"{definition_names.get(w['definition_id'], w.get('title', 'Работа'))} → модуль {w.get('module_key') or 'без модуля'}"
                    for w in p.incoming_works
                ]
                lines += list(p.warnings) + list(p.conflicts)
                self.preview_text.setPlainText("\n".join(lines))
                self.confirmed.setEnabled(not p.conflicts)
                self.save_button.setText("Применить подтверждённый пакет")
                return
            self.service.apply_plan_content(self.preview, confirmed=self.confirmed.isChecked())
            self.accept()
        except Exception as error:
            self.error_label.setText(
                str(error) if isinstance(error, ValueError) else error_message(error)
            )


class CalendarChangeForm(FormDialog):
    def __init__(self, service, context, snapshot, parent=None):
        self.service, self.context, self.snapshot = service, context, snapshot
        super().__init__("Календарь и перенос модулей", self.apply, parent)
        self.first = self.day("starts_on", snapshot.plan.first_week_start)
        self.weeks = spin(snapshot.plan.weeks)
        self.offset = spin(snapshot.plan.week_utc_offset_minutes, -840, 840)
        self.form.addRow("Учебных недель", self.weeks)
        self.form.addRow("UTC offset, минут", self.offset)
        self.reason = QLineEdit()
        self.form.addRow("Причина изменения", self.reason)
        self.modules = QTableWidget(len(snapshot.modules), 3)
        self.modules.setHorizontalHeaderLabels(["Модуль", "С недели", "По неделю"])
        for row, module in enumerate(snapshot.modules):
            self.modules.setItem(row, 0, QTableWidgetItem(module.title))
            self.modules.setCellWidget(row, 1, spin(module.start_week))
            self.modules.setCellWidget(row, 2, spin(module.end_week))
        self.body_layout.addWidget(self.modules)

    def values(self):
        changes = []
        for row, module in enumerate(self.snapshot.modules):
            values = {
                "title": self.modules.item(row, 0).text(),
                "start_week": self.modules.cellWidget(row, 1).value(),
                "end_week": self.modules.cellWidget(row, 2).value(),
            }
            if any(getattr(module, name) != value for name, value in values.items()):
                changes.append((module.id, module.revision, values))
        return {
            "plan_values": {
                "first_week_start": date_value(self.first),
                "weeks": self.weeks.value(),
                "week_utc_offset_minutes": self.offset.value(),
                "configured": True,
            },
            "module_changes": changes,
            "reason": self.reason.text(),
        }

    def apply(self, values):
        preview = self.service.preview_plan_change(self.context.offering.id, **values)
        apply_preview(self, self.service, preview)


def apply_preview(parent, service, preview):
    if preview.conflicts:
        raise ValueError("\n".join(preview.conflicts + preview.suggestions))
    description = "Изменения затронут:\n" + "\n".join(preview.affected or ("Календарь плана",))
    if preview.warnings:
        description += "\n\nПредупреждения:\n" + "\n".join(preview.warnings)
    description += "\n\nПрименить весь пакет? Предыдущий план сохранится в истории."
    if confirm(parent, description, action_label="Применить"):
        service.apply_plan_change(preview, confirmed=True)
    else:
        raise ValueError("Изменения отменены; план не изменён")


class PlannedWorkForm(FormDialog):
    def __init__(self, service, context, snapshot, original=None, parent=None):
        self.service, self.context, self.snapshot, self.original = (
            service,
            context,
            snapshot,
            original,
        )
        super().__init__("Работа и сроки", self.save_work, parent)
        self.title = self.line("name", original.title if original else "", required=True)
        self.number = QLineEdit(original.number if original else "")
        self.type = choose(
            [(label, value) for value, label in ASSESSMENT_LABELS.items()],
            original.type if original else AssessmentType.HOMEWORK,
        )
        self.module = choose(
            [("Без модуля", None)] + [(m.title, m.id) for m in snapshot.modules],
            original.module_id if original else None,
        )
        self.form.addRow("Номер", self.number)
        self.form.addRow("Тип", self.type)
        self.form.addRow("Модуль", self.module)
        self.type.setEnabled(original is None)
        self.issue = self.day("issued_at", original.issue_date if original else None)
        self.due = self.day("due_at", original.due_date if original else None)
        self.issue_enabled = QCheckBox("Плановая дата выдачи")
        self.due_enabled = QCheckBox("Новый срок по учебному дню")
        self.issue_enabled.setChecked(bool(original and original.issue_date))
        self.due_enabled.setChecked(
            bool(original and original.due_date and original.deadline_kind == "DATE_EXCLUSIVE")
        )
        for check, field in ((self.issue_enabled, self.issue), (self.due_enabled, self.due)):
            self.form.addRow(check)
            field.setEnabled(check.isChecked())
            check.toggled.connect(field.setEnabled)
        self.clear_deadline = QCheckBox("Явно убрать срок")
        if original:
            self.form.addRow(self.clear_deadline)
            self.clear_deadline.toggled.connect(
                lambda checked: self.due_enabled.setChecked(False) if checked else None
            )
            self.due_enabled.toggled.connect(
                lambda checked: self.clear_deadline.setChecked(False) if checked else None
            )
        self.minimum = QLineEdit(
            score_text(original.min_cents) if original and original.min_cents is not None else "0"
        )
        self.maximum = QLineEdit(
            score_text(original.max_cents) if original and original.max_cents is not None else "30"
        )
        if original is None:
            self.form.addRow("Минимальный начисляемый балл", self.minimum)
            self.form.addRow("Максимальный балл", self.maximum)
        else:
            hint(
                self.body_layout,
                "Существующий точный/недельный срок сохраняется, пока не выбран новый срок. Правила оценки меняются отдельно.",
            )
        self.reason = QLineEdit()
        self.form.addRow("Причина изменения", self.reason)

    def values(self):
        values = {
            "title": self.title.text(),
            "number": self.number.text(),
            "module_id": self.module.currentData(),
            "issue_date": date_value(self.issue) if self.issue_enabled.isChecked() else None,
        }
        if self.due_enabled.isChecked():
            values["due_date"] = date_value(self.due)
        elif (
            not self.original
            or self.clear_deadline.isChecked()
            or self.original.deadline_kind == "DATE_EXCLUSIVE"
        ):
            values["due_date"] = None
        return values

    def save_work(self, values):
        if self.original:
            preview = self.service.preview_plan_change(
                self.context.offering.id,
                work_changes=((self.original.id, self.original.revision, values),),
                reason=self.reason.text(),
            )
            apply_preview(self, self.service, preview)
        else:
            conflicts, warnings, suggestions = self.service.preview_new_planned_work(
                self.context.offering.id,
                values["title"],
                self.type.currentData(),
                minimum=self.minimum.text(),
                maximum=self.maximum.text(),
                **{k: v for k, v in values.items() if k != "title"},
            )
            if conflicts:
                raise ValueError("; ".join(conflicts))
            if warnings and not confirm(
                self,
                "Добавление работы:\n" + "\n".join(warnings) + "\nПодтвердить указанные сроки?",
                action_label="Подтвердить",
            ):
                raise ValueError("Добавление отменено")
            self.service.add_planned_work(
                self.context.offering.id,
                type=self.type.currentData(),
                minimum=self.minimum.text(),
                maximum=self.maximum.text(),
                confirmed=True,
                **values,
            )


class SemesterPlanWidget(QWidget):
    def __init__(self, window, context, parent=None):
        super().__init__(parent)
        self.window, self.context = window, context
        layout = QVBoxLayout(self)
        self.caption = hint(layout, "План семестра")
        toolbar(
            layout,
            [
                ("Настроить / календарь", lambda: run_action(self, self.configure)),
                ("+ Модуль", lambda: run_action(self, self.add_module)),
                ("+ Работа", lambda: run_action(self, self.add_work)),
                ("История плана", lambda: run_action(self, self.history)),
                ("Версия содержания", lambda: run_action(self, self.select_content)),
                ("Обязательные работы", lambda: run_action(self, self.required_works)),
            ],
        )
        self.model = TableModel(
            [
                ("Работа", lambda w: w.title),
                ("Тип", lambda w: ASSESSMENT_LABELS[w.type]),
                ("Содержание назначения", lambda w: self.source_names.get(w.id, "Неизвестно")),
                ("Плановая выдача", lambda w: str(w.issue_date or "—")),
                (
                    "Фактическая выдача",
                    lambda w: (
                        display_time(self.issued[w.id].actual_issued_at)
                        if w.id in self.issued and self.issued[w.id].actual_issued_at
                        else "Неизвестно"
                        if w.id in self.issued
                        else "Не выдано"
                    ),
                ),
                ("Первоначальный срок", self.original_due),
                (
                    "Текущий срок",
                    lambda w: (
                        display_time(w.exact_due_at)
                        if w.deadline_kind == "EXACT_INCLUSIVE"
                        else f"Неделя {w.due_week}"
                        if w.deadline_kind == "WEEK_ONLY"
                        else str(w.due_date or "—")
                    ),
                ),
                (
                    "Состояние",
                    lambda w: (
                        "Отменено"
                        if w.cancelled
                        else "Выдано"
                        if w.id in self.issued
                        else "Запланировано"
                    ),
                ),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.menu)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.edit_work))
        from studium.presentation.desktop.annual_plan_lessons import AnnualPlanLessons

        self.lesson_plan = AnnualPlanLessons(window.service, context, self)
        layout.addWidget(self.lesson_plan, 1)
        self.snapshot = None
        self.issued = {}
        self.source_names = {}

    def original_due(self, work):
        for history in self.snapshot.history if self.snapshot else ():
            data = json.loads(history.snapshot_json)
            for value in data.get("works", []):
                if value.get("id") == str(work.id):
                    if history.provenance == "migration_baseline":
                        return "Неизвестно (есть база миграции)"
                    return (
                        display_time(UtcInstant.from_epoch_microseconds(value["exact_due_at"]))
                        if value.get("exact_due_at")
                        else str(value.get("due_date") or "Не задан")
                    )
        return "Неизвестно"

    def refresh(self):
        context = self.context()
        self.snapshot = self.window.service.semester_plan(context.offering.id) if context else None
        self.issued = {i.planned_work_id: i for i in self.snapshot.issued} if self.snapshot else {}
        bindings = self.window.service.plan_content_bindings(context.offering.id) if context else ()
        self.source_names = {
            v.planned_work_id: (
                f"Версия {self.window.service.get_program_version(v.program_version_id).version_no}"
                if v.program_version_id
                else "Отдельное назначение"
            )
            + f" · семестр курса {v.course_semester or 'неизвестен'}"
            for v in bindings
            if v.planned_work_id
        }
        self.model.replace_rows(self.snapshot.works if self.snapshot else [])
        self.lesson_plan.refresh()
        self.caption.setText(
            "Настройте план семестра или отложите настройку. Открытие не создаёт записей."
            if not self.snapshot
            else f"{context.group.number} · {context.term.name} · {self.snapshot.plan.weeks} недель · "
            + "; ".join(f"{m.title}: {m.start_week}–{m.end_week}" for m in self.snapshot.modules)
        )

    def configure(self):
        context = self.context()
        if not context:
            return
        form = (
            CalendarChangeForm(self.window.service, context, self.snapshot, self)
            if self.snapshot
            else PlanSetupForm(self.window.service, context, self)
        )
        if form.exec():
            self.refresh()

    def add_module(self):
        if not self.snapshot:
            self.configure()
            return
        widget = self

        class Module(FormDialog):
            def __init__(self):
                super().__init__(
                    "Новый модуль",
                    lambda v: widget.window.service.add_plan_module(
                        widget.context().offering.id, **v
                    ),
                    widget,
                )
                self.title = self.line("name", required=True)
                self.first, self.last = (
                    spin(1, maximum=widget.snapshot.plan.weeks),
                    spin(6, maximum=widget.snapshot.plan.weeks),
                )
                self.form.addRow("С недели", self.first)
                self.form.addRow("По неделю", self.last)

            def values(self):
                return {
                    "title": self.title.text(),
                    "start_week": self.first.value(),
                    "end_week": self.last.value(),
                }

        if Module().exec():
            self.refresh()

    def select_content(self):
        if not self.snapshot:
            self.configure()
            return
        form = PlanContentForm(self.window.service, self.context(), self.snapshot, self)
        if form.exec():
            self.refresh()

    def required_works(self):
        from studium.presentation.desktop.qa_workflow import RequiredWorksForm

        if (
            self.snapshot
            and RequiredWorksForm(self.window.service, self.context(), self.snapshot, self).exec()
        ):
            self.refresh()

    def add_work(self):
        if not self.snapshot:
            self.configure()
            return
        if PlannedWorkForm(self.window.service, self.context(), self.snapshot, parent=self).exec():
            self.refresh()

    def edit_work(self):
        work = selected(self.view)
        if (
            work
            and PlannedWorkForm(
                self.window.service, self.context(), self.snapshot, work, self
            ).exec()
        ):
            self.refresh()

    def issue(self):
        work = selected(self.view)
        if work:
            widget = self

            class Issue(FormDialog):
                def __init__(self):
                    super().__init__(
                        "Фактическая выдача",
                        lambda values: widget.window.service.issue_planned_work(work.id, **values),
                        widget,
                    )
                    self.at = self.timestamp("issued_at")

                def values(self):
                    return {"actual_issued_at": instant_value(self.at)}

            if Issue().exec():
                self.refresh()

    def cancel(self):
        work = selected(self.view)
        if work:
            preview = self.window.service.preview_plan_change(
                self.context().offering.id,
                work_changes=((work.id, work.revision, {"cancelled": True}),),
                reason="Отмена работы; факты сохраняются",
            )
            apply_preview(self, self.window.service, preview)
            self.refresh()

    def menu(self, point):
        index = self.view.indexAt(point)
        if index.isValid():
            self.view.setCurrentIndex(index)
        if not selected(self.view):
            return
        menu = QMenu(self)
        for label, action in (
            ("Изменить сроки", self.edit_work),
            ("Выдать", self.issue),
            ("Отменить в плане", self.cancel),
        ):
            menu.addAction(label, lambda _=False, action=action: run_action(self, action))
        menu.exec(self.view.viewport().mapToGlobal(point))

    def history(self):
        if not self.snapshot:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Первый сохранённый и текущий план")
        layout = QVBoxLayout(dialog)
        model = TableModel(
            [
                ("Редакция", lambda h: h.plan_revision),
                ("Когда", lambda h: display_time(h.created_at)),
                ("Причина", lambda h: h.reason),
            ]
        )
        model.replace_rows(self.snapshot.history)
        view = table(model)
        layout.addWidget(view)
        # Readable snapshots keep both source/current values, without editing.
        from PySide6.QtWidgets import QPlainTextEdit

        detail = QPlainTextEdit()
        detail.setReadOnly(True)
        layout.addWidget(detail, 1)
        view.clicked.connect(
            lambda index: detail.setPlainText(history_text(model.rows[index.row()].snapshot_json))
        )
        dialog.resize(900, 620)
        dialog.exec()
