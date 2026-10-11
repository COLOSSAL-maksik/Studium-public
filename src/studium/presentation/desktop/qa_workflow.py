"""Evidence-backed submissions, immutable reviews, queue and module debts."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from studium.domain.enums import AssessmentType, AttemptResult, GradeKind
from studium.domain.qa import score_text
from studium.presentation.desktop.attachment_picker import StagedAttachmentPicker
from studium.presentation.desktop.background import BackgroundCall
from studium.presentation.desktop.components import (
    confirm,
    hint,
    run_action,
    selected,
    table,
    toolbar,
)
from studium.presentation.desktop.dialogs import FormDialog, HistoryDialog, combo, instant_value
from studium.presentation.desktop.files import FilesWidget
from studium.presentation.desktop.messages import ATTEMPT_LABELS, GRADE_LABELS
from studium.presentation.desktop.models import TableModel, display_time
from studium.presentation.desktop.navigation import present_detail
from studium.presentation.desktop.workflow_widgets import data_index


class AsyncForm(FormDialog):
    """Copy/hash outside the UI thread; cancellation is available before commit."""

    busy = False

    def submit(self):
        if self.busy:
            return
        try:
            values = self.values()
        except Exception as error:
            self.error_label.setText(str(error))
            return
        self.busy = True
        self.save_button.setEnabled(False)
        self.scroll.setEnabled(False)
        BackgroundCall(self, lambda: self.on_save(values), self.saved, self.failed)

    def saved(self, value):
        self.saved_value = value
        self.busy = False
        self.accept()

    def failed(self, error):
        from studium.presentation.desktop.components import error_message

        self.busy = False
        self.save_button.setEnabled(True)
        self.scroll.setEnabled(True)
        message = str(error) if isinstance(error, ValueError) else error_message(error)
        if "ACCEPTED" in message:
            message = "После доработки требуется явный зачёт работы. Выберите «Зачтено»."
        self.error_label.setText(message)

    def reject(self):
        if not self.busy:
            super().reject()


class SubmissionForm(AsyncForm):
    def __init__(self, service, student_id, *, assessment_id=None, parent=None):
        super().__init__("Зарегистрировать сдачу", self.save_submission, parent)
        self.service, self.student_id = service, student_id
        self.choices = service.student_submission_choices(student_id)
        self.work = QComboBox()
        for a, w, group, course, term in self.choices:
            self.work.addItem(
                f"{term.name} · {group.number} · {course.name} · {a.title}"
                + (" · архив" if a.deleted_at or w and w.deleted_at else ""),
                a.id,
            )
        if assessment_id:
            self.work.setCurrentIndex(data_index(self.work, assessment_id))
        self.form.addRow("Исходная работа и период", self.work)
        toolbar(
            self.body_layout,
            [
                (
                    "История выбранной работы / восстановление",
                    lambda: run_action(self, self.open_history),
                ),
                ("Восстановить исходный контекст", lambda: run_action(self, self.restore_context)),
            ],
        )
        self.received = self.timestamp("occurred_at")
        self.offset = QSpinBox()
        self.offset.setRange(-840, 840)
        self.offset.setValue(180)
        self.form.addRow("Часовой пояс SLA (UTC, минуты)", self.offset)
        self.comment = self.notes("comment")
        self.files = StagedAttachmentPicker(self)
        self.body_layout.addWidget(self.files)
        hint(
            self.body_layout,
            "Файлы и фактическая дата сохраняются вместе с новой сдачей. Отмена до сохранения не создаёт записей.",
        )

    def values(self):
        if self.work.currentData() is None:
            raise ValueError("Выберите исходную работу")
        return dict(
            assessment_id=self.work.currentData(),
            received_at=instant_value(self.received),
            paths=self.files.paths,
            comment=self.comment.toPlainText(),
            offset=self.offset.value(),
        )

    def open_history(self):
        selected_id = self.work.currentData()
        work = next((w for a, w, g, c, t in self.choices if a.id == selected_id), None)
        if work:
            SubmissionHistory(self.service, work.id, self).exec()
        else:
            self.error_label.setText("У выбранной работы пока нет истории этого студента")

    def save_submission(self, values):
        return self.service.register_student_submission(self.student_id, **values)

    def restore_context(self):
        from studium.presentation.desktop.components import confirm

        if (
            not self.busy
            and self.work.currentData()
            and confirm(
                self,
                "Восстановить исходный контекст выбранной работы? Завершённое участие и факты сохраняются; сдача будет зарегистрирована только отдельно.",
            )
        ):
            self.service.restore_student_submission_context(
                self.student_id,
                self.work.currentData(),
                confirmed=True,
                reason="Явное восстановление исходного контекста из регистрации сдачи",
            )


class RuleForm(FormDialog):
    def __init__(self, service, assessment_id, parent=None):
        super().__init__(
            "Новое правило баллов",
            lambda v: service.change_scoring_rule(assessment_id, **v),
            parent,
        )
        rule = service.current_rule(assessment_id)
        self.minimum, self.maximum = (
            QLineEdit(score_text(rule.min_cents) if rule else ""),
            QLineEdit(score_text(rule.max_cents) if rule else ""),
        )
        self.form.addRow("Минимум", self.minimum)
        self.form.addRow("Максимум", self.maximum)
        hint(
            self.body_layout,
            "Сохранённые проверки сохраняют своё правило. Для следующей проверки старой сдачи правило выбирается явно.",
        )

    def values(self):
        return dict(minimum=self.minimum.text(), maximum=self.maximum.text())


class ReviewForm(AsyncForm):
    def __init__(self, service, submission, assessment, sequence=0, parent=None):
        super().__init__(
            "Проверка сдачи",
            lambda v: service.review_submission(submission.id, expected_review_seq=sequence, **v),
            parent,
        )
        self.result_combo = combo(
            {
                k: v
                for k, v in ATTEMPT_LABELS.items()
                if k != AttemptResult.PRESENTED
                and not (k == AttemptResult.REJECTED and assessment.type == AssessmentType.HOMEWORK)
            },
            AttemptResult.ACCEPTED,
        )
        self.form.addRow("Результат проверки", self.result_combo)
        self.at = self.timestamp("occurred_at")
        current = service.current_rule(assessment.id)
        self.rule = QComboBox()
        self.rule.addItem(
            "Выберите правило"
            if current and submission.rule_id != current.id
            else "Правило сдачи / без баллов",
            None,
        )
        if submission.rule_id:
            bound = service.scoring_rule(submission.rule_id)
            self.rule.addItem(
                f"Правило сдачи: {score_text(bound.min_cents)}–{score_text(bound.max_cents)}",
                bound.id,
            )
        if current and current.id != submission.rule_id:
            self.rule.addItem(
                f"Текущее правило: {score_text(current.min_cents)}–{score_text(current.max_cents)}",
                current.id,
            )
        self.rule_required = bool(current and current.id != submission.rule_id)
        self.form.addRow("Правило оценивания", self.rule)
        if not service.fractional_scores_enabled():
            rules = [service.scoring_rule(submission.rule_id)] if submission.rule_id else []
            if current and current.id != submission.rule_id:
                rules.append(current)
            if any((r.min_cents + 99) // 100 > r.max_cents // 100 for r in rules):
                hint(
                    self.body_layout,
                    "В сохранённых границах нет целого балла. Для начисления включите дробные баллы или явно выберите новое правило; сохранённые границы не меняются.",
                )
        self.score = QLineEdit()
        self.score.setPlaceholderText("Точный балл; дробный ввод зависит от настройки")
        self.form.addRow("Балл (по желанию)", self.score)
        self.grade = combo({None: "Без отдельной оценки", **GRADE_LABELS})
        self.form.addRow("Вид оценки", self.grade)
        self.passed = QCheckBox("Зачтено")
        self.label = QLineEdit()
        self.form.addRow("Зачёт", self.passed)
        self.form.addRow("Традиционная оценка", self.label)
        self.comment = self.notes("comment")
        self.files = StagedAttachmentPicker(self)
        self.body_layout.addWidget(self.files)
        hint(
            self.body_layout,
            "Проверенные файлы преподавателя станут отдельными неизменяемыми копиями. SCORED после доработки требует явного принятия.",
        )
        self.grade.currentIndexChanged.connect(self.grade_changed)
        self.grade_changed()

    def grade_changed(self):
        self.passed.setVisible(self.grade.currentData() == GradeKind.PASS_FAIL)
        self.label.setVisible(self.grade.currentData() == GradeKind.TRADITIONAL)

    def values(self):
        if self.rule_required and self.rule.currentData() is None:
            raise ValueError("Явно выберите прежнее или текущее правило")
        return dict(
            result=self.result_combo.currentData(),
            reviewed_at=instant_value(self.at),
            score=self.score.text().strip() or None,
            rule_id=self.rule.currentData(),
            grade_kind=self.grade.currentData(),
            passed=self.passed.isChecked(),
            label=self.label.text(),
            comment=self.comment.toPlainText(),
            paths=self.files.paths,
        )


class SubmissionHistory(QDialog):
    def __init__(self, service, work_id, parent=None):
        super().__init__(parent)
        self.service, self.work_id = service, work_id
        history = service.history(work_id)
        self.assessment, self.student = history.assessment, history.student
        self.setWindowTitle(history.assessment.title + " · сдачи и проверки")
        self.resize(940, 670)
        layout = QVBoxLayout(self)
        self.summary = hint(layout, "")
        toolbar(
            layout,
            [
                ("+ Зарегистрировать сдачу", self.add_submission),
                ("Проверить / перепроверить", self.review),
                ("Записать возврат", self.returned),
                ("Правило баллов", self.rule),
                ("Восстановить архивный контекст", self.restore),
                ("Исторические попытки", self.legacy),
                ("Результаты задач сдачи", self.item_results),
            ],
        )
        self.model = TableModel(
            [
                ("Сдача", lambda r: f"№{r[1].attempt_no} · {display_time(r[0].received_at)}"),
                ("Записана", lambda r: display_time(r[0].created_at)),
                ("Проверка", lambda r: ATTEMPT_LABELS[r[2].result] if r[2] else "Ожидает проверки"),
                (
                    "Балл / максимум",
                    lambda r: (
                        score_text(r[2].score_cents) + " / " + score_text(r[2].max_cents)
                        if r[2]
                        else "—"
                    ),
                ),
                ("Проверено", lambda r: display_time(r[2].reviewed_at) if r[2] else "—"),
                ("Возвращено", lambda r: ", ".join(display_time(v.returned_at) for v in r[5])),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        self.tabs = QTabWidget()
        self.files = FilesWidget(
            service, editable=False, asynchronous=True, compact=True, parent=self
        )
        self.tabs.addTab(self.files, "Оригиналы студента")
        teachers = QWidget()
        body = QVBoxLayout(teachers)
        self.teacher_model = TableModel(
            [("Проверенный файл преподавателя", lambda row: row[1].original_filename)]
        )
        self.teacher_view = table(self.teacher_model)
        body.addWidget(self.teacher_view)
        toolbar(
            body,
            [
                ("Предпросмотр", self.preview_teacher),
                ("Редактировать рабочую копию", self.edit_teacher),
                ("Копия оригинала студента", self.edit_original),
            ],
        )
        self.tabs.addTab(teachers, "Файлы преподавателя")
        layout.addWidget(self.tabs, 1)
        self.view.selectionModel().currentChanged.connect(lambda *_: run_action(self, self.select))
        self.view.doubleClicked.connect(lambda _: run_action(self, self.review))
        self.refresh()

    def refresh(self):
        rows = []
        self.sequences = {}
        for submission, attempt, reviews in self.service.submission_history(self.work_id):
            self.sequences[submission.id] = max((r[0].review_seq for r in reviews), default=0)
            rows.extend(
                (submission, attempt, review, grade, files, returns)
                for review, grade, files, returns in reviews
            )
            if not reviews:
                rows.append((submission, attempt, None, None, (), ()))
        self.model.replace_rows(rows)
        result = self.service.work_result(self.work_id)
        from studium.presentation.desktop.messages import STATUS_LABELS

        self.summary.setText(
            self.student.full_name
            + " · "
            + STATUS_LABELS[result.status]
            + " · "
            + (
                score_text(result.score)
                if result.exact
                else str(result.score if result.score is not None else "—")
            )
        )
        if rows:
            self.view.selectRow(len(rows) - 1)
        else:
            self.files.set_attempt(None)
            self.teacher_model.replace_rows([])

    def select(self):
        row = selected(self.view)
        self.files.set_attempt(row[1] if row else None)
        self.teacher_model.replace_rows(
            [
                (link, self.service.get_file_asset(link.file_asset_id, include_deleted=True))
                for link in row[4]
            ]
            if row
            else []
        )

    def add_submission(self):
        if SubmissionForm(
            self.service, self.student.id, assessment_id=self.assessment.id, parent=self
        ).exec():
            self.refresh()

    def review(self):
        row = selected(self.view)
        if (
            row
            and ReviewForm(
                self.service, row[0], self.assessment, self.sequences[row[0].id], self
            ).exec()
        ):
            self.refresh()

    def returned(self):
        row = selected(self.view)
        if not row or not row[2]:
            return
        service, review = self.service, row[2]

        class Return(FormDialog):
            def __init__(self):
                super().__init__(
                    "Возврат проверенной работы",
                    lambda v: service.record_review_return(review.id, **v),
                )
                self.at = self.timestamp("occurred_at")
                self.comment = self.notes("comment")

            def values(self):
                return dict(returned_at=instant_value(self.at), comment=self.comment.toPlainText())

        if Return().exec():
            self.refresh()

    def rule(self):
        if RuleForm(self.service, self.assessment.id, self).exec():
            self.refresh()

    def restore(self):
        if confirm(
            self,
            "Восстановить исходную работу, студента, группу, дисциплину и период? История участия и факты сохраняются.",
        ):
            self.service.restore_debt_context(
                self.work_id, confirmed=True, reason="Восстановление из истории долга"
            )
            self.refresh()

    def legacy(self):
        return present_detail(
            HistoryDialog(self.service, self.work_id, editable=False, parent=self),
            self,
            title="Исторические попытки",
        )

    def item_results(self):
        row = selected(self.view)
        if row:
            from studium.presentation.desktop.analytics import AttemptItemsWidget

            page = QDialog(self)
            page.setWindowTitle("Результаты задач сдачи")
            body = QVBoxLayout(page)
            widget = AttemptItemsWidget(
                self.service, self.assessment.id, editable=True, parent=page
            )
            widget.set_attempt(row[1])
            body.addWidget(widget)
            present_detail(
                page, self, title=f"Попытка {row[1].attempt_no} · задачи", refresh=self.refresh
            )

    def preview_teacher(self):
        row = selected(self.teacher_view)
        if row:
            picker = StagedAttachmentPicker(self)
            picker.add_paths([self.service.accessible_file_path(row[1].id)])
            picker.list.setCurrentRow(0)
            picker.preview()

    def edit_teacher(self):
        row = selected(self.teacher_view)
        if row:
            run_action(self, lambda: self.service.open_working_copy(row[1].id))

    def edit_original(self):
        row = selected(self.files.view)
        if row:
            run_action(self, lambda: self.service.open_working_copy(row.asset.id))


class ReviewQueue(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        layout = QVBoxLayout(self)
        self.summary = hint(layout, "Очередь сдач всех групп")
        self.history = QCheckBox("Показать проверенные сдачи")
        layout.addWidget(self.history)
        self.history.toggled.connect(lambda _: self.refresh())
        toolbar(
            layout,
            [("Обновить", self.refresh), ("Открыть сдачу", lambda: run_action(self, self.open))],
        )
        self.model = TableModel(
            [
                ("Студент", lambda r: r.student.full_name),
                ("Группа / дисциплина", lambda r: r.group.number + " · " + r.course.name),
                ("Работа", lambda r: r.assessment.title),
                ("Тип", lambda r: "ДЗ" if r.assessment.type == AssessmentType.HOMEWORK else "РК"),
                ("Попытка", lambda r: r.attempt.attempt_no),
                ("Получено", lambda r: display_time(r.submission.received_at)),
                ("Записано", lambda r: display_time(r.submission.created_at)),
                ("Срок проверки", lambda r: display_time(r.deadline)),
                ("Ожидание", self.waiting_time),
                (
                    "Состояние",
                    lambda r: (
                        ATTEMPT_LABELS[r.result]
                        if r.reviewed
                        else {
                            "waiting": "Ожидает",
                            "near_due": "Срок близко",
                            "overdue": "Просрочено",
                            "unknown": "Время неизвестно",
                        }[r.state]
                    ),
                ),
                ("Файлы", lambda r: r.file_count),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))
        self.generation = 0

    @staticmethod
    def waiting_time(row):
        from studium.domain.value_objects import UtcInstant

        seconds = max(
            0, int((UtcInstant.now().value - row.submission.received_at.value).total_seconds())
        )
        return f"{seconds // 86400} д {seconds % 86400 // 3600} ч"

    def refresh(self):
        self.generation += 1
        generation = self.generation
        include = self.history.isChecked()

        def loaded(rows):
            if generation != self.generation:
                return
            self.model.replace_rows(rows)
            self.summary.setText(
                f"Сдач: {len(rows)} · Срок близко: {sum(r.state == 'near_due' and not r.reviewed for r in rows)} · Просрочено: {sum(r.state == 'overdue' and not r.reviewed for r in rows)}"
            )

        BackgroundCall(
            self,
            lambda: self.service.review_queue(include_reviewed=include),
            loaded,
            lambda e: self.summary.setText(str(e)),
        )

    def open(self):
        row = selected(self.view)
        if row:
            present_detail(
                SubmissionHistory(self.service, row.work.id, self),
                self,
                refresh=self.refresh,
                title=row.assessment.title,
            )


class RequiredWorksForm(FormDialog):
    def __init__(self, service, context, snapshot, parent=None):
        super().__init__("Обязательные работы студента", self.save_set, parent)
        from studium.presentation.desktop.learning import CheckList

        self.service = service
        self.module, self.student = QComboBox(), QComboBox()
        for module in snapshot.modules:
            self.module.addItem(module.title, module.id)
        for entry in service.list_students_for_offering(context.offering.id, include_ended=True):
            self.student.addItem(entry.student.full_name, entry.student.id)
        self.form.addRow("Модуль", self.module)
        self.form.addRow("Студент", self.student)
        self.works = CheckList()
        self.body_layout.addWidget(self.works)
        self.reason = self.line("comment", required=True)
        self.module.currentIndexChanged.connect(lambda _: self.load())
        self.student.currentIndexChanged.connect(lambda _: self.load())
        hint(
            self.body_layout,
            "Модуль закрывается только после явного зачёта каждой выбранной работы. Отсутствие списка показывается как неизвестное требование.",
        )
        self.load()

    def load(self):
        if self.module.currentData() and self.student.currentData():
            works, selected_ids = self.service.module_required_choices(
                self.module.currentData(), self.student.currentData()
            )
            self.works.fill([(a.id, a.title) for a in works], selected_ids)

    def values(self):
        return dict(
            module_id=self.module.currentData(),
            student_id=self.student.currentData(),
            assessment_ids=self.works.ids(),
            reason=self.reason.text(),
        )

    def save_set(self, values):
        if not values["module_id"] or not values["student_id"]:
            raise ValueError("Выберите модуль и студента")
        return self.service.set_required_assessments(**values)


class PackageSummary(QWidget):
    def __init__(self, service, student_id, parent=None, *, on_section=None):
        super().__init__(parent)
        self.service, self.student_id = service, student_id
        layout = QVBoxLayout(self)
        self.caption = hint(layout, "")
        from studium.presentation.desktop.messages import ASSESSMENT_LABELS

        self.model = TableModel(
            [
                ("Период / группа / дисциплина", lambda r: r[1]),
                ("Категория", lambda r: ASSESSMENT_LABELS[r[2]]),
                ("Всего выдано (активных)", lambda r: r.total),
                ("Выполнено / выдано", lambda r: f"{r[3]} / {r[5]}"),
                ("Зачтено / выдано", lambda r: f"{r[4]} / {r[5]}"),
                ("Не выдано", lambda r: r[6]),
                ("Отменено", lambda r: r[7]),
                ("На доработке", lambda r: r.revision_required),
                ("Ожидают проверки", lambda r: r.awaiting_review),
                ("Не сдано в срок", lambda r: r.not_submitted_in_time),
                (
                    "Фактические баллы",
                    lambda r: "; ".join(f"{title}: {score}" for _, title, score in r.scores) or "—",
                ),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view, 1)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open_category))
        toolbar(
            layout,
            [
                ("Открыть работы", lambda: run_action(self, self.open_category)),
                ("+ Зарегистрировать сдачу", self.submission),
            ],
        )
        if on_section:
            toolbar(
                layout,
                [
                    ("Факты тем и навыков", lambda: on_section("evidence")),
                    ("Графики", lambda: on_section("charts")),
                ],
            )
        hint(layout, "Долги модулей всех периодов")
        self.debts = TableModel(
            [
                (
                    "Период / модуль",
                    lambda r: self.context_names.get(r.offering_id, "") + " · " + r.module.title,
                ),
                (
                    "Состояние",
                    lambda r: {
                        "unknown": "Требования не определены",
                        "open": "Не закрыт",
                        "closed": "Закрыт",
                    }[r.state],
                ),
                (
                    "Долги / обязательные",
                    lambda r: (
                        f"{len(r.debt_works)} / {len(r.required_works)}"
                        if r.required_set_id
                        else "—"
                    ),
                ),
            ]
        )
        self.debt_view = table(self.debts)
        layout.addWidget(self.debt_view, 1)
        self.debt_view.doubleClicked.connect(lambda _: run_action(self, self.open_debt))

    def refresh(self):
        rows, attendance = self.service.student_package_summary(self.student_id)
        self.context_names = {row[0]: row[1] for row in rows}
        self.model.replace_rows(rows)
        self.caption.setText(
            f"Занятий: {attendance.lessons} · Посещено: {attendance.attended} · Пропущено: {attendance.absent}"
            f" · Опоздания: {attendance.late} · Уважительные причины: {attendance.excused}"
            f" · Неизвестно: {attendance.unknown} · Без отметки: {attendance.unmarked}\n"
            + (
                f"Доля посещённых: {attendance.attended} / {attendance.denominator} = {attendance.rate:.1%}"
                if attendance.rate is not None
                else "Доля посещённых: нет данных"
            )
        )
        self.debts.replace_rows(self.service.student_module_results(self.student_id))

    def submission(self):
        if SubmissionForm(self.service, self.student_id, parent=self).exec():
            self.refresh()

    def open_category(self):
        row = selected(self.view)
        if not row:
            return
        present_detail(
            WorkDrilldown(self.service, self.student_id, self, offering_id=row[0], kind=row[2]),
            self,
            refresh=self.refresh,
            title="Работы · " + row[1],
        )

    def open_debt(self):
        row = selected(self.debt_view)
        if row and row.required_works:
            present_detail(
                WorkDrilldown(self.service, self.student_id, self, work_ids=row.required_works),
                self,
                refresh=self.refresh,
                title="Обязательные работы · " + row.module.title,
            )


class WorkDrilldown(QDialog):
    def __init__(self, service, student_id, parent=None, **filters):
        super().__init__(parent)
        self.service, self.student_id, self.filters = service, student_id, filters
        self.setWindowTitle("Работы студента")
        self.resize(850, 520)
        layout = QVBoxLayout(self)
        toolbar(
            layout,
            [
                ("История и проверка", lambda: run_action(self, self.open)),
                ("+ Зарегистрировать сдачу", self.submission),
            ],
        )
        from studium.presentation.desktop.messages import STATUS_LABELS

        self.model = TableModel(
            [
                ("Исходный период", lambda r: r[2]),
                ("Работа", lambda r: r[0].title),
                ("Состояние", lambda r: STATUS_LABELS[r[3].status] if r[3] else "Нет сдач"),
                (
                    "Балл",
                    lambda r: (
                        score_text(r[3].score)
                        if r[3] and r[3].exact
                        else str(r[3].score)
                        if r[3] and r[3].score is not None
                        else "—"
                    ),
                ),
                ("Архив", lambda r: "Да" if r[0].deleted_at or r[1] and r[1].deleted_at else "—"),
            ]
        )
        self.view = table(self.model)
        layout.addWidget(self.view)
        self.view.doubleClicked.connect(lambda _: run_action(self, self.open))
        self.refresh()

    def refresh(self):
        self.model.replace_rows(self.service.student_work_details(self.student_id, **self.filters))

    def open(self):
        row = selected(self.view)
        if row and row[1]:
            present_detail(
                SubmissionHistory(self.service, row[1].id, self),
                self,
                refresh=self.refresh,
                title=row[0].title,
            )

    def submission(self):
        row = selected(self.view)
        if (
            row
            and SubmissionForm(
                self.service, self.student_id, assessment_id=row[0].id, parent=self
            ).exec()
        ):
            self.refresh()
